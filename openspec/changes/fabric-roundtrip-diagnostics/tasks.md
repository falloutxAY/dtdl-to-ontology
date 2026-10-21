# Tasks

## 1. Definition part comparison

- [x] 1.1 Extend the deploy result with part-path match, complete decoded-text equality, and changed shared-path reporting; add Fabric-client tests covering identical, missing, additional, and changed parts while asserting service acceptance and `semantic_equivalence` remain independent.

## 2. User-facing diagnostics

- [x] 2.1 Show path/text comparison status and non-empty difference lists in the readable deploy report; add CLI report tests and document that textual equality is not semantic equivalence.
- [x] 2.2 Run focused Fabric and CLI tests, the full test suite, Ruff checks, and strict OpenSpec validation; verify all pass without changing deploy success behavior for reported differences.
