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

### Mechanism
Compliance posture is implemented by two cooperating middleware. **Layer 1 — geo-block** lives at `backend/src/proxy/middleware/geo_block.rs` and runs as Axum middleware mounted in front of auth (`fortress_geo_block_middleware`, line 588); blocked traffic never touches the database. The middleware classifies every request by source country (MaxMind GeoLite2 lookup with 24h in-process DashMap cache) and routes to one of `Allow | BlockSanctioned | BlockHighRisk | RedirectToWaitlist | AllowPrivate`. **Layer 2 — sanctions screening** lives at `backend/src/proxy/middleware/sanctions.rs` and runs at signup in `auth_oauth_register_handler` (per the docstring cross-reference at `sanctions.rs:548-550`); it's the secondary defence that catches designated persons who travel, use a VPN, or register via OAuth from a non-sanctioned-country proxy. The screening table is loaded once at process start into an `AHash`-keyed `HashSet<String>` of normalised tokens (`sanctions.rs:42-44`); lookups are O(1) per token.

### Guarantees
- **Fail-CLOSED on the geo-block**: missing/unreadable GeoIP database → 503 `geoip_unavailable` (`geo_block.rs:696-708`); unparseable peer / XFF → 403 `client_ip_unresolvable` (post-NR-124 fix at lines 642-674). Per CLAUDE.md §4, enforcement paths fail-CLOSED by default.
- **Fail-CLOSED on `extract_client_ip`**: replaces the pre-2026-07-08 `allow, log loudly` posture that allowed the sanctioned-jurisdiction VPN signup bypass; today, an unparseable peer is rejected outright.
- **Sanctions screening is ON by default**: `NULLRUN_SANCTIONS_SCREENING_DISABLED=1` (or case-insensitive `true`) disables; unset or any other value leaves it ON (`sanctions.rs:322-330`). The OnceLock caches the env-var lookup at first call.
- **Match is opaque**: a 403 response on SDN match does NOT echo the matched display name to the client (`sanctions-screening.md:73-75`); the matched name + field (`name` or `email`) are logged at WARN for audit.
- **Sanctions table load is graceful**: missing CSV → hand-curated 6-name fallback with `degraded: true` flag (`sanctions.rs:185-221`); signup still allowed but the operator is alerted via WARN log + `OPERATIONAL_METRICS`.
- **Compliance posture is fail-CLOSED at both layers**: a regression on either one is a compliance incident — never a "we will email you when we do" bridge for strict-liability jurisdictions.

### Patterns
- **Geo-block tiers**: `SANCTIONED` (comprehensive sanctions, 8 codes: RU/IR/KP/SY/CU/BY/VE/MM/AF) and `HIGH_RISK_NO_SERVICE` (GDPR + CCPA + PIPL + DPDPA burden, EU-27 + EEA/EFTA + CH + GB + CN + IN). Both are compiled-in constants (`geo_block.rs:64-86`).
- **Sanctions tokenisation**: NFKC normalise (catches `ＡＢＣ` → `ABC`) → lowercase → split on non-alphanumeric → drop tokens <3 chars (`sanctions.rs:90-100`). A single shared given name like "Anatoly" never matches a 2-token SDN entry (`sanctions.rs:503-512` test).
- **Trust-proxy chain for XFF**: `TRUSTED_PROXY_CIDRS` configures which peers can inject XFF; an XFF from an untrusted peer is treated as attacker-controlled and ignored (`geo_block.rs:357-455`). The BFF→backend hop (single-entry XFF) is handled at line 439-444 so the BFF container IP doesn't cause false classification.
- **Waitlist carve-out**: `WAITLIST_PATH = "/api/v1/waitlist"` is the only bypass for `BlockHighRisk` (`geo_block.rs:783-792`); SANCTIONED-tier IPs are NOT bypassed there. The branch runs AFTER `lookup.action()` so a code refactor that changes the order would re-open the bypass.
- **Headers at WARN only**: country code is PII under GDPR; logged at WARN level, never INFO (`geo_block.rs:761-767`). The `x-nullrun-fortress-block: sanctions` and `x-nullrun-fortress-country: <ISO>` headers carry the wire signal.

### Approaches
The two-layer model (IP + identity) was chosen because the IP defence alone misses three classes of designated persons: those travelling abroad, those using commercial VPNs that exit in non-sanctioned jurisdictions, and those signing up via OAuth where the only data is name + email. Geo-block alone is necessary but not sufficient for OFAC/EU/UK/UN comprehensive-sanctions regimes.

Both layers are fail-CLOSED rather than fail-OPEN because the cost of a 503 (operator notices, fixes the misconfiguration) is lower than the cost of a fail-OPEN (sanctioned traffic silently served). This is consistent with CLAUDE.md §4: enforcement paths are fail-CLOSED by default.

### Limitations
- **Cyrillic / Latin homoglyphs are NOT collapsed** (`sanctions.rs:90-93`): NFKC normalises full-width / ligature forms but does NOT transliterate between scripts. A Cyrillic `а` stays Cyrillic; only the full-width Latin / ASCII cases collapse. A designated individual can circumvent name-based screening by transliterating to a homoglyph script — the geo-block catches the non-Latin-from-sanctioned-country case.
- **No email-domain match** (`sanctions-screening.md:128-132`): emails tokenise on `@` and `.`, but the resulting tokens (`gmail`, `mail`) are too common to screen. Only the email local-part is tokenised and matched.
- **OAuth callback bypass is provisional** (`geo_block.rs:534-555`): sanctioned-jurisdiction visitors can complete OAuth via the BFF until the BFF carries XFF. The secondary name/email screen is the catch.
- **OnceLock caches the env-var override at first call** (`sanctions.rs:323-329`): changing `NULLRUN_SANCTIONS_SCREENING_DISABLED` at runtime does NOT take effect for the running process — restart required.
- **Refresh cadence is manual**: the sanctions table is loaded at process start; the docs note restart is required after each CSV update (`sanctions-screening.md:43-45`). No automatic refresh worker.
