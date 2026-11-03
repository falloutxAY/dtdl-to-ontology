# Known conversion gaps

The converter compiles DTDLv3 directly to Fabric Ontology new-experience TMDL.
It is not a lossless general DTDL implementation. Strict mode blocks semantic losses;
`--compatibility` alone approves none. Complete originals remain in `manifest.json`,
not unsupported uploaded definition parts. Every finding links to a category below.

## Source validation

Loader, resolver, selection, schema-mapping and identity findings identify malformed,
unsupported or ambiguous source constructs by DTMI, file and JSON pointer. Correct
the source or select an independent valid projection. Compatibility policies cannot
waive invalid definitions, conflicting declarations, recursive shapes, missing
required schemas or unknown contexts. This bounded Python resolver is not certified
equivalent to Microsoft's DTDLParser. See [supported subset](dtdl-support.md).

## Inheritance

`INHERITANCE`: approve `flatten-inheritance` to materialize compatible effective
properties, retaining every source parent in the manifest. Multiple parents have
**no native multiple-parent equivalent**; a parent is never guessed.
Native single-parent output requires an affirmative `inheritance: true` target
declaration. That declaration is not proof of tenant rollout or service acceptance.
Ordinary relationships are explicitly expanded per consumer, not inherited by
Fabric; their count can exceed capacity. Deep native polymorphic queries are not
equivalent: documented expansion covers base plus direct children, not all ancestors.
Use the recorded ancestor graph for explicit downstream queries.

## Components

**Live service finding (2026-10-20):** unbound struct projection is rejected in the
tested environment. The Building example's 15 complex properties produced
`ComplexLogicalBackingMismatch`: every struct node requires an exact recursive
`backingConfiguration`. This affects fixed Objects as well as projected Components.
`UNBOUND_STRUCT` now blocks publication unless `json-objects` explicitly approves
mapping the whole property to String. The manifest retains original schemas and
`pre_fallback_logical_type`; nested source, metadata, runtime and relationship
checks still run before this fallback. `json-collections` and `component-properties`
do not authorize that additional loss. The corrected bounded Building projection
passed a live round trip with 15 such string projections.

JSON strings lose native field typing/querying and do not enforce object shape.
The converter emits type definitions only: downstream ingestion must serialize
valid JSON values, and no instance-value ingestion was tested. Faithful native
structs need real field/column backings, outside this version's scope; fabricated
tables or columns are not a workaround.

`COMPONENT`: approve `component-properties` to analyze a component as a recursive
fixed-struct property; unbound publication also requires `json-objects`.
This loses independent component identity. Component-contained ordinary
relationships require exact path-specific omission or block; they cannot silently
become owner relationships. Nested components retain paths in source/target provenance.
Empty or recursive component shapes block; there is no complete native component
equivalent. Separate child entities and bindings are future designs, not fallbacks
implemented by this policy.
The source-language prohibition on Component-inside-Component is now diagnosed
as `DTDL_NESTED_COMPONENT` before any projection; compatibility cannot waive it.

## Collections and enums

`COLLECTION`: approve `json-collections` to store Array/Map values as JSON strings.
There are no invented array/map complex kinds, typed element queries or automatic
runtime serialization. A future ingestion layer must supply valid JSON values.
`ENUM_UNDERLYING`: approve `enum-underlying` to use the underlying string/int64
primitive. Allowed values and labels remain in the manifest; external validation
must enforce them. Normalized child collections are not implemented.

`GEOSPATIAL_MAPPING`: all six standard geometries are recognized source schemas,
not missing user dependencies. Their identity and full source coordinate-array
structure are retained in the manifest. Native geometry types, variable-length
coordinate arrays and spatial querying are not provided. No new fallback was added.

## Temporal primitives

`TEMPORAL_STRING`: approve `temporal-strings` for date/time/duration ISO strings.
Native temporal operations and constraints are not equivalent. dateTime maps
directly to dateTime; no timezone or instance-value conversion is performed.

## Metadata and constraints

`METADATA_SEMANTICS`, `SOURCE_WIDTH`, `WRITABLE`: approve `metadata-semantics`
to retain unsupported semantics as manifest data, not execution.
Units and quantitative vocabulary do not establish dimensional conversion or
reasoning. ValueAnnotation/Override preserve instance links, including per-instance
effective unit overrides; Fabric inheritance `redefines`/metadata overrides do
**not** execute these links. A runtime processor must interpret instance values.
Integer/long and float/double source distinctions are retained but do not preserve
all widths. Writable state requires external synchronization.
Multiplicity and other source constraints require upstream validation; table
cardinality and natural-language rules are not equivalent enforcement.
Localized labels and versioned DTMIs remain complete in the manifest; target
technical names are deterministic and display names are server-derived.
No silent annotation truncation is used.

`FIELD_PRESENCE`: Requirement v1 distinguishes optional-by-default Fields from
explicit Required Fields. Source schema typing does not enforce field presence.
Required declarations remain blocked even with existing loss policies; the
manifest explicitly records that target enforcement is absent.

## Relationships

`UNBOUND_RELATIONSHIP`: unbound relationship acceptance is **unverified and gated**.
There is no public switch to waive this. Supply authoritative acceptance evidence
in a future supported profile or explicitly omit each edge using
`omit-relationships` and `omit_relationships` selectors.
`UNTARGETED_RELATIONSHIP`: configure a concrete target or omit it; no unrestricted
native `toEntity` exists.
`MISSING_TARGET`: provide the definition, map a target, omit the edge, or explicitly
approve a visibly marked placeholder with `placeholder-targets`.
A placeholder cannot reconstruct missing source meaning.
`TARGET_MAPPING`, `PLACEHOLDER_TARGET`, `RELATIONSHIP_OMITTED` record these losses.
`RELATIONSHIP_PROPERTIES`: `reify-relationship-properties` plans edge entities with
typed properties, an unbound edge-ID property and source/target endpoint links.
It is not native attributed-edge identity and **does not override the unbound-link
gate**. Runtime edge IDs and endpoint bindings must be supplied later.
`EDGE_ID_COLLISION` blocks a source collision with the generated edge-ID property.
Junction tables alone do not expose native per-edge property collections.

## Runtime and bindings

`COMMAND_RUNTIME`: **no definition-payload-only solution** executes device commands.
External device integration is required; metadata preservation is not execution.
`TELEMETRY_BINDING`: a telemetry property can be retained, but **no payload-only
solution** provides ingestion, stream correlation or time-series bindings.
No fake timeSeries/backing table/source expression is emitted.
Real tables, columns and runtime keys cannot be inferred from schemas. Neither a
model DTMI nor a property called uniqueID proves an instance key. Data bindings
and deployment are outside this version. Willow has no Telemetry/Command
declarations, so synthetic CLI fixtures cover these diagnostics.

`HISTORIZATION_BINDING` and `MQTT_RUNTIME` preserve recognized source intent but
remain non-waivable runtime/target gaps. Historized does not create change capture
or historical queries. MQTT declarations do not create transport, command
dispatch, topic expansion or a wire-format serializer. No new table, key, ordering
column or backing is fabricated to make these definitions appear supported.

## Capacity

`LIMIT_*` findings stop publication instead of truncating output.
Use smaller explicit roots, omissions or a different explicitly designed projection.
Batching REST parts does not bypass per-item limits. Automatic partitioning and
generic-twin projections are not implemented. Whole-source Willow expansion is not
a lossless single-item conversion. See [target profile](support-matrix.md).
Local structural checks do not establish unknown transport/tenant limits or service
acceptance; a separate authorized Fabric create/getDefinition check is necessary.
`ONTOLOGY_NAME` rejects item display names that the live service rejects: names
must begin with an ASCII letter, contain only ASCII letters/digits/underscores,
and have at most 89 characters. This item-name contract is separate from the
512-character bound on ordinary model names.
