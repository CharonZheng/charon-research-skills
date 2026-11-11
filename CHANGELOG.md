# Changes

## journal-submission-prep 0.3.0 — 2026-11-11

- Add offline environment diagnostics that run without DOCX dependencies.
- Aggregate six delivery checks with manuscript, report, PDF and page-image hashes; missing evidence remains incomplete.
- Keep authorized content-edit review separate from strict formatting integrity checks.
- Return exit code 3 when mandatory `check` rules remain unresolved or unchecked. Update callers that previously treated the absence of failures as completion.
- Include PDF hash and expected font families in CLI layout reports.
- Publish synthetic DOCX examples, behavior tests and a Linux/Windows CI matrix outside the installable skill.
- License original code under MIT, retaining upstream notices.

The new aggregator checks records, not their truthfulness: policy interpretation, render provenance and page inspection still require actual reviewer/agent work. Table reconstruction, native multilevel-numbering repair and reference-manager plugin automation are not added in this release.
