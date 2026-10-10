# SOC dashboard

The SOC role already has its own page, `/dashboard/soc`, separate from the admin pages. This note records
how the page maps to what a SOC analyst needs, and what was added in the first version of the gaps.

## Wireframe (text)

```
┌ Sidebar ──────┐ ┌ Incidents ───────────────────────────────────────────────┐
│ Incidents  3  │ │ [3 Open] [1 Critical] [1 High] [2 Resolved]              │
│ Security inbox│ │ ┌ Incident queue (severity · id · owner · status) ┐ ┌────┐ │
│ Traffic & pol.│ │ │ Critical  INC-2041  secure-payroll-update…      │ │Det.│ │
│ Risk analysis │ │ │ High      INC-2040  invoice-october.pdf.exe     │ │ail │ │
│ Audit log     │ │ └─────────────────────────────────────────────────┘ └────┘ │
└───────────────┘ └──────────────────────────────────────────────────────────┘

┌ Traffic & policies ─────────────── Last traffic 20 min ago · [● Live] ───────┐
│ [2 Open alerts] [1 SOC blocks] [3 Recent traffic]                            │
│ ┌ Security alerts (urgency · site · when · Allow/Block) ┐ ┌ Domain policy ┐  │
│ ├ Live traffic (when · site · result · Block)           ┤ ├ Most blocked  ┤  │
│ └───────────────────────────────────────────────────────┘ ├ Recent decis. ┤  │
│ Detections per day · Threat intelligence feed · Sign-in history              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Needs mapped to components

| Need | Component | Data source | Status |
|---|---|---|---|
| Alert feed | `IncidentQueue`, "Security alerts" in `ProxyOperationsSection` | `/api/incident`, `/api/proxy/alerts` (+ SSE `alerts/stream`) | existed |
| Severity | `SeverityBadge` (symbol + word, `--sev-*` tokens) | incident and alert `urgency` | existed |
| Blocked-domain activity | "Live traffic" rows, "Recent decisions", **"Most blocked websites"** | `/api/proxy/traffic`, `/api/proxy/verdicts` | summary card added |
| Gateway status | "Live / Reconnecting" chip plus **"Last traffic … ago"** | SSE connection state, newest traffic event | last-traffic text added |

## First-version limits

- "Most blocked websites" counts only the latest 200 traffic events the page already loads, so it is a recent
  window, not a daily or weekly total. A proper time-range total needs a backend aggregate endpoint.
- Gateway status says whether the dashboard's live stream is connected and when traffic was last seen. It does
  not report the proxy process health, certificate state or per-device heartbeats; there is no SOC-level
  endpoint for that. `/api/proxy/device/status` is per device and is meant for the employee view.
