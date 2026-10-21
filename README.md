# DTDL to Fabric Ontology

A Python CLI for direct DTDLv3 to Fabric Ontology **new-experience TMDL**
conversion. No RDF/Turtle intermediate or .NET runtime. Analyze and convert stay
offline and need no Fabric credentials; an explicit `deploy` command can use a
pre-acquired Fabric access token for a service round trip.

Produces locally validated definition payloads for the documented subset.
Unverified relationships remain gated; semantic losses require named policies.
Local conversion does not imply Fabric acceptance. `deploy` is opt-in, creates a
new Ontology, retrieves its definition, and does not claim semantic equivalence
or clean up the created item.

**Live acceptance (2026-10-20):** the corrected bounded Willow Building projection
passed Fabric create/get-definition and new-experience UI checks: **10 types,
79 properties, 15 parts**, with 15 explicitly approved JSON-string object/component
projections and 22 explicit relationship omissions. The original unbound structs
were rejected because they require recursive backing configurations; the CLI now
blocks them unless `json-objects` approves string projection. This loses native
field typing/querying, preserves source and pre-fallback shapes in the manifest,
and requires downstream ingestion to serialize JSON values. See the
[live acceptance evidence](docs/fabric-acceptance.md). This is not a lossless
whole-Willow import or runtime-data test; local success alone is not service verification.

## Development setup

Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\dtdl-to-ontology.exe --help
.\.venv\Scripts\dtdl-to-ontology.exe analyze --help
.\.venv\Scripts\dtdl-to-ontology.exe convert --help
.\.venv\Scripts\dtdl-to-ontology.exe deploy --help
```

`analyze INPUT` inventories local models and reports compatibility.
`convert INPUT --name NAME --output FOLDER` additionally generates the selected
ontology-first definition, manifest, and reports.
`deploy DEFINITION --workspace-id UUID` explicitly creates an Ontology and
retrieves its service definition. `--root DTMI` selects roots; omitted roots mean
all input interfaces. Analyze and convert never deploy or resolve models over the
network.

Ontology-first means types and metadata only: no lakehouse tables, data bindings,
runtime twins, telemetry ingestion, or device command execution. Unsupported or
lossy behavior must be explicit; compatibility mode alone approves no losses.

Local structural validation is not proof of Fabric service acceptance. See the
[target support matrix](docs/support-matrix.md) for documented versus unverified
features, including the disabled unbound-relationship mapping.

## Conversion examples

Fixed-object example with an explicit JSON-string fallback:

```powershell
.\.venv\Scripts\dtdl-to-ontology.exe convert examples\minimal.json --name Example --output output\example --compatibility --policy json-objects
```

Explicitly approved inheritance, component, collection, enum and unit projection:

```powershell
.\.venv\Scripts\dtdl-to-ontology.exe convert examples\projection.json --name Projection --output output\projection --compatibility --policy flatten-inheritance --policy component-properties --policy json-collections --policy json-objects --policy enum-underlying --policy metadata-semantics
```

Native single-parent syntax, **only if the target tenant actually supports
inheritance**, can be declared using `examples\native.json`:

```powershell
.\.venv\Scripts\dtdl-to-ontology.exe convert examples\inheritance.json --name Native --output output\native --config examples\native.json
```

This is a user feature declaration, not feature discovery or service verification.
Native multiple-parent output is rejected. `baseEntityType` is immutable on
create; changing it in Fabric requires delete/recreate. Without this declaration,
no rollout-only inheritance keywords are emitted. The examples are exercised by
the local CLI tests, not claimed as service-accepted imports.

See [known gaps and workarounds](docs/known-gaps.md) and
[outputs, exit codes and limits](docs/output-and-limits.md).
The full pinned Willow-corpus coverage sweep and its remaining limits are
documented in [Willow full coverage](docs/willow-full-coverage.md).

## Optional Fabric round trip

The deployment command reads the display name from the locally generated
`.platform` part. It requires an access token in `FABRIC_ACCESS_TOKEN` by default;
the token is never written to the output directory or included in reports. For
example, in PowerShell with an already authenticated Azure CLI:

```powershell
$env:FABRIC_ACCESS_TOKEN = az account get-access-token --scope https://api.fabric.microsoft.com/.default --query accessToken --output tsv
.\.venv\Scripts\dtdl-to-ontology.exe deploy output\willow-building-json\definition.json --workspace-id <workspace-guid>
Remove-Item Env:FABRIC_ACCESS_TOKEN
```

This creates a new workspace-root Ontology and retrieves its definition. Use a
unique item name when converting. The result includes exact part-path/text
differences and a normalized comparison of supported TMDL fields: namespaces,
entities, properties, relationships, types, descriptions, annotations and lineage.
When the generated manifest is beside `definition.json`, the report also summarizes
approved mapping losses with source examples. This bounded comparison is not proof
of full semantic equivalence or runtime behavior; the command does not test instance
ingestion or delete the created item.
Fabric may return a regional `*-redirect.analysis.windows.net` operation URL;
the client validates the operation host and follows the result location supplied
by the service.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Acquire the optional full [Willow fixture](docs/willow-fixture.md) explicitly.
The pinned source has 3,705 interfaces; its known gaps must not be silently fixed.
