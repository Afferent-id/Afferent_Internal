# UI issues

Checked on 2026-10-10 in mock mode (`npm run dev:mock`), every role and tab, light and dark, 1440px wide.
No backend was running (Docker was off), so nothing here was tested against real Flask responses.

## Fixed on this branch

- Theme did not follow the operating system. It now follows `prefers-color-scheme` until a choice is saved.
- Second-opinion button (SOC, Traffic) always returned 404 outside mock mode: the BFF allowlist lacked it.
- Chips, badges and language buttons used odd paddings, and the sidebar EN/ID buttons (26px) and sortable
  table headers (28px) were small tap targets.

## Open

| # | Where | Issue | Size |
|---|---|---|---|
| 1 | SOC, Incidents | Incident table is wider than its column; the last column ("R…") is clipped, no scroll hint | medium |
| 2 | Charts (all roles, light) | Bars and donut use the dark `--sev-*` text colours as fills, so they look muddy in light mode; a lighter fill token is needed | medium |
| 3 | Buttons, inputs, `th` | Padding 7/9px relies on the 1px border to reach the 8px grid; correct but not expressed with `--space-*` | small |
| 4 | Whole app | Nothing was verified against the real backend, so unconnected buttons that only fail on real responses are not covered | large |
| 5 | Mock mode | `proxy-check.afferent.invalid` probe logs a console error when offline (expected, ignored in checks) | small |

## Checked and fine

- Contrast: automated WCAG AA check of text vs. effective background found no failures in any role or tab, in
  light or dark. The checker cannot read gradient backgrounds, so white text on the blue "Next step" card
  (employee) was confirmed by eye.
- All 58 `/api/...` calls from the front end resolve to a BFF route; BFF-to-Flask paths match a Flask route.
- Clicking every enabled button on every tab (destructive ones skipped) raised no 4xx/5xx, page errors or
  console errors.
