# Geographic restrictions

NullRun's edge gateway classifies every inbound request by source
country and applies one of three actions:

- **Allow** — request proceeds normally.
- **Hard block** — request is rejected (403 `service_unavailable_in_jurisdiction` or 503 `geoip_unavailable`).
- **Waitlist redirect** — compliance-blocked visitor on the marketing
  site is 302-redirected to `/waitlist` so the lead is captured without
  exposing the API surface.

The lookup is performed by the **Fortress geo-block middleware** at
`backend/src/proxy/middleware/geo_block.rs`, which runs before auth
and before the per-org quota checks so blocked traffic never touches
the database.

## Why this is needed

GDPR Art. 3 and the CJEU Planet49 ruling (C-673/17) turn on whether
the operator is "offering goods or services" to, or "monitoring", EU
data subjects. A Terms-of-Service clause alone is not enough — a
regulator will infer targeting from the fact that the API endpoint is
reachable from EU IP space. Hard-blocking at the edge is the only
reliable signal.

The same logic applies to the other comprehensive-sanctions regimes
(OFAC, EU, UK, UN) for the sanctioned-country blocklist. Those are
**strict-liability**: a single accepted signup or payment from one of
those jurisdictions is a criminal-law violation, not a civil one.

## Blocklist

The blocklist is compiled into the binary in two tiers. Both lists
live in `geo_block.rs` and are unit-tested in
`backend/src/proxy/middleware/geo_block.rs:550-567`.

### Tier 1 — Sanctioned (strict-liability block)

| Code | Country | Rationale |
| --- | --- | --- |
| `RU` | Russia | OFAC + EU + UK comprehensive |
| `IR` | Iran | OFAC comprehensive |
| `KP` | DPRK | OFAC + UN comprehensive |
| `SY` | Syria | OFAC + EU comprehensive |
| `CU` | Cuba | OFAC comprehensive |
| `BY` | Belarus | Post-2022 UK + EU sectoral |
| `VE` | Venezuela | Partial — block at signup, allow read-only API |
| `MM` | Myanmar | OFAC + EU restrictive measures |
| `AF` | Afghanistan | Post-2021 sanctions regime |
| `ZW` | Zimbabwe | OFAC selective sanctions |

Sanctioned requests are blocked with **403** even on the marketing
site — no waitlist, no email capture. Strict liability does not allow
the "we will email you when we do" bridge.

### Tier 2 — High-risk / no-service (compliance block)

| Code | Region | Rationale |
| --- | --- | --- |
| `AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE` | EU-27 | GDPR + active enforcement |
| `IS NO LI` | EEA / EFTA | Treated like EU for our purposes |
| `CH` | Switzerland | FADP — high compliance burden |
| `GB` | United Kingdom | UK GDPR + ICO + class actions |
| `US CA` | United States / Canada | CCPA + state patchwork |
| `CN` | China | PIPL + data localisation |
| `IN` | India | DPDPA 2023 + criminal penalties for officers |

For high-risk countries:

- **`/api/*` and `/ws/*`** → 403 `service_unavailable_in_jurisdiction`
- **Marketing site** (anything NOT under `/api/` or `/ws/`) → 302 to
  `/waitlist?cc=<ISO>`. The waitlist page lives at
  `frontend/app/waitlist/page.tsx`.

## Decision matrix

```mermaid
flowchart TD
    R["Request arrives<br/>at the edge"] --> E{"Extract<br/>client IP"}
    E -->|None| L["Log WARN, allow<br/>(should not happen in prod)"]
    E -->|Loopback /<br/>private / CGNAT| L2["Allow<br/>(bypass IP)"]
    E -->|Public IP| B{"GeoIP DB<br/>available?"}
    B -->|No| H["503 geoip_unavailable<br/>(fail-CLOSED)"]
    B -->|Yes| L3["Look up country"]
    L3 --> S{"Sanctioned<br/>country?"}
    S -->|Yes| H2["403 service_unavailable_in_jurisdiction<br/>(strict-liability block)"]
    S -->|No| H3{"High-risk<br/>country?"}
    H3 -->|No| A["Allow"]
    H3 -->|Yes| P{"On marketing<br/>site?"}
    P -->|Yes| W["302 → /waitlist?cc=…"]
    P -->|No| H4["403 service_unavailable_in_jurisdiction"]
```

The action table is covered by `geo_block.rs::Lookup::action()` and
its unit tests at `geo_block.rs:600-652`.

## Fail-CLOSED posture

The middleware is **fail-CLOSED on the blocklist**: if the GeoIP
database is missing, unreadable, or returns an error, **all** ingress
is rejected with 503. The rationale is in the module-level doc-comment
of `geo_block.rs`:

> If the GeoIP database is missing or unreadable, ALL ingress is
> rejected (503) so the operator notices the misconfiguration.

The trace log emits `fortress: GeoIP database unavailable` at ERROR
level on every request that hits the failure path — that log line in
ELK is the operator's first signal that the `.mmdb` needs to be
restored.

The earlier behaviour was that a missing `.mmdb` made the reader
return `None` and the request was allowed. That regression caused a
prod 503-storm on 2026-06-30 until `20a5d7f fix(infra)` pinned
`NULLRUN_GEOIP_DB=/tmp/geoip/GeoLite2-Country.mmdb` and bind-mounted
`/opt/nullrun/backend/data` into the container so the file survives
`docker compose up -d`. See the [runbook appendix](#runbook-vps-deploy)
below.

## Operator overrides

!!! warning "These are escape hatches. Production must never set them."

| Env var | Effect | When to use |
| --- | --- | --- |
| `NULLRUN_GEOBLOCK_DISABLED=1` | Disables the middleware entirely. One-shot WARN is logged on first request. | Local development only. Set in `dev.env`, never in `.env.prod`. |
| `NULLRUN_GEOIP_DB=/path/to/file.mmdb` | Override the path to the MaxMind database. Default: `data/GeoLite2-Country.mmdb` (relative to container CWD). | VPS / staging deployments where the operator supplies the file. |

The `NULLRUN_GEOBLOCK_DISABLED=1` flag is the most dangerous knob in
the codebase — it is a **fail-OPEN** setting on a regulatory control.
The middleware emits the WARN exactly once per process to surface the
misconfiguration without flooding the log.

## What is bypassed

The middleware **never** blocks:

- **Localhost and private IPs** — `127.0.0.0/8`, `10/8`, `172.16/12`,
  `192.168/16`, `169.254/16`, `100.64.0.0/10` (CGNAT), IPv6
  `fc00::/7` (ULA), `fe80::/10` (link-local). These are pod-to-pod
  traffic, monitoring agents, or the operator's local-dev loopback;
  none of them can themselves trigger GDPR.
- **Health and metrics** — `/health`, `/healthz`, `/ready`, `/readyz`,
  `/metrics`, `/internal/*`. These are infrastructure-internal probes
  and must never be geo-blocked.
- **The waitlist endpoint** — `POST /api/v1/waitlist`. The marketing
  site redirects compliance-blocked visitors here; if the geo-block
  then 403'd the form POST, the lead-capture flow would be broken.
  The waitlist has its own rate limit (5/hour/IP via
  `ip_rate_limit::waitlist_rate_limit`).

The bypass rules live in `is_bypass_ip` and `is_bypass_path` at
`geo_block.rs:258-362` and are unit-tested at `:570-597`.

## Audit headers

Every blocked response carries two headers for observability and
debugging:

| Header | Meaning |
| --- | --- |
| `x-nullrun-fortress-block: sanctions` | Blocked by the Tier-1 sanctions list. |
| `x-nullrun-fortress-block: waitlist` | Marketing-site redirect to `/waitlist`. |
| `x-nullrun-fortress-country: <ISO>` | The resolved ISO 3166-1 alpha-2 country code. Absent when the GeoIP database is unavailable. |

These headers are **not** logged at INFO level (the country code is
PII under GDPR, ironically) — they appear at WARN. See
`geo_block.rs:455-477` for the sanitised log behaviour.

## Runbook — VPS deploy

This is the operator recipe that ships with the
`fix(infra): wire NULLRUN_GEOIP_DB + bind mount MaxMind db`
commit (`20a5d7f`).

1. **Download the database.** A free MaxMind license key is required:
   <https://www.maxmind.com/en/geolite2/signup>.

    ```bash
    curl -L "https://download.maxmind.com/app/geoip_download?\
edition_id=GeoLite2-Country&license_key=$MAXMIND_LICENSE_KEY&suffix=tar.gz" \
        -o /tmp/geolite2.tar.gz
    mkdir -p /opt/nullrun/backend/data
    tar -xzf /tmp/geolite2.tar.gz -C /tmp/
    mv /tmp/GeoLite2-Country_*/GeoLite2-Country.mmdb \
        /opt/nullrun/backend/data/
    rm -rf /tmp/GeoLite2-Country_*
    ```

2. **Pin the env var.** The `docker-compose.yml` already declares:

    ```yaml
    environment:
      NULLRUN_GEOIP_DB: /tmp/geoip/GeoLite2-Country.mmdb
    volumes:
      - /opt/nullrun/backend/data:/tmp/geoip:ro
    ```

    The bind-mount is **read-only** and pins the path so the
    `data/GeoLite2-Country.mmdb` lookup in `geo_block.rs:128` resolves
    to the operator-supplied file.

3. **Restart the gateway.** Until in-process hot-reload lands, a
   fresh `docker compose up -d` is required to pick up a new `.mmdb`.

4. **Verify.** From a known EU IP: `curl -i https://api.nullrun.io/healthz`
   should be 200, and `curl -i https://api.nullrun.io/api/v1/auth/register`
   should be 403 with `x-nullrun-fortress-block: sanctions` or `service_unavailable_in_jurisdiction` in the body.

5. **Schedule weekly refresh.** A weekly cron is recommended — see
   `infra/cron.d/` for an example. The GeoIP allocation drift is
   slow (weeks), but OFAC/EU/UK SDN lists move faster; see
   [Sanctions screening](sanctions-screening.md).

## Testing

The middleware is covered by unit tests in
`geo_block.rs:545-735`:

- `sanctioned_list_includes_core_targets` — RU, IR, KP, SY, CU present
- `high_risk_list_includes_eu_us_china_india_uk` — DE, FR, IT, ES, NL,
  US, CN, IN, GB, CH present
- `bypass_ip_skips_geo_block` — loopback / private / CGNAT pass through
- `bypass_path_skips_geo_block` — health, metrics, `/internal/*`, the
  waitlist, and the marketing site all bypass
- `lookup_action_matrix` — the sanctioned / high-risk / allowed /
  miss / down branches of the action table
- `geo_block_loads_mmdb` (`--ignored`) — integration smoke test that
  requires `data/GeoLite2-Country.mmdb` to be present. Runs
  `cargo test -p breaker-core geo_block_loads_mmdb -- --ignored`.