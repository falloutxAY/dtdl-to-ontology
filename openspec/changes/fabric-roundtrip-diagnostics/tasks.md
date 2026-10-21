# Tasks

## 1. Definition part comparison

- [x] 1.1 Extend the deploy result with part-path match, complete decoded-text equality, and changed shared-path reporting; add Fabric-client tests covering identical, missing, additional, and changed parts while asserting service acceptance and `semantic_equivalence` remain independent.

## 2. User-facing diagnostics

- [x] 2.1 Show path/text comparison status and non-empty difference lists in the readable deploy report; add CLI report tests and document that textual equality is not semantic equivalence.

## 3. Supported semantic comparison

- [x] 3.1 Parse converter-emitted TMDL into normalized supported fields and compare submitted versus returned namespaces, entities, properties, and relationships; report unsupported syntax without changing successful service acceptance.
- [x] 3.2 Add comparison coverage and expose supported-field differences and approved mapping-loss context in deployment output and documentation.
- [x] 3.3 Compare the retained bounded Building service result with the generated local definition and record the observed supported-field differences.

## 4. Verification

- [x] 4.1 Run focused Fabric, semantic, and CLI tests, the full test suite, Ruff checks, and strict OpenSpec validation; verify reported differences do not change deploy success behavior.
