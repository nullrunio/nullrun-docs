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
