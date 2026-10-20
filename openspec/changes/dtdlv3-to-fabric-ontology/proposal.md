# Proposal

## Why

DTDLv3 building models should be usable in Fabric Ontology's new experience without an RDF/Turtle conversion step. A direct Python converter must expose unsupported semantics and Fabric capacity limits instead of producing a misleadingly lossless import.

## What Changes

- Introduce a Python CLI that analyzes local DTDLv3 model collections and generates ontology-first, new-experience TMDL definition payloads without RDF processing or a .NET runtime.
- Resolve interfaces, inheritance, components, shared schemas, and supported quantitative-types, annotation, and overriding extensions.
- Analyze the complete input independently of explicitly selected output roots and their dependencies; support bounded projections rather than silently truncating an oversized ontology.
- Emit the REST definition payload, a deterministic source-to-target mapping manifest, and machine-readable and readable compatibility reports.
- Default to strict conversion. Require explicit policies for lossy mappings, preserve source semantics in the manifest, and block unsupported constructs or capacity violations that have no approved workaround.
- Capture a maintained known-gap catalog, including native alternatives, short-term workarounds, semantic losses, and cases with no payload-only solution.
- Use Willow's source models at commit `1d19b2584df02e05714628a57a7ddd69edeef29c` as the reproducible integration fixture, supplemented by focused DTDLv3 fixtures.
- Keep first-version scope ontology-first, as confirmed by the user. Real data bindings, Fabric deployment, device control, and automatic repair of source models are excluded.

## Capabilities

### New Capabilities

- `dtdl-model-resolution`: Load and resolve DTDLv3 collections, supported extension vocabularies, source provenance, and explicit bounded model selections.
- `fabric-ontology-emission`: Map resolved models directly to deterministic ontology-first TMDL parts and the Fabric REST definition envelope.
- `conversion-compatibility`: Classify mapping fidelity, enforce explicit loss policies and capacity checks, and publish source-addressable gap reports and manifests.

### Modified Capabilities

None. The project currently has no existing capability specs or converter implementation.

## Impact

- Add a Python package, CLI, focused tests, fixture acquisition/checksum metadata, and user documentation during implementation; this change creates planning artifacts only.
- Introduce no RDF libraries, Fabric credentials, network model resolution, or mandatory .NET dependencies.
- Target the documented new-experience Ontology item definition, not the old entity-type JSON contract.
- Fabric tenant rollout and service-side validation remain external acceptance dependencies. Local validation alone must never be described as a verified Fabric import.
- Large Willow projections can exceed the 10,000 entity-relationship limit and, if data-backed later, the combined table/column budget. The converter must fail explicitly, not claim that multiple requests bypass item-level limits.
