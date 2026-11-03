# DTDL source conformance evidence

This work addresses source interpretation and diagnostics, not missing Ontology
capabilities. No new lossy mapping policy, runtime backing, collection datatype,
transport implementation, or geometry fallback was added.

## Reproducible local evidence

The authored corpus at `tests\fixtures\conformance\cases.json` contains 38 models
across 24 declared feature categories, with positive and negative coverage for
each category. `test_conformance_corpus.py` fails on a missing disposition,
duplicate case, missing category, or incomplete diagnostic contract. Generated
tests additionally cover exact/one-over identifier, original UTF-8 byte,
inheritance, contents-count and schema-depth boundaries.

The complete local run on 2026-11-03 passed **354 tests**, including all three
integration tests against the checksum-pinned 3,705-Interface Willow corpus at
revision `1d19b2584df02e05714628a57a7ddd69edeef29c`. Willow remains unchanged.
The source checks now expose five invalid quantity co-types on Fields in
PhotovoltaicPanel and an additional override diagnostic caused by the existing
WaterLeakEvent sibling-name mismatch. These are upstream source defects, not
Ontology feature gaps. The full policy sweep has 25,303 blockers; its existing
capacity and missing-target limitations remain real.

Run the ordinary suite without any Fabric credentials:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Willow acquisition remains explicit, as documented in [Willow fixture](willow-fixture.md).
CI explicitly acquires that checksum-pinned fixture before the complete Python
suite; local runs without it clearly skip the three optional integration tests.

## Independent source oracle

`tools\DtdlOracle` pins Microsoft's **DTDLParser 1.1.3**. It is an optional test
tool, not a converter runtime dependency. Its acceptance results agree with the
38 source expectations except for two explicit, checked differences:

| Case | Converter | Independent parser | Interpretation |
| --- | --- | --- | --- |
| `annotation-missing-target` | Rejects missing effective sibling | Accepts | Converter additionally requires the annotation link to resolve consistently for conversion |
| `mqtt-v3-recognition` | Accepts the supported v3 declaration | Rejects unresolvable extension context | This parser version does not implement MQTT v3; this is not evidence that the declaration is malformed |

The invalid-topic model deliberately uses MQTT v1 so its independent rejection
tests topic validation rather than an unavailable extension context.
Canonical extension aliases were verified against pinned upstream contexts;
invented generic aliases are rejected. The six geometry source shapes, including
their Enum literals and nested coordinate Array identifiers, are independently
compared against the parser's actual built-in schema objects.

```powershell
dotnet build tools\DtdlOracle\DtdlOracle.csproj --verbosity quiet
dotnet run --project tools\DtdlOracle\DtdlOracle.csproj --no-build -- tests\fixtures\conformance\cases.json > oracle-results.json
dotnet run --project tools\DtdlOracle\DtdlOracle.csproj --no-build -- --geospatial > geometry-results.json
.\.venv\Scripts\python.exe tools\check_dtdl_oracle.py oracle-results.json geometry-results.json
```

Where direct NuGet access is unavailable, the tested approved restore source is
`https://packagefeedproxy.microsoft.io/nuget/v3/index.json`; do not disable TLS.
The CI workflow runs ordinary regressions and independent parser comparisons as
separate jobs. An unexpected disagreement, omitted/duplicate oracle case, or
changed built-in geometry shape fails the comparison.

## Authorized live Fabric run, 2026-11-03

Testing used a uniquely named folder in the user-authorized workspace. Only
resources created by that run were targeted for deletion. No existing item,
binding, table, permission, or source model was changed.

Five direct, no-policy definitions passed create/getDefinition and normalized
supported-field comparison, with no reported namespace/entity/property/type/
description/lineage differences:

| Model | Verified surface |
| --- | --- |
| Normative source spellings | Class/property/schema aliases, singleton/literal forms and localized description |
| Native scalars | String, Boolean, long, double, dateTime and a maximum-width major.minor DTMI |
| Private partitions | Distinct element identities with the same programming name in separate Interfaces |
| Inline parent | Two native entity types and single-parent `baseEntityType`, using the existing affirmative tenant declaration |
| Item-name boundary | A service-accepted 89-character item display name |

An initial run used hyphens in item names and received explicit HTTP 400 name
validation errors. The converter now rejects these locally with `ONTOLOGY_NAME`;
ordinary model-name limits remain separate. Those failed requests created no
Ontology items, and that first test folder was deleted.

The versionless-scalar case was accepted locally and by the independent source
parser, but failed service provisioning with `ALMOperationImportFailed`. Its
cause is not established; it is not classified as an unsupported DTDL feature.
Five successful Ontologies were deleted. A KQL database created by the failed
service operation was also deleted. The operation additionally left an orphan
GraphModel whose deletion failed through both the Fabric API and the workspace
UI; consequently its otherwise test-only folder could not yet be deleted.
The exact resource ownership and cleanup attempts are preserved in the run
ledger. Cleanup is an outstanding service blocker, not a completed assertion.

An ordinary relationship stayed locally gated as `UNBOUND_RELATIONSHIP` and was
not uploaded. No existing gate was bypassed, and no fabricated backing was used
to force service acceptance.

## What this evidence does not establish

Source parser acceptance, local payload validation, live definition acceptance,
and runtime semantic equivalence are four different claims. These tests do not
verify device commands, MQTT delivery/serialization, history capture, required
field enforcement, data ingestion, spatial queries, arbitrary JSON-LD expansion,
or exhaustive compatibility with every older DTDL version. They do not make a
full Willow conversion fit into one Ontology.

The [source disposition matrix](dtdl-support.md) and [known target gaps](known-gaps.md)
retain those distinctions. Existing compatibility policies are neither expanded
nor implicitly approved by this work.
