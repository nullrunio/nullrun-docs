title: Sanctions screening
maturity: stable
description: OFAC SDN screening on signup, the degraded-fallback semantics when the screening service is unavailable, and the audit trail.
# Sanctions screening

The geo-block stops ingress from sanctioned countries at the edge.
**Sanctions screening** is the second layer: a name/email/handle check
on every signup that catches the case where a designated individual
travels, uses a VPN, or signs up through a non-sanctioned-country
proxy. It runs on both the standard signup form and the OAuth
registration flow.

The screening runs against the OFAC SDN list (with EU / UK / UN
list support).

## Why both layers

OFAC's comprehensive-sanctions regimes are **strict-liability**. A
single accepted signup or payment from a designated person is a
criminal-law violation. The geo-block is the always-on defence;
sanctions screening is the secondary layer:

- A designated individual travelling abroad and signing up from a
  hotel Wi-Fi in a non-sanctioned country.
- A designated individual using a commercial VPN that exits in
  Armenia or Singapore.
- A designated individual signing up via OAuth (Google / GitHub) from
  a non-sanctioned IP, where the only signal we have is the email
  handle or display name.

The full list of sanctioned jurisdictions is in
[Geographic restrictions → Blocklist](geo-restrictions.md#blocklist).

## List source

The screening matches against the OFAC SDN list. Source:
<https://ofac.treasury.gov/sanctions-list-service>

The EU consolidated list and the UK HMT consolidated list are also
supported.

!!! tip "Refresh cadence"
    OFAC SDN: refresh **daily**. MaxMind GeoLite2: weekly. EU / UK
    consolidated: as published (typically monthly). Restart the
    gateway after each CSV update to pick up the new file.

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
negatives carry regulatory exposure.

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

## Operator override — `NULLRUN_SANCTIONS_SCREENING_DISABLED`

The screening is **ON by default**. The IP-level Fortress geo-block
excludes sanctioned-country traffic before signup; name-based SDN
screening is the secondary layer that catches designated persons
who travel, use a non-sanctioned-country VPN, or register via
OAuth from a non-sanctioned IP.

To **disable** name-based screening entirely (the screening always
returns `Clean`), set:

```bash
NULLRUN_SANCTIONS_SCREENING_DISABLED=1
```

There is no other accepted value — only `1` and the case-insensitive
`true` disable the screening. Any other value (including `0`,
`false`, or an unset variable) leaves screening ON.

### Posture by environment

| Environment | Default |
| --- | --- |
| Production | **ON** — screening active |
| Local dev / sandbox | **OFF** by default — set the override above |

### When to keep it disabled

The dev/local override exists because token-based name matching has
a high false-positive rate at the pre-revenue / pre-customer stage
— a perfectly innocent "Vladimir Petrov" may match an SDN surname
token. With no customers to lose, the maintenance burden (weekly
SDN list refresh, false-positive triage) outweighs the residual
sanctions risk. The geo-block remains the always-on sanctions
defence in every environment.

### When to re-enable

Remove the env var (or set it to `0`) as soon as the service has a
meaningful customer base or accepts payments in volume. The
recommended cutover is at first paying customer, not at first
signup. A regulator's view of "acceptable false-positive cost" is
sharper once money is in the picture.

## Known limitations

- **Cyrillic / Latin homoglyphs are NOT collapsed.** A Cyrillic `а`
  stays Cyrillic after normalisation; only the full-width Latin /
  ASCII cases collapse. A designated individual could circumvent
  name-based screening by transliterating their name to a homoglyph
  script. A non-Latin name from a sanctioned-country IP is still
  blocked by the geo-block.
- **No email-domain match.** Emails are tokenised on `@` and `.`,
  but the resulting tokens (e.g. `gmail`, `mail`) are common enough
  that matching them would produce false positives. The name tokens
  are the primary signal; the email is a secondary, weaker signal.

## Deep dive

### Mechanism
The sanctions screening module lives at `backend/src/proxy/middleware/sanctions.rs`. The `SanctionsTable` struct (lines 103-117) holds an `AHash`-keyed `HashSet<String>` of normalised tokens plus the full `Vec<SdnEntry>` for identity-based matching. `load_or_degraded` (lines 124-161) reads from `data/sanctions/sdn.csv` (path configurable via `NULLRUN_SANCTIONS_CSV`); on missing file or parse failure, `degraded_fallback` (lines 185-221) returns a hand-curated 6-name subset (`Vladimir Putin`, `Kim Jong Un`, `Ali Khamenei`, `Bashar Assad`, `Miguel Díaz-Canel`, `Alexander Lukashenko`) with a `degraded: true` flag. `tokenise` (lines 90-100) NFKC-normalises (catches `ＡＢＣ` → `ABC`), lowercases, splits on non-alphanumeric, drops tokens <3 chars. `screen_signup` (lines 332-356) is the public entry: name first, then email local-part; returns `Clean | Match { matched, field } | DegradedFallback`. The module-level OnceLock caches the table at first call (lines 274-280).

### Guarantees
- **Screening is ON by default**: `NULLRUN_SANCTIONS_SCREENING_DISABLED=1` (or case-insensitive `true`) disables; any other value (or unset) keeps it ON (`sanctions.rs:322-330`). The override is cached at first call (OnceLock per process) — runtime env-var changes do NOT take effect for the running process.
- **Match is opaque to the client**: 403 body does NOT echo the matched display name; the matched name + field (`name` or `email`) are logged at WARN for audit (`sanctions-screening.md:73-75`). Avoiding confirming the screening target is a deliberate disclosure posture.
- **Identity match requires ≥2 tokens OR a 1-token query that matches a 1-token entry** (`sanctions.rs:230-242`): a single shared given name like "Anatoly" does NOT match a 2-token SDN entry like "ANATOLY KOLODKIN" (test at lines 503-512). A shared first name is not enough to identify a sanctioned party.
- **Email TLD does NOT match SDN tokens**: `gmail`/`mail`/`com` are too common to be screened as SDN tokens; only the email local-part is tokenised and matched (`sanctions.rs:248-254`). Tested at `email_tld_does_not_match_sdn_name_token` (lines 489-501).
- **Degraded fallback still allows signup**: the WARN log + `OPERATIONAL_METRICS` flag the misconfiguration; the geo-block is still on at the IP layer as the always-on defence. `is_degraded()` is checked at `sanctions.rs:351`.
- **Token-set collapses the homoglyph space (full-width only)**: `ＡＢＣ` → `ABC` via NFKC, then lowercased and split (`sanctions.rs:90-100`). Tested at lines 374-378.

### Patterns
- **Module-level OnceLock table** (`sanctions.rs:274-280`): `TABLE.get_or_init(...)` reads the CSV exactly once per process; lookups are O(1) per token against the `HashSet`. For 10k SDN entries the memory footprint is ~5 MB.
- **Source-of-list identity column**: OFAC CSV column layout `ent_num, SDN_Name, SDN_Type, Program, ...` — only column 1 (`SDN_Name`) is read (`sanctions.rs:78-86`). EU/UK/UN equivalents share the same column layout.
- **Identity-based match, not token-based**: a single shared word is never sufficient — common first names (`Anatoly`), email TLDs, and corporate suffixes are not unique identifiers (`sanctions.rs:225-242`).
- **Operator override cached at first call**: `sanctions_screening_disabled()` uses a OnceLock per process; changing the env var at runtime does NOT take effect for the running process — restart required.
- **Refresh cadence** (per docs): OFAC SDN daily, MaxMind GeoLite2 weekly, EU/UK consolidated monthly. The table is loaded once at process start; restart is required after each CSV update.

### Approaches
The two-layer model (geo-block + sanctions screen) was chosen because the IP defence alone misses three classes of designated persons: those travelling abroad, those using commercial VPNs that exit in non-sanctioned jurisdictions, and those signing up via OAuth where the only data is name + email. The secondary layer catches the worst cases (designated persons / sanctioned addresses) even when the IP geo-block is bypassed.

The token-match strategy is intentionally aggressive — false positives are cheap (rejected signup, the user retries with a different email); false negatives carry criminal-law exposure per OFAC Sanctions Compliance Guidance for the Financial Sector (2014) and 31 CFR Part 501 (referenced in `sanctions.rs:54-56`). The `NULLRUN_SANCTIONS_SCREENING_DISABLED=1` operator override exists for the pre-revenue stage where the false-positive cost of "Vladimir Petrov" outweighs the residual sanctions risk.

The OnceLock caching of the env-var lookup is intentional: it makes the override decision atomic with process start, so a misconfigured `set_var` later in the process lifetime can't accidentally flip the screening on/off mid-execution. The trade-off is that operators who want to flip must restart the process.

### Limitations
- **Cyrillic / Latin homoglyphs are NOT collapsed** (`sanctions.rs:90-93`): NFKC normalises full-width / ligature forms but does NOT transliterate between scripts. A Cyrillic `а` stays Cyrillic; only the full-width Latin / ASCII cases collapse. A designated individual can circumvent by transliterating to a homoglyph script — the geo-block catches the non-Latin-from-sanctioned-country case.
- **No email-domain match**: emails tokenise on `@` and `.`, but the resulting tokens (`gmail`, `mail`) are too common. The name is the primary, email is secondary (`sanctions-screening.md:128-132`).
- **OnceLock caches the env-var override at first call** (`sanctions.rs:323-329`): changing `NULLRUN_SANCTIONS_SCREENING_DISABLED` at runtime does NOT take effect for the running process — restart required.
- **Degraded fallback covers 6 state actors**: the hand-curated subset (`sanctions.rs:188-195`) is intentionally minimal. A real SDN download is required before production (`sanctions.rs:208-214` WARN log).
- **Refresh cadence is manual**: the table is loaded at process start; the docs note restart is required after each CSV update (`sanctions-screening.md:43-45`). No automatic refresh worker.
- **Pre-existing `email` DB rows are not screen-relevant here**: the screening is signup-time only — historical rows are not re-screened. A redesign that re-screens existing rows on every login is not currently scoped.
