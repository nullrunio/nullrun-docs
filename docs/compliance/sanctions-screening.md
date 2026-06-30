# Sanctions screening

The geo-block stops ingress from sanctioned countries at the edge.
**Sanctions screening** is the second layer: a name/email/handle check
on every signup that catches the case where a designated individual
travels, uses a VPN, or signs up through a non-sanctioned-country
proxy. It is wired into both the standard `/api/v1/auth/register` and
the OAuth registration flow.

The screening table is loaded at process start from
`backend/data/sanctions/sdn.csv` (downloaded by the operator from
OFAC's Sanctions List Service). On file or parse failure the screening
falls back to a hand-curated subset of obvious state actors and emits
an ERROR log so the operator notices the misconfiguration.

## Why both layers

OFAC's comprehensive-sanctions regimes (Russia, Iran, DPRK, Syria,
Cuba, Crimea / Donetsk / Luhansk) are **strict-liability**. A single
accepted signup or payment from a designated person is a criminal-law
violation. The geo-block is the always-on defence; sanctions screening
is the catch-net for the cases where the IP alone is insufficient:

- A designated individual travelling abroad and signing up from a
  hotel Wi-Fi in a non-sanctioned country.
- A designated individual using a commercial VPN that exits in
  Armenia or Singapore.
- A designated individual signing up via OAuth (Google / GitHub) from
  a non-sanctioned IP, where the only signal we have is the email
  handle or display name.

## List source

The screening table is loaded from `data/sanctions/sdn.csv`. The
expected CSV format is the OFAC SDN format:

```
ent_num, SDN_Name, SDN_Type, Program, Title, Call_Sign, Vess_type, Tonnage, GRT, Vess_flag, Vess_owner, Remarks
12345, "PUTIN, Vladimir Vladimirovich", individual, UKRAINE-EO13662, "", "", "", "", "", "", "", ""
```

The EU consolidated list and the UK HMT consolidated list share the
same column layout and can be appended as additional CSVs (one per
jurisdiction). See `backend/data/README.md` for the download recipe.

!!! tip "Refresh cadence"
    OFAC SDN: refresh **daily**. MaxMind GeoLite2: weekly. EU / UK
    consolidated: as published (typically monthly). Until in-process
    hot-reload lands, a process restart is required to pick up a new
    CSV.

## Screening logic

For each signup the screening runs:

1. **Normalise** the name and email with NFKC (catches full-width
   homoglyphs like `ＡＢＣ` → `ABC`) and lowercase.
2. **Tokenise** on whitespace and non-alphanumeric characters.
3. **Drop short noise** — tokens shorter than 3 characters are
   skipped (so `Mr.`, `de`, `la`, `Jr.` do not contribute).
4. **Match** — if **any** token of the name or the email appears in
   the SDN token set, the signup is rejected with
   `ScreenResult::Match { matched, field }`.

The matching is intentionally aggressive. False positives are cheap
(rejected signup, the user retries with a different email); false
negatives are criminal. The tokenisation lives in
`backend/src/proxy/middleware/sanctions.rs:87-97`.

## Screen outcomes

The screening returns one of three results to the signup handler
(`sanctions.rs:260-330`):

| Result | Meaning | Handler action |
| --- | --- | --- |
| `Clean` | No SDN token matched. | Allow signup. |
| `Match { matched, field }` | The name or email contained a known SDN token. | Reject with 403. The matched display name and the field that hit are logged at WARN for audit. |
| `DegradedFallback` | Screening ran but the table is the hand-curated fallback (CSV missing or unparseable). | Allow signup. A separate WARN log + a Prometheus-friendly counter flag the misconfiguration. The geo-block is still on — the IP-level defence is intact. |

The signup handler is `auth_register_handler` /
`auth_oauth_register_handler` in
`backend/src/proxy/handlers.rs:12339, 12572`. On `Match` the handler
returns 403 with a generic body — the matched display name is **not**
echoed to the client to avoid confirming the screening target.

## Operator override — disabled by default

```bash
NULLRUN_SANCTIONS_SCREENING_DISABLED=1
```

Setting this env var makes `screen_signup` a no-op that always returns
`Clean`. The recommended posture for the **pre-revenue / pre-customer**
stage of the service, where the false-positive rate of token-based
name matching (`Vladimir Petrov` rejected because the surname token
matches an SDN) outweighs the residual sanctions risk.

!!! info "Why pre-revenue default is disabled"
    A small pre-revenue SaaS has no customers to lose, and the IP-level
    Fortress geo-block already excludes sanctioned countries from
    network ingress. A sanctioned individual would need to physically
    travel to a non-sanctioned country to even reach the signup form,
    or use a VPN — and the geo-block already rejects the VPN exit IPs
    that exit in sanctioned countries. Name-based screening is
    high-leverage for a bank or a payment processor; for a pre-revenue
    SaaS the false-positive triage cost is not yet worth the maintenance
    burden (weekly SDN list updates, false-positive triage).

**Re-enable** the screening by removing (or setting to `0`) the env
var as soon as the service has a meaningful customer base or accepts
payments in volume. The IP-level Fortress geo-block stays on in
either posture — see [Geographic restrictions](geo-restrictions.md).

## Fail-CLOSED vs degraded fallback

The two layers fail differently, on purpose:

| Layer | Failure mode | Posture |
| --- | --- | --- |
| Geo-block (IP) | `.mmdb` missing | **fail-CLOSED** (503). The edge must never silently let traffic through. |
| Sanctions screening (name) | `.csv` missing | **degraded fallback**. Screening runs against a hand-curated subset of obvious state actors; an ERROR log + `degraded: true` flag surface the gap. |

The asymmetry is documented in the module-level doc-comment of
`sanctions.rs:14-19`:

> If the file is missing the screening falls back to a hand-curated
> subset of well-known state actors, plus a hard fail-CLOSED log so
> the operator notices the misconfiguration.

The rationale is operational: a geo-database outage is a hard outage
(no traffic should be served); a sanctions-CSV outage is a degraded
posture (some defence remains, the gap is logged, the geo-block is
still on). Operators are expected to monitor the
`fortress: hard-blocking SANCTIONED-jurisdiction request` log line
and the `sanctions: Sanctions table loaded from …` log line at
process start; absence of the latter is the signal that the CSV
never loaded.

## Testing

The screening is covered by unit tests in
`sanctions.rs:333-451`:

- `tokenise_strips_short_tokens` — NFKC + lowercase + ≥3-char filter
- `tokenise_strips_full_width_homoglyphs` — full-width `Ａ` → ASCII `A`
- `tokenise_drops_short_noise` — `Mr. de la Cruz Jr.` → only `cruz`
- `screen_signup_matches_degraded_state_actor` — degraded fallback
  correctly rejects `Ali Khamenei`
- `screen_signup_clean_for_unrelated_name` — generic `Test User`
  returns `Clean` or `DegradedFallback` (never `Match` against a
  benign name)
- `screen_signup_clean_when_disabled` — the
  `NULLRUN_SANCTIONS_SCREENING_DISABLED=1` override is honoured

An **integration smoke test** against the real OFAC SDN list lives at
`geo_block.rs:705-734` (placed next to the geo-block tests for
discoverability):

```bash
cargo test -p breaker-core sanctions_loads_sdn -- --ignored
```

Run this after dropping the real `sdn.csv` into `data/sanctions/`. It
asserts that `Vladimir PUTIN` / `v.putin@example.com` matches against
the real list.

!!! note "Run with `--test-threads=1`"
    The screening table is loaded once per process via `OnceLock`. If
    other tests run first and the table is already cached in degraded
    mode, the assertion will fail because the real CSV will not be
    re-read. `--test-threads=1` ensures this test is the first to
    touch the screening table.

## Known limitations

- **Cyrillic / Latin homoglyphs are NOT collapsed.** `Cyrillic а`
  (U+0430) stays Cyrillic after NFKC; only the full-width Latin /
  ASCII cases collapse. A designated individual could circumvent
  name-based screening by transliterating their name to a homoglyph
  script. The geo-block is the durable defence here — a non-Latin
  name from a sanctioned-country IP is still blocked.
- **No email-domain match.** Emails are tokenised on `@` and `.`,
  but the resulting tokens (e.g. `gmail`, `mail`) are common enough
  that matching them would produce false positives. The name tokens
  are the primary signal; the email is a secondary, weaker signal.
- **OnceLock cache is process-once.** A new CSV requires a process
  restart. Until in-process hot-reload lands, the recommended cadence
  is daily process restarts paired with a daily OFAC CSV refresh.

## Where to look in the codebase

| Concern | File | Notes |
| --- | --- | --- |
| Screening table load + match | `backend/src/proxy/middleware/sanctions.rs` | `SanctionsTable::load_or_degraded()`, `screen_signup(name, email)`. |
| Signup handler wiring | `backend/src/proxy/handlers.rs:12339, 12572` | `auth_register_handler`, `auth_oauth_register_handler`. |
| CSV layout and refresh recipe | `backend/data/README.md` | Operator runbook. |
| Geo-block (the always-on defence) | `backend/src/proxy/middleware/geo_block.rs` | IP-level, fail-CLOSED. |
| Fortress risk register | (forthcoming) | Brief lives at `FORTRESS_TIER1_BRIEF.md` in the gateway repo. |