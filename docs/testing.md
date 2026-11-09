# Testing and contributing

Coverage order is **DTDL specification -> independent application samples ->
Willow scale test -> Fabric acceptance**, not Willow as the language definition.
No ordinary test downloads data or needs Fabric credentials.
Use [requirements and acceptance checks](requirements.md) as the maintained
checklist; passing local tests is separate from pending data/runtime acceptance.

## Local checks

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Tests cover source validity, policy decisions, deterministic payloads/manifests,
failure recovery, CLI examples, and a wheel installed outside the checkout.
Optional application-corpus tests explicitly skip when fixtures are absent.
Naming regressions include case/version/namespace collisions, inherited property
scopes, explicit aliases, prompt cancellation, JSON/CI non-interactivity,
provenance annotations, and service-normalized annotation ordering/label strings.

## Official specification sweep

```powershell
python tools\fetch_samples.py spec .fixtures\spec
python tools\check_spec.py .fixtures\spec --output output\spec-results.json
```

This runs all **6,760 cases in 895 files** from the pinned v3 normative
specification. Each upstream `input` entry is a separate JSON document, not a
nested array invented by the harness. Upstream valid cases requiring unknown
extensions are reported as `unsupported_extension`, not counted as passes.
The November 9 run matched **6,663** expected outcomes and explicitly rejected
**97** valid unknown-extension cases; there were **zero unexpected disagreements
or crashes**. The baseline count is checked so coverage cannot silently shrink.
Unexpected disagreements fail the command; crashes fail rather than being hidden.
The output lists every deviation. This is bounded conformance evidence, not
certification for all possible models or arbitrary JSON-LD.

The first full sweep exposed malformed-literal crashes, an off-by-one primitive
schema-depth check, and incorrectly accepted literal-form relationship targets.
These are now covered by `test_spec_regressions.py`.

## Independent samples and Willow

```powershell
python tools\fetch_samples.py parser .fixtures\parser
python tools\fetch_willow.py .fixtures\willow
python -m pytest tests\test_public_samples.py tests\test_willow.py
```

The six DTDLParser application samples exercise telemetry, units, inheritance,
components, untargeted and attributed relationships. Their absent Moon target
and empty Crater component are preserved, not repaired. A separately selected
temperature-device projection converts with explicit policies.

Willow's 3,705 Interfaces are a **secondary** unchanged scale corpus. They do
not cover Telemetry or Command declarations. Full conversion is blocked by
source issues (including an absent LeaseContract and invalid annotation/unit
declarations), more than 10,000 planned relationships, and the full logical
document budget including emitted provenance metadata.

For the bounded, relationship-preserving Building projection:

```powershell
dtdl-to-ontology convert .fixtures\willow\Ontology --root "dtmi:com:willowinc:Building;1" --compatibility --config examples\willow-building.json --name WillowBuilding --output output\willow
```

This selects **15 types, 128 property declarations and 30 relationship
definitions**, with 19 explicit object/component-to-String fallbacks.
The only omissions are the targetless `servedBy` relationships on Building,
Space, Calendar, Collection and EventCollection. No targets are guessed.
It replaces the old property-only configuration; review the larger dependency
closure and use a fresh output directory when upgrading.

The configuration matches the policies and selection used for the
[readable-name service test](fabric-acceptance.md#readable-name-willow-verification).
The regression checks source fingerprints, dependency closure, every retained
relationship, exact omissions, counts and deterministic output. This is local
reproducibility, not a new service run or proof of instance/query equivalence.

## Independent parser oracle

Optional .NET 8 tooling pins DTDLParser 1.1.3; Python conversion needs no .NET:

```powershell
dotnet build tools\DtdlOracle\DtdlOracle.csproj --verbosity quiet
dotnet run --project tools\DtdlOracle\DtdlOracle.csproj --no-build -- tests\fixtures\conformance\cases.json > oracle-results.json
dotnet run --project tools\DtdlOracle\DtdlOracle.csproj --no-build -- --geospatial > geometry-results.json
python tools\check_dtdl_oracle.py oracle-results.json geometry-results.json
```

The authored 38-case corpus has 24 categories and two explicit oracle differences:
this converter requires annotation siblings to resolve; this parser version
does not recognize MQTT v3. New disagreements fail. CI runs both the official
spec sweep and this independent parser comparison.

## Third-party sources

Acquisition verifies archive SHA-256, retains original `LICENSE` and per-file
fingerprints, and refuses to overwrite an existing destination. No downloaded
source is relicensed under this project's Apache-2.0 license.

| Source | Pinned revision | Upstream license |
| --- | --- | --- |
| [Azure DTDL specification](https://github.com/Azure/opendigitaltwins-dtdl) | `d19669a438a63be377c3cfc2fcabeac2e16ad55b` | CC-BY-4.0 |
| [Digital Twin Consortium DTDLParser samples](https://github.com/digitaltwinconsortium/DTDLParser) | `c368fb0828aa7944747d147c1bf6e3999c095f62` | MIT |
| [Willow building ontology](https://github.com/WillowInc/opendigitaltwins-building) | `1d19b2584df02e05714628a57a7ddd69edeef29c` | MIT |

Fixtures are downloaded unchanged into ignored `.fixtures/`; generated reports
belong in ignored `output/`. Keep credentials, tenant IDs, customer models, raw
backend source and private evidence out of contributions.
