# Spec Delta

## Purpose

Resolve local DTDLv3 model collections into a traceable interpretation suitable for direct conversion and explicit bounded projections.

## ADDED Requirements

### Requirement: Load local DTDLv3 collections

The converter SHALL accept a local directory of JSON model files or one JSON collection file. It SHALL support interface objects and arrays of interfaces, require DTDLv3 contexts, and identify malformed input, conflicting model identifiers, and unsupported versions without silently discarding them.

#### Scenario: Directory and collection inputs agree
- **WHEN** equivalent DTDLv3 definitions are supplied as separate files or one JSON array
- **THEN** the resolved model identities and contents are equivalent
- **AND** each declaration retains its input file and JSON pointer

#### Scenario: Conflicting identifiers
- **WHEN** two input declarations use the same DTMI with different definitions
- **THEN** analysis identifies both declarations and conversion fails

#### Scenario: Invalid input
- **WHEN** a file is malformed JSON or a model uses an unsupported DTDL version
- **THEN** the converter reports its location and reason rather than producing a successful definition

### Requirement: Resolve inheritance and shared schemas

The converter SHALL resolve local interface inheritance, component schemas, and named complex schemas, retaining declaring-source provenance. It SHALL detect inheritance cycles, missing required definitions, and incompatible inherited names rather than depend on input order or overwrite conflicting declarations.

#### Scenario: Shared ancestor
- **WHEN** an interface inherits the same ancestor declaration through two parents
- **THEN** the declaration is resolved once and its inheritance paths remain traceable

#### Scenario: Incompatible inherited names
- **WHEN** different inherited declarations have the same content name and incompatible meanings or schemas
- **THEN** conversion is blocked with the conflicting source locations

#### Scenario: Missing required schema
- **WHEN** a selected component or property references an absent required schema
- **THEN** conversion is blocked with the referring element and unresolved identifier

#### Scenario: Inheritance cycle
- **WHEN** interfaces form an inheritance cycle
- **THEN** the converter reports the cycle and does not recurse indefinitely

### Requirement: Interpret supported extension vocabularies

The converter SHALL recognize quantitativeTypes, annotation, and overriding version 1 contexts and their vocabulary when used with DTDLv3. It SHALL preserve adjunct types, units, annotates, and overrides links and diagnose unknown extension semantics instead of treating them as ordinary core fields.

#### Scenario: Built-in unit schema
- **WHEN** a quantitative property uses the extension-defined TemperatureUnit schema
- **THEN** it resolves through the declared extension vocabulary without requiring a local interface of that name

#### Scenario: Instance metadata override
- **WHEN** a property annotates another value and overrides its unit
- **THEN** resolution retains the instance-level metadata relationship
- **AND** does not reinterpret it as an inherited-property redefinition

#### Scenario: Unknown extension
- **WHEN** a selected model declares an unsupported extension
- **THEN** analysis reports the unsupported context and strict conversion is blocked

### Requirement: Separate full inventory from selected output

The converter SHALL inventory the complete supplied collection while allowing output selection by explicit root DTMIs. Selection SHALL include required inheritance and schema dependencies and target definitions for retained relationships. It SHALL list dependencies and exclusions and SHALL NOT silently include all descendants or omit required dependencies to satisfy limits.

#### Scenario: Bounded projection
- **WHEN** roots are supplied and unrelated models exist in the input
- **THEN** the report inventories all input models
- **AND** the selected projection contains the roots and required dependency closure, with exclusions recorded

#### Scenario: Retained relationship target
- **WHEN** a retained relationship references a target outside the initial root set
- **THEN** the target is included as a dependency or conversion reports a blocker
- **AND** any explicitly approved relationship omission is recorded as semantic loss

### Requirement: Distinguish relationship target references

The converter SHALL distinguish an absent by-reference relationship target definition from an absent required component or schema definition. It SHALL report missing and unconstrained relationship targets and require explicit target mapping, approved omission, or an approved placeholder policy before emitting affected relationships.

#### Scenario: Willow missing target
- **WHEN** Lease.regulatedBy references the absent dtmi:com:willowinc:LeaseContract;1 definition
- **THEN** analysis records a missing relationship target without claiming that this alone invalidates DTDL
- **AND** default conversion blocks the affected relationship

#### Scenario: Unconstrained target
- **WHEN** a selected relationship has no target
- **THEN** the converter does not invent a target or expand to every input entity by default

### Requirement: Offline and bounded resolution

Model resolution SHALL operate without fetching contexts, schemas, or models over the network and SHALL enforce documented input-size and traversal limits. It SHALL identify exceeded limits and unsupported recursive schema shapes without partial success.

#### Scenario: Unresolved identifier is not fetched
- **WHEN** a required definition is absent locally
- **THEN** the converter reports it without making a network request

#### Scenario: Recursive schema
- **WHEN** a schema cannot be represented as a finite target shape within the configured analysis limits
- **THEN** the converter reports the source cycle or exceeded bound instead of hanging
