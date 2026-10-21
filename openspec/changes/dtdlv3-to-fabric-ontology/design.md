# Design

## Context

See proposal.md for motivation and the three capability specs for the behavior contract. The workspace contains OpenSpec and assistant configuration but no converter, package manifest, application tests, or existing capability specs. This is a greenfield Python implementation, not an adaptation of existing application code.

The user confirmed Python and ontology-first output for the first version. Fabric's new experience accepts TMDL parts, including ontology-only extensions; its old entity-type JSON format is not the target.

Read-only exploration of Willow source at commit `1d19b2584df02e05714628a57a7ddd69edeef29c` found:

| Source construct | Count |
| --- | ---: |
| Interfaces, all DTDLv3 | 3705 |
| Interfaces with multiple direct parents | 225 |
| Declared properties / relationships / components | 1384 / 111 / 62 |
| Relationships without targets / with properties | 22 / 12 |
| Object / Array / Map / Enum declarations | 69 / 16 / 49 / 166 |
| ValueAnnotation / Override occurrences | 388 / 362 |
| Telemetry / Command declarations | 0 / 0 |

The bundled collection has 3699 interfaces and differs from the source tree. It must not be mixed into the fixture. Lease.regulatedBy references an absent LeaseContract interface; by-reference relationship targets do not necessarily invalidate DTDL, but cannot silently become resolved Fabric targets.

Structural name-based inheritance expansion estimated 24363 effective relationship declarations and 122054 effective properties across all interfaces. These are planning estimates, not validated compiler output. They already exceed the 10000 entity-relationship limit under naive relationship projection. A hypothetical table-per-interface mapping would use `2 + 3705 + 122054 = 125761` of the 16000 combined table/column engine budget, before components. That future data-backed estimate is not an ontology-first payload measurement.

## Goals / Non-Goals

**Goals:**

- Separate source interpretation, compatibility decisions, and serialization so unsupported semantics cannot disappear during rendering.
- Preserve source identity and meaning outside the constrained target using a complete sidecar manifest.
- Make complete-source analysis useful even when whole-source conversion is blocked.
- Produce reproducible bounded projections with explicit policies and measurable capacity.

**Non-Goals:**

- Full certification as a general-purpose DTDL validator or support for every extension.
- Live data binding, telemetry ingestion, device commands, cloud deployment, or automatic tenant feature discovery.
- A lossless native representation of all Willow semantics in one item.
- Automatic partitioning across Fabric items, generic-twin runtime projections, normalized collection child tables, or an RDF compatibility layer.

## Decisions

### 1. Pure Python compiler with explicit supported semantics

Use a small installable Python package with a `src` layout, a console entry point, pytest, and a formatter/linter. Prefer standard-library JSON, hashing, UUID, path, and Base64 support; add dependencies only when they solve a demonstrated need. Proposed minimum Python version is 3.11.

Microsoft's .NET DTDLParser would reduce semantic-validation work, and Willow uses it, but a mandatory .NET bridge conflicts with the selected Python distribution. Implement a deliberately bounded resolver and publish its support matrix; do not claim parity with the official parser.

Preserve raw declarations alongside normalized typed records. A source index keyed by DTMI resolves interfaces and named schemas. Built-in extension vocabulary definitions are versioned local data, not network lookups. Resolve inheritance with cycle detection and declaration-aware diamond deduplication. Ambiguous name collisions block rather than use last-write-wins semantics.

Validate interpreted source shapes before applying loss policies: enum literals
must match their primitive type and have distinct names/values, while omitted or
empty enumValues is valid. Relationship state must contain distinctly named
Properties; multiplicities, target identifiers, writable flags and adjunct unit
value types are checked before omission or target mapping. Compatibility is not
permission to repair invalid source declarations. Diagnostics retain entry-level
JSON pointers, including malformed values that would otherwise raise Python type
errors. This strengthens the bounded subset without claiming full parser parity.

### 2. Separate analysis from output selection

Provide `analyze` and `convert` commands. Both accept an input directory or collection file. Analyze inventories the whole input; convert additionally accepts explicit root DTMIs, a target feature profile, and repeated named compatibility policies. No roots means all input interfaces, never an automatically selected small sample.

Compute an explicit dependency closure through inheritance, schemas, components, and retained relationship targets. Record why each dependency was included. Do not include descendants automatically. Effective inherited relationships are planned explicitly because Fabric does not propagate ordinary relationships through inheritance.

Selection is a user-directed bounded projection, not a promise that every root produces a small result. Missing dependencies and target expansion can still block it. Explicit relationship omission can bound a projection only when approved and visible as loss. Findings outside the selection remain in the full inventory without pretending they were converted.

### 3. Compatibility decisions precede TMDL rendering

Every planned transformation has a stable finding code and one of: supported, lossy, unsupported, or unverified. Severity and target verification are separate fields. Strict conversion blocks lossy, unsupported, and unverified selected mappings unless the applicable policy resolves them; an unsupported or unverified operation cannot be enabled by a blanket permissive flag.

Initial named policies:

| Policy | Behavior | Loss or constraint |
| --- | --- | --- |
| flatten-inheritance | Materialize effective compatible properties and explicitly plan inherited relationships | No equivalent native multiple-parent type hierarchy or inherited polymorphism |
| json-collections | Map arrays and dynamic maps to string properties containing JSON | No native collection shape or typed element queries |
| json-objects | Map fixed objects and projected component structs to JSON-string properties after full source and mapping analysis | No native field typing/querying; downstream ingestion must serialize values; original and resolved logical shapes remain in the manifest |
| enum-underlying | Emit the enum's string or integer value type | Allowed-value and label semantics require external validation |
| temporal-strings | Preserve date, time, and duration as ISO-formatted strings | No corresponding native temporal operations |
| component-properties | Analyze component properties as recursive structs; unbound publication additionally requires json-objects string projection | Component identity and relationship semantics remain separately reported |
| metadata-semantics | Preserve units, source width distinctions, writable flags, annotation/override links, localization, and constraints as metadata/manifest | Metadata storage does not execute source behavior |
| reify-relationship-properties | Introduce an edge entity with a stable role identity, edge-ID property definition, typed edge properties, and endpoint relationship declarations | Does not preserve native attributed-edge identity; depends on accepted unbound endpoint relationships |
| omit-relationships | Omit only explicitly identified relationships | Deliberate graph incompleteness; never implicitly applied to every relationship |

Native single-parent inheritance is opt-in and requires a target feature profile affirming rollout support. Multiple-parent native projection remains unsupported; initial implementation uses approved flattening rather than arbitrarily choosing a parent. Reusable properties are not necessary for the initial output.

Concrete target mappings and missing-target placeholders require element-specific configuration. A placeholder is visibly marked and never presented as the absent source definition. Unknown policy names and invalid combinations fail. Input-invalidating conflicts cannot be waived by a compatibility policy.

### 4. Use only ontology-first parts

Generate `.platform`, `database.tmdl`, `model.tmdl`, the default namespace, additional namespaces as needed, entity files, and supported entity relationship declarations. Do not generate tables, source expressions, partitions, runtime rows, or data bindings.

Use the documented database compatibility level 1000000 and platform config version 2.0. Include model references even though the service can synthesize some of them. Definition-part paths use Fabric's slash-separated API convention, independently of local filesystem separators.

Unbound entity/property support is documented. Unbound entity-relationship acceptance is not established by the inspected example, which shows backing configurations. Before enabling that mapping, obtain authoritative contract confirmation or a small service acceptance result. If unavailable or rejected, report the relationship mapping as unverified/unsupported and allow only an explicit omission; do not invent backing tables. This is an acceptance gate with a defined fallback, not permission to claim support.

Live acceptance on 2026-10-20 established a narrower property boundary: Willow
Address passed with three entity types and six unbound string properties, but
Building's fifteen struct properties failed ComplexLogicalBackingMismatch because
structs require exact recursive backing. Update the profile and gate every planned
fixed-object/component struct before publication. Explicit json-objects approval
changes the whole emitted property to string only after nested metadata, runtime,
relationship and source checks have run. Keep the pre-fallback logical shape in
the manifest and issue one source-addressable loss finding per emitted property.
Component identity loss still independently requires component-properties.
No data backings, runtime JSON values or new deployment client are introduced.

The converter emits the definition envelope, not an authenticated create-item request. Item display name is a user input; derive a stable local logical identity unless explicitly supplied. Never use a model identifier as a runtime instance key.

### 5. Deterministic identity and safe serialization

Map full source DTMI namespaces to valid Fabric namespaces and include the DTMI version in target naming. Derive UUIDv5 lineage tags from the complete source identity plus mapping role, including component paths and generated edge roles. Resolve sanitized and case-insensitive collisions using stable identity-derived suffixes, not enumeration order.

Implement one TMDL identifier/text serializer, including quoted names, multiline doc comments, annotations, and JSON-assignment complexDataType lines. Use canonical JSON ordering, stable file ordering, and UTF-8 encoding before Base64 packaging. Do not insert raw source names, comments, or descriptions as TMDL syntax.

Primitive mappings are string to string, boolean to boolean, integer/long to int64, float/double to double, and dateTime to dateTime. Preserve source distinctions in the manifest. Fixed objects are analyzed as recursive structs, but publication requires the explicit JSON-string fallback while native structs require real backings. Never invent an array or map complex kind.

### 6. Sidecars and publication

Successful output consists of `definition.json`, `manifest.json`, `report.json`, `report.md`, and readable definition parts under a dedicated parts directory. Only actual Fabric parts are included in definition.json; no report or manifest is uploaded as an arbitrary part.

The manifest records source revision if supplied, input-content fingerprints, root selection, dependency reasons, original schemas and localized metadata, target identities, policies, and exclusions. Avoid timestamps and random IDs in deterministic content. Respect annotation size/count limits by keeping complete data in sidecars rather than truncating it.

Reject nonempty output directories instead of deleting or overwriting a previous run. Stage a new result and publish it only after preflight succeeds. Failed runs provide diagnostics without a ready payload; reports state analysis and emission outcomes separately. A successful local result is labeled locally validated, service acceptance unverified unless explicit evidence exists.

### 7. Versioned limit preflight

Measure the planned target, not only raw source declarations. Track at least 10000 entities, 10000 entity relationships, 1000 properties per entity, 100 annotations/synonyms per object, 4000 characters per annotation value/description, and 512 characters for ordinary names. Complex shapes have depth 32, 4096 nodes, and 1024 fields per struct. Apply documented whole-document backstops of 1000000 JSON nodes and depth 160.

The logical model's 10000 relationship limit is distinct from the Base64 envelope's collection length. Document the exact counting representation and boundary tests; if transport or tenant limits are unknown, retain an explicit service-unverified status instead of inventing thresholds.

Record the documentation revision/profile used. Changing a limit profile cannot declare an unsupported semantic mapping supported. Stop before publication on any exceeded supported limit; batching does not evade per-item constraints.

### 8. Known-gap catalog

Maintain these entries in user documentation and emit matching finding categories:

| Gap | Short-term treatment | Remaining limitation |
| --- | --- | --- |
| Multiple inheritance | Approved flattening, retain all parents in manifest | No native multiple-parent semantics |
| Inheritance rollout | Flatten when approved or require confirmed feature profile | Unsupported tenants reject native inheritance keywords |
| Inherited ordinary relationships | Explicit expansion, omission, or blocker | Fabric does not inherit them; expansion can exceed capacity |
| Deep polymorphism | Record ancestor closure for downstream explicit queries | Documented native query expansion is only one hop |
| Components | Property projection; separately handle contained relationships | No complete native component equivalent |
| Unbound fixed objects/component structs | Block, or explicitly approve json-objects with full provenance | Live service requires recursive backing for native structs; JSON strings lose native field typing/querying |
| Arrays and dynamic maps | Approved JSON strings | No native array/map kinds or typed collection queries |
| Enums | Approved primitive mapping with allowed values in manifest | No native allowed-value enforcement |
| Relationship properties | Approved edge-entity reification when endpoint mappings are accepted | Not native attributed edges; ordinary junction tables do not expose edge properties |
| Untargeted relationships | Explicit target mapping or omission | No unrestricted native toEntity |
| Missing relationship target | Block, approved placeholder, or omission | Missing source meaning cannot be reconstructed |
| Quantity/unit semantics | Preserve vocabulary and metadata | No established automatic dimensional reasoning or conversion |
| ValueAnnotation/Override | Retain source links and instance properties | Metadata does not implement effective per-instance overrides |
| Date/time/duration | Approved ISO strings | Native temporal semantics differ |
| Writable state and commands | Metadata and unsupported-runtime findings | No payload-only device execution or synchronization |
| Telemetry | Preserve source construct and report required future bindings | No ingestion, stream correlation, or fabricated time series |
| Localization and DTMI versions | Deterministic names plus manifest | Display names are server-derived; full localization is not native |
| Multiplicity and constraints | Preserve and require upstream validation | Table cardinality and natural-language rules are not enforcement equivalents |
| Capacity | Smaller explicit projection or stop | No lossless naive whole-Willow projection; batching is not a workaround |
| Data bindings and instance keys | Defer to later explicitly configured stage | Cannot derive real source tables/columns/keys from schema alone |
| Unbound relationship acceptance | Verify before enabling, otherwise block or approved omission | Not verified by the supplied reference example |

Normalized child-entity collections and generic-twin projections are documented alternatives, not first-version implemented fallbacks.

### 9. Acceptance strategy

- Unit fixtures cover reference cycles, diamond inheritance, collisions, shared schemas, extension vocabulary, instance unit overrides, components, nested objects, collections, enums, temporal primitives, relationship properties/targets, escaping, deterministic naming, and policy rejection.
- Focused telemetry and command fixtures test explicit diagnostics because Willow has neither construct in this snapshot.
- Pin Willow by commit and file fingerprints; retain MIT attribution for any vendored extracts. Fetching a public fixture is a deliberate setup step, never runtime model resolution.
- Full-source analysis asserts 3705 interfaces and records the known missing relationship target. Expanded counts are regression measurements with explained algorithms, not brittle claims of official parser equivalence.
- A small representative Willow root selection exercises inheritance, components, collections, enums, and units with explicitly named policies. Assert exact inclusions, exclusions, report findings, and actual target limits. Do not modify Willow source to make it pass.
- Compare decoded emitted parts to expected TMDL and validate the REST envelope; use golden snapshots only for meaningful representative outputs.
- Build a wheel without fetching runtime dependencies, install it in a clean
  Python 3.11 environment, and run the CLI from outside the checkout. Verify both
  strict success and non-waivable invalid-source failures from that installation,
  not only the editable development package.
- Extend negative regressions when source-shape gaps are reproduced, then rerun
  the full pinned source and bounded Willow CLI projection. Keep prior output
  directories unchanged and record any newly diagnosed source issues explicitly.
- Separately perform or document a manual Fabric create/get-definition round trip against an available test workspace. No deployment client is added. Compare normalized semantics, not byte-for-byte equality, because the service elides defaults and synthesizes parts. Record tenant feature state and relationships/inheritance acceptance. If access is absent, record the service check as blocked, not passed.
- Repeat the bounded Building service check with json-objects approved, wait for
  create completion, retrieve using the working default-format request, and compare
  target properties, types and lineages. Keep rejected and accepted evidence
  separate; platform-owned logicalId normalization is not entity-lineage loss.

## Risks / Trade-offs

- [Python resolver diverges from DTDL semantics] -> Keep raw provenance, a bounded support matrix, focused official-example fixtures, and explicit unsupported findings rather than permissive JSON-only interpretation.
- [All-source inventory is mistaken for successful conversion] -> Separate inventory, selected projection, blocker counts, emitted artifacts, and service-verification status.
- [No tested Fabric serializer for ontology extensions] -> Narrow hand-authored serialization to documented grammar and require representative round-trip evidence before claiming service acceptance.
- [Relationship projection causes combinatorial growth] -> Plan concrete endpoints and count before rendering; require smaller roots or explicit omissions.
- [Persisting metadata is mistaken for enforcement] -> Report each lost runtime/validation behavior and retain a no-payload-only-solution category.
- [Documentation or tenant rollout changes] -> Version the target profile and distinguish user-declared features from actual service verification.
- [Metadata exceeds target limits] -> Keep complete originals in the manifest; never silently truncate or add unknown definition parts.

## Migration Plan

No existing application or stored format requires migration. Introduce the CLI and support matrix with the first implementation release. Keep outputs separate from inputs and require new/empty output locations. Rollback is selecting the previous converter release and its explicit target profile; no cloud mutation occurs during conversion.

## References

- Fabric definition contract: https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition
- Inheritance behavior: https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-inheritance
- Pinned Willow source: https://github.com/WillowInc/opendigitaltwins-building/tree/1d19b2584df02e05714628a57a7ddd69edeef29c/Ontology/Willow
- Willow existing parser tooling: https://github.com/WillowInc/opendigitaltwins-building/blob/1d19b2584df02e05714628a57a7ddd69edeef29c/Tools/DTDLMerger/Program.cs
- DTDLv3: https://github.com/Azure/opendigitaltwins-dtdl/blob/master/DTDL/v3/DTDL.v3.md
- Annotation extension: https://github.com/Azure/opendigitaltwins-dtdl/blob/master/DTDL/v3/DTDL.annotation.v1.md
- Overriding extension: https://github.com/Azure/opendigitaltwins-dtdl/blob/master/DTDL/v3/DTDL.overriding.v1.md
