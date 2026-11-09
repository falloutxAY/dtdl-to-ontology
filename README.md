# DTDL v3 to Fabric Ontology

Convert **DTDL v3 model definitions** into Microsoft Fabric Ontology
**new-experience TMDL**. Python 3.11+, no runtime dependencies.
Analysis and conversion are offline; deployment is explicit.

**This is a definition migration tool, not a twin-data or application migrator.**
It does not create data bindings, ingest telemetry, execute commands, or port
Azure Digital Twins APIs. Fabric Ontology is in preview; validate your target
environment before relying on a migration.

## Start here

From a checkout, in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
dtdl-to-ontology convert examples\scalars.json --name Sensors --output output\sensors
```

On macOS/Linux, activate with `source .venv/bin/activate` and use `/` in paths.
Use a new output directory for each run. Successful conversion writes
`definition.json`, readable `parts/`, a provenance `manifest.json`, and reports.

For your models:

```powershell
dtdl-to-ontology analyze .\models
dtdl-to-ontology convert .\models --root "dtmi:example:Sensor;1" --name Sensors --output output\my-sensors
```

Start in strict mode. Resolve errors, inspect the report, and approve **only**
the named losses you intend. `--compatibility` alone approves nothing.

Output uses readable names such as `com_willowinc#Settings` and `height`.
Source identity and model version live in key/value annotations such as
`dtdlModelId` and `dtdlModelVersion`, not visible hash/version suffixes.
Conflicts block publication; use explicit aliases or `--interactive-names`
in a terminal. See [naming, metadata and upgrade guidance](docs/naming.md).

## What can migrate?

| Path | Examples | Boundary |
| --- | --- | --- |
| Direct definitions | Interfaces, string/boolean/long/double/dateTime properties, concrete-target relationships | Unbound types and edges, not instances |
| Conditional native mapping | Single-parent inheritance | Requires an explicit tenant capability declaration |
| Explicit transformation | Multiple-parent flattening, JSON objects/collections, enum primitives, edge-as-entity | Changes semantics; original definitions and losses remain in the manifest |
| Separate solution | Commands, MQTT, history capture, required fields, geometry, runtime synchronization | Not implemented by a definition payload; see Fabric/external-service guidance |

The [complete DTDL v3 matrix](docs/dtdl-support.md) starts from the specification,
not any vendor model. [Workarounds](docs/known-gaps.md) distinguish implemented
policies from architecture guidance. [Live acceptance](docs/fabric-acceptance.md)
records what the service actually accepted and rejected.

## Deploy only after review

The command below creates a **new** Ontology and retrieves its definition.
It can provision companion Fabric items and consume capacity. It never deletes
resources or overwrites an existing item. Use an authorized test workspace first.

```powershell
$env:FABRIC_ACCESS_TOKEN = az account get-access-token --scope https://api.fabric.microsoft.com/.default --query accessToken -o tsv
try {
    dtdl-to-ontology deploy output\sensors\definition.json --workspace-id <workspace-guid> --folder-id <folder-guid> --json
} finally {
    Remove-Item Env:FABRIC_ACCESS_TOKEN
}
```

Omit `--folder-id` to create at workspace root. A successful round trip is **not**
proof of data/query equivalence. After conversion, supply real instance keys,
data, and [bindings](https://learn.microsoft.com/fabric/iq/ontology/how-to-bind-data).

## Repository guide

- [CLI, outputs and limits](docs/output-and-limits.md): configuration, failures and recovery.
- [Testing](docs/testing.md): official specification corpus, independent samples, Willow, and contributor checks.
- `examples/`: small runnable models; `src/`: converter; `tests/`: regressions.

[Apache-2.0](LICENSE). Downloaded fixtures retain their upstream licenses;
see [attribution](docs/testing.md#third-party-sources). This is an independent
project, not a Microsoft-supported migration service.
