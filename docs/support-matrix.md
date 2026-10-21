# Target support and verification

The current profile is `fabric-new-2026-10-20`, based on the
[new-experience definition contract](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition).
It targets TMDL ontology extensions, not old-experience entity JSON.

| Surface | Evidence | Current status |
| --- | --- | --- |
| Unbound entities and scalar properties | Address passed with 3 types/6 strings; corrected Building passed with 10 types/79 properties: 65 string, 10 double, 2 boolean, 2 int64 | These scalar projections service-verified in the supplied test environment; dateTime not independently live-tested |
| Complex fixed structs | Syntax documented, but original Building create rejected 15 unbound struct properties with ComplexLogicalBackingMismatch | Native unbound publication gated; real recursive backing is outside scope |
| JSON-string object/component projection | Corrected Building round trip preserved all 15 approved string fallbacks and entity/property lineages | Implemented behind json-objects; native field typing/querying lost; runtime serialization/ingestion not tested |
| Single-parent inheritance | Contract documents baseEntityType, with gradual rollout | Requires explicit user target declaration |
| Unbound entity relationships | Reference examples use backing configurations; no explicit unbound acceptance evidence obtained | Unverified and disabled |
| Real tenant import/round trip | Authorized service tests on 2026-10-20: Address and corrected bounded Building passed create/getDefinition/UI | Bounded acceptance, not whole-Willow support |

The revised profile requires struct backing and identifies `json-objects` as the
explicit lossy fallback. Component identity loss separately requires
`component-properties`. Source and nested mapping blockers remain non-waivable.
Service evidence is separate from generated reports, whose service-acceptance
status remains unverified. See [acceptance evidence](fabric-acceptance.md).

Declaring tenant inheritance support does not verify service acceptance.
No CLI flag can override the unbound-relationship gate in the shipped profile.
An internal profile must carry both contract support and recorded evidence before
the relationship serializer can be used. This is not a claim that relationships
are unsupported by Fabric generally.

The profile checks 10,000 entities/relationships, 1,000 properties per entity,
100 annotations per object, 4,000-character descriptions/annotation values, and
512-character names. Complex properties have 32 levels, 4,096 nodes and 1,024
fields per struct. Whole logical-document backstops are 1,000,000 JSON nodes and
160 levels. These apply to the planned logical definition, not its Base64 envelope.
Unknown transport/tenant constraints remain unverified. Multiple API requests
cannot bypass per-item limits.
