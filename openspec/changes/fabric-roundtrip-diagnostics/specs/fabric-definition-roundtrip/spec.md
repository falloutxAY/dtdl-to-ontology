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
