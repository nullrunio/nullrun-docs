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

These two layers together implement the eligibility clauses in the
[Terms of Service](https://nullrun.io/terms) and the data-residency
disclosures in the [Privacy Policy](https://nullrun.io/privacy).

## Operating posture

| Concern | Posture | Why |
| --- | --- | --- |
| GeoIP database missing | **fail-CLOSED** (503) | A misconfigured edge must never silently let traffic through. |
| Sanctions CSV missing | **degraded fallback** (logged) | Screening still runs against a hand-curated subset of obvious state actors; an ERROR log surfaces the gap. |
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

## What this means for you

If you are signing up from a country on either list:

- **Sanctioned countries** — your request is rejected with 403. There is
  no waitlist or alternative sign-up path; strict-liability does not
  allow a "we will email you when we do" bridge.
- **High-risk / no-service countries** — your request to the marketing
  site is redirected to `/waitlist`. The waitlist form records your
  email and the country you are visiting from. Requests to `/api/*` or
  `/ws/*` from these countries are hard-rejected with 403.

If you are an operator, see:

- [Geographic restrictions → Runbook](geo-restrictions.md#runbook-vps-deploy)
  for the GeoIP database deploy steps.
- [Sanctions screening → Operator override](sanctions-screening.md#operator-override)
  for the opt-out env var.