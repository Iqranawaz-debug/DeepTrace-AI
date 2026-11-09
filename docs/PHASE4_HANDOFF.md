# Phase 4 handoff — Evidence-Grounded Synthesis and Reporting

Prepared 2026-10-28 on `feature/phase3-evidence-collection` (HEAD `17c2bf1`).
**Nothing was committed, staged, pushed or merged.** Exact validation commands
and results are in TESTING.md.

## What Phase 4 is (and is not)

A deterministic, local, **user-authored** synthesis workflow. The user classifies
evidence, writes claims and selects citations. DeepTrace validates references and
quotations and renders an immutable Markdown report from a fixed template. **No
language model, provider or network is used.** Nothing is generated, inferred or
auto-cited. Per ADR-A04/A14 and DATABASE §5.11, a valid citation means only that
the passage exists, is active, belongs to this investigation and (if quoted)
contains the quotation after NFC and whitespace normalization, case-sensitively.
It **does not** mean the passage supports the claim.

## Implemented

- **Evidence review** (`evidence_notes`). Any saved passage can be linked to the
  main question or a plan step, with the classification `unreviewed`, `supports`,
  `contradicts`, `context` or `insufficient`, and an optional note. Each is
  labelled as the user's judgment. Revisioned optimistic updates; one review per
  passage per target. If a plan step is later removed, the saved label snapshot is
  kept and flagged (`target_current:false`), never retargeted. The UI counts
  passages without a review.
- **Draft report** (`answers`, one per investigation). Scope, methodology,
  summary, limitations and next steps, plus up to 30 ordered claims typed as
  finding, interpretation, conflicting evidence, unsupported hypothesis, missing
  evidence or user conclusion. Each claim has up to 10 citations with a relation
  (supports, contradicts or context) and an optional exact quotation. Whole-draft
  saves are atomic and revision-checked (409 on stale).
- **Citation integrity.** Every citation is validated **before** anything is
  written. A fabricated, cross-investigation or removed passage, or a quotation
  mismatch, rejects the whole save with 422 and a position-only reason (for
  example `claim 1 citation 1: quote_mismatch`); nothing is silently dropped. The
  database also enforces composite `(passage_id, investigation_id)` foreign keys.
  Each citation stores the SHA-256 of the passage text, so a later text change
  would surface as `passage_changed` rather than silently retargeting.
- **Evidence state.** A claim is `cited` only if it has at least one valid
  **supporting** citation; otherwise it is `not_established`. The state is
  recomputed on every read and at report creation, so a stored label can never
  outlive its evidence. Contradicting-only claims remain `not_established` and
  show the contradicting evidence.
- **Immutable report versions** (`report_versions`). Creating a version requires
  the current draft revision, revalidates every citation, renders Markdown, stores
  its SHA-256 and increments `version_no`. An UPDATE trigger forbids changes. Reads
  and downloads re-verify the checksum (500 `report_integrity` on mismatch).
  Viewing a version shows contextual warnings ("older version", "draft changed")
  without touching the stored bytes.
- **Report contents** (template `manual-template-v1`): research-aid disclaimer
  (citation validity ≠ support; no automated verification), a SIMULATED EVIDENCE
  banner when the evidence is mock, version, timestamps and draft revision,
  question, scope, summary, each claim with its type and Cited/Not-established
  state, citations (passage ID, relation, source, character offsets, reference
  check, matched quotation or "withheld" if not matching), supporting /
  conflicting-or-missing / contextual-and-unreviewed evidence groups, user and
  automatic limitations, next steps, methodology plus recorded process (run count,
  saved-but-unretrieved URLs, no searches executed, check totals) and references
  (source ID, original/canonical URL, status, retrieval/extraction times,
  extraction version, text hash, "author and publication date unknown", and the
  extraction limitation).
- **Safe rendering.** User and source text is escaped so it cannot form HTML,
  links, images, emphasis, code, tables, headings, quotes, lists or thematic
  breaks. URLs and hashes are code spans. The in-app preview shows the exact stored
  bytes as React text in `<pre>`; there is no Markdown/HTML renderer and no remote
  images.
- **Export.** `GET …/reports/{n}/download` returns the stored bytes as a
  `text/markdown` attachment named `deeptrace-report-<id8>-v<n>.md`, with
  `nosniff` and an `X-Report-SHA256` header. The file name is server-chosen, and
  nothing is written to the server filesystem. Markdown is the only format,
  following DESIGN §8.8 / FR-07.4; PDF was not added.
- **UI.** A new `/investigations/:id/report` route ("Report"), linked from an
  `Investigation` navigation in the workspace (DESIGN §7.2). It shows evidence
  review, the draft editor (unsaved-change protection reused from Phase 2; edits
  kept on failure, with the server's reason shown), citation chips that open the
  saved passage dialog with its checks, version selection (`?version=n`), the
  check summary, SHA-256, the download link and the exact file preview.

## Recorded spec deviations (owner review needed)

1. **`answers`/`report_versions` without a run.** DATABASE §5.11/§5.12 assume a
   model-generated answer tied to a run. Here the draft is user-authored:
   `run_id`, `provider_id`, `model_id` and `generated_at` are NULL (provider and
   model are constrained to NULL), and `authorship='user'`. `report_versions.run_id`
   is NULL, `prompt_version` holds the template version, and `answer_revision`
   records which draft revision was rendered.
2. **Disclaimer wording.** DESIGN's fixed string "AI-generated research aid…"
   would be false here, because no AI generated anything. The report states that
   it is a user-authored research aid instead.
3. **Additional tables.** `saved_urls` and `evidence_notes` are not in DATABASE.md.
   `evidence_notes` follows the M3 "human-review data distinct from model output"
   principle. No M3 `claim_assessments` exist.
4. **Report creation trigger.** DESIGN §8.8 defers the trigger for new versions
   and has no "Edit report" control. Here, editing happens on the draft and each
   explicit "Create report version" adds an immutable version.

The five specifications were **not** modified.

## Database (migration 005_evidence_synthesis)

Adds the unique index `passages(id,investigation_id)` (the parent key for
composite FKs) and the tables `evidence_notes`, `answers`, `claims`, `citations`
and `report_versions` (with an immutability trigger), with CHECK limits on every
text field and enum. The migration is additive; earlier migrations are unchanged.
The populated 003 → 005 upgrade preserves sources and passages, and a failing 005
rolls back all pending migrations, with the backup verified by tests.

## API (all under `/api/investigations/{id}`; mutations need Origin + token + JSON)

| Method | Path | Contract |
|---|---|---|
| GET | `/passages?offset=` | Active passages with source title/status/origin (50/page) |
| GET / PUT | `/evidence-notes` | List / create (`expected_revision:0`) or update (revision) |
| GET / PUT | `/answer` | Draft with recomputed states and per-citation checks / atomic save |
| GET / POST | `/reports` | Version list / create from `expected_revision` (201) |
| GET | `/reports/{n}` | Stored Markdown, summary, warnings (checksum-verified) |
| GET | `/reports/{n}/download` | Attachment of the exact stored bytes |

Errors use the existing envelope: 404 for unknown or foreign IDs (no existence
leak), 409 for stale or duplicate, 422 for validation or invalid citation, 413
for the size limit. The 64 KiB request-body cap still applies, so a very large
draft is refused with 413 instead of being truncated.

## Security and privacy

Ownership is enforced in every query and by composite FKs. The local
Host/Origin/token/content-type guard covers all new mutations (tested). No new
outbound path, dependency, telemetry, credential or model exists. Hostile text
tests cover HTML, script, link and image injection in the stored report and the
browser.

## Limitations and remaining risks

- Classifications and claim types are user judgments. There is no semantic
  support assessment (M3), no confidence metrics and no automated contradiction
  detection.
- The evidence pool is synthetic fixtures until live fetching is approved, so
  every report is labelled SIMULATED.
- At most 200 passages are offered in the UI picker (4 × 50), 30 claims, 10
  citations per claim, and a 64 KiB request body.
- There is no investigation/report deletion, retention workflow or PDF export.
  Reports are immutable, so sensitive text stays until a future, approved
  deletion workflow exists.
- Quote matching is NFC/whitespace-normalized and case-sensitive only; it
  does not accept paraphrases.
- Accessibility: automated axe checks (serious/critical) and keyboard paths were
  tested; this is not a manual WCAG/NVDA certification.

## Re-audit addendum (2026-10-29)

A second full audit against an expanded checklist re-ran every gate (see
TESTING.md) and checked the code, not just this handoff.

- **Gap fixed: claim reordering.** The draft editor had no way to reorder
  claims, even though claims are ordered. It now has keyboard-accessible
  **Move up / Move down** controls per claim, with the same naming and
  live-region announcements as the Phase 2 plan editor. The new order takes
  effect on **Save draft**.
- **Tests added** (`test_phase4_integrity.py`, 10 tests):
  - Mixed collection: a success plus a failure gives `failed/partial_collection`,
    and the successful passages are kept.
  - Limits: 31 claims, 11 citations and duplicate citations are refused with 422,
    with nothing saved.
  - An oversized draft returns 413, and the saved draft is unchanged (not
    truncated).
  - Context-only and contradicting-only claims are `not_established`, and the
    contradicting citation is still shown.
  - Out-of-band passage tampering gives `passage_changed`: the claim becomes
    `not_established` on read and is marked REFERENCE INVALID in a new report.
  - A removed passage is never valid.
  - Requests involving another investigation are refused: download returns 404,
    and invalid version, invalid ID and malformed JSON are rejected.
  - Malformed, JavaScript-only and Unicode HTML fixtures.

  All passed on first run; none exposed a product defect.
- **Owner review (dependency), not changed:** httpx 0.28.1 and httpcore 1.0.9 are
  runtime dependencies, but no application module imports them. Only the test
  client uses httpx. They are the reason certifi (MPL-2.0) is in the runtime
  closure. Moving them back to development-only would shrink the runtime licence
  surface, but it is a dependency change, so it needs explicit approval.
- **Passages can't currently be removed.** Migration 003 constrains
  `passages.removed_at` to NULL, so "inactive passage" is reachable only through
  the kernel (unit-tested). A future deletion workflow must re-run these checks.
