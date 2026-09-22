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

| Environment | Default | Source |
| --- | --- | --- |
| Production (`infra/docker-compose.prod.yml`) | **ON** — env var not set | `sanctions.rs:325-328` (`unwrap_or(false)` ⇒ `disabled == false` ⇒ screening active) |
| Local dev (`infra/docker-compose.local.yml`) | **OFF** — default `1` | Compose line 155: `NULLRUN_SANCTIONS_SCREENING_DISABLED: ${NULLRUN_SANCTIONS_SCREENING_DISABLED:-1}` |

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
