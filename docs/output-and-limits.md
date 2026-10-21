# Results, failures and capacity

## Output contract

A successful `convert` publishes one directory containing `definition.json`,
`manifest.json`, `report.json`, `report.md` and readable `parts\` files.
Only genuine Fabric parts enter the InlineBase64 envelope. Source originals,
fingerprints, supplied revision, all localized metadata, origins, selection reasons,
exclusions and transformations remain in the manifest. Source revisions are
recorded as supplied, not authenticated. JSON and part ordering is deterministic
for unchanged source bytes, paths and options; no timestamps/random IDs are added.
Changing source files or array positions legitimately changes fingerprints or
JSON-pointer provenance. Merely changing enumeration order does not.

The report separates analysis, selected mapping readiness, emission and service
acceptance. Counts are provisional when mappings are blocked, since a complete
target may not exist yet. `locally_validated` **never means imported or verified
by Fabric**. Runtime data bindings are not generated.

Fixed objects and projected components require explicit `json-objects` approval
to publish as unbound String properties. Each transformed property's manifest entry
retains `pre_fallback_logical_type` in addition to original source and emitted type.
This sidecar shape is not an uploaded native struct or a runtime JSON value.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Analysis completed without loader errors, or conversion published locally validated output. Analysis may still report mapping blockers. |
| 1 | Conversion blocked, or source loading had errors. Inspect findings and `source_loading_complete`. |
| 2 | Invalid arguments/configuration, nonempty destination, filesystem/publication failure, or console status-delivery failure. Inspect stderr; `--json` provides a failure object when publication has not occurred. |

## Failure recovery

Strict conversion of `examples\projection.json` returns 1 and publishes
diagnostics/manifest only: its inheritance/collections/etc. need named approval.
For example:

```powershell
.\.venv\Scripts\dtdl-to-ontology.exe convert examples\projection.json --name Blocked --output output\blocked
```

No failed conversion publishes `definition.json` or `parts\`. Configuration or I/O
errors can prevent even diagnostic files from being written; console diagnostics
then explain the failure. Reports and parts are first written to a unique sibling
staging directory, which is renamed into place only after all writes succeed.
If console output fails **after** publication, exit 2 and stderr explicitly state
that the result was saved; the valid published directory is retained, not falsely
reported as unpublished or rolled back.
Interrupted processes can leave a clearly named `.NAME.staging-*` directory; it
is not a published result and can be inspected/removed manually.

Nonempty destinations are rejected before analysis or writes. A failed retry does
not overwrite the earlier result; choose a new/empty directory. Never interpret an
unchanged previous `definition.json` as output of the failed retry. The CLI tests
exercise semantic blockers, nonempty destinations and injected disk-write failures.

## Versioned local limits

Profile `fabric-new-2026-10-20` derives from the
[new-experience definition contract](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition).
Checks run before publication, never truncate, and have exact/one-over regression
cases:

| Bound | Limit |
| --- | ---: |
| Entity types / entity relationships per item | 10,000 each |
| Effective properties per entity, including native ancestors | 1,000 |
| Annotations per object | 100 |
| Emitted descriptions / annotation values | 4,000 characters |
| Ordinary names | 512 characters |
| Complex logical-node depth / nodes per property | 32 / 4,096 |
| Fields in any individual struct | 1,024 |
| Normalized logical document nodes / depth | 1,000,000 / 160 |

Entity/relationship counts measure planned declarations, including expanded
inherited edges and generated edge roles, **not** `parts[]` length. Complex-node
counting counts each primitive/struct/any/timeSeries occurrence; root depth is 1.
Reused shape objects count each expanded occurrence, not unique Python identities.
An approved JSON-object fallback is measured as its emitted primitive String,
not its retained pre-fallback struct; that original shape remains sidecar-only.
Source resolution/traversal bounds and non-waivable source/mapping checks still
apply before fallback.

Whole-document backstops use `preflight.logical_document`: compatibility level,
model name, namespace names/lineages, target entities/properties/relationships with
their emitted names/lineages/shapes/descriptions/annotations, and platform details.
Each JSON container or scalar value counts one node; object keys do not, and root
depth is 1. Source definitions, raw metadata sidecars, report findings, TMDL escape
bytes and Base64 transport are excluded. This documented local normalization is
not proof that a tenant's internal validator counts identical synthesized defaults.
The profile does not invent transport-byte or tenant-specific limits.

Technical names use stable identity hashes, disambiguating case/sanitization
collisions independently of selection order. Source names remain in the manifest.
Annotation metadata is not automatically generated from arbitrarily large originals;
keeping it in sidecars avoids both unsupported parts and silent truncation.
An internal annotation supplied to the serializer is still size/count checked.

The future data-backed engine budget `2 + tables + columns <= 16000` is distinct;
it is not a measured budget for these unbound payloads. REST batching cannot evade
any per-item capacity constraint. Use explicit smaller roots/mappings/omissions,
not automatic truncation or an implied lossless whole-Willow conversion.

The resolver also has separate input/resource bounds documented in
[DTDL subset](dtdl-support.md), including a one-million schema/component projection
step guard. Service acceptance, feature rollout and transport limits require the
separate [manual acceptance procedure](fabric-acceptance.md).
