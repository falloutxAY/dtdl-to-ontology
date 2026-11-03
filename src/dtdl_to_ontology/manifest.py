"""Complete provenance sidecar, deliberately separate from Fabric definition parts."""

from dataclasses import asdict

from .extensions import semantics
from .geo import GEOSCHEMAS
from .naming import lineage, property_name, target_name
from .plan import Plan
from .report import ordered_findings


def build_manifest(plan: Plan) -> dict:
    collection = plan.selection.resolution.collection
    source_models = {}
    for identifier, model in collection.models.items():
        source_models[identifier] = {
            "definition": model.original if model.original is not None else model.raw,
            "normalized_definition": model.raw,
            "sources": [asdict(source) for source in sorted(model.sources)],
            "selected": identifier in plan.selection.selected,
        }
    targets = {}
    for identity, entity in sorted(plan.entities.items()):
        name = target_name(identity)
        targets[identity] = {
            "kind": "entity",
            "name": name.qualified,
            "lineageTag": name.lineage_tag,
            "source": asdict(entity.source),
            "role": entity.role,
            "placeholder": entity.placeholder,
            "base": entity.base,
            "properties": [
                {
                    "name": prop.name,
                    "target_name": property_name(identity, prop.name),
                    "lineageTag": lineage(identity + "/" + prop.name, "property"),
                    "source_owner": prop.owner,
                    "source": asdict(prop.source),
                    "logical_type": prop.logical_type,
                    **(
                        {"pre_fallback_logical_type": prop.pre_fallback_logical_type}
                        if prop.pre_fallback_logical_type is not None
                        else {}
                    ),
                    "original": prop.original,
                }
                for prop in sorted(entity.properties, key=lambda prop: prop.name)
            ],
        }
    relationships = {}
    for relation in sorted(plan.relationships, key=lambda relation: relation.identity):
        name = target_name(relation.identity, "relationship")
        relationships[relation.identity] = {
            "name": name.qualified,
            "lineageTag": name.lineage_tag,
            "from": relation.from_entity,
            "to": relation.to_entity,
            "source": asdict(relation.source),
        }
    return {
        "schema_version": 1,
        "source_revision_as_supplied": plan.options.source_revision,
        "source_files_sha256": dict(sorted(collection.fingerprints.items())),
        "selection": plan.selection.inventory(),
        "target_profile": plan.profile.to_dict(),
        "source_models": source_models,
        "normalization": [
            {"source": asdict(change["source"]), "owner": change["owner"]}
            for change in collection.normalization
        ],
        "source_elements": {
            identity: {
                "owner": element.owner,
                "source": asdict(element.source),
                "explicit": element.explicit,
                "types": element.raw.get("@type"),
                "active_contexts": collection.active_contexts.get(element.source, ()),
                "semantics": {
                    **semantics(element.raw, collection.contexts_at(element.source)),
                    "target_enforcement": False,
                },
            }
            for identity, element in sorted(
                plan.selection.resolution.graph.elements.items()
                if plan.selection.resolution.graph
                else []
            )
        },
        "standard_geospatial_schemas": GEOSCHEMAS,
        "target_entities": targets,
        "target_relationships": relationships,
        "policies": sorted(plan.options.policies),
        "target_mappings": plan.options.target_mappings,
        "transformations_and_findings": [
            finding.to_dict() for finding in ordered_findings(plan.findings)
        ],
        "source_parent_graph": plan.selection.resolution.parents,
        "effective_declaration_origins": {
            identifier: {
                name: [
                    {"owner": origin.owner, "source": asdict(origin.source)} for origin in origins
                ]
                for name, origins in contents.items()
            }
            for identifier, contents in plan.selection.resolution.origins.items()
            if identifier in plan.selection.selected
        },
    }
