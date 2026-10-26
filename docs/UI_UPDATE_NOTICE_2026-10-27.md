# UI update notice — 27 October 2026

This update consolidates the SOC and employee UI revisions for **Afferent Reflex**.
The next UI/UX pass is the **Administrator dashboard**, including the phishing
campaign workflow. That pass is planned, not completed by this update.

The same development update includes earlier unpublished workflow changes. See
[reports, incidents, roles and assessments](REVIEW_REVISION_2026-10-26.md) and
[ML experiments and release decision](DOMAIN_ML_RETRAINING_2026-10-26.md).
Training experiments do not replace the active runtime model.

## Changes included

- **Brand and typography:** Poppins throughout the interface; blue `Reflex`
  wordmark; English UI copy; calmer text weights and spacing.
- **SOC workspace:** Incidents focuses on assignment and resolution. Charts and
  behavioral analysis are under Insights. Long lists use pagination and details
  open on demand. Donut labels sit below the ring.
- **Reading live traffic:** Pause feed freezes the displayed rows while collection
  and enforcement continue. Stream connection and delayed updates have distinct
  labels; Unknown does not mean malicious.
- **Risk summary:** the card uses its content height instead of stretching to the
  adjacent People card. Header counts and action buttons share vertical alignment.
- **Employee file checks:** styled Browse files, filename/size, Change and Remove;
  consent checkbox aligned beside its text; result panels use status colors and
  provider details. History separates filename, timestamp, verdict and View result.
- **Dropdowns:** removed the legacy style that added a border to the wrapping
  label. Controls have one border, consistent padding, a chevron and theme colors.
  Chrome/Edge can also theme the native options popup with `base-select`.
  Unsupported browsers retain a native picker and the styled closed control.

The employee page's card/grid arrangement is retained. These presentation changes
do not change scoring, file-sharing consent, proxy connection checks or SOC policy
authority. File checks remain private and do not create employee reports.

## Colors

Use the CSS variables instead of copying hex values into individual components.
These are the declared theme values; sidebar colors have their own scoped tokens.

| Purpose / token | Light | Dark |
| --- | --- | --- |
| Accent / `--accent` | `#2563B9` | `#7DB3FF` |
| Strong accent / `--accent-strong` | `#163F77` | `#A9CDFF` |
| Page / `--bg-deep` | `#F3F6FB` | `#0A111C` |
| Base / `--bg-base` | `#F6F9FD` | `#0F1826` |
| Card / `--bg-surface` | `#FFFFFF` | `#152236` |
| Elevated / `--bg-elevated` | `#ECF2FA` | `#1B2C43` |
| Hover / `--bg-hover` | `#E4ECF7` | `#223650` |
| Border / `--border` | `#D9E3F1` | `#2B3E57` |
| Main text / `--text-primary` | `#0B1B33` | `#EDF3FB` |
| Secondary text / `--text-secondary` | `#485C76` | `#B9C8DC` |
| Muted text / `--text-muted` | `#5A6C82` | `#A4B7D0` |
| Danger text / `--text-danger` | `#B42318` | `#FF8575` |
| Warning text / `--text-warning` | `#8C6809` | `#F7D87F` |
| Success text / `--text-success` | `#166534` | `#86EFAC` |

The wordmark uses `#2563B9` on light content surfaces and `#7DB3FF` on dark
surfaces, including the sidebar. Status colors accompany a label or symbol.

| Gradient | Light stops | Dark stops |
| --- | --- | --- |
| Primary action, `120deg` | `#163F77` → `#2563B9` at 62% → `#217C88` | `#235493` → `#286AA1` at 62% → `#246D79` |
| Sidebar, `170deg` | `#142945` → `#183959` at 66% → `#194958` | `#0B1A2F` → `#112D45` at 66% → `#123E49` |

## Fonts and component rules

| Item | Definition |
| --- | --- |
| Main interface and headings | **Poppins**, through `--font-body` / `--font-heading` |
| Loaded Poppins weights | 400, 500, 600, 700, 800; regular copy generally uses 400, compact emphasis 500, section headings 600 |
| Technical identifiers | **JetBrains Mono**, through `--font-mono-data`; loaded weights 400–700 |
| Fallbacks | Arial/sans-serif for the main font; monospace for technical data |
| Base text tokens | 12px metadata, 13px compact controls, 14px body, 16–20px section titles, 24–32px larger headings; components may use a specific token |
| Card / large panel radii | 14px / 18px |
| Select and input radius | 12px |
| Standard action shape | Pill buttons; icon buttons use a 12px radius |
| Spacing | 4px-based scale; common gaps 12px/16px, card padding 24px |
| Dropdown sizing | Minimum height 40px; filter widths remain constrained so changing an option does not resize the filter row |

Keep visible keyboard focus, native field labels and disabled/error states. Do not
turn a select into a clickable generic `div` or add a menu dependency just for
appearance. Do not apply borders to both a field wrapper and its actual control.

## Source map

| File | Responsibility |
| --- | --- |
| `dashboard/src/app/layout.tsx` | Font loading and shared stylesheet imports |
| `dashboard/src/app/globals.css` | Base typography, semantic colors and spacing tokens |
| `dashboard/src/app/warmth.css` | Blue/teal palette, gradients, radii and wordmark color |
| `dashboard/src/app/sidebar-soc.css` | Sidebar colors shared by administrator roles |
| `dashboard/src/app/soc.css` | SOC density, table spacing, alignment and content-sized Risk summary |
| `dashboard/src/app/select.css` | Shared native dropdown appearance and progressive enhancement |
| `dashboard/src/app/ui.css` | Shared tables, filters, buttons, dialogs and pagination |
| `dashboard/src/components/file-upload.css` | File chooser and consent alignment |
| `dashboard/src/components/scan-results.css` | File result panel and history layout |
| `dashboard/src/i18n/messages.ts` | UI copy and existing EN/ID translations |

## Verification and limits

- Latest dashboard Docker build and its TypeScript check passed.
- All 15 frontend behavior/accessibility contract scripts passed.
- Full dashboard ESLint passed with zero warnings.
- Full backend discovery completed: 153 tests, 149 passed and four proxy-runtime
  integration tests skipped because the isolated container has networking/proxy
  runtime disabled. Its source mount was read-only and databases were temporary.
  Test fixtures now establish their own account/secret/schema prerequisites rather
  than depending on discovery order. The retired combined-analysis endpoint is
  checked for HTTP 410 without invoking a provider or model.
- The running dashboard was updated and reported healthy.
- Browser visual review could not be completed through the automation tools;
  screenshot feedback was used to make the follow-up corrections. No measured
  layout-shift score or completed Kali-browser end-to-end test is claimed.
- No mobile-screen testing was performed, as requested.
- The fresh Docker dependency install reported four dependency vulnerabilities
  (three high, one critical). Dependency remediation is still open; this UI
  revision is not a production security sign-off.

The repository submission guard checks candidate files for known local secret
values, private/generated paths and the repository size budget. It is not a
complete secret-history or dependency vulnerability audit. Local credentials,
certificates, databases, bulk datasets and downloaded model weights stay excluded.

## Next: Administrator dashboard UI/UX revision

Status: **planned**. Shared fonts, palette and dropdown improvements are already
available there; a complete administrator page review is still pending.

- [ ] Simplify the overview: prioritize campaign status, completion and employees
  who need follow-up; remove duplicate or low-value explanatory copy.
- [ ] Review campaign creation from employee selection through template/landing
  page, Mailpit delivery settings, final review and launch. Make validation and
  loading/error states clear without changing GoPhish telemetry or scoring.
- [ ] Review template preview and the existing Firecrawl import flow; keep the
  current authorized simulation behavior and education/assessment destination.
- [ ] Align employee management, role/division filters, account forms and tables
  with shared Field, FilterBar, DataTable and Dialog components.
- [ ] Polish the training recommendation inbox: show the assessment result,
  follow-up action, email confirmation and delivery outcome clearly.
- [ ] Check card alignment, long text, empty/loading/error states and light/dark
  contrast across all administrator tabs at desktop sizes.
- [ ] Verify the host/admin plus bridged-Kali employee demo manually: launch a
  Mailpit campaign, open the simulation, confirm education/exam and inspect the
  training recommendation email. Preserve existing accounts and volumes.

Do not mark this checklist complete solely because a build succeeds. The
administrator flow needs a separate UI review and functional walkthrough.
