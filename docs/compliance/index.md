# Compliance

NullRun operates a **Fortress** posture for jurisdiction-based access
control. Two cooperating enforcement layers run at the gateway edge:

- **Geo restrictions** — every inbound request is classified by source
  country (MaxMind GeoLite2) and either allowed, waitlisted, or hard
  blocked. The blocklist is fail-CLOSED: a missing GeoIP database
  rejects **all** traffic until the operator drops the file in place.
  See [Geographic restrictions](geo-restrictions.md).
- **Sanctions screening** — signup-time name/email/handle check against
  the OFAC SDN list (with EU, UK, and UN lists supported as additional
  CSVs). Catches the case where a designated individual travels, uses
  a VPN, or signs up through a non-sanctioned-country proxy.
  See [Sanctions screening](sanctions-screening.md).

Both layers shipped together on **2026-06-30** (`6274c23 g fixes16` +
follow-up `1655801 g fixes 17` for the geo-block wiring, and
`20a5d7f fix(infra)` for the MaxMind bind-mount). They are the
authoritative enforcement for the corresponding Terms-of-Service
clauses and the regulatory disclosures on `nullrun.io/privacy` and
`nullrun.io/terms`.

## Operating posture

| Concern | Posture | Why |
| --- | --- | --- |
| GeoIP database missing | **fail-CLOSED** (503) | A misconfigured edge must never silently let traffic through. |
| Sanctions CSV missing | **degraded fallback** (logged) | Screening still runs against a hand-curated subset of obvious state actors; an ERROR log and `degraded: true` flag surface the gap. |
| Sanctions screening opt-out | `NULLRUN_SANCTIONS_SCREENING_DISABLED=1` | Disables name-based screening. The IP-level Fortress geo-block stays on. Intended for the pre-revenue / pre-customer stage. |
| Geo-block dev bypass | `NULLRUN_GEOBLOCK_DISABLED=1` | Disables geo-block entirely. **Fail-OPEN on a regulatory control** — a one-shot WARN is emitted; production must never set this. |
| Localhost / private IPs | Always allowed | Pod-to-pod health probes and operator local dev must not be blocked. |
| Marketing-site visitors | 302 → `/waitlist` | Compliance-blocked visitors are lead-captured, not 403'd, so the marketing surface is still informative. |
| `/api/*` and `/ws/*` from blocked countries | Hard 403 | The API surface is never reachable from a blocked jurisdiction. |

!!! warning "Regulatory exposure"
    Sanctions violations are **strict-liability** (criminal, not civil).
    The geo-block and the sanctions screening are the **only** line of
    defence; nothing downstream re-checks the IP or the name. A regression
    on either path is an enforcement-path incident and must be reverted
    immediately.

## Where to look in the codebase

| Concern | File | Notes |
| --- | --- | --- |
| IP → country lookup + blocklist | `backend/src/proxy/middleware/geo_block.rs` | `fortress_geo_block_middleware`, fail-CLOSED on missing `.mmdb`. |
| Wire-in (middleware stack) | `backend/src/proxy/server.rs:294` | Registered before auth and per-org quota. |
| Signup-time screening | `backend/src/proxy/middleware/sanctions.rs` | `screen_signup(name, email)`; called from `auth_register_handler` and `auth_oauth_register_handler`. |
| Wiring in signup handlers | `backend/src/proxy/handlers.rs:12339, 12572` | Rejects `ScreenResult::Match` with 403. |
| GeoIP / sanctions data layout | `backend/data/README.md` | Operator runbook for the `.mmdb` and `sdn.csv`. |
| VPS bind-mount (prod) | `infra/docker-compose.yml` | Pins `NULLRUN_GEOIP_DB=/tmp/geoip/GeoLite2-Country.mmdb` and mounts `/opt/nullrun/backend/data` into the container so the database survives redeploys. |
| Waitlist endpoint (public bridge) | `frontend/app/waitlist/page.tsx` | Receives compliance-blocked visitors from the marketing-site redirect. Rate-limited at 5/hour/IP via `ip_rate_limit::waitlist_rate_limit`. |