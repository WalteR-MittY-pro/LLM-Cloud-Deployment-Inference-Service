//go:build practice

package platform

import (
	"bufio"
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

const role = "data: {\"choices\":[{\"delta\":{\"role\":\"assistant\"}}]}\n\n"
const word = "data: {\"choices\":[{\"delta\":{\"content\":\"云\"}}]}\n\n"
const usage = "data: {\"choices\":[],\"usage\":{\"prompt_tokens\":8,\"completion_tokens\":1}}\n\n"

func TestDay1Complete(t *testing.T) {
	w := httptest.NewRecorder()
	body := role + word + usage + "data: [DONE]\n\n"
	stats, err := Relay(context.Background(), w, strings.NewReader(body))
	if err != nil || !w.Flushed || w.Body.String() != body || !stats.Completed || stats.FirstContent.IsZero() || stats.OutputTokens == nil || *stats.OutputTokens != 1 {
		t.Fatalf("%+v %v output=%q", stats, err, w.Body.String())
	}
}
func TestDay1Truncated(t *testing.T) {
	stats, err := Relay(context.Background(), httptest.NewRecorder(), strings.NewReader(role))
	if err == nil || errors.Is(err, ErrExercise) || stats.Completed || !stats.FirstContent.IsZero() || stats.OutputTokens != nil {
		t.Fatalf("%+v %v", stats, err)
	}
}

// The source sends its second event only after the client sees the first frame.
// An implementation that reads to EOF before flushing cannot pass.
func TestDay1Progressive(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	resume := make(chan struct{})
	s := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		pr, pw := io.Pipe()
		defer pr.Close()
		go func() {
			defer pw.Close()
			_, _ = io.WriteString(pw, word)
			select {
			case <-resume:
				_, _ = io.WriteString(pw, "data: [DONE]\n\n")
			case <-ctx.Done():
			}
		}()
		_, _ = Relay(r.Context(), w, pr)
	}))
	defer s.Close()
	req, _ := http.NewRequestWithContext(ctx, "GET", s.URL, nil)
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	line, err := bufio.NewReader(res.Body).ReadString('\n')
	if err != nil || !strings.Contains(line, "云") {
		t.Fatalf("first frame=%q err=%v", line, err)
	}
	close(resume)
}
