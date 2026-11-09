# Requirements and acceptance checks

This is the maintained checklist for **DTDL v3 model definitions to Fabric
Ontology new-experience TMDL**. It replaces the completed development plans;
Git history retains those plans. Instance migration and an ADT-compatible
application/device runtime are not part of the converter.

The [DTDL coverage matrix](dtdl-support.md) defines supported mappings.
[Workarounds and boundaries](known-gaps.md) distinguish implemented projections
from guidance. A requirement below does not promise lossless conversion of
unsupported constructs.

## Baseline requirements

Each requirement has regression checks. Passing them proves local behavior,
not service acceptance or equivalent runtime behavior.

| ID | Requirement to check | Automated checks |
| --- | --- | --- |
| REQ-01 | Install and run on Python 3.11+ without runtime dependencies, RDF tooling or .NET. Resolve local inputs offline and enforce input/traversal bounds. | [Installation](../tests/test_installation.py), [loading](../tests/test_loader.py) |
| REQ-02 | Validate supported DTDL declarations before mapping. Report malformed input and unsupported contexts with stable codes, source files, DTMIs and JSON pointers; policies cannot waive invalid source. | [Conformance](../tests/test_conformance_corpus.py), [source regressions](../tests/test_spec_regressions.py), [reports](../tests/test_report.py) |
| REQ-03 | Resolve inheritance, components and named schemas with declaring-source provenance. Detect cycles, missing required definitions and incompatible inherited names; deduplicate shared diamond ancestors. | [Resolution](../tests/test_resolver.py), [extensions](../tests/test_extensions.py) |
| REQ-04 | Inventory the entire input separately from selected roots and dependency closure. Record exclusions and exact omissions; never silently add descendants, guess targets or repair source models. | [Selection](../tests/test_selection.py), [target planning](../tests/test_plan.py) |
| REQ-05 | Default to strict mode. Require explicit, applicable loss policies; compatibility mode alone approves nothing. Reject unknown policies and invalid combinations. | [Options](../tests/test_options.py), [projections](../tests/test_projection.py), [CLI](../tests/test_cli.py) |
| REQ-06 | Use readable names without automatic hashes/version suffixes/truncation. Block case-insensitive conflicts unless explicit aliases resolve them. Keep model version in metadata and lineage source-based; JSON/CI runs must not prompt. | [Readable names](../tests/test_readable_names.py), [naming](../tests/test_naming.py) |
| REQ-07 | Emit only supported target shapes. Require an explicit capability declaration for native single-parent inheritance and separate approvals for lossy projections. Do not invent instance keys, rows or backings for unsupported unbound shapes. | [Target profile](../tests/test_profile.py), [projections](../tests/test_projection.py), [gap diagnostics](../tests/test_gaps.py) |
| REQ-08 | Produce deterministic, safely escaped UTF-8 TMDL parts and a matching InlineBase64 envelope. Emit new-experience parts only, not reports or manifests as upload parts. | [TMDL](../tests/test_tmdl.py), [definition](../tests/test_definition.py), [determinism](../tests/test_naming.py) |
| REQ-09 | Retain source fingerprints, declared revision, roots/dependencies, original schemas/localization, target identities, policies and losses in the manifest. Metadata preservation must not imply enforcement. | [Manifest](../tests/test_manifest.py), [reports](../tests/test_report.py), [readable metadata](../tests/test_readable_names.py) |
| REQ-10 | Check the selected projection against the versioned target limits, including generated edges, inherited properties and provenance metadata. Test exact and one-over boundaries; fail instead of truncating or claiming batching bypasses limits. | [Preflight](../tests/test_preflight.py), [target profile](../tests/test_profile.py) |
| REQ-11 | Publish consistent results through staging, reject nonempty destinations, and return explicit failures. Blocked runs emit diagnostics without a ready payload; write/console failures cannot masquerade as success. | [Publication](../tests/test_publication.py), [CLI](../tests/test_cli.py) |
| REQ-12 | Deploy only on explicit request: create a new item, handle service operations and retrieve its definition. Never overwrite/delete resources or expose tokens. Reject untrusted operation URLs and surface failures. | [Fabric client](../tests/test_fabric.py), [CLI](../tests/test_cli.py) |
| REQ-13 | Compare decoded part paths/text and supported normalized TMDL fields separately from service acceptance. Report unavailable comparisons and approved mapping losses; never assert full semantic equivalence. | [Comparison](../tests/test_semantic.py), [Fabric client](../tests/test_fabric.py), [CLI](../tests/test_cli.py) |
| REQ-14 | Check the specification before vendor samples. Pin downloaded sources, verify checksums, preserve licenses, and keep public docs/examples consistent with recorded evidence. Report unknown extensions as unsupported, not passes. | [Spec harness](../tests/test_spec_harness.py), [independent samples](../tests/test_public_samples.py), [Willow](../tests/test_willow.py), [acquisition](../tests/test_fixture_acquisition.py), [public docs](../tests/test_public_docs.py) |
| REQ-15 | Summarize selected blocking causes, affected models, pending policy reviews and target-limit measurements without dropping diagnostics. Separate non-blocking/excluded findings and count occurrences, not distinct source defects. | [Reports](../tests/test_report.py), [CLI](../tests/test_cli.py) |

Use the [testing commands](testing.md#local-checks) and
[conformance CI](../.github/workflows/conformance.yml). The official specification
sweep and independent parser oracle have their own reproducible checks in
[Testing](testing.md); ordinary local tests do not download fixtures or access
Fabric.

## Service acceptance

Follow the [acceptance procedure](fabric-acceptance.md#reproduce) for a new target
shape or changed serializer, using an explicitly authorized test workspace.

- Record the converter/source revision, options, exact submitted payload
  fingerprint, target profile and actual service outcome.
- Retrieve the definition and inspect names, types, annotations, lineage,
  inheritance and relationship endpoints within the comparator's supported scope.
- Explain differences; successful creation or matching text is not proof of
  data/query equivalence.
- Publish sanitized evidence only. Keep credentials, tenant identifiers and
  private source/evidence out of the repository.

[Recorded acceptance](fabric-acceptance.md) covers definition shapes, including
readable-name Willow output. It does **not** close the data/runtime checks below.
Do not treat old payload fingerprints as acceptance of newly generated payloads.

## Pending acceptance

These are **not verified end to end**. Issues hold the detailed completion
criteria; recording metadata or importing definitions does not mark them done.

| ID | Check still required | Tracking |
| --- | --- | --- |
| ACC-01 | Real rows, keys, bindings, queries, updates/deletes and freshness agree with a small expected dataset. | [Data pilot](https://github.com/falloutxAY/dtdl-to-ontology/issues/29) |
| ACC-02 | Object/component fields remain typed and queryable through tested backings or explicit normalized tables, preserving by-value component paths. | [Objects and components](https://github.com/falloutxAY/dtdl-to-ontology/issues/30) |
| ACC-03 | Targetless/component relationships and reified attributed/parallel edges preserve reviewed targets, ownership, IDs, endpoint bindings and query meaning. | [Relationships](https://github.com/falloutxAY/dtdl-to-ontology/issues/28) |
| ACC-04 | Descendant queries and inherited relationships behave as documented with native inheritance or explicit flattening/ancestry queries. | [Inheritance](https://github.com/falloutxAY/dtdl-to-ontology/issues/32) |
| ACC-05 | Upstream validation checks required/missing/null fields, enum/range errors, temporal values, JSON serialization and effective units. | [Value validation](https://github.com/falloutxAY/dtdl-to-ontology/issues/33) |
| ACC-06 | An explicit large-catalog partition plan fits every item's limits and accounts for identities, dependencies, exclusions and cross-partition edges. | [Scale](https://github.com/falloutxAY/dtdl-to-ontology/issues/31) |
| ACC-07 | Willow owners review unresolved references and invalid annotation/unit declarations before fixture revisions or conversion mappings change. | [Source review](https://github.com/falloutxAY/dtdl-to-ontology/issues/34) |
| ACC-08 | A geometry path preserves coordinates/reference assumptions and has tested query behavior, or remains explicitly unsupported. | [Geometry](https://github.com/falloutxAY/dtdl-to-ontology/issues/27) |

## Keeping this checklist current

For each change, identify the affected requirement IDs, add/update regression
checks, and update the coverage/gap docs when behavior changes. For an acceptance
claim, link reproducible evidence and state its scope; close pending work only
when its completion criteria are met. New requirements need a stable ID and a
test or explicit pending acceptance check, not another planning folder.
