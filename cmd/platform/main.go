package main

import (
	"context"
	"database/sql"
	"flag"
	_ "github.com/jackc/pgx/v5/stdlib"
	"log"
	"net"
	"net/http"
	"os"
	"team-inference-lab/internal/platform"
	"time"
)

func main() {
	role := flag.String("role", "demo", "demo, gateway, control, worker")
	addr := flag.String("listen", "127.0.0.1:8001", "HTTP address")
	upstream := flag.String("dev-upstream", "", "day 1 only: direct upstream, bypass database and auth")
	control := flag.String("control", "http://127.0.0.1:8090", "control plane URL")
	node := flag.String("node", "node-a", "worker ID")
	flag.Parse()
	token := os.Getenv("LAB_ADMIN_TOKEN")
	var store platform.Store
	if *role == "control" || (*role == "gateway" && *upstream == "") {
		dsn := os.Getenv("DATABASE_URL")
		if dsn == "" {
			log.Fatal("set DATABASE_URL")
		}
		db, err := sql.Open("pgx", dsn)
		if err != nil {
			log.Fatal(err)
		}
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		err = db.PingContext(ctx)
		cancel()
		if err != nil {
			log.Fatal(err)
		}
		defer db.Close()
		store.DB = db
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write([]byte("up\n")) })
	switch *role {
	case "demo":
		mux.HandleFunc("POST /v1/chat/completions", platform.Demo)
	case "gateway":
		if *upstream != "" {
			host, _, err := net.SplitHostPort(*addr)
			if err != nil || !net.ParseIP(host).IsLoopback() {
				log.Fatal("dev gateway must listen on loopback")
			}
		}
		g := &platform.Gateway{Store: store, DevelopmentUpstream: *upstream}
		mux.HandleFunc("POST /v1/chat/completions", g.Chat)
	case "control":
		if token == "" {
			log.Fatal("set LAB_ADMIN_TOKEN")
		}
		mux.Handle("/", platform.Control(store, token))
	case "worker":
		if token == "" {
			log.Fatal("set LAB_ADMIN_TOKEN")
		}
		for {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			err := platform.WorkerTick(ctx, *control, token, *node)
			cancel()
			if err != nil {
				log.Printf("reconcile: %v", err)
			}
			time.Sleep(2 * time.Second)
		}
	default:
		log.Fatal("unknown role")
	}
	log.Printf("%s on %s", *role, *addr)
	log.Fatal((&http.Server{Addr: *addr, Handler: mux, ReadHeaderTimeout: 5 * time.Second}).ListenAndServe())
}
