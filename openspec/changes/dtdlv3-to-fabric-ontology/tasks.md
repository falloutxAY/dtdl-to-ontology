# Tasks

## 1. Package and target-contract baseline

- [ ] 1.1 Create the Python package, console entry point, pytest configuration, and formatter/linter configuration without RDF or .NET dependencies; verify the installed CLI help and a package import work on the documented minimum Python version.
- [ ] 1.2 Define the versioned Fabric target feature/limit profile and establish whether unbound entity relationships are accepted using authoritative contract evidence or an authorized minimal service check; verify the support matrix records evidence and a regression test keeps unverified mappings disabled.
- [ ] 1.3 Add pinned Willow fixture acquisition metadata and checksum verification for commit 1d19b2584df02e05714628a57a7ddd69edeef29c, excluding the bundled Metadata collection; verify acquisition is an explicit setup action and retain source license/attribution.
- [ ] 1.4 Document analyze versus convert, ontology-first scope, offline resolution, and local versus service verification; verify CLI help matches the documented command forms.

## 2. DTDLv3 loading and resolution

- [ ] 2.1 Implement directory/collection loading with source paths, JSON pointers, version checks, bounded input processing, and duplicate-identifier diagnostics; verify focused tests cover equivalent forms, malformed JSON, conflicting duplicates, and unsupported versions.
- [ ] 2.2 Implement interface/schema indexing and reference resolution with cycle detection and shared-schema provenance; verify missing component schemas, missing named schemas, recursive shapes, and inheritance cycles report source-addressable failures.
- [ ] 2.3 Implement effective-content inheritance with declaring-identity diamond deduplication and incompatible-name detection; verify focused tests prevent last-write-wins conflicts and preserve ancestor provenance.
- [ ] 2.4 Add local quantitativeTypes, annotation, and overriding v1 vocabulary support and context checks; verify TemperatureUnit resolves without a local interface and annotates/overrides are retained as instance metadata semantics.
- [ ] 2.5 Add full-input inventory, explicit root selection, dependency reasons, and retained-target closure; verify unrelated models remain inventoried but excluded, omitted relationships are recorded, and absent by-reference targets differ from missing required schemas.
- [ ] 2.6 Document the implemented DTDLv3 subset and resolver limits with representative unsupported examples; verify the examples produce the documented findings without network resolution.

## 3. Compatibility planning and provenance

- [ ] 3.1 Implement stable finding codes, fidelity/severity categories, selected versus unselected findings, and JSON/readable reports; verify a source-level fixture produces matching machine and human explanations.
- [ ] 3.2 Implement strict defaults and named policy validation for inheritance, collections, enums, temporal strings, components, metadata-only semantics, and explicit relationship omission; verify compatibility mode alone approves no losses and unknown policies fail.
- [ ] 3.3 Implement element-specific concrete relationship target mappings and visibly marked missing-target placeholders, subject to the target relationship support gate; verify no unconstrained target, guessed repair, or placeholder is emitted by default.
- [ ] 3.4 Implement relationship-property reification planning with deterministic edge-role identities and explicit endpoint diagnostics; verify edge properties are preserved and unverified endpoint relationships cannot be enabled by the reification policy alone.
- [ ] 3.5 Implement the complete manifest including fingerprints, revision, original schemas, localized metadata, root/dependency selection, transformations, and exclusions; verify large metadata remains intact in sidecars and does not become an unsupported definition part.
- [ ] 3.6 Publish the known-gap catalog with workarounds, residual losses, and no-payload-only-solution entries from design.md; verify every implemented finding category links to its corresponding documentation.

## 4. Direct TMDL and definition emission

- [ ] 4.1 Implement deterministic namespace/name/UUIDv5 lineage assignment and shared TMDL escaping; verify shuffled inputs, DTMI versions, case collisions, quotes, newlines, and source text resembling declarations.
- [ ] 4.2 Implement primitive, fixed-object complex struct, and explicitly approved collection/enum/temporal mappings; verify representative decoded TMDL snapshots and reject invented array/map kinds.
- [ ] 4.3 Implement approved flattened inheritance, component property projection, and opt-in native single-parent inheritance; verify unsupported profiles emit no rollout-only keywords and multiple parents never silently select a winner.
- [ ] 4.4 Implement explicit inherited relationship projection and edge-entity output only for accepted target relationship shapes; verify unsupported/unverified shapes block or require source-specific approved omission, without fabricating tables or backing configurations.
- [ ] 4.5 Emit platform/database/model/default namespace parts, entity references, readable part files, and the UTF-8 InlineBase64 definition envelope; verify required parts, compatibility level, metadata version, path conventions, and decode equality.
- [ ] 4.6 Document concrete strict and policy-approved conversion examples plus native inheritance prerequisites; verify each example against the implemented CLI and focused fixtures.

## 5. Preflight and safe result publication

- [ ] 5.1 Implement selected-target count, property, annotation, name, complex graph, and whole-document limit checks using the versioned profile; verify exact-boundary and one-over-boundary tests, including relationship expansion beyond 10000.
- [ ] 5.2 Implement consistent output staging, rejection of nonempty destinations, nonzero conversion failures, and diagnostic-only failed results; verify blockers and write failures cannot publish a ready payload or overwrite earlier successful output.
- [ ] 5.3 Integrate analyze/convert exit behavior, policy configuration, target verification status, and report summaries; verify analysis completion cannot be mistaken for successful conversion or a verified live import.
- [ ] 5.4 Document output artifacts, failure recovery, target limits, and the distinction between transport batching and item capacity; verify the documented failure examples against tests.

## 6. End-to-end acceptance

- [ ] 6.1 Run full pinned-Willow inventory and assert 3705 interfaces, extension usage, multiple inheritance, and the absent LeaseContract target; verify source-only input, report completeness, and explicit whole-source strict blockers.
- [ ] 6.2 Define a reproducible bounded Willow selection and explicit policies that exercise inheritance, components, objects, collections, enums, and units; verify exact dependency/exclusion manifests, deterministic payloads, applicable target limits, and any intentional relationship omissions.
- [ ] 6.3 Exercise focused telemetry and command fixtures through the CLI; verify missing binding/runtime behavior is reported and neither Willow nor metadata-only preservation is claimed as execution coverage.
- [ ] 6.4 Run the package's targeted tests, lint/format checks, and full end-to-end commands; verify all local checks pass and fix only failures relevant to this converter.
- [ ] 6.5 Deliver a manual Fabric create/get-definition acceptance procedure and, if an authorized workspace is available, record normalized round-trip results and feature state; otherwise record service verification as blocked/unverified and leave affected mappings gated, without claiming deployment success.
