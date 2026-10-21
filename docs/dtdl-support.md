# Supported DTDLv3 interpretation

The Python resolver is deliberately not a certified replacement for Microsoft's
DTDLParser or a general JSON-LD processor. Source objects and locations are kept
even when a target mapping is unavailable.

## Inputs and limits

- Local JSON Interface objects, arrays of Interface objects, or directories of
  such files. Each top-level interface declares the DTDLv3 context.
- Interface `extends` as one DTMI or a list; components reference local interfaces.
- Named Array, Enum, Map, and Object schemas declared inside interfaces.
- Core primitive schemas, plus local quantitativeTypes v1 unit vocabularies.
- Annotation and overriding v1 links, including inherited annotated values.
- No remote contexts, implicit JSON-LD expansion, top-level schema-only documents,
  or unknown extension contexts.
- At most 20,000 files, 16 MiB per file, 128 MiB total, 1,000,000 JSON value
  nodes per file, and 128 JSON/inheritance/schema traversal levels. Recursive
  schema graphs are diagnosed rather than infinitely expanded.
- Symlink inputs and files outside the input root are rejected.

Diamond inheritance deduplicates the original declaration. Distinct incompatible
declarations with the same effective name block conversion. The parent graph and
all compatible declaring origins remain traceable; file order is not precedence.

Arrays/maps, enums, components, units, writable state, and relationships can be
resolved without having a faithful Fabric mapping. Resolution is not emission.

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
| Context `dtmi:dtdl:context;2` | VERSION | test_loader.py |
| Conflicting declarations using the same DTMI | DUPLICATE_ID | test_loader.py |
| Property schema `dtmi:example:Absent;1` | MISSING_SCHEMA | test_resolver.py |
| Component schema `dtmi:example:Absent;1` | MISSING_COMPONENT | test_resolver.py |
| A extends B and B extends A | INHERITANCE_CYCLE | test_resolver.py |
| Object whose next field references itself | SCHEMA_CYCLE | test_resolver.py |
| Two parents define value with incompatible schemas | CONTENT_CONFLICT | test_resolver.py |
| Enum entry has missing/wrong/duplicate literal or invalid/duplicate name | ENUM_VALUE | test_resolver.py, test_cli.py |
| Enum enumValues is not an array or valueSchema is unsupported | SCHEMA_SHAPE | test_resolver.py |
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
