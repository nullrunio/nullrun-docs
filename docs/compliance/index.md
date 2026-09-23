---
title: Index
description: NullRun's compliance posture: geo-block at the network edge, sanctions screening at signup, and what to expect when rules degrade.
---

# Compliance

NullRun enforces geo and sanctions restrictions at the edge gateway. Two
cooperating layers control jurisdiction-based access:

| Layer | Purpose | Reference |
| --- | --- | --- |
| Geo restrictions | Classify every inbound request by source country and apply allow / hard-block / waitlist actions. | [Geographic restrictions](geo-restrictions.md) |
| Sanctions screening | Match signup name and email against the OFAC SDN list (with EU / UK / UN lists supported as additional CSVs). | [Sanctions screening](sanctions-screening.md) |

Sanctions violations are strict-liability; see legal review for full
rationale. A regression on either layer is a compliance incident.

## Deep dive

!!! info "Deep dive"

    Compliance posture is implemented by two cooperating
    middleware. **Layer 1 — geo-block** lives at
    `backend/src/proxy/middleware/geo_block.rs` and runs as Axum
    middleware mounted in front of auth
    (`fortress_geo_block_middleware`); blocked traffic never
    touches the database. The middleware classifies every
    request by source country (MaxMind GeoLite2 lookup with 24h
    in-process DashMap cache) and routes to one of `Allow |
    BlockSanctioned | BlockHighRisk | RedirectToWaitlist |
    AllowPrivate`. **Layer 2 — sanctions screening** lives at
    `backend/src/proxy/middleware/sanctions.rs` and runs at
    signup in `auth_oauth_register_handler` (per the docstring
    cross-reference at `sanctions.rs`); it's the secondary
    defence that catches designated persons who travel, use a
    VPN, or register via OAuth from a non-sanctioned-country
    proxy. The screening table is loaded once at process start
    into an `AHash`-keyed `HashSet<String>` of normalised
    tokens (`sanctions.rs`); lookups are O(1) per token.

    Both layers fail CLOSED. On the geo-block, missing/unreadable
    GeoIP database returns 503 `geoip_unavailable`
    (`geo_block.rs`); an unparseable peer / XFF returns 403
    `client_ip_unresolvable` (post-NR-124 fix). Per CLAUDE.md §4,
    enforcement paths fail-CLOSED by default — this replaces the
    pre-2026-07-08 `allow, log loudly` posture that allowed the
    sanctioned-jurisdiction VPN signup bypass. Sanctions
    screening is ON by default:
    `NULLRUN_SANCTIONS_SCREENING_DISABLED=1` (or case-insensitive
    `true`) disables; unset or any other value leaves it ON
    (`sanctions.rs`). The OnceLock caches the env-var lookup at
    first call. Match is opaque: a 403 response on SDN match
    does NOT echo the matched display name to the client
    (`sanctions-screening.md`); the matched name + field
    (`name` or `email`) are logged at WARN for audit. The
    sanctions table load is graceful — missing CSV returns a
    hand-curated 6-name fallback with a `degraded: true` flag
    (`sanctions.rs`); signup is still allowed but the operator
    is alerted via WARN log + `OPERATIONAL_METRICS`. A
    regression on either layer is a compliance incident — never
    a "we will email you when we do" bridge for strict-liability
    jurisdictions.

    Geo-block tiers are `SANCTIONED` (comprehensive sanctions, 9
    codes: RU/IR/KP/SY/CU/BY/VE/MM/AF) and `HIGH_RISK_NO_SERVICE`
    (GDPR + CCPA + PIPL + DPDPA burden, EU-27 + EEA/EFTA + CH +
    GB + CN + IN). Both are compiled-in constants
    (`geo_block.rs`). Sanctions tokenisation is NFKC normalise
    (catches `ＡＢＣ` → `ABC`) → lowercase → split on
    non-alphanumeric → drop tokens <3 chars (`sanctions.rs`).
    A single shared given name like "Anatoly" never matches a
    2-token SDN entry (`sanctions.rs` test). The trust-proxy
    chain for XFF is `TRUSTED_PROXY_CIDRS`-configured: an XFF
    from an untrusted peer is treated as attacker-controlled
    and ignored (`geo_block.rs`). The BFF→backend hop
    (single-entry XFF) is handled so the BFF container IP
    doesn't cause false classification. Waitlist carve-out is
    `WAITLIST_PATH = "/api/v1/waitlist"` — the only bypass for
    `BlockHighRisk` (`geo_block.rs`); SANCTIONED-tier IPs are
    NOT bypassed there. The branch runs AFTER `lookup.action()`
    so a code refactor that changes the order would re-open the
    bypass. Country code is PII under GDPR and is logged at WARN
    level, never INFO; the `x-nullrun-fortress-block: sanctions`
    and `x-nullrun-fortress-country: <ISO>` headers carry the
    wire signal.

    The two-layer model (IP + identity) was chosen because the
    IP defence alone misses three classes of designated persons:
    those travelling abroad, those using commercial VPNs that
    exit in non-sanctioned jurisdictions, and those signing up
    via OAuth where the only data is name + email. Geo-block
    alone is necessary but not sufficient for OFAC/EU/UK/UN
    comprehensive-sanctions regimes. Both layers are fail-CLOSED
    rather than fail-OPEN because the cost of a 503 (operator
    notices, fixes the misconfiguration) is lower than the cost
    of a fail-OPEN (sanctioned traffic silently served) —
    consistent with CLAUDE.md §4.

    Cyrillic / Latin homoglyphs are NOT collapsed
    (`sanctions.rs`): NFKC normalises full-width / ligature
    forms but does NOT transliterate between scripts. A
    Cyrillic `а` stays Cyrillic; only the full-width Latin /
    ASCII cases collapse. A designated individual can circumvent
    name-based screening by transliterating to a homoglyph
    script — the geo-block catches the
    non-Latin-from-sanctioned-country case. There is no
    email-domain match (`sanctions-screening.md`): emails
    tokenise on `@` and `.`, but the resulting tokens (`gmail`,
    `mail`) are too common to screen — only the email local-part
    is tokenised and matched. OAuth callback bypass is
    provisional (`geo_block.rs`): sanctioned-jurisdiction
    visitors can complete OAuth via the BFF until the BFF
    carries XFF — the secondary name/email screen is the catch.
    The OnceLock caches the env-var override at first call
    (`sanctions.rs`): changing
    `NULLRUN_SANCTIONS_SCREENING_DISABLED` at runtime does NOT
    take effect for the running process — restart required.
    Refresh cadence is manual: the sanctions table is loaded at
    process start; restart is required after each CSV update
    (`sanctions-screening.md`) — no automatic refresh worker.
