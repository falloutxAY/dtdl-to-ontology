# Readable names and source metadata

The converter uses DTDL model/programming names, not hashes or a guessed
localized display label. For `dtmi:com:willowinc:Settings;1`:

| Surface | Generated name |
| --- | --- |
| Namespace | `com_willowinc` |
| Entity type | `Settings` |
| Property | Its source name, for example `height` |
| Relationship | Owner plus source name, for example `Building_ownedBy` |
| Relationship label | `ownedBy` |

Names use ASCII letters, digits and underscores; source punctuation becomes
underscores. There is no automatic hash, model-version suffix or truncation.
A DTMI with no namespace uses a bare entity name in Fabric's default namespace.
Generated edge entities/links also use readable owner/path/role names.

## Metadata, not name decoration

Supported Ontology annotations carry key/value provenance:

```text
entity 'com_willowinc#Settings'
    annotation 'dtdlModelId' = dtmi:com:willowinc:Settings;1
    annotation 'dtdlModelVersion' = 1
    annotation 'dtdlSourceName' = Settings
```

`dtdlModelVersion` is the model's `;1` or `;major.minor`, **not** DTDL language
version 3. It is omitted for versionless source models, not invented.
Property metadata identifies its **declaring** source model even when its
properties were flattened into a derived type.

| Annotation | Meaning |
| --- | --- |
| `dtdlModelId`, `dtdlModelVersion` | Original model identity and optional version |
| `dtdlSourceName` | Source model/property/relationship name |
| `dtdlNamespace` | Original namespace, on the namespace object |
| `dtdlSchema`, `dtdlUnit` | Recognized source property schema/unit, when present |
| `dtdlValueEncoding = json` | Projected property requires downstream JSON serialization |
| `dtdlSourceSelector` | Exact source selector for a generated relationship |
| `dtdlProjectionRole` | Identifies a generated edge entity or missing-target placeholder |

These are annotations, not business properties, validation rules or runtime
behavior. They do not consume entity-property slots, but do count against
annotation/text/document limits. Complete originals and localized metadata
remain in `manifest.json`; large enum/object definitions are not stuffed into
annotations.

## Conflicts require a decision

The converter checks the **selected output**, case-insensitively, before
publication. Checks cover namespaces, entities, relationships, and properties
including native inherited scopes. Examples:

- Two versions of `Settings` both want the name `Settings`.
- `Sensor` and `sensor` collide in Fabric.
- Namespaces `a:b` and `a_b` both normalize to `a_b`.
- A renamed local property collides with an inherited property.

`NAME_CONFLICT` lists the source keys and scope. No winner, suffix or source
repair is chosen automatically. Unknown aliases, reserved namespace/filename
names and nonportable filename lengths produce `NAME_CONFIG`.
These checks do not inspect an existing workspace: analyze/convert stay offline.

To supply reviewed aliases, put a `names` object in `--config`:

```json
{
  "names": {
    "entities": {
      "dtmi:example:Settings;1": "SettingsLegacy",
      "dtmi:example:Settings;2": "SettingsCurrent"
    }
  }
}
```

The supported maps are `namespaces` (original colon-separated namespace),
`entities` (source identity), `properties` (`emitted-entity-identity/property`),
and `relationships` (exact generated relationship identity). Values are
nonempty ASCII identifiers. Use keys from the selected output/manifest;
stale or misspelled entries are rejected. Naming aliases do not require
`--compatibility` and do not approve semantic losses.

```powershell
dtdl-to-ontology convert examples\name-conflict.json --config examples\names.json --name Named --output output\named
```

For terminal prompts instead:

```powershell
dtdl-to-ontology convert examples\name-conflict.json --interactive-names --name Named --output output\interactive
```

Prompts occur only after a conflict is found. They require a terminal and cannot
be combined with `--json`; CI/redirected runs never wait for input. A blank
answer or EOF cancels without publishing. Resolved aliases are saved as
`naming.json` alongside reports, ready to reuse with `--config`. Combine that
file's `names` object with your policy configuration when both are needed.

Without explicit resolution, a blocked conversion publishes diagnostics and
the manifest, **not** a ready definition.

## Existing deployments

This naming strategy changes visible names, part paths and namespace lineage
tags from the older always-hashed output. Entity/property/relationship lineage
UUIDs remain source-based and unchanged by aliases; they are not visible name
suffixes. Metadata alone does not make multiple model versions the same type.

TMDL annotation values are text, not JSON literals. The converter emits
trimmed single-line provenance values without adding quotation marks.
Unsupported annotation text is rejected, not silently escaped into a different
metadata value.

The deploy command creates a new item; it does not rename an old ontology.
Use a separately named test item and review bindings, queries and downstream
dependencies before adopting readable output. Stable lineage does not prove
that an in-place rename is safe or supported. Historical acceptance fingerprints
remain evidence for the original payload, not the new naming strategy.

The readable Building projection has separate
[definition-level service evidence](fabric-acceptance.md#readable-name-willow-verification).
That does not establish safe renaming of existing bound items.
