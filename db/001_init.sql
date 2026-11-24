-- Run once in the course database, with ON_ERROR_STOP enabled.
BEGIN;
CREATE TABLE tenant (
 id text PRIMARY KEY,
 rpm integer NOT NULL CHECK (rpm > 0),
 input_tpm integer NOT NULL CHECK (input_tpm > 0),
 output_tpm integer NOT NULL CHECK (output_tpm > 0)
);
CREATE TABLE api_key (
 digest bytea PRIMARY KEY,
 tenant_id text NOT NULL REFERENCES tenant,
 prefix text NOT NULL,
 revoked_at timestamptz
);
CREATE TABLE worker (
 id text PRIMARY KEY,
 last_seen timestamptz NOT NULL
);
CREATE TABLE gpu (
 node_id text REFERENCES worker, device_id text,
 PRIMARY KEY(node_id,device_id)
);
CREATE TABLE deployment (
 id text PRIMARY KEY, model text NOT NULL, node_id text NOT NULL, device_id text NOT NULL,
 endpoint text, phase text NOT NULL, desired boolean NOT NULL DEFAULT true,
 FOREIGN KEY (node_id,device_id) REFERENCES gpu
);
-- Exercise: enforce one live reservation per physical GPU even with two controllers.
CREATE TABLE usage_event (
 request_id text PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenant,
 started_at timestamptz NOT NULL, ended_at timestamptz NOT NULL,
 first_content_at timestamptz, status integer NOT NULL, complete boolean NOT NULL,
 prompt_tokens integer, output_tokens integer, failure text
);
CREATE INDEX usage_by_tenant_time ON usage_event(tenant_id,started_at);
COMMIT;
