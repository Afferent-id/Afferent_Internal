# Dashboard, reports and assessment revision

This is a local lab revision for Afferent Reflex. Existing accounts, telemetry,
proxy connection probes, certificates and Docker volumes are preserved.

## Access roles

The supported roles are Administrator (`phishing_admin` internally), SOC (`soc`)
and employee (`employee`). GRC/CISO records remain in the database for historical
audit, but cannot sign in, complete an outstanding OTP, or reuse an existing
session. Their former dashboard URLs return 404. An administrator can deliberately
assign a supported role to a retained account; there is no automatic privilege upgrade.

## URL and file checks

- Live proxy traffic uses the existing domain ML path only. It never invokes VT,
  urlscan or a local LLM.
- Employee Scan URL and Report a link use the same VT/urlscan evidence. A VT 404
  now queues a URL submission and bounded analysis polling rather than treating a
  lookup miss as a completed scan. Status reads do not submit another scan.
- Poll results are account-owned. API key rejection, provider quotas, missing
  records and incomplete analyses remain explicit; none means safe or blocked.
- Failed/Unknown file checks can be retried by explicitly uploading the file with
  consent again. Known completed results remain deduplicated. Files are opaque,
  size-limited and private; they do not create SOC reports or alter domain policies.
- The shared VT request budget still applies. Queued provider work can take a few
  minutes, especially with a free API quota. Browser status refresh does not call VT.
- A link report creates a stable linked incident. Later provider evidence refreshes
  its evidence, retaining the existing reward dedupe/daily cap. Evidence never
  silently overrides an explicit SOC decision.

## SOC incident workflow

1. Employee submits Report a link. It appears in SOC Incidents with reporter and
   source, as well as the security inbox. Existing employee reports are backfilled
   once; their previous SOC resolutions are imported with original actor/reason/time
   when available, without issuing a new proxy decision. Historical tickets remain
   marked as historical.
2. SOC takes ownership with Assign to me. Another analyst cannot steal or resolve
   that assignment. The owner can release it for another analyst.
3. Resolve incident requires Block domain or Allow domain and a reason of at least
   five characters. The policy covers the domain and its subdomains for proxy users.
4. Resolution applies the existing authoritative proxy policy and then closes the
   incident. If policy storage fails, the incident remains open. Retrying the same
   resolution uses a stable request ID and does not duplicate the proxy decision.
5. Incident history is append-only and includes actor, time, before/after state,
   request ID and source alert. Reopening retains the current proxy policy; it does
   not undo a previous Block/Allow. A further policy change requires another decision.

The queue refreshes on SOC server events, with a 30-second fallback refresh. An
employee sees submitted, under review after assignment, and resolved/false positive
after their incident's Block/Allow resolution.

## Campaign assessment and training inbox

New campaigns default to the configurable click gateway, `/simulation/entry`,
through `SIMULATION_ENTRY_URL` or `SERVER_BASE_URL`. Keep its hostname the same as
the dashboard so the existing employee session cookie is recognized. GoPhish is
contacted at a fixed internal listener, `GOPHISH_PHISH_INTERNAL_URL`; the browser
cannot choose an upstream. GoPhish open/click/submission telemetry is retained.
Credential field values are not forwarded by the gateway.

A click verified through the GoPhish API queues one assessment per employee and
campaign when the score after the click is below `EXAM_SCORE_THRESHOLD` (60/200).
The gateway sends that employee to the exam before displaying the simulated login
form. A RID never signs somebody in. Unauthenticated visitors must use their employee
SSO account. Older campaigns using the direct GoPhish URL retain their existing
landing behavior; the worker/education page still syncs their clicks and the app
opens a required assessment. Use a newly launched gateway campaign for the immediate
click-to-exam demo.

The assessment has 15 versioned basic phishing questions. Answers are graded on the
server, results cannot be overwritten by resubmission, and another employee cannot
open the attempt. Exactly 80% passes; below `EXAM_PASS_PERCENT` (80) appears as a
training recommendation in **Administrator → Security inbox**. Email is sent only
when the administrator adds a recommendation and chooses Send email. The existing
durable Mailpit outbox handles retries and deduplicates by assessment. The result,
recommendation, actor and delivery status are retained.

### Cross-inbox email coordination (27 October follow-up)

Administrator training recommendations and SOC baseline warnings share one
recipient-wide pending/cooldown check, including optional automatic education.
An email awaiting delivery or retry blocks another approval. After delivery the
configured `EDUCATION_COOLDOWN_SECONDS` (default 24 hours, minimum one hour) is
measured from the later of creation/delivery time. Cancelled, ineligible sends do
not count as delivered mail. Approval checks and insertion share the same SQLite
write transaction, so simultaneous administrator/SOC requests create one email.
The assessment's own recommendation remains idempotent by exam ID.

Both inboxes display the persisted outcome. The SOC delivery record joins each
approval to its actual outbox status; it is not proof of delivery merely because
an approval exists. Existing audit entries and already delivered duplicates are
retained. No schema change or cleanup of historical records is required.

For the click-to-exam flow, an authenticated employee using the same hostname as
the new gateway campaign is redirected to **Start assessment** once the verified
click makes the score strictly below the threshold: 60 to 50 triggers it, while
70 to 60 does not. The employee presses Start to request fullscreen and fetch
questions; the app does not silently start the exam. Direct GoPhish links from
older campaigns and delayed telemetry do not guarantee an immediate redirect.

The web exam requests fullscreen and prevents copy/cut/paste/context menus inside
the assessment. Tab hiding, window blur and fullscreen exit are recorded, bounded
to 100 observations per attempt. They are informational and do not alter the grade.
A browser cannot prevent OS screenshots or access to other applications; this is
not an OS kiosk. No screenshot-prevention claim is made.

## Manual two-machine verification

1. On Kali, open the dashboard using the Windows host's reachable LAN IP or DNS
   name. Sign in as employee; enable the OS proxy and keep the existing CA setup.
   On the host, use a separate browser to sign in as SOC.
2. Check an unrecorded public URL: see queued/pending VT state followed by a result.
   Check a non-confidential file with consent. Provider Unknown is not a safe verdict.
3. Report a link; find its `RPT-…` incident in SOC. Assign it, choose Block and add a
   reason. Reconnect/request the domain from Kali and verify the block behavior.
   Reopen and resolve with Allow to verify the reverse flow and history.
4. Keep the existing proxy ON/OFF check unchanged: the employee card must still
   reflect the actual connection, and traffic monitoring must remain ML-only.
5. Use an employee below 60/200 and launch a **new** Mailpit campaign with the
   default gateway URL. Click its link while signed in as that employee. Complete
   15 answers, including a tab switch to inspect the observation log.
6. For a result below 80%, sign in as Administrator, open Security inbox, review the
   result and queue a recommendation. Inspect the delivered email in Mailpit.
   Exactly 12/15 should pass and should not offer a training email.

No mobile-screen testing is required for this revision.

## Verification completed locally

- 65 targeted backend regressions passed, including assessment grading, three-role
  access control, VT URL/file handling, incident ownership and historical resolution
  migration. Nine campaign checks and 11 compatibility checks also passed (85 total).
- Fourteen frontend checks, TypeScript, ESLint and the Docker dashboard build passed.
- All nine Compose services reported healthy after activation. SQLite integrity was
  `ok`; six previously blocked and one previously allowed employee reports retained
  their closed resolutions. No migration backlog remained.
- A real PostgreSQL transaction verified decision retry deduplication. All smoke-test
  writes were rolled back; no live proxy policy was added by that check.
- Live unauthenticated access to exam, training inbox, incidents and scan status
  returned 401. The public health endpoint returned 200.
- Existing credentials, volumes and PKI were retained. A SQLite backup was created
  in the database volume's `backups/` directory before migrations.
- The full Kali-browser exercise above remains a manual validation task. Provider
  lifecycle tests used fixtures; the earlier live VT lookup returned HTTP 200, but
  no real employee file was uploaded as part of these checks.
