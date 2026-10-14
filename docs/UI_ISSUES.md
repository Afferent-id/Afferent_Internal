# UI issues

Checked on 2026-10-10 in mock mode (`npm run dev:mock`), every role and tab, light and dark, 1440px wide.
No backend was running (Docker was off), so nothing here was tested against real Flask responses.

## Fixed on this branch

- Theme did not follow the operating system. It now follows `prefers-color-scheme` until a choice is saved.
- Second-opinion button (SOC, Traffic) always returned 404 outside mock mode: the BFF allowlist lacked it.
- Chips, badges and language buttons used odd paddings, and the sidebar EN/ID buttons (26px) and sortable
  table headers (28px) were small tap targets.
- (2026-10-14) SOC incident table no longer clips its last column: low-priority columns drop out in narrow boxes
  and a table that is still wider shows a scroll shadow (only when it really overflows) and scrolls by keyboard.
  The CISO posture page uses the same incident list, so it changed in the same way.
- (2026-10-14) Charts use per-theme `--chart-*` tokens (at least 3:1 against the card) and carry shapes or value
  labels, so they no longer rely on colour alone.

## Open

| # | Where | Issue | Size |
|---|---|---|---|
| 1 | Every role | axe-core `heading-order` (moderate): section titles are `h3` directly under the page `h1`, no `h2`. Present before this branch (checked on 6e54d59). Found 2026-10-14, not fixed yet | small |
| 2 | GRC Audit log / Leaderboard / Compliance / Accounts, SOC Threat intelligence and Sign-in & devices tabs | axe-core `landmark-unique` (moderate): two regions share one accessible name. Present before this branch. Found 2026-10-14, not fixed yet | small |
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

## Backlog (decided 2026-10-14)

- Fix the two axe moderate findings above (heading levels, unique region names) as their own change.
- Run the real flows against the Docker stack before the PR: email OTP sign-in (dev/test mechanism, no real Telegram
  token), Request access from the blocked page, and the toast and bell for an answered request; then every tab of
  every role, noting console errors and 4xx/5xx. Everything on this branch so far was checked in mock mode.
- The dark sidebar is applied to the SOC role only (`data-role="soc"`); roles are not decided yet, so GRC, CISO and
  Phishing admin keep the current sidebar.
- Live traffic and alerts tables on phones scroll sideways (the Action column stays in view); a card layout would
  avoid that but is a bigger change.
