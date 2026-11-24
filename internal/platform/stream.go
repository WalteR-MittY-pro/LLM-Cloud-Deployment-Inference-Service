package platform

import (
	"context"
	"errors"
	"io"
	"net/http"
	"time"
)

var ErrExercise = errors.New("learner TODO")

type StreamStats struct {
	FirstContent               time.Time
	Completed                  bool // Only a terminal [DONE] confirms a complete OpenAI-compatible stream.
	PromptTokens, OutputTokens *int // nil means unknown; a disconnected stream may have no usage event.
}

func Relay(ctx context.Context, dst http.ResponseWriter, src io.Reader) (StreamStats, error) {
	// Day 1. Forward SSE frames as they arrive. Preserve data and event boundaries.
	// Record the first non-empty delta.content, optional usage, and the terminal marker.
	// A role-only delta, an empty line or a chunk boundary is not an output token.
	// Return partial stats on cancellation, short stream or write failure.
	return StreamStats{}, ErrExercise
}
