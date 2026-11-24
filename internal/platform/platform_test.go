package platform

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestDemoProtocol(t *testing.T) {
	r := httptest.NewRequest("POST", "/v1/chat/completions", strings.NewReader(`{"model":"lab-model","stream":true}`))
	w := httptest.NewRecorder()
	Demo(w, r)
	if w.Code != 200 || !w.Flushed || !strings.Contains(w.Body.String(), "[DONE]") || !strings.Contains(w.Body.String(), "completion_tokens") {
		t.Fatalf("incomplete fixture: %s", w.Body)
	}
}
func TestGatewayRejectsInvalidInput(t *testing.T) {
	r := httptest.NewRequest("POST", "/v1/chat/completions", strings.NewReader(`{"model":"lab-model"}`))
	w := httptest.NewRecorder()
	(&Gateway{}).Chat(w, r)
	if w.Code != 400 {
		t.Fatal(w.Code)
	}
}
func TestControlRequiresToken(t *testing.T) {
	h := Control(Store{}, "secret")
	r := httptest.NewRequest("GET", "/workers/n/desired", nil)
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != 401 {
		t.Fatal(w.Code)
	}
}
func TestGatewayRelaysUpstreamFailure(t *testing.T) {
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { http.Error(w, "busy", 503) }))
	defer up.Close()
	g := Gateway{DevelopmentUpstream: up.URL}
	w := httptest.NewRecorder()
	g.Chat(w, httptest.NewRequest("POST", "/", strings.NewReader(`{"model":"lab-model","stream":true}`)))
	if w.Code != 503 || w.Header().Get("X-Request-ID") == "" {
		t.Fatal(w.Code)
	}
}
func TestDevRoute(t *testing.T) {
	d, err := (&Gateway{DevelopmentUpstream: "http://local"}).Admit(context.Background(), "", "lab-model")
	if err != nil || d.Upstream != "http://local" {
		t.Fatal(d, err)
	}
}
