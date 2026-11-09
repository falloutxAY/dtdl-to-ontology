# DTDL v3 coverage

Baseline: the [DTDL v3 language description][dtdl] and its
[normative specification][normative], pinned at
`d19669a438a63be377c3cfc2fcabeac2e16ad55b`.
Target: the [public new-experience Ontology TMDL contract][target],
profile `fabric-new-2026-11-09`.

**Source validity, local conversion, service acceptance, and runtime equivalence
are separate claims.** The Python reader is not a certified DTDLParser replacement.
See [tests](testing.md) and [service evidence](fabric-acceptance.md).

## Core language

| DTDL v3 construct | Converter disposition | What does not carry over automatically |
| --- | --- | --- |
| Interface, DTMI, versions | Readable entity/namespace names; original DTMI/version in annotations and manifest; stable source-based lineage | Conflicting versions require explicit aliases; a model identifier is not an instance key |
| Single-parent `extends` | Native with `{"inheritance": true}` config, or explicit `flatten-inheritance` | Tenant rollout; polymorphic query equivalence |
| Multiple-parent/diamond `extends` | Resolve all parents and conflicts; `flatten-inheritance` materializes effective properties | Native multiple-parent ancestry; never choose one parent silently |
| Property: string, boolean, long, double, dateTime | Direct scalar definition | Instance-value validation, null/missing rules, timezone conversion |
| Property: integer, float | int64/double with `metadata-semantics` | Source width/range enforcement |
| date, time, duration | String with `temporal-strings` | Temporal operations and value validation |
| Telemetry | Unbound property with `metadata-semantics` | Ingestion, timestamps, correlation, time-series binding |
| Command, request, response | Validate and retain source; block conversion of selected command-bearing models | Device execution and request/response transport |
| Relationship with concrete target | Native unbound relationship definition | Runtime edges, keys, bindings, multiplicity enforcement |
| Relationship with no/missing target | Explicit target mapping, marked placeholder, or exact omission | An inferred wildcard target or recovered missing model |
| Relationship properties | `reify-relationship-properties`: edge entity plus two endpoint links | Native attributed-edge identity/traversal; runtime IDs still required |
| Component | By-value schema resolved; `component-properties` plus `json-objects` projects its state | Component-scoped paths/relationships; a component was never an independent twin |
| Array, Map | `json-collections`: String definition | Typed collection queries and runtime serialization |
| Enum, EnumValue | `enum-underlying`: underlying primitive | Allowed-value enforcement and labels |
| Object, Field | `json-objects`: String definition | Native field access; unbound Struct is service-rejected |
| Interface `schemas` and schema references | Resolve named schemas within their owning Interface partition | Cross-interface private-schema reuse |
| Six standard geospatial schemas | Recognize and retain geometry identity/shape; block native conversion | Spatial datatype/query equivalence |
| Description, displayName, comment, localization | Supported description; remaining metadata retained with `metadata-semantics` | Full localized display and metadata execution |

The current public target contract exposes **one `baseEntityType`**, not a list.
Single-parent inheritance has live acceptance evidence; multiple-parent DTDL
input must be flattened or remodeled. This is a statement about the supported
public conversion contract, not every internal or future Ontology capability.
See [naming and metadata](naming.md) for conflict resolution and version provenance.

## Representations, references and extensions

The reader handles canonical aliases, material-type arrays, allowed singleton
representations, typed literals, localized strings, inline Interfaces, generated
element identities, and local dependencies. Unknown contexts and remote
resolution are rejected, not silently ignored.

| Extension | Source handling | Target boundary |
| --- | --- | --- |
| quantitativeTypes v1 | Quantity/unit vocabulary validation | Metadata only; no unit conversion or dimensional reasoning |
| annotation and overriding v1/v2 | Resolve sibling links and schema/context contracts | Instance overrides are not Fabric `redefines` |
| historization v1/v2 | Validate and retain capture intent | `HISTORIZATION_BINDING`: separate history storage/ingestion required |
| MQTT v1/v2/v3 | Validate versioned types, topics and payload declarations | `MQTT_RUNTIME`: no transport or serializer |
| Requirement v1 | Recognize optional-by-default and Required Fields | `FIELD_PRESENCE`: no target field-presence enforcement |
| Unknown extensions / general JSON-LD | Explicit unsupported diagnostics | No speculative interpretation |

Locally included v2 dependencies retain bounded v2 checks. This is **not** a
standalone v2 converter; changing `@context` is not a version migration.

## Source validation boundaries

The reader rejects malformed JSON, duplicate identifiers, invalid literal types,
missing required dependencies, cycles, incompatible inherited content, invalid
enums/relationships, and nested Components. Policies cannot waive invalid source.
Relationship target absence alone is legal DTDL but needs a conversion decision.

Normative v3 limits include 1 MiB per Interface's original UTF-8 text excluding
nested Interfaces; 1,024 inheritance values and 10 `extends` links; 100,000
contents-hierarchy values; five `schema`/`elementSchema` links, including a
terminal primitive reference. Interface/element/generated identifiers have
128/2,048/4,096-character bounds.

Separate defensive limits: 20,000 files, 16 MiB/file, 128 MiB total, one million
JSON nodes/file, 128 traversal levels, and one million schema/projection steps.
Inputs must be local JSON objects/arrays/directories; symlinks are rejected.
These guards are not additional DTDL language rules.

[dtdl]: https://github.com/Azure/opendigitaltwins-dtdl/blob/d19669a438a63be377c3cfc2fcabeac2e16ad55b/DTDL/v3/DTDL.v3.md
[normative]: https://github.com/Azure/opendigitaltwins-dtdl/blob/d19669a438a63be377c3cfc2fcabeac2e16ad55b/DTDL/v3/DTDL.Specification.v3.md
[target]: https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/ontology-definition
