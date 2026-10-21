# Reproducible Willow fixture

The canonical fixture is the source `Ontology` directory at
`WillowInc/opendigitaltwins-building` commit
`1d19b2584df02e05714628a57a7ddd69edeef29c`.

Acquisition is an explicit network-enabled setup step:

```powershell
python tools\fetch_willow.py .fixtures\willow
```

The script verifies SHA-256
`13be79b36c06c32711c73f778ff50e1baee51833d2dc143fc19a958765c01044`
before extracting model JSON and LICENSE. It excludes the differing bundled
Metadata collection and writes per-file fingerprints in `fixture.json`.
An archive checksum change requires review; do not silently update the pin.
The converter itself never downloads models.

The original MIT license is retained with the downloaded models:
Copyright (c) 2021 Willow Technology Corporation Pty Limited.
Retain that license with any future redistributed source extracts.
The fixture is ignored by Git rather than automatically vendored.

Run the full pinned regression explicitly after acquisition:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_willow.py -q
```

Without the explicitly acquired fixture, those integration tests skip rather than
download. All other synthetic tests remain offline. Full-source findings are
intentionally extensive; bounded output still inventories excluded source models
and retains their original definitions in sidecars.

Known source issues are not repaired: `Lease.regulatedBy` references absent
`dtmi:com:willowinc:LeaseContract;1`. In `WaterLeakEvent`, the property is named
`leakeRate` but its ValueAnnotation says `annotates: leakRate`; the bounded resolver
reports `ANNOTATION_TARGET` at `Willow/Event/Water Leak/WaterLeakEvent.json#/contents/1`.
This is a source mismatch, not an automatic permission to rename properties.

## Bounded Building projection

**Bounded live acceptance:** on 2026-10-20, the corrected Building projection passed
Fabric create/get-definition and new-experience UI checks using 15 explicitly
approved JSON-string object/component projections. The original native unbound
structs were rejected; the CLI now gates them. See [results and limitations](fabric-acceptance.md).
The command below still produces a local artifact, not a deployment or a newly
service-verified result.

After acquisition, a reproducible property-focused projection is:

```powershell
.\.venv\Scripts\dtdl-to-ontology.exe convert .fixtures\willow\Ontology --root "dtmi:com:willowinc:Building;1" --compatibility --config examples\willow-building.json --source-revision 1d19b2584df02e05714628a57a7ddd69edeef29c --name WillowBuilding --output output\willow-building-json
```

This selects exactly Address, Building, Component, Space, SpaceArea, SpaceCapacity,
SpaceComponent, TimeZone, UtilityEmissionFactor and UtilityRate (all
`dtmi:com:willowinc:NAME;1`). The other 3,695 interfaces remain inventoried and
excluded, not declared converted. Source objects, arrays, maps, enums, quantities,
temporal strings, component projection and inheritance are exercised.

The example names eight policies, including `json-objects`, and **22 exact consumer-specific relationship
omissions** in `examples\willow-building.json`, including ordinary inherited
relationships on both Building and Space. No wildcard or implicit omit-all behavior
is implemented. The resulting graph is deliberately incomplete: 10 entity types,
79 top-level emitted properties (maximum 37 on one entity), **zero relationships**
and 15 definition parts. The component schema dependencies are also unbound entity
types, not claims of standalone runtime twins.

The 15 object/component fallbacks lose native field typing/querying and require
future ingestion to serialize JSON values. Their complete source and pre-fallback
logical shapes remain in the manifest. Removing `json-objects` leaves exactly 15
blocking `UNBOUND_STRUCT` findings, rather than publishing the rejected native form.
Choose a fresh output directory for each run; existing results are never overwritten.

It does not select/repair WaterLeakEvent or LeaseContract. Their unselected findings
remain visible. Complete sidecars can therefore be much larger than the selected
payload. Tests compare exact inclusions/exclusions and byte-identical envelopes,
manifests and reports after reversing input enumeration. Those tests establish local
acceptance; separate live evidence establishes only the tested bounded definition
round trip, not unit/constraint execution, instance ingestion or full-source support.
