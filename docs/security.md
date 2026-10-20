# Security design

This document describes defensive behavior present in the inspected code. It is not a security certification, and a scan result does not prove that a repository is secure.

## Threats and controls

| Threat | Control | Implementing file | Test |
| --- | --- | --- | --- |
| Archive path traversal or absolute paths | Normalize archive names, reject traversal, absolute paths, drive prefixes, invalid names, and reserved Windows device names. | `backend/app/core/security.py` | `backend/tests/test_security.py`, `backend/tests/test_hardening.py` |
| Extraction outside the temporary workspace | Resolve the target and require it to remain under the extraction root. | `backend/app/core/security.py` | `backend/tests/test_security.py` |
| Symlink or special-file extraction | Reject symlinks and special file entries for uploads; skip unsafe entries in lenient GitHub ingestion. | `backend/app/services/repository_service.py` | `backend/tests/test_github_service.py`, `backend/tests/test_hardening.py` |
| ZIP bombs and oversized archives | Limit upload bytes, archive entries, extracted files, individual files, total extracted bytes, and extraction time. | `backend/app/core/middleware.py`, `backend/app/services/repository_service.py`, `backend/app/core/config.py` | `backend/tests/test_hardening.py`, `backend/tests/test_upload_api.py` |
| Binary or irrelevant source content | Inspect a prefix for NUL bytes and extract only supported extensions or known filenames. | `backend/app/services/repository_service.py` | `backend/tests/test_hardening.py`, `backend/tests/test_upload_api.py` |
| Scanner command injection | Invoke tools with argument arrays and no shell interpretation. | `backend/app/scanners/base.py` | `backend/tests/test_hardening.py` |
| Scanner access to application secrets | Provide a restricted subprocess environment rather than forwarding the parent environment. | `backend/app/scanners/base.py` | `backend/tests/test_hardening.py` |
| Scanner hangs or excessive output | Apply subprocess timeouts and output-size limits. | `backend/app/scanners/base.py`, `backend/app/core/config.py` | `backend/tests/test_hardening.py` |
| Resource exhaustion from concurrent scans | Limit active scans and return a retryable busy response. | `backend/app/services/scan_service.py`, `backend/app/services/github_service.py` | `backend/tests/test_hardening.py` |
| SSRF through GitHub scanning | Accept only HTTPS `github.com` repository or branch URLs and allow redirects only to `github.com` or `codeload.github.com`. | `backend/app/services/github_service.py` | `backend/tests/test_github_service.py`, `backend/tests/test_github_api.py` |
| GitHub download abuse | Limit redirects, download size, download duration, and response statuses; only public repository archives are supported. | `backend/app/services/github_service.py` | `backend/tests/test_github_service.py` |
| Leaking internal exception details | Convert unexpected API exceptions to a generic 500 response. | `backend/app/main.py` | `backend/tests/test_hardening.py` |
| Browser framing, MIME sniffing, referrer, and caching risks | Add `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Cache-Control` headers without overriding route-specific values. | `backend/app/core/middleware.py` | `backend/tests/test_hardening.py`, `backend/tests/test_report_api.py` |
| Unsafe or misleading AI prompt input | Place finding data inside an explicit untrusted-data block rather than system instructions. | `backend/app/ai/prompts.py` | `backend/tests/test_ai_explanations.py` |
| Invalid or oversized AI responses | Limit provider response and completion sizes, parse structured output, normalize fields, and retry invalid model output once where implemented. | `backend/app/ai/provider.py`, `backend/app/ai/explanation_service.py`, `backend/app/ai/patch_service.py` | `backend/tests/test_ai_explanations.py`, `backend/tests/test_fix_service.py` |
| AI output being mistaken for scanner evidence | Store explanations and fix suggestions in separate tables, make report inclusion opt-in, and label AI content. | `backend/app/db/models.py`, `backend/app/services/report_service.py` | `backend/tests/test_report_api.py` |
| Automatic source modification from generated patches | Store a proposed diff for review; do not apply it. Mark generated patches as untested. | `backend/app/ai/patch_service.py`, `backend/app/api/routes/fixes.py` | `backend/tests/test_fix_service.py`, `backend/tests/test_report_api.py` |
| Database orphan records after scan deletion | Use SQLAlchemy cascade relationships for findings and related optional records. | `backend/app/db/models.py`, `backend/app/db/repository.py` | `backend/tests/test_scan_history_api.py` |

## Dependency scanner boundaries

- Bandit analyzes Python files when Bandit is installed.
- Semgrep is optional, uses the repository's local rules, and may be unavailable on native Windows.
- pip-audit collects only exact `name==version` lines from `requirements.txt`, then invokes pip-audit with `--disable-pip` and `--no-deps`. Its vulnerability lookup needs internet access.
- npm audit requires a `package-lock.json` beside `package.json` and invokes `npm audit --json --package-lock-only`. Its vulnerability lookup needs internet access.
- Scanner coverage is reported per run. An unavailable, skipped, failed, partial, or timed-out scanner is not equivalent to a clean scan.

## Operational guidance

- Run the backend in a controlled environment and keep the example environment file free of real credentials.
- Treat uploaded source, scanner evidence, and AI output as untrusted data.
- Keep AI credentials only in a private environment configuration.
- Review every generated diff before applying it outside the application.
- Do not expose the unauthenticated API to untrusted users without adding authentication, authorization, and deployment controls.

## Known gaps

- There is no authentication or authorization in the inspected application.
- Scanner processes are not isolated in an operating-system sandbox.
- Scans run synchronously, so a deployment must account for long-running requests.
- Dependency checks depend on external network services and can be unavailable or incomplete.
- The scanner set does not include ESLint or a general JavaScript/TypeScript static analyzer beyond the configured Semgrep rules.
- There are no frontend unit tests in the current project.
- The application does not claim exhaustive vulnerability coverage; unsupported languages, rules, files, unavailable tools, skipped entries, and failed dependency lookups can leave coverage gaps.
- The inspected project initializes database tables with SQLAlchemy metadata and does not include a migration workflow.
