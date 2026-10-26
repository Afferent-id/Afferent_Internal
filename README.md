# Afferent Reflex — Human-Centric Telemetry Security

Lab/demo platform for 5–8 users: email/password + OTP, phishing awareness,
employee reporting, and SOC-controlled proxy monitoring. This checkout is not
a claim of production readiness or regulatory certification.

## Start here

- [Fresh-clone setup](README_SETUP.md)
- [Repository size and team migration](docs/REPOSITORY_SIZE.md)
- [Final submission readiness](docs/FINAL_SUBMISSION.md)
- [Host + bridged Kali VM demo](docs/DEMO_VM_SOC.md)
- [Technical debt checklist](docs/TECHNICAL_DEBT_CHECKLIST.md)
- [UI update notice: colors, fonts and next administrator revision](docs/UI_UPDATE_NOTICE_2026-10-27.md)
- [Centralized proxy](docs/CENTRALIZED_PROXY.md)
- [Selective TLS blocking limitations](docs/SELECTIVE_TLS_DEMO.md)
- [Measured domain-model evaluation](docs/DOMAIN_ML_EVALUATION.md)
- [ML integration contract](docs/ML_INTEGRATION_SPEC.md)
- [Domain algorithm research](docs/DOMAIN_ML_ALGORITHM_REVIEW.md)
- [Latest retraining results and release decision](docs/DOMAIN_ML_RETRAINING_2026-10-26.md)
- [Pitch deck handoff](docs/PITCH_DECK_HANDOFF.md)

## Current stack

Next.js dashboard/BFF → Flask/gunicorn. SQLite preserves accounts, sessions,
phishing telemetry, quizzes, gamification, reports and the email outbox.
PostgreSQL stores proxy traffic/verdicts/SOC alerts/audit; Redis caches verdicts
and transports live events. Squid + opaque tunnel relay enforce domain policy.
GoPhish remains the simulation engine. Mailpit captures OTP and education mail;
a small worker sends education only to active employees below the score threshold.

Proxy inference uses a local **domain-only** calibrated ML model. Employee URL
scans and link reports use VirusTotal/urlscan evidence, never the proxy ML model.
Private file scans use VirusTotal only and create no SOC report or score event.
These providers never process live proxy traffic, including in the background.
Local LLM/Ollama is retired from the active stack; offline artifacts are retained.

Allowed HTTPS is spliced, not decrypted. Denied connections alone use the lab CA
to show `BLOCKED BY AFFERENT REFLEX`. Manual SOC Block/Allow takes precedence. Genuine
ML Unknown is allowed for review; pending/unavailable inference is denied
temporarily, not saved as a malicious verdict.

n8n and Telegram are retired from the active Compose/notification flow. Exports
and old setup documents are recoverable under [archive](archive/README.md);
historical telemetry is retained. External SMTP deployment and new NAC sensors
are Future Work, intentionally not implemented.

## Repository layout

| Directory | Purpose |
| --- | --- |
| `dashboard/` | Employee, SOC and Administrator workspaces; authenticated BFF |
| `backend/` | Flask services, durable application data and isolated regression checks |
| `proxy/`, `gophish/` | Domain-policy enforcement and authorized phishing simulations |
| `docs/`, `scripts/` | Demo runbooks, measured evidence, bootstrap and submission guard |
| `dataset/`, `notebooks/`, `ml/` | Dataset metadata, offline training code and evaluation tools; bulk data is restored separately |
| `archive/` | Historical plans and retired integrations; not part of the active demo |

Training data and experiment results are not automatically trusted or promoted.
Runtime model manifests identify the active artifact and operating point.
The small runtime artifacts in `backend/models/` are included; training CSVs,
downloaded LLM weights and checkpoints are not needed to run the application.
See [dataset restoration](dataset/README.md) before retraining. Run
`node scripts/check_submission.cjs --staged` before publishing changes; it
rejects files over 10 MiB and tracked content over 25 MiB in total.

Copy `.env.example` only for a new setup; preserve existing `.env`,
`.env.proxy.local`, certificates and Docker volumes. Never run `down -v` on a
checkout containing demo data. Do not commit credentials or CA private keys.
