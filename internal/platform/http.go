package platform

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"
)

func failure(w http.ResponseWriter, err error) {
	code := 500
	switch {
	case errors.Is(err, ErrExercise):
		code = 501
	case errors.Is(err, ErrDenied):
		code = 401
	case errors.Is(err, ErrQuota):
		code = 429
	case errors.Is(err, ErrCapacity):
		code = 503
	}
	http.Error(w, http.StatusText(code), code)
}
func (g *Gateway) Chat(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	var rid [16]byte
	if _, err := rand.Read(rid[:]); err != nil {
		failure(w, err)
		return
	}
	id := hex.EncodeToString(rid[:])
	w.Header().Set("X-Request-ID", id)
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, 2<<20))
	if err != nil {
		http.Error(w, "invalid body", 400)
		return
	}
	var meta struct {
		Model  string
		Stream bool
	}
	if json.Unmarshal(body, &meta) != nil || meta.Model == "" || !meta.Stream {
		http.Error(w, "expected model and stream=true", 400)
		return
	}
	key, _ := strings.CutPrefix(r.Header.Get("Authorization"), "Bearer ")
	if !strings.HasPrefix(r.Header.Get("Authorization"), "Bearer ") {
		key = ""
	}
	choice, err := g.Admit(r.Context(), key, meta.Model)
	if err != nil {
		failure(w, err)
		return
	}
	result := Outcome{ID: id, Tenant: choice.Tenant, Started: start}
	defer func() {
		result.Finished = time.Now()
		log.Printf("request=%s status=%d completed=%t elapsed=%s error=%q", id, result.Status, result.Stream.Completed, result.Finished.Sub(start), result.Failure)
		if g.DevelopmentUpstream == "" {
			ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
			defer cancel()
			if err := g.Store.Record(ctx, result); err != nil {
				log.Printf("accounting request=%s: %v", id, err)
			}
		}
	}()
	req, err := http.NewRequestWithContext(r.Context(), "POST", strings.TrimRight(choice.Upstream, "/")+"/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		result.Status = 500
		failure(w, err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Request-ID", id)
	upstream, err := http.DefaultClient.Do(req)
	if err != nil {
		result.Status = 502
		result.Failure = err.Error()
		http.Error(w, "upstream unavailable", 502)
		return
	}
	defer upstream.Body.Close()
	result.Status = upstream.StatusCode
	if upstream.StatusCode != 200 {
		http.Error(w, "upstream: "+upstream.Status, upstream.StatusCode)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	result.Stream, err = Relay(r.Context(), w, upstream.Body)
	if err != nil {
		result.Failure = err.Error()
		if errors.Is(err, ErrExercise) {
			result.Status = 501
			failure(w, err)
		}
		// Once a stream starts, its HTTP status cannot be changed. Clients must check [DONE].
	}
}
func Control(s Store, token string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /admin/deployments", func(w http.ResponseWriter, r *http.Request) {
		var in struct{ ID, Model string }
		if !input(w, r, &in) {
			return
		}
		if in.ID == "" || in.Model == "" {
			http.Error(w, "missing ID or model", 400)
			return
		}
		v, err := s.Publish(r.Context(), in.ID, in.Model)
		respond(w, v, err)
	})
	mux.HandleFunc("POST /workers/heartbeat", func(w http.ResponseWriter, r *http.Request) {
		var h Heartbeat
		if !input(w, r, &h) {
			return
		}
		respond(w, map[string]string{"node": h.Node}, s.Observe(r.Context(), h))
	})
	mux.HandleFunc("GET /workers/{node}/desired", func(w http.ResponseWriter, r *http.Request) {
		v, err := s.Desired(r.Context(), r.PathValue("node"))
		respond(w, v, err)
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if token == "" || subtle.ConstantTimeCompare([]byte(r.Header.Get("Authorization")), []byte("Bearer "+token)) != 1 {
			http.Error(w, "unauthorized", 401)
			return
		}
		mux.ServeHTTP(w, r)
	})
}
func input(w http.ResponseWriter, r *http.Request, v any) bool {
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(v); err != nil {
		http.Error(w, "invalid JSON", 400)
		return false
	}
	return true
}
func respond(w http.ResponseWriter, v any, err error) {
	if err != nil {
		failure(w, err)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(v)
}
func WorkerTick(ctx context.Context, base, token, node string) error {
	call := func(method, path string, in, out any) error {
		var body io.Reader
		if in != nil {
			b, err := json.Marshal(in)
			if err != nil {
				return err
			}
			body = bytes.NewReader(b)
		}
		req, err := http.NewRequestWithContext(ctx, method, strings.TrimRight(base, "/")+path, body)
		if err != nil {
			return err
		}
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Content-Type", "application/json")
		res, err := http.DefaultClient.Do(req)
		if err != nil {
			return err
		}
		defer res.Body.Close()
		if res.StatusCode != 200 {
			return fmt.Errorf("%s %s: %s", method, path, res.Status)
		}
		if out != nil {
			return json.NewDecoder(res.Body).Decode(out)
		}
		return nil
	}
	var desired []Deployment
	if err := call("GET", "/workers/"+node+"/desired", nil, &desired); err != nil {
		return err
	}
	report, err := Reconcile(ctx, node, desired)
	if err != nil {
		return err
	}
	return call("POST", "/workers/heartbeat", report, nil)
}
