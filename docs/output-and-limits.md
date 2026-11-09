# CLI reference

| Command | Behavior |
| --- | --- |
| `analyze INPUT` | Offline inventory and compatibility findings; no files or service mutations |
| `convert INPUT --name NAME --output DIR` | Offline validated definition, manifest and reports |
| `deploy DEFINITION --workspace-id UUID` | Create a new Ontology and retrieve its definition; credentials required |

`INPUT` is a local JSON file or directory. Use `--root DTMI` repeatedly to select
roots; their required dependencies are included. No root means all Interfaces.
Use `--json` for machine-readable console output and `--help` for every option.
`--interactive-names` asks for explicit aliases only when conflicts occur in a
terminal; it cannot be combined with `--json`. Otherwise conflicts block output
with actionable diagnostics. [Names and annotations](naming.md).
`--source-revision` records your supplied revision; it does not authenticate it.

## Approving transformations

Strict mode is the default. `--compatibility` enables named approvals, not
automatic loss acceptance:

```powershell
dtdl-to-ontology convert examples\minimal.json --name Objects --output output\objects --compatibility --policy json-objects
```

For element-specific decisions, pass `--config mapping.json`:

```json
{
  "policies": ["omit-relationships"],
  "omit_relationships": ["dtmi:example:Building;1/contains"]
}
```

Other supported fields are `target_mappings` (selector -> target DTMI),
`placeholders` (DTMI array, requiring `placeholder-targets`), and `inheritance`
(boolean tenant capability declaration). `names` contains explicit readable-name
aliases and does not require compatibility mode. Target mapping itself requires
`--compatibility`; a placeholder does not supply the missing definition.
Selectors are exact, never wildcards. Native inheritance and
`flatten-inheritance` cannot be combined. See [policy effects](known-gaps.md).

## Output and recovery

Successful conversion publishes:

| Artifact | Purpose |
| --- | --- |
| `definition.json`, `parts/` | Fabric InlineBase64 envelope and equivalent readable UTF-8 parts |
| `manifest.json` | Original/normalized source, fingerprints, identities, selection, origins and losses |
| `report.json`, `report.md` | Findings, readiness, emission and verification status |
| `naming.json` (when aliases exist) | Reusable explicit naming decisions for `--config` |

Only actual Fabric parts enter `definition.json`. Complete originals and
pre-fallback object shapes remain in the manifest, not hidden upload parts.
Sidecars can contain sensitive source models; store them accordingly.

For unchanged input bytes/paths/options, local output is deterministic.
`locally_validated` does not mean service-accepted. Blocked conversion publishes
diagnostics only, never a partial ready definition.

Publication uses a sibling staging directory and refuses nonempty destinations.
Interrupted `.NAME.staging-*` directories are not completed results. Do not
reuse old `definition.json` after a failed run. Console failure after publication
reports that files were saved rather than rolling them back.

| Exit | Meaning |
| --- | --- |
| 0 | Analyze completed without loader errors (mapping blockers can remain), or convert published, or deploy completed create/retrieval |
| 1 | Source loading error or blocked conversion |
| 2 | Arguments/configuration, missing token, output/I/O or console delivery failure |
| 3 | Fabric request/operation/retrieval failure; created or companion items may remain |

Deployment reads `FABRIC_ACCESS_TOKEN` by default (`--token-env` changes the
variable name). Tokens are neither printed nor saved. `--folder-id` takes a
UUID; without it, creation is at workspace root. No automatic deletion occurs.
Inspect an uncertain create before retrying.

The deployment report compares part paths/text and supported normalized TMDL
fields. Differences or unsupported comparator syntax need review even when
create/retrieval succeeds. `semantic_equivalence` remains `not_asserted`.
[Acceptance procedure](fabric-acceptance.md).

## Target limits

Profile `fabric-new-2026-11-09`, based on the [public contract][contract]:

| Bound | Limit |
| --- | --- |
| Entities / relationships | 10,000 each per item |
| Effective properties / annotations | 1,000 per entity / 100 per object |
| Description or annotation text / ordinary names | 4,000 / 512 characters |
| Ontology item name | 89 ASCII letters/digits/underscores; starts with a letter |
| Complex depth / nodes / struct fields | 32 / 4,096 / 1,024 |
| Logical document nodes / depth | 1,000,000 / 160 |

Counts include generated edge entities/links and inherited properties, not just
files. Whole-document checks use the planned logical model, not Base64 transport
or source sidecars. Provenance annotations count toward annotation/text/document
budgets, but do not add entity properties. Names used as part filenames have a
250-character portability guard; choose aliases instead of truncating.
`ANNOTATION_TEXT` rejects empty, multiline/control-containing or untrimmed
annotation values rather than changing them through JSON escaping.
JSON fallbacks count as emitted String properties. Unknown
tenant/transport limits remain unverified. The separate backing-table engine
budget is not a sizing guarantee for this unbound converter.

Preflight fails rather than truncating or silently splitting an ontology.
[Source limits](dtdl-support.md#source-validation-boundaries) are separate.

[contract]: https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/ontology-definition
