# Supported DTDLv3 interpretation

The Python resolver is deliberately not a certified replacement for Microsoft's
DTDLParser or a general JSON-LD processor. Source objects and locations are kept
even when a target mapping is unavailable.

## Inputs and limits

- Local JSON Interface objects, arrays of Interface objects, or directories of
  such files. A DTDLv3 root is required; locally included v2 dependencies retain
  their own version rules.
- Inline Interfaces in `extends` and Component `schema`, and permitted local
  dependent references, with global identifier uniqueness and Interface partition
  referenceability. Private schemas are not reusable across Interfaces, including
  through inheritance or Components.
- Explicit and normative automatically assigned element identities are indexed
  separately from unchanged target naming/lineage conventions.
- Named Array, Enum, Map, and Object schemas declared inside Interfaces.
- Core primitive schemas, plus local quantitativeTypes v1 unit vocabularies.
- Annotation, overriding and historization v1/v2; MQTT v1/v2/v3; Requirement v1.
  Active contexts are inherited by nested elements; an explicit newer context
  replaces the older context in the same family. Canonical aliases are checked
  against their active version before normalization.
- Core/class/property/schema aliases, material-type arrays, singleton set values,
  permitted singleton scalar arrays, representational literals, language maps
  and arrays of language-tagged values. Duplicate member aliases and invalid
  scalar cardinalities, language tags/defaults and literal types are rejected.
- Six standard geospatial schemas, by compact term or canonical standard DTMI.
- No remote contexts, implicit JSON-LD expansion, top-level schema-only documents,
  or unknown extension contexts.
- At most 20,000 files, 16 MiB per file, 128 MiB total, 1,000,000 JSON value
  nodes per file, and 128 defensive JSON/graph traversal levels. These are input
  resource guards, not language limits. Recursive dependent graphs are rejected.
- Symlink inputs and files outside the input root are rejected.

Diamond inheritance deduplicates the original declaration. Distinct incompatible
declarations with the same effective name block conversion. The parent graph and
all compatible declaring origins remain traceable; file order is not precedence.

Arrays/maps, enums, components, units, writable state, and relationships can be
resolved without having a faithful Fabric mapping. Resolution is not emission.

## Normative source limits

These non-waivable limits use the pinned DTDL v3 specification, independently of
Fabric preflight and defensive traversal limits:

| Source bound | Limit |
| --- | --- |
| Original UTF-8 Interface text, excluding descendant Interface text | 1 MiB |
| Inheritance path | 10 `extends` members |
| Values in the inheritance hierarchy | 1,024 |
| Values in the defined contents hierarchy, including inherited declarations | 100,000 |
| Complex-schema path | 5 `schema`/`elementSchema` links |
| Component inside a Component through `schema`/`contents` | Forbidden |
| User Interface / other element or reference / generated system DTMI | 128 / 2,048 / 4,096 characters |

Versionless and major.minor DTMIs are valid v3 source identities. User-authored
identifiers cannot use reserved system segments or the DTDL/standard namespaces.
Byte accounting uses original JSON text, including whitespace and Unicode bytes,
not normalized or reserialized objects. Diamond traversal counts shared
declarations once. A large file of individually valid Interfaces is not treated
as one oversized Interface.

V2 dependencies additionally retain bounded v2 checks for one-part versions,
64-character names/display names, Object/Enum counts, direct parents, inherited
contents, and arrays/geometries below Properties. This is not a standalone v2
converter or a claim of exhaustive v2 conformance.

## Source-to-target disposition matrix

| Construct | Source interpretation | Target disposition without new workarounds |
| --- | --- | --- |
| Interface, identifiers, aliases, singleton/literal/localized forms | Normalize with original objects, pointers and active contexts retained | Equivalent forms produce deterministic native output where their semantics are supported |
| Inheritance and inline parents | Resolve parents, conflicts, partitions and cycles | Single native parent requires the existing tenant declaration; multiple inheritance remains a gap |
| Property | Validate members, flags and schema | String, Boolean, long, double and dateTime are direct; widths, writable state and other constraints are separate losses |
| Telemetry / Command / request / response | Validate all declarations, including schemas that will not be emitted | Ingestion, correlation and device-command execution remain runtime gaps |
| Component and Relationship | Resolve Interface references, nested state and target syntax | Component identity/backings and unbound/attributed edges remain gated |
| Array / Map / Enum | Validate elements, keys/values, entry names, literals and dependencies | Typed collections and enum enforcement remain gaps |
| Object / Field | Validate optional/empty fields, nesting and dependencies | Unbound native structs remain backing-dependent |
| Primitives and quantitative units | Recognize the pinned primitive/unit vocabularies and quantity contracts | Temporal operations, numeric widths, unit conversion and dimensional reasoning are not inferred |
| ValueAnnotation / Override v1/v2 | Resolve effective sibling links and schema/context/property contracts | Instance-level overrides are not Fabric `redefines`, conversion, or enforcement |
| Historized v1/v2 | Validate Property/Telemetry co-types and retain capture intent | Non-waivable `HISTORIZATION_BINDING`; no fabricated history table |
| MQTT v1/v2/v3 | Validate versioned co-types, topics, payload, ttl/index and result/error contracts | Non-waivable `MQTT_RUNTIME`; no transport or serializer is invented |
| Requirement v1 | Record optional-by-default and explicit Field+Required | Non-waivable `FIELD_PRESENCE` for required fields; no invented TMDL keyword |
| Standard geospatial schemas | Recognize all six identities and coordinate-array shapes | Non-waivable `GEOSPATIAL_MAPPING`; no native geometry/array kind or new JSON fallback |
| Unknown contexts, arbitrary JSON-LD expansion, remote dependencies | Out of scope; explicit incomplete/unsupported diagnostics | Never silently interpreted or uploaded |

The authored positive/negative corpus covers 24 declared feature categories;
generated regressions exercise actual boundary/one-over values and every material
family. This is bounded evidence, not universal parser certification.
See [conformance evidence](conformance-evidence.md) for the independent parser,
CI coverage gate, Willow sweep and live acceptance distinctions.

## Validation before mapping policies

Enums may omit `enumValues` or provide an empty array. When entries are present,
each needs a valid programming name and an `enumValue` matching `valueSchema`.
Names and wire values must be unique. Integer literals are signed 32-bit integers,
not booleans; explicit entry types must be `EnumValue`.

Relationship state contains only uniquely named Properties, not Telemetry or
other content kinds. Content names and boolean `writable` flags are checked.
When specified, `minMultiplicity` must be integer zero, `maxMultiplicity` a positive
signed 32-bit integer, and `target` a syntactically valid DTMI. An absent target
remains distinct from an invalid target.

These checks run before compatibility policies. `enum-underlying` cannot approve
an invalid enum, omitting a relationship cannot hide malformed state, and target
mapping cannot repair an invalid source identifier. Malformed quantitative unit
values produce source-addressable diagnostics rather than Python exceptions.
This is bounded validation of interpreted declarations, not full DTDL certification.

## Representative failures

| Source condition | Finding | Existing regression |
| --- | --- | --- |
| Malformed JSON or duplicate JSON keys | INPUT | test_loader.py |
| Standalone v2-only input | VERSION | test_loader.py |
| Conflicting declarations using the same DTMI | DUPLICATE_ID | test_loader.py |
| Property schema `dtmi:example:Absent;1` | MISSING_SCHEMA | test_resolver.py |
| Component schema `dtmi:example:Absent;1` | MISSING_COMPONENT | test_resolver.py |
| A extends B and B extends A | DEPENDENCY_CYCLE / INHERITANCE_CYCLE | test_conformance.py, test_resolver.py |
| Object whose next field references itself | SCHEMA_CYCLE | test_resolver.py |
| Two parents define value with incompatible schemas | CONTENT_CONFLICT | test_resolver.py |
| Enum entry has missing/wrong/duplicate literal or invalid/duplicate name | ENUM_VALUE | test_resolver.py, test_cli.py |
| Invalid Enum values/material or unsupported valueSchema | SCHEMA_SHAPE / REFERENCE_TYPE | test_conformance.py, test_resolver.py |
| Relationship state contains Telemetry instead of Property | CONTENT_TYPE | test_resolver.py, test_cli.py |
| Duplicate relationship property, invalid name/target/multiplicity or nonboolean writable | CONTENT_SHAPE | test_resolver.py, test_plan.py |
| Unit schema without quantitativeTypes v1 context | EXTENSION_CONTEXT | test_resolver.py |
| Quantitative unit is unknown or not a string | QUANTITY_UNIT | test_resolver.py |
| Unknown context `dtmi:example:extension;1` | UNKNOWN_EXTENSION | test_resolver.py |
| Relationship target absent from source | MISSING_TARGET | test_selection.py |
| Relationship has no target | UNTARGETED_RELATIONSHIP | test_selection.py |
| Unknown output root or relationship selector | MISSING_SELECTION / SELECTION_CONFIG | test_selection.py |

Missing by-reference relationship targets do not automatically mean invalid
DTDL. They are unresolved dependencies for this conversion. Configuring a
placeholder does not reconstruct the missing definition.

`ValueAnnotation`/`Override` are instance-level metadata semantics. A unit
property such as `valueUnit` can override a model-declared unit for `value`;
it must not be reinterpreted as Fabric `redefines` or metadata inheritance.
Numeric literals outside Python's finite floating-point range are rejected during
loading rather than leaking Infinity into JSON sidecars. Shared valid named schemas
are memoized per consuming model/context during semantic validation. Validation
and projection each have a one-million schema-step resource guard in addition to
depth bounds; exhausting validation produces a blocker for every affected consumer,
never an implicit validation success.
