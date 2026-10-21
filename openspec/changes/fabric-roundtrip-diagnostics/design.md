# Design

## Context

`deploy_definition` decodes the submitted and returned definition parts, but currently reports only missing and additional paths in its JSON result. The readable CLI report shows counts, so it does not expose all returned path or text differences. See `proposal.md` and `specs/fabric-definition-roundtrip/spec.md`.

## Goals / Non-Goals

**Goals:**
- Report whether part-path sets match and whether all decoded part text is identical.
- List missing paths, additional paths, and changed text at shared paths.
- Keep service acceptance and exit status independent from part comparison.

**Non-Goals:**
- Parse TMDL or infer semantic equivalence.
- Change the submitted payload, Fabric operations, or existing mappings.
- Fail deployment solely because Fabric normalized, added, omitted, or changed parts.

## Decisions

- Compare the already-decoded `dict[path, text]` values. This avoids comparing Base64 encodings and makes the report independent of JSON part ordering.
- Keep existing `missing_part_paths` and `additional_part_paths` fields, and add `changed_part_paths`, `definition_part_paths_match`, and `definition_parts_textually_identical`. The text-identical flag is true only when the complete path-to-text mappings are equal.
- Extend the human-readable deployment report with the path and text statuses and each non-empty difference list. Empty lists display as `none`.
- Preserve `service_acceptance` and the existing success exit code when create and get-definition succeed, regardless of comparison results. Continue reporting `semantic_equivalence` as `not_asserted`.

Alternatives considered: comparing only part counts cannot detect substitutions; comparing raw JSON or Base64 is sensitive to ordering and encoding; parsing or normalizing TMDL would risk presenting an incomplete parser as semantic verification.

## Risks / Trade-offs

- [Fabric may normalize harmless formatting or synthesize parts] → Report decoded text differences as diagnostics, not failures or semantic mismatches.
- [Exact text equality can be mistaken for semantic equivalence] → Use explicit field and CLI wording that limits the claim to part paths and decoded text.

## Migration Plan

The JSON result is additive and retains existing fields. The readable report gains comparison lines. No migration or rollback is required.
