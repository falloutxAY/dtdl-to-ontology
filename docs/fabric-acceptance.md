# Fabric acceptance evidence

**Tested November 9, 2026** in an authorized Fabric test folder, using new
Ontology items and the public Create Item / Get Definition APIs. Existing
items were not modified. No runtime bindings, data ingestion or graph queries
were performed. Items and service-created companions were retained for review.

## Verified definition shapes

The following **actual converter outputs** completed creation (`202` ->
`Succeeded`) and retrieval (`200`). The comparator found no differences in
supported names, namespaces, properties, types, descriptions, lineage,
`baseEntityType`, or relationship endpoints. All expected part paths returned.

| Runnable source | Entities / declared properties / relationships | Required options |
| --- | --- | --- |
| `examples/scalars.json` | 1 / 5 / 0 | None: string, boolean, int64, double, dateTime |
| `examples/relationships.json` | 2 / 2 / 1 | None: concrete-target unbound edge |
| `examples/inheritance.json` | 2 / 1 / 0 | `--config examples/native.json` |
| `examples/multiple-inheritance.json` | 3 / 5 / 0 | `flatten-inheritance` |
| `examples/edge-properties.json` | 2 / 2 / 2 | `reify-relationship-properties` |
| `examples/projection.json` | 3 / 6 / 0 | Component/JSON/enum/metadata/flattening policies below |

Property counts are **declarations**, not expanded inherited instance values.
These results justify enabling unbound relationships in the default profile;
they do not guarantee tenant rollout or acceptance of every possible graph.
Native inheritance remains an explicit target declaration.

The service normalized whitespace and platform metadata, so byte-for-byte
equality was false. Supported-field equality is narrower than semantic
equivalence. The [sanitized record](evidence/2026-11-09.json) contains source and
payload fingerprints, counts and outcomes, without tenant/resource IDs.

## Rejected and unverified shapes

A separate hand-authored **unbound Struct** probe returned HTTP 400 with
`ComplexLogicalBackingMismatch`: a logical Struct requires exact recursive
backing configuration. The CLI continues to block it unless `json-objects`
explicitly approves String projection. Backed structs were not tested.

An initial exploratory payload incorrectly used `default#Name`; the service
rejected it with `InvalidCompositeName`. Corrected probes used an explicit
namespace. That rejection is not a DTDL limitation, and the converter's generated
namespace syntax was already valid.

Native multiple inheritance was **not** submitted with invented syntax:
the current public contract has one `baseEntityType`. Its implemented
flattening alternative was tested. Deep polymorphism, runtime reified-edge
traversal, external Fabric workarounds, and instance-value validation remain
unverified. Historical Willow runs are not used as evidence for these new cases.

## Reproduce

Install the package, choose a fresh name/output directory, and convert:

```powershell
dtdl-to-ontology convert examples\relationships.json --name RelationshipCheck --output output\relationship-check
dtdl-to-ontology convert examples\multiple-inheritance.json --name FlattenCheck --output output\flatten-check --compatibility --policy flatten-inheritance
dtdl-to-ontology convert examples\edge-properties.json --name EdgeCheck --output output\edge-check --compatibility --policy reify-relationship-properties
dtdl-to-ontology convert examples\projection.json --name ProjectionCheck --output output\projection-check --compatibility --policy flatten-inheritance --policy component-properties --policy json-collections --policy json-objects --policy enum-underlying --policy metadata-semantics
```

Inspect `report.json` and approved losses in `manifest.json`. Then use the
[README deployment command](../README.md#deploy-only-after-review) for each
`definition.json`. Supply a **folder UUID**, not the numeric browser
`subfolderId`. Get Definition must omit `format=TMDL` in the tested environment.

Check `service_acceptance`, `create_operation_status`,
`semantic_comparison.supported_fields_match`, missing/additional parts, and
mapping-loss context. A successful command does not make an unexplained
comparison difference acceptable. Never change the offline report to claim
live verification after the fact.

For production acceptance, additionally test actual keys/bindings, row counts,
values, duplicates/deletes, edge endpoints, queries, freshness and rollback.
Approve any cleanup separately: a failed operation may leave companion items,
and an uncertain create must be investigated before retrying.

Public references: [Ontology definition][definition], [Create Item][create],
[Get Item Definition][get], [long-running operations][lro].

[definition]: https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/ontology-definition
[create]: https://learn.microsoft.com/rest/api/fabric/core/items/create-item
[get]: https://learn.microsoft.com/rest/api/fabric/core/items/get-item-definition
[lro]: https://learn.microsoft.com/rest/api/fabric/articles/long-running-operation
