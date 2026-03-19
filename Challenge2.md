# 🧠 Challenge 2: Least-Privilege + Idempotent Ingestion + Backup/Restore

Welcome back. This time you’ll build the same 3-tier stack, but with a “real-world” level of operational complexity:

- least-privilege database roles
- idempotent ingestion (safe to retry)
- persistent Metabase state
- a backup/restore drill that proves data durability

You must complete everything using **pure Docker CLI commands** (no `docker compose`).


## 🚫 The Rules
* **No Docker Compose allowed.** Everything must be done via the `docker` command line.
* Use a dedicated Docker Network (no default bridge assumptions).
* **Data must persist** across container restarts/crashes (volumes are mandatory).
* Your ingestion step must be **idempotent**: if the ingest container crashes and restarts, your data must not be duplicated.
* You must use **least privilege**:
  - Ingestion uses a non-superuser role that only has the rights it needs.
  - Metabase uses a read-only role scoped to your reporting schema.
* **No AI Copilot allowed.** 🆘


## 📍 Step 1: Foundation (2 networks + 3 persistent volumes)

Create:

- A custom bridge network named `data-tier-v2`
- A custom bridge network named `ops-tier` (for your admin/backup containers)
- A persistent Postgres volume named `pg-data-v2`
- A persistent Postgres backup volume named `pg-backups-v2`
- A persistent Metabase volume named `metabase-data-v2`

Run:

```bash
docker network create --driver bridge data-tier-v2
docker network create --driver bridge ops-tier

docker volume create pg-data-v2
docker volume create pg-backups-v2
docker volume create metabase-data-v2
```

> If you use the same names you can re-run safely. If you re-run on an existing Docker host, you may need `docker rm -f` / `docker volume rm` first.


## 📍 Step 2: Postgres with roles (init SQL + health checks)

### Task 2.1: Create an init SQL file

Create a host file named `init-v2.sql` in the repo root.

The goal: create roles and a reporting schema before Metabase or ingestion runs.

Minimum requirements:

1. Create roles:
   - `ingestor_user` (can insert/upsert into tables)
   - `metabase_user` (read-only on reporting tables)
   - `backup_user` (can connect and read enough to create a backup)
2. Create schema `reporting`.
3. Create a migration tracker table `reporting.schema_migrations` (even if you only do one migration for this challenge).
4. Grant least-privilege access:
   - `ingestor_user` can create tables inside `reporting`
   - `metabase_user` can read from `reporting` tables (at least `schema_migrations` initially)

Use the superuser credentials you set via `POSTGRES_USER`/`POSTGRES_PASSWORD` when starting Postgres.

Example `init-v2.sql` starter:

```sql
-- reporting schema
CREATE SCHEMA IF NOT EXISTS reporting;

-- Roles (passwords must be set to something you choose)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ingestor_user') THEN
    CREATE ROLE ingestor_user LOGIN PASSWORD 'CHANGEME_INGESTOR_PASSWORD';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'metabase_user') THEN
    CREATE ROLE metabase_user LOGIN PASSWORD 'CHANGEME_METABASE_PASSWORD';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'backup_user') THEN
    CREATE ROLE backup_user LOGIN PASSWORD 'CHANGEME_BACKUP_PASSWORD';
  END IF;
END $$;

-- Migration tracking
CREATE TABLE IF NOT EXISTS reporting.schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Least-privilege grants (you can expand this later as you add more tables)
GRANT USAGE, CREATE ON SCHEMA reporting TO ingestor_user;
GRANT USAGE ON SCHEMA reporting TO metabase_user;

GRANT SELECT ON TABLE reporting.schema_migrations TO metabase_user;
GRANT INSERT, UPDATE ON TABLE reporting.schema_migrations TO ingestor_user;

DO $$
BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO ingestor_user', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO metabase_user', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO backup_user', current_database());
END $$;
```

### Task 2.2: Launch Postgres primary

Launch Postgres 15 with:

- Container name: `warehouse-primary`
- Attached to: `data-tier-v2` (for app traffic)
- Also attached to: `ops-tier` (for admin/backup traffic)
- Volume: mount `pg-data-v2` to `/var/lib/postgresql/data`
- Health check: must use `pg_isready`
- Init: mount `init-v2.sql` into `/docker-entrypoint-initdb.d/`
- Environment: set `POSTGRES_PASSWORD` (and also `POSTGRES_USER`/`POSTGRES_DB` if your `.env` supports them)

Run:

```bash
docker run -d \
  --name warehouse-primary \
  --network data-tier-v2 \
  -v pg-data-v2:/var/lib/postgresql/data \
  -v "$PWD/init-v2.sql":/docker-entrypoint-initdb.d/01-init-v2.sql:ro \
  --env-file .env \
  -p 5432:5432 \
  --health-cmd='pg_isready -U postgres_user -d my_db' \
  --health-interval=5s \
  --health-timeout=5s \
  --health-retries=30 \
  postgres:15
```

Then attach it to your ops network:

```bash
docker network connect ops-tier warehouse-primary
```

> The `.env` in this repo currently includes `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`, and `YOUR_NAME`. If your host `.env` differs, adjust the command accordingly.

## 📍 Step 3: Ingestion must be idempotent (UPSERT + retry-safe)

This step is the “hard” part.

### Task 3.1: Update/extend ingestion

Update `lib/ingest.py` (or add a new script) so it:

1. Creates tables in `reporting` (if they don’t exist).
2. Uses a **unique constraint** such that re-running ingestion does not duplicate records.
3. Uses **UPSERT** (`INSERT ... ON CONFLICT ...`) so repeated attempts are safe.

Minimum table set:

- `reporting.bootcamp_test_v2` with:
  - `name TEXT NOT NULL`
  - `id SERIAL` (optional)
  - `UNIQUE(name)`

You can keep the existing “insert YOUR_NAME” behavior, but now you must make it safe for retries.

### Task 3.2: Build and run ingest using a non-superuser

Your ingestion container must connect using `ingestor_user` credentials, not the Postgres superuser.

Important: the existing code in `lib/ingest.py` reads `POSTGRESS_HOST` (note the misspelling). Set the variable exactly like that.

Build:

```bash
docker build -t ingest-v2 .
```

Run it with:

- Network: `data-tier-v2`
- Env vars: pass host, user, password, database name
- Retry policy: configure Docker to restart the ingest container on failure

Use a command like:

```bash
docker run \
  --name ingest-v2-run \
  --network data-tier-v2 \
  --restart on-failure:10 \
  --env POSTGRES_USER=ingestor_user \
  --env POSTGRES_PASSWORD=CHANGEME_INGESTOR_PASSWORD \
  --env POSTGRES_DB=my_db \
  --env POSTGRESS_HOST=warehouse-primary \
  --env YOUR_NAME="$YOUR_NAME" \
  ingest-v2
```

> If your ingest container exits immediately with an error, inspect logs and iterate. Your final goal is: “restart does not duplicate data”.


## 📍 Step 4: Metabase must use persistent storage + read-only role

Launch Metabase and ensure it uses:

- Container name: `viz-tool-v2`
- Network: `data-tier-v2`
- Volume: `metabase-data-v2` mounted to `/metabase-data`
- DB config: point Metabase at `warehouse-primary`
- Auth: use `metabase_user` (read-only)

Run:

```bash
docker run -d \
  --name viz-tool-v2 \
  --network data-tier-v2 \
  -p 3001:3000 \
  -v metabase-data-v2:/metabase-data \
  --env MB_DB_TYPE=postgres \
  --env MB_DB_HOST=warehouse-primary \
  --env MB_DB_PORT=5432 \
  --env MB_DB_DBNAME=my_db \
  --env MB_DB_USER=metabase_user \
  --env MB_DB_PASS="CHANGEME_METABASE_PASSWORD" \
  metabase/metabase:latest
```

Open `localhost:3001` and in the setup wizard:

1. Connect Metabase to `warehouse-primary`
2. Ensure the connected user is `metabase_user`

### Task 4.1: Reporting question

Create at least one question based on:

- `reporting.bootcamp_test_v2`

And add it to a dashboard.


## 📍 Step 5: Backup/restore drill (prove durability)

This step proves persistence and correctness.

### Task 5.1: Create a backup into `pg-backups-v2`

Run a one-off backup container that writes a dump file into the backup volume.

Example:

```bash
docker run --rm \
  --name pg-backup \
  --network ops-tier \
  -v pg-backups-v2:/backups \
  --env PGPASSWORD=CHANGEME_BACKUP_PASSWORD \
  postgres:15 \
  pg_dump -Fc \
    --no-owner --no-acl \
    -U backup_user \
    -d my_db \
    -f /backups/bootcamp_latest.dump
```

> You must verify the file exists in the dump volume (check via `docker run` + `ls` inside the container, since `pg-backups-v2` lives on the Docker host).

### Task 5.2: Restore into a fresh Postgres data volume

Create a new empty volume:

```bash
docker volume create pg-data-v2-restore
```

Stop/remove the running Postgres container:

```bash
docker rm -f warehouse-primary
```

Start Postgres again, but mount the restore volume instead of `pg-data-v2`:

```bash
docker run -d \
  --name warehouse-primary \
  --network data-tier-v2 \
  -v pg-data-v2-restore:/var/lib/postgresql/data \
  --env-file .env \
  --health-cmd='pg_isready -U postgres_user -d my_db' \
  --health-interval=5s \
  --health-timeout=5s \
  --health-retries=30 \
  postgres:15
```

Then attach it to your ops network:

```bash
docker network connect ops-tier warehouse-primary
```

Wait until healthy, then restore:

```bash
docker run --rm \
  --network ops-tier \
  -v pg-backups-v2:/backups \
  --env PGPASSWORD=secret123 \
  postgres:15 \
  pg_restore --no-owner --no-acl \
    -U postgres_user \
    -d my_db \
    /backups/bootcamp_latest.dump
```

### Task 5.3: Verify data via query

Connect to the restored DB and confirm:

- `reporting.bootcamp_test_v2` contains the expected row(s)
- Metabase can still display the data without reconfiguration

Example verification:

```bash
docker run --rm -it \
  --network data-tier-v2 \
  postgres:15 \
  psql -h warehouse-primary -U postgres_user -d my_db \
  -c "SELECT name FROM reporting.bootcamp_test_v2 ORDER BY name;"
```


## 🧠 Deliverables (what “done” means)
1. `docker ps` shows `warehouse-primary` and `viz-tool-v2` running and healthy/stable.
2. Ingestion was restarted at least once (either manually or via `--restart on-failure`) and you confirmed no duplicates.
3. Metabase question/dashboard exists and is backed by `metabase_user`.
4. Backup dump exists in `pg-backups-v2` and a restore into a fresh volume successfully recovered your data.

