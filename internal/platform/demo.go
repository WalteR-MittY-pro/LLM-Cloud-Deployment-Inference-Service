package platform

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// Deterministic protocol fixture. Numbers in the usage event are synthetic.
func Demo(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Model  string `json:"model"`
		Stream bool   `json:"stream"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || !req.Stream || req.Model != "lab-model" {
		http.Error(w, "expected lab-model and stream=true", 400)
		return
	}
	f, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming unavailable", 500)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	frames := []string{
		`{"choices":[{"delta":{"role":"assistant"}}]}`,
		`{"choices":[{"delta":{"content":"云"}}]}`,
		`{"choices":[{"delta":{"content":"服务"}}]}`,
		`{"choices":[],"usage":{"prompt_tokens":8,"completion_tokens":2}}`,
		"[DONE]",
	}
	for i, frame := range frames {
		if i > 0 {
			select {
			case <-r.Context().Done():
				return
			case <-time.After(150 * time.Millisecond):
			}
		}
		if _, err := fmt.Fprintf(w, "data: %s\n\n", frame); err != nil {
			return
		}
		f.Flush()
	}
}
