# Spec Delta

## Purpose

This capability makes a retrieved Fabric Ontology definition easier to verify against the submitted definition by reporting part-level differences without claiming semantic equivalence.

## ADDED Requirements

### Requirement: Compare submitted and returned definition parts
After successful create and get-definition operations, the system MUST compare the decoded submitted and returned part paths and text, and report missing, additional, and textually changed paths.

#### Scenario: Identical definition parts
- **WHEN** every submitted part is returned at the same path with identical decoded text
- **THEN** the comparison reports matching paths and no textually changed paths

#### Scenario: Missing, additional, or changed parts
- **WHEN** the returned definition omits a submitted path, adds a path, or changes text at a shared path
- **THEN** the comparison reports each missing, additional, and textually changed path in a distinct category

### Requirement: Distinguish part comparison from semantic equivalence
The deployment result MUST present part-level comparison separately from service acceptance and MUST NOT treat identical or different text as proof of semantic equivalence.

#### Scenario: Successful service round trip with differences
- **WHEN** Fabric successfully creates the Ontology and returns a definition whose parts differ
- **THEN** deployment retains its successful service-acceptance exit status and reports the part differences without asserting semantic equivalence

#### Scenario: Readable deployment report
- **WHEN** the deployment result is rendered for a human
- **THEN** it shows the part-comparison summary and any missing, additional, or textually changed paths

### Requirement: Compare supported normalized TMDL fields
After successful create and get-definition operations, the system MUST compare the supported normalized TMDL fields in the submitted and returned definitions. The comparison MUST identify namespaces, entities, properties, and relationships, including supported names, types, descriptions, annotations, endpoints, and lineage tags. It MUST label its bounded scope and MUST NOT claim full semantic equivalence.

#### Scenario: Supported fields match
- **WHEN** the submitted and returned definitions contain the same supported normalized TMDL fields
- **THEN** the result reports that supported fields match and keeps `semantic_equivalence` as `not_asserted`

#### Scenario: Supported fields differ
- **WHEN** a supported field or declaration is missing, additional, or changed in the returned definition
- **THEN** the result reports the difference by category and field without changing successful service acceptance

#### Scenario: TMDL comparison is unavailable
- **WHEN** either definition contains malformed or unsupported syntax needed by the bounded parser
- **THEN** the result reports the comparison as unavailable and retains successful service acceptance

### Requirement: Explain approved mapping losses
When a sibling conversion manifest is available, the deployment result MUST summarize approved and selected mapping-loss findings with their policy and bounded source examples. It MUST NOT describe those approved losses as preserved target semantics.

#### Scenario: Manifest contains approved mappings
- **WHEN** the sibling manifest contains approved and selected transformation findings
- **THEN** the result groups them by finding code and policy and includes no more than three source examples per group

#### Scenario: No manifest is available
- **WHEN** the sibling conversion manifest is absent
- **THEN** the semantic comparison remains available and mapping-loss context is reported as unavailable
