# Proposal

## Why

The deploy command confirms that Fabric created an Ontology and returned a definition, but its readable output only shows part counts. A count can conceal missing, extra, or changed parts, so exposing a decoded part-by-part comparison will make service results easier to inspect without claiming semantic equivalence.

## What Changes

- Compare locally submitted and service-returned definition parts by path and decoded text.
- Report missing paths, additional paths, and changed text for paths present in both definitions in machine-readable and readable output.
- Keep service acceptance distinct from part comparison and semantic equivalence. A successful create/get-definition round trip retains its current success exit code when differences are reported.

## Capabilities

### New Capabilities

- `fabric-definition-roundtrip`: Compare submitted and retrieved Fabric definition parts and report differences without asserting semantic equivalence.

### Modified Capabilities

None.

## Impact

The Fabric deployment result and CLI report in `src/dtdl_to_ontology/fabric.py` and `src/dtdl_to_ontology/cli.py`, focused tests in `tests/test_fabric.py` and `tests/test_cli.py`, and deployment documentation. No service behavior, target mappings, or dependencies change.
