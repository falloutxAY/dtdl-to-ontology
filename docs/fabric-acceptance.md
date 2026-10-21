# Fabric acceptance: bounded live verification

**Authorized live tests were performed on 2026-10-20.** Willow Address and the
corrected bounded Building projection passed create/get-definition and
new-experience UI checks. Building requires 15 explicitly approved JSON-string
object/component projections; its original native unbound structs were rejected.
This is bounded definition acceptance, not a lossless whole-Willow import or a
runtime-data test. Local test-only profiles remain insufficient service evidence.

## Observed live results

The final full suite passed **137 tests**, including all pinned Willow tests
and clean installed-wheel acceptance, with no skipped tests. Using the
user-supplied test workspace and folder, the following results were observed:

| Case | Observed result |
| --- | --- |
| Original Building: 10 types, 79 properties, 15 parts | Create returned HTTP 400, ALMOperationBadRequest; 15 native unbound struct properties failed ComplexLogicalBackingMismatch |
| Address: Address, Component and SpaceComponent | Create returned HTTP 202; the long-running operation reached Succeeded |
| Address getDefinition with explicit format=TMDL | HTTP 400, InvalidDefinitionFormat |
| Address getDefinition with no format parameter | HTTP 200; returned 8 new-experience TMDL parts |
| Address semantic comparison | 3 types and 6 string properties preserved; names, namespaces, types, entity/property lineages and model references matched |
| Address new-experience UI | All 6 properties displayed as String and Unbound; no entity key defined |
| Corrected Building with json-objects | Create returned HTTP 202; operation reached Succeeded; default getDefinition returned HTTP 200 and 15 TMDL parts |
| Building semantic comparison | All 10 types/79 properties preserved, including descriptions, names, types, entity/property lineages, namespaces and model references |
| Building scalar data types | 65 string, 10 double, 2 boolean and 2 int64; all 15 object/component fallbacks independently checked as string |
| Building new-experience UI | Graph reports 10 total types/0 relationships; all 37 Building properties displayed as Unbound, including projected String properties |
| Platform metadata | Type/name/config version preserved; service normalized the platform logicalId to the zero GUID |
| Optional CLI deployment (2026-10-21) | Create returned HTTP 202; regional operation reached Succeeded; getDefinition returned HTTP 200; all 15 expected part paths returned; semantic equivalence not asserted |
| Full Willow compiler sweep (2026-10-21) | All 3,705 pinned interfaces loaded, selected and planned; strict mode has 14,744 relationship candidates and 1,432,050 logical-document nodes; all-policy mode remains blocked with 25,297 findings and 14,780 relationships |

The rejection states that every Struct logical node requires exact recursively
paired backing configuration. Generic documentation that backingConfiguration is
optional does not establish that an unbound struct is accepted. Real data backings
are outside the current ontology-first scope. The corrected profile now blocks
these native unbound mappings with `UNBOUND_STRUCT`. Only explicit `json-objects`
approval permits whole-property string projection, after nested source and mapping
checks. Original and pre-fallback logical shapes remain in the manifest.
`component-properties`, collection and metadata policies remain independently
required where applicable. The accepted Building payload contains 22 exact
relationship omissions and no native relationships, fabricated backings or instances.
JSON strings lose field typing/querying; future ingestion must serialize valid JSON.
No instance ingestion, JSON-value validation or native-struct execution was tested.

Sanitized request/response, operation, decoded-part comparison and UI evidence is
under `output\willow-live-20261020T043948Z` for the original rejection/Address case.
Corrected Building evidence is under `output\willow-building-json-20261020T051328Z`:
`create-operation.json`, `created-item.json`, `get-definition-response.json`,
`roundtrip-comparison.json`, decoded `service-parts\`, `ui-verification.json`,
`ui-summary.json`, UI accessibility snapshots and `retained-resources.json`.
The graph viewport showed 6 of 10 entities; the total is 10, not 6 converted types.
These outputs and browser traces are ignored by Git; do not commit
workspace-specific records or credentials. Temporary authorization capture was
removed after testing. Generated conversion reports retain their original
unverified status; service results are separate evidence, not retroactive edits.

Each successful test created a new ontology. Fabric also provisioned its associated
Eventhouse, KQL database and Graph model. Both sets of test resources were retained
for inspection; no prior test/existing item was modified or cleanup deletion performed.
The optional CLI deployment verification also created and retained its own test item
and Fabric-managed companion resources.

## Procedure for further acceptance

The opt-in CLI deployment path supports the create/get-definition round trip but
does not assert semantic equivalence or runtime behavior. The remaining steps are
for an authorized human reviewing the returned parts in an isolated Fabric test
workspace on supported capacity. Do not use a production item or record credentials
in the repository, sidecars, screenshots or HTTP logs.
Fabric may return the long-running operation URL on a regional `*-redirect.analysis.windows.net`
host; the client validates this host family and uses the result URL returned by the
service when available.

## Prepare local artifacts

Run the explicitly approved fixed-object and bounded Willow commands in the
[README](../README.md) and [fixture guide](willow-fixture.md), respectively.
Inspect `report.json`: emission must be `locally_validated`, selected mapping ready
must be true and blockers zero. Service acceptance must still be `unverified`.
Confirm that `definition.json` contains only actual definition parts.

The local Building example deliberately omits relationships, so it cannot establish
unbound relationship or edge-reification support. Its 15 parts define 10 types and
79 properties, with source originals and all omissions retained in sidecars.

## Create and retrieve in a test workspace

1. Obtain explicit permission to create an isolated ontology test item. Record the
   workspace/capacity, tenant feature state, caller permission model and converter
   revision in an access-controlled acceptance record. A contributor workspace role
   and an applicable Fabric item read/write authorization are required; do not
   assume all identity types or preview features are supported.
2. For an automated create/get-definition round trip, set an already acquired access
   token in `FABRIC_ACCESS_TOKEN` and invoke the opt-in CLI command with a generated
   `definition.json`:

   ```powershell
   $env:FABRIC_ACCESS_TOKEN = az account get-access-token --scope https://api.fabric.microsoft.com/.default --query accessToken --output tsv
   .\.venv\Scripts\dtdl-to-ontology.exe deploy output\willow-building-json\definition.json --workspace-id <workspace-guid> --json
   Remove-Item Env:FABRIC_ACCESS_TOKEN
   ```

   The command creates a new Ontology in the workspace root, follows `202` operation
   status/result requests, then calls `getDefinition` without a format override and
   decodes the returned UTF-8 parts. Supply `--folder-id <folder-guid>` only when a
   Fabric folder UUID is known; omitting it creates at workspace root. Use a unique
   display name when converting. The command reports item/operation IDs, whether
   submitted and returned part paths match, whether decoded part text is identical,
   and lists missing, additional and textually changed paths. These are exact
   decoded-text diagnostics only: text equality is not semantic equivalence, and
   text differences may reflect harmless service normalization. The command
   deliberately does not assert semantic equivalence or save raw service responses.
   Its success means create plus retrieval succeeded, not full migration acceptance.
   The created item and Fabric-managed companion resources are retained; no automatic
   cleanup occurs.

   To perform the steps manually instead, follow [Create Item](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/create-item):
   submit `POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items`.
   Supply a JSON body with `displayName` equal to the intended test item name,
   `type` equal to `Ontology`, and `definition` equal to the **parsed contents**
   of generated `definition.json`. Do not wrap that contents in a JSON string,
   send `creationPayload` as well, or upload the manifest/report as extra parts.
3. Record the response status and returned item ID. On `202 Accepted`, follow the
   documented [long-running operation protocol](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation),
   including `Location`, `Retry-After`, final operation status and result.
   A `202` alone is not successful import. Preserve sanitized validation error codes
   and messages for any rejected construct; never suppress them or fake a backing table.
4. Follow [Get Item Definition](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/get-item-definition):
   submit `POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/getDefinition`.
   In the tested environment, specifying `format=TMDL` was rejected; omitting it
   returned TMDL. Check the actual returned part paths/content rather than assuming
   a successful response uses the new-experience format.
   This endpoint requires item read **and write** permission, despite being a
   retrieval operation. Handle `202`/LRO and throttling as documented.
   Save the successful response's `definition.parts` separately from local output.
5. Strictly decode every returned `InlineBase64` payload as UTF-8. Compare normalized
   semantics, not byte hashes: part ordering, whitespace, quoting and defaults can
   differ, and the service can synthesize required parts or elide defaults.
   Verify required platform/database/model/default namespace parts, compatibility
   level 1000000, metadata type Ontology/config version 2.0, entity names/namespaces,
   descriptions, lineages and property data types. Verify every approved object
   fallback is String and its pre-fallback shape remains in the local manifest;
   do not mistake this for accepted native complex shapes.
   Descriptions may be rendered as doc comments. Display names/namespaces are
   server-derived, not writable TMDL fields.
6. Inspect the new-experience item UI as an additional check. Types/properties must
   be present and unbound; there must be no fabricated rows, keyProperty, tables,
   partitions, source expressions or property backing configurations. This does
   not test device execution, ingestion, unit conversion or constraint enforcement.
7. Record passed/rejected cases and normalized differences. Obtain separate approval
   before any cleanup deletion. Keep acceptance evidence outside generated local
   reports rather than changing their unverified status retroactively.

## Separate feature probes

The corrected Building result exercises approved object/component, enum,
collection, temporal-string and metadata projections as scalar definitions.
It does not establish native struct or runtime semantics. Test independent
primitive/feature cases separately; for example, native dateTime was not included
in this live payload.

Native inheritance requires confirmed target rollout. Only then use the explicit
`examples\native.json` declaration to create a **new** base/derived item, retrieve
it, and verify `baseEntityType` and inherited properties. Test deeper ancestors
separately: native polymorphic query expansion is documented as base plus direct
children, not a transitive DTDL query equivalent. `baseEntityType` and property
`redefines` are immutable on create, so do not reparent an existing test item.

Unbound relationships remain disabled in the shipped profile. An authorized
contract/service probe must independently create two unbound entities and one
hand-authored `entityRelationship` with concrete `fromEntity`/`toEntity`, without
backing configuration; then retrieve and inspect the accepted relationship.
If rejected or unavailable, retain the blocker and exact omission workaround.
If accepted, retain request/response/normalized evidence and review a versioned
profile change with regressions before enabling production output. Reification
also needs a separate edge-entity/endpoints probe; a policy alone is not evidence.

## Acceptance record

The current local acceptance run uses Python 3.11 and includes the complete pinned
Willow fixture, not skipped integration tests:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
openspec validate dtdlv3-to-fabric-ontology --strict
```

`tests\test_installation.py` builds a wheel offline, installs it without dependencies
in a new virtual environment, and invokes its console entry point outside the
checkout with Python path overrides removed and user-site packages disabled.
It verifies installed-package imports, strict conversion, decoded/readable part
equality, unverified service status and diagnostic-only rejection of malformed
enums even with `enum-underlying` approved. This checks packaging and local behavior,
not the Fabric service's interpretation of TMDL.

| Evidence | Current state |
| --- | --- |
| Automated local checks | 137 passed, including all pinned Willow tests; Ruff lint/format and strict OpenSpec passed |
| Installed distribution | Clean Python 3.11 environment; offline wheel installation and CLI execution outside checkout passed |
| Pinned Willow source/fingerprints | Locally checked at revision `1d19b2584df02e05714628a57a7ddd69edeef29c` |
| Bounded Building payload | `output\willow-building-json-20261020T051328Z\definition.json`; 10 types, 79 properties, 0 relationships, 15 parts, 15 JSON-object fallbacks and 22 explicit omissions |
| Full-corpus coverage | `docs\willow-full-coverage.md`; detailed execution output is in ignored `output\willow-full-coverage-20261021\` |
| Payload integrity | Every Base64 payload equals its readable UTF-8 part; all returned parts compared semantically without losing property/type/lineage associations |
| Definition SHA-256 | `513d772f5551ae3f97f8262732c14d7b3ef98de285c4fe348f091d532ab251aa` |
| Selected mapping blockers | 0 for the explicitly configured bounded example |
| Whole-source strict conversion | Blocked, including absent LeaseContract, annotation mismatch and target limits |
| Fabric create/getDefinition/UI | **Address and corrected bounded Building passed; original native unbound structs rejected and now gated** |
| Explicit getDefinition format | format=TMDL rejected; default request returned TMDL successfully |
| Native inheritance service probe | **Unverified; user declaration is not evidence** |
| Unbound relationship service probe | **Unverified; output remains gated** |
| Device/ingestion/unit execution | Outside this definition-only implementation |

Authoritative syntax:
[Ontology new-experience definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/ontology-definition).
