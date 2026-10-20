# Spec Delta

## Purpose

Make conversion fidelity, unsupported semantics, workarounds, and Fabric capacity limits observable before an ontology payload is treated as usable.

## ADDED Requirements

### Requirement: Report source-addressable compatibility findings

Analysis SHALL produce JSON and readable reports with stable finding codes, source DTMIs and locations, affected selections, mapping fidelity, severity, workaround, and remaining limitation. Reports SHALL distinguish supported mappings, lossy workarounds, unsupported behavior, and unverified target behavior.

#### Scenario: Lossy mapping
- **WHEN** an enum is mapped to its underlying primitive
- **THEN** the report identifies the enum, loss of native allowed-value enforcement, external-validation workaround, and applied policy

#### Scenario: No payload-only workaround
- **WHEN** a requirement depends on command execution or device synchronization
- **THEN** the finding states that no definition-payload-only solution exists
- **AND** external execution is not described as native support

### Requirement: Require explicit approval for semantic loss

Conversion SHALL default to strict mode and reject unapproved semantic losses. Compatibility mode SHALL require named policies applicable to identified finding categories or source elements; enabling that mode alone SHALL NOT approve every loss. Unknown or unsupported policy requests SHALL fail explicitly.

#### Scenario: Compatibility mode without policy
- **WHEN** compatibility mode is enabled but array fallback has not been approved
- **THEN** an array mapping remains a blocker

#### Scenario: Approved serialized collection
- **WHEN** the JSON-string fallback is approved for an array or map
- **THEN** output uses a string property
- **AND** the manifest retains the original shape and records lost native typing and querying

#### Scenario: Unknown policy
- **WHEN** an option names a policy that the converter does not implement
- **THEN** the command fails instead of treating it as permission to skip data

### Requirement: Preserve transformation provenance

The manifest SHALL record source revision and fingerprints when available, selected roots, dependency reasons, exclusions, target identities, original schemas and metadata, applied policies, and losses. Sidecar data SHALL NOT be inserted as unsupported Fabric definition parts or silently truncated to fit annotation limits.

#### Scenario: Large source schema
- **WHEN** a source schema exceeds Fabric annotation-value limits
- **THEN** the complete schema remains available in the manifest
- **AND** the converter either uses bounded valid annotations or omits them with traceable provenance

### Requirement: Enforce target limits before publication

The converter SHALL check the selected target projection against a documented versioned limit profile, including entity and relationship counts, properties per entity, complex-shape bounds, text sizes, and whole-document bounds. Limit violations SHALL block publication; request batching SHALL NOT be presented as bypassing item-level limits.

#### Scenario: Relationship expansion exceeds capacity
- **WHEN** projected entity relationships exceed the profile's 10000-item limit
- **THEN** conversion reports the measured count and violated limit
- **AND** requires an explicit smaller selection or mapping change instead of truncating relationships

#### Scenario: Metadata exceeds a field limit
- **WHEN** an emitted annotation exceeds 4000 characters
- **THEN** preflight prevents the invalid payload and reports the affected metadata

### Requirement: Maintain a known-gap catalog

The converter documentation SHALL catalog inheritance and polymorphism, components, arrays, maps, enums, relationship properties and targets, units and value overrides, temporal primitives, runtime behavior, localization, constraints, capacity, and source-data bindings. Each entry SHALL identify a supported mapping, explicit workaround with losses, or absence of a payload-only solution.

#### Scenario: DTDL unit override
- **WHEN** a reader inspects the unit-override gap
- **THEN** the catalog distinguishes per-instance effective units from Fabric inheritance metadata overrides
- **AND** explains that storing the link as metadata does not execute its semantics

### Requirement: Reproducible Willow coverage

Acceptance SHALL use Willow source models pinned to commit 1d19b2584df02e05714628a57a7ddd69edeef29c, not mix source with the differing bundled collection, and supplement missing constructs with focused fixtures. Full-source inventory SHALL be independent of successful bounded emission; a whole-source strict run can legitimately fail with documented blockers.

#### Scenario: Full-source analysis
- **WHEN** the pinned Willow source directory is analyzed
- **THEN** the inventory identifies 3705 interfaces and the missing LeaseContract relationship target
- **AND** reports source multiplicity and extension usage
- **AND** does not claim complete payload conversion merely because analysis completed

#### Scenario: Coverage absent from Willow
- **WHEN** telemetry and command handling are evaluated
- **THEN** focused fixtures exercise their mapping or unsupported-behavior diagnostics
- **AND** Willow's lack of those declarations is not presented as coverage

### Requirement: Separate local validity from service acceptance

Reports SHALL distinguish local structural checks, documented target compatibility, and actual Fabric service acceptance. They SHALL state the target feature profile and verification evidence and SHALL NOT claim tenant compatibility, deployment, or a successful round trip without a recorded service result.

#### Scenario: Offline conversion
- **WHEN** all local checks pass but no Fabric request has been made
- **THEN** the report states that service acceptance has not been verified

#### Scenario: Feature rollout
- **WHEN** native inheritance output is selected with a declared target feature profile
- **THEN** the report records that declaration separately from evidence of service verification
