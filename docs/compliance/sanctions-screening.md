# Sanctions screening

The geo-block stops ingress from sanctioned countries at the edge.
**Sanctions screening** is the second layer: a name/email/handle check
on every signup that catches the case where a designated individual
travels, uses a VPN, or signs up through a non-sanctioned-country
proxy. It runs on both the standard signup form and the OAuth
registration flow.

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

The screening table is loaded from `[Office of Foreign Assets Control`](https://ofac.treasury.gov/sanctions-list-service). The
expected CSV format is the OFAC SDN format:

```
35096,"PUTIN, Vladimir Vladimirovich","individual","RUSSIA-EO14024","President of the Russian Federation",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,"DOB 07 Oct 1952; POB Leningrad, Russia; nationality Russia; citizen Russia; Gender Male; Secondary sanctions risk: See Section 11 of Executive Order 14024.; President of the Russian Federation."
```

The EU consolidated list and the UK HMT consolidated list share the
same column layout and can be appended as additional CSVs (one per
jurisdiction).

!!! tip "Refresh cadence"
    OFAC SDN: refresh **daily**. MaxMind GeoLite2: weekly. EU / UK
    consolidated: as published (typically monthly). Until in-process
    hot-reload lands, a process restart is required to pick up a new
    CSV.

## Screening logic

For each signup the screening runs:

1. **Normalise** the name and email (catches full-width homoglyphs like
   `ＡＢＣ` → `ABC`) and lower-case them.
2. **Tokenise** on whitespace and non-alphanumeric characters.
3. **Drop short noise** — tokens shorter than 3 characters are
   skipped (so `Mr.`, `de`, `la`, `Jr.` do not contribute).
4. **Match** — if **any** token of the name or the email appears in
   the SDN token set, the signup is rejected.

The matching is intentionally aggressive. False positives are cheap
(rejected signup, the user retries with a different email); false
negatives are criminal.

## Screen outcomes

The screening returns one of three results:

| Result | Meaning | What happens |
| --- | --- | --- |
| Clean | No SDN token matched. | Allow signup. |
| Match | The name or email contained a known SDN token. | Reject with 403. The matched display name and the field that hit are logged at WARN for audit. |
| Degraded | Screening ran but the table is the hand-curated fallback (CSV missing or unparseable). | Allow signup. A separate WARN log + an ops-counter flag the misconfiguration. The geo-block is still on — the IP-level defence is intact. |

On a `Match` the response body is a generic 403 — the matched display
name is **not** echoed to the client to avoid confirming the
screening target.

## Operator override — disabled by default

```bash
NULLRUN_SANCTIONS_SCREENING_DISABLED=1
```

Setting this env var makes the screening a no-op that always returns
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
| Sanctions screening (name) | `.csv` missing | **degraded fallback**. Screening runs against a hand-curated subset of obvious state actors; an ERROR log + a `degraded` flag surface the gap. |

The rationale is operational: a geo-database outage is a hard outage
(no traffic should be served); a sanctions-CSV outage is a degraded
posture (some defence remains, the gap is logged, the geo-block is
still on). Operators are expected to monitor the
`fortress: hard-blocking SANCTIONED-jurisdiction request` log line
and the `sanctions: Sanctions table loaded from …` log line at
process start; absence of the latter is the signal that the CSV
never loaded.

## Known limitations

- **Cyrillic / Latin homoglyphs are NOT collapsed.** A Cyrillic `а`
  stays Cyrillic after normalisation; only the full-width Latin /
  ASCII cases collapse. A designated individual could circumvent
  name-based screening by transliterating their name to a homoglyph
  script. The geo-block is the durable defence here — a non-Latin
  name from a sanctioned-country IP is still blocked.
- **No email-domain match.** Emails are tokenised on `@` and `.`,
  but the resulting tokens (e.g. `gmail`, `mail`) are common enough
  that matching them would produce false positives. The name tokens
  are the primary signal; the email is a secondary, weaker signal.
- **The screening table is loaded once per process.** A new CSV
  requires a process restart. Until in-process hot-reload lands, the
  recommended cadence is daily process restarts paired with a daily
  OFAC CSV refresh.

## Self-check

If you are an operator and want to confirm the screening is wired up:

1. Drop the real `sdn.csv` into `data/sanctions/`.
2. Restart the gateway.
3. Attempt a signup with a name that appears in the OFAC SDN list
   (e.g. `Vladimir PUTIN` / `v.putin@example.com`). The request
   should return 403.
4. Confirm the `sanctions: Sanctions table loaded from …` log line
   appears at process start, with a non-degraded token count.