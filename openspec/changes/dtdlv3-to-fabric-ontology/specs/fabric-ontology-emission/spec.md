# Spec Delta

## Purpose

Produce deterministic Fabric Ontology new-experience definition payloads directly from resolved DTDLv3 models without an RDF intermediate or live data bindings.

## ADDED Requirements

### Requirement: Emit the new-experience definition format

The converter SHALL generate TMDL ontology definition parts and an InlineBase64 REST definition envelope directly from resolved DTDL. It SHALL include valid platform metadata, database compatibility level 1000000, model references, and the default namespace. It SHALL NOT generate old-experience entity-type JSON or require RDF/Turtle processing.

#### Scenario: Minimal ontology-first entity
- **WHEN** a supported model is converted
- **THEN** the definition contains platform, database, model, default namespace, and entity parts
- **AND** every part payload decodes as UTF-8 text or JSON appropriate to its kind
- **AND** each payloadType is InlineBase64

#### Scenario: No RDF intermediate
- **WHEN** conversion runs without RDF tooling or a .NET runtime installed
- **THEN** supported inputs can be converted using the Python distribution alone

### Requirement: Keep ontology-first output unbound

The converter SHALL omit data-source expressions, backing tables, property backing configurations, and fabricated instance data in the first version. It SHALL emit unbound relationship declarations only after their support is established against the target contract; otherwise it SHALL report an explicit blocker or approved omission.

#### Scenario: Source model has no instance identity
- **WHEN** an interface has no proven runtime twin key
- **THEN** the converter does not use the model DTMI or an assumed uniqueID property as a fabricated keyProperty

#### Scenario: Unbound relationship support is unverified
- **WHEN** service acceptance of an unbound relationship has not been established
- **THEN** the report marks that mapping unverified
- **AND** strict conversion does not claim a verified deployable relationship

### Requirement: Preserve identity deterministically

The converter SHALL derive stable target names, namespace assignments, and lineage tags from versioned source identities and mapping roles. It SHALL escape TMDL identifiers and text, detect case-insensitive and path collisions, and preserve source DTMIs and original localized metadata in the manifest.

#### Scenario: Input order changes
- **WHEN** equivalent inputs are enumerated in a different order with identical options
- **THEN** emitted part order, names, lineage tags, manifest content, and payload bytes are unchanged

#### Scenario: Name collision
- **WHEN** source identifiers sanitize to the same target name or differ only by case
- **THEN** deterministic disambiguation preserves distinct mappings or conversion fails explicitly

#### Scenario: TMDL-sensitive text
- **WHEN** names or descriptions contain quotes, line breaks, or TMDL control-like text
- **THEN** serialization preserves their data meaning without introducing unintended declarations

### Requirement: Map supported scalar and object schemas

The converter SHALL map strings, booleans, integer and long values, float and double values, and dateTime values to compatible Fabric types while recording source distinctions. Fixed-shape objects SHALL map recursively to complex structs. Unsupported collection or primitive semantics SHALL require a compatibility policy.

#### Scenario: Fixed object
- **WHEN** a property contains a supported fixed-shape object
- **THEN** its target property uses dataType complex and a recursive struct complexDataType assignment

#### Scenario: Array is not a struct
- **WHEN** a property uses an array or dynamic map
- **THEN** the converter does not emit an invented native array or map kind
- **AND** it applies only an explicitly approved fallback or reports a blocker

### Requirement: Make inheritance projection explicit

The converter SHALL support an explicitly approved flattened projection and an opt-in native single-parent projection. Native inheritance SHALL require an affirmative target feature profile. Multiple inheritance and inherited non-is-a relationships SHALL receive explicit compatibility treatment rather than being assumed to work natively.

#### Scenario: Tenant inheritance feature disabled
- **WHEN** the target profile does not affirm inheritance support
- **THEN** emitted TMDL contains no baseEntityType, redefines, or overriddenMetadataFields keywords

#### Scenario: Flattened multiple inheritance
- **WHEN** flattening is approved for a model with multiple parents
- **THEN** its compatible effective properties are materialized
- **AND** lost native type relationships and original parents are recorded

#### Scenario: Inherited ordinary relationship
- **WHEN** a selected derived type inherits a DTDL relationship
- **THEN** the converter explicitly projects it, reports an approved omission, or blocks it
- **AND** does not rely on Fabric property inheritance to propagate it

### Requirement: Publish consistent artifacts

Successful conversion SHALL publish a payload, mapping manifest, and JSON and readable compatibility reports as a consistent result. Failed conversion SHALL return a nonzero exit code and diagnostics without publishing a new success-shaped payload. Existing successful output SHALL NOT be mistaken for the failed run's result.

#### Scenario: Mapping blocker
- **WHEN** conversion encounters an unapproved semantic loss
- **THEN** it returns nonzero and identifies the blocker in reports
- **AND** does not publish a payload marked ready

#### Scenario: Reusing an output location
- **WHEN** a failed run targets a location containing an earlier successful result
- **THEN** the command clearly distinguishes the failed attempt from the unchanged prior result
- **AND** does not overwrite unrelated files
