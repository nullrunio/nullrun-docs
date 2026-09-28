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

## Operator override

The screening is **ON by default**. The IP-level Fortress geo-block
excludes sanctioned-country traffic before signup; name-based SDN
screening is the secondary layer that catches designated persons
who travel, use a non-sanctioned-country VPN, or register via
OAuth from a non-sanctioned IP.

To **disable** name-based screening entirely (the screening always
returns `Clean`), set the operator-level override env var to `1`
(or the case-insensitive `true`). Any other value (including `0`,
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

!!! info "Deep dive"

    Identity screening is a token match, and it is deliberately
    blunt. A submitted name is case-folded and normalised across
    full-width character forms, then split on whitespace and
    non-alphanumeric characters; tokens of three characters or
    fewer are discarded, so titles and particles contribute
    nothing. A single shared given name is never sufficient to
    identify a designated party on its own, so a match is
    required against a sufficiently specific entry. The email
    local part is screened after the name, as a weaker secondary
    signal; the domain and top-level part are not screened at
    all, because tokens drawn from them are common enough that
    matching them would reject innocent signups. Cross-script
    transliteration is not performed: a name rendered in a
    different script may not normalise onto a listed form, which
    is a genuine limitation of the approach rather than a detail
    of implementation.

    The network layer answers a different question, where a
    request came from, and neither layer is sufficient alone. A
    person travelling abroad, connecting through a commercial
    proxy that exits in an unremarkable jurisdiction, or arriving
    through a delegated sign-in flow where the only data
    available is a name and an email address, is invisible to an
    address-based check. Screening catches that case; the address
    check catches the volume case. The two run together so a gap
    in one is still covered by the other.

    A match produces a generic rejection that never echoes the
    matched name, so a screening result cannot be used to confirm
    whether a particular individual is listed; the matched name
    and the field that hit are recorded for audit instead. The
    approach is intentionally aggressive, because a false
    positive costs a rejected signup that the applicant can retry
    and a false negative carries regulatory exposure. If the
    reference data cannot be loaded, the layer reports itself as
    degraded, records an alert, and allows the signup to proceed
    on the assumption that the address layer is still intact,
    rather than failing every applicant. Screening applies at
    sign-up only; accounts created earlier are not re-screened.

    Reference data is refreshed on a published cadence, with the
    primary list refreshed daily and the consolidated regional
    lists as they are issued; the service is restarted once an
    update lands. The NullRun team owns that refresh, and a
    current download is required before the service carries real
    traffic.
