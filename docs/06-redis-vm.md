# 06 — Redis on a free-tier e2-micro VM

We need one always-on, shared place to store caches and counters across requests and instances. The
cheapest option that's still "real infrastructure" is a single **`e2-micro`** VM (free tier in
`us-central1`/`us-east1`/`us-west1`) running Redis in a container.

## What we create

- An `e2-micro` VM named `redis-vm` running **Container-Optimized OS** (Docker preinstalled).
- A **startup script** that runs `redis:7-alpine` with a password, capped memory, and LRU eviction.
- A **firewall rule** that allows port 6379 **only from the internal VPC** (10.128.0.0/20) — never the
  public internet.
- The connection string stored in **Secret Manager** as `REDIS_URL`.

## The commands (already run for this project; here for reproducibility)

```bash
PROJECT=portfolio-agent-499115
ZONE=us-central1-a

# A strong password for Redis AUTH
REDIS_PASS=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")

# Firewall: 6379 reachable only from inside the VPC, by VMs tagged "redis"
gcloud compute firewall-rules create allow-redis-internal \
  --network=default --direction=INGRESS --action=ALLOW \
  --rules=tcp:6379 --source-ranges=10.128.0.0/20 --target-tags=redis

# Startup script: run Redis in a container
cat > /tmp/redis-startup.sh <<EOF
#!/bin/bash
docker rm -f redis 2>/dev/null || true
docker run -d --name redis --restart always -p 6379:6379 redis:7-alpine \
  redis-server --requirepass "${REDIS_PASS}" --maxmemory 200mb --maxmemory-policy allkeys-lru --appendonly no
EOF

# The VM (free-tier-eligible e2-micro, COS image)
gcloud compute instances create redis-vm \
  --zone $ZONE --machine-type=e2-micro \
  --image-family=cos-stable --image-project=cos-cloud \
  --tags=redis \
  --metadata-from-file=startup-script=/tmp/redis-startup.sh \
  --no-service-account --no-scopes

# Store the connection string (use the VM's INTERNAL IP, e.g. 10.128.0.2)
printf '%s' "redis://:${REDIS_PASS}@10.128.0.2:6379/0" | \
  gcloud secrets create REDIS_URL --data-file=- --replication-policy=automatic
```

## How Cloud Run reaches it

The VM has **no public Redis port**, so Cloud Run connects over the private network using **Direct VPC
egress** (a flag on the `api` deploy — see [07](07-deploy-cloud-run.md)):

```
--network=default --subnet=default --vpc-egress=private-ranges-only
```

This routes the `api`'s private-range traffic (like `10.128.0.2`) into the VPC, where the firewall lets it
hit Redis. No paid VPC connector required.

## Design choices

- **Memory cap + LRU** (`--maxmemory 200mb --maxmemory-policy allkeys-lru`): the cache can never OOM the
  tiny VM; old entries are evicted automatically.
- **`--appendonly no`**: this is a *cache*, not a database — losing it on reboot is fine (it just re-warms).
- **Password + internal-only firewall**: even though it's private, we still set AUTH (defense in depth).
- **Plain Redis (not Redis Stack)**: our semantic cache is implemented in app code (brute-force cosine over
  a capped list), so we don't need the RediSearch module — vanilla `redis:7-alpine` is enough.

## Verifying / debugging

```bash
gcloud compute ssh redis-vm --zone us-central1-a
# on the VM:
docker logs redis
docker exec -it redis redis-cli -a "$REDIS_PASS" ping   # -> PONG
```

Or just hit the deployed `api`'s `/health` — `redis_ok:true` confirms the path works end to end.

> **Cheaper-still alternative:** you can skip the VM entirely and run Redis as a **Cloud Run sidecar
> container** (multi-container service). That's $0 and scales to zero, at the cost of per-instance
> (ephemeral) cache. We chose the VM because it gives a single shared cache across instances and matches
> the requested architecture.

Next: [07 — Deploy to Cloud Run](07-deploy-cloud-run.md).
