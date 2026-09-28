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

!!! info "Deep dive"

    Screening runs in two layers. Every inbound request is
    classified by its network origin before authentication is
    attempted, and every signup is screened against the identity
    data supplied by the applicant. Neither layer is sufficient
    on its own: a network-origin check does not follow a
    designated person across a border, and an identity check made
    only at signup sees nothing about the traffic that later
    arrives from an address we have already refused.

    The network layer's blocklist has two tiers, and the tier
    decides what the request experiences. Jurisdictions under
    comprehensive sanctions regimes are refused outright, on
    both the API surface and the marketing site. Jurisdictions
    carrying a heavy privacy-regime burden are refused on the API
    surface and redirected to a commercial waitlist from the
    marketing site, so that interest is recorded without the
    service being exposed.

    Both layers fail closed. If the geolocation data is
    unavailable, or the screening reference data cannot be
    loaded, the request is refused or the screening layer
    reports itself degraded and raises an operational alert,
    rather than admitting traffic it cannot classify. An operator
    watching every request fail sees the problem within minutes; a
    screening layer that has silently stopped matching produces
    no signal at all. Refusing loudly is the cheaper failure, so
    the service refuses rather than admitting a request it cannot
    classify.

    Identity screening is deliberately blunt and deliberately
    narrow. Names are case-folded and normalised across
    full-width character forms, split into tokens, and screened
    only where a token is long enough to carry signal; a single
    shared given name is never sufficient to match. The email
    local part is screened after the name, as a weaker signal,
    and a match returns a generic response that never echoes the
    matched name. Cross-script transliteration is not performed,
    which is a real limitation. Screening applies at sign-up
    only, and the reference data is refreshed on a published
    cadence, with the NullRun team owning that refresh.
