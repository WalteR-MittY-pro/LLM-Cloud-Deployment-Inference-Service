package platform

import (
	"context"
	"database/sql"
	"errors"
	"time"
)

// A catalog entry is configured by the operator. Tenants can only request inference.
type Deployment struct{ ID, Model, Node, GPU, Endpoint, Phase string }
type Heartbeat struct {
	Node     string
	GPUs     []string
	Replicas []Deployment
}
type Decision struct{ Tenant, Upstream string }
type Outcome struct {
	ID, Tenant        string
	Started, Finished time.Time
	Stream            StreamStats
	Status            int
	Failure           string
}

var ErrDenied = errors.New("invalid or revoked key")
var ErrQuota = errors.New("rate limited")
var ErrCapacity = errors.New("no ready capacity")

type Store struct{ DB *sql.DB }

func (s Store) Publish(ctx context.Context, id, model string) (Deployment, error) {
	// Day 2: reserve a live GPU and persist intent atomically. Retrying one ID reuses its intent.
	return Deployment{}, ErrExercise
}
func (s Store) Observe(ctx context.Context, h Heartbeat) error {
	// Days 2/6: update inventory and observed state. Enforce ownership and handle stale reports.
	return ErrExercise
}
func (s Store) Desired(ctx context.Context, node string) ([]Deployment, error) {
	// Day 2: read the durable assignments for this worker.
	return nil, ErrExercise
}
func Reconcile(ctx context.Context, node string, desired []Deployment) (Heartbeat, error) {
	// Days 2/6: inspect local managed containers, converge by stable ID, probe actual generation.
	// Use an operator-controlled model/image map. Observe hardware on this host even when desired is empty.
	return Heartbeat{Node: node}, ErrExercise
}

type Gateway struct {
	Store               Store
	DevelopmentUpstream string
	// Day 3: add synchronized per-tenant limiter state. Day 5: add routing policy here.
}

func (g *Gateway) Admit(ctx context.Context, key, model string) (Decision, error) {
	if g.DevelopmentUpstream != "" {
		return Decision{"lesson-one", g.DevelopmentUpstream}, nil
	}
	// Day 3: authenticate, check tenant budget, and select a ready replica for this model.
	return Decision{}, ErrExercise
}
func (s Store) Record(ctx context.Context, result Outcome) error {
	// Days 3/6: idempotent final event, distinguish unknown usage and interruption.
	return ErrExercise
}
