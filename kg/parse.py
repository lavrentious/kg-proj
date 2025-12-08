import argparse
import logging
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace

from kg.logger import getLogger, setLevel
from kg.scraper.dota.types import AbilityStats, AbilityType, Buffs, DotaItem
from kg.scraper.dota.utils import parse_from_json
from kg.utils import normalize_name, snake_case_to_camel_case

BASE = "http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#"
ONTO_CLASSES = [
    "Ability",
    "PassiveAbility",
    "ActiveAbility",
    "NoTargetActiveAbility",
    "PointTargetActiveAbility",
    "UnitTargetActiveAbility",
    "AuraAbility",
    "ToggleAbility",
    "Item",
    "NeutralItem",
    "DotaItem",
]
KG = Namespace(BASE)

logger = getLogger(__name__)


def build_item(graph: Graph, item: DotaItem) -> None:
    name = item.name.replace(" ", "_").replace("'", "")
    item_uri = KG[name]

    # Create item individual
    graph.add((item_uri, RDF.type, KG.DotaItem))
    graph.add((item_uri, KG.cost, Literal(item.cost, datatype=XSD.integer)))
    graph.add((item_uri, KG.name, Literal(item.name)))
    graph.add((item_uri, KG.imageUrl, Literal(item.image)))
    graph.add((item_uri, KG.wikiUrl, Literal(item.url)))

    # Build schema
    if item.recipe:
        schema_uri = KG[f"{name}_BS"]
        graph.add((schema_uri, RDF.type, KG.BuildSchema))
        graph.add((item_uri, KG.hasBuildSchema, schema_uri))

        used = set()
        for comp in item.recipe:
            normalized_name = normalize_name(comp)
            qty = item.recipe.count(comp)

            if normalized_name not in used:
                used.add(normalized_name)

                if qty == 1:
                    slot_ref = KG[normalized_name]
                else:
                    slot_id = f"{normalized_name}_{qty}x"
                    slot_ref = KG[slot_id]
                    graph.add((slot_ref, RDF.type, KG.BuildSchemaSlot))
                    graph.add((slot_ref, KG.hasItem, KG[normalized_name]))
                    graph.add(
                        (slot_ref, KG.quantity, Literal(qty, datatype=XSD.integer))
                    )

                graph.add((schema_uri, KG.hasSlot, slot_ref))

    # Buffs
    if item.buffs:
        for k, val in item.buffs.asdict().items():
            if val:
                logger.debug(f"adding buff {k}={val} to item {item.name}")
                buff = snake_case_to_camel_case(k)
                prop = KG[buff]
                graph.add((item_uri, prop, Literal(val, datatype=XSD.decimal)))

    # Abilities
    if item.abilities:
        for ability in item.abilities:
            logger.debug(f"adding ability {ability} to item {item.name}")
            ability_name = name + "_" + ability.name.replace(" ", "_").replace("'", "")
            ability_uri = KG[ability_name]

            ability_type = KG.Ability
            if ability.ability_type == AbilityType.PASSIVE:
                ability_type = KG.PassiveAbility
            elif ability.ability_type == AbilityType.NO_TARGET:
                ability_type = KG.NoTargetActiveAbility
            elif ability.ability_type == AbilityType.POINT_TARGET:
                ability_type = KG.PointTargetActiveAbility
            elif ability.ability_type == AbilityType.UNIT_TARGET:
                ability_type = KG.UnitTargetActiveAbility
            elif ability.ability_type == AbilityType.AURA:
                ability_type = KG.AuraAbility
            elif ability.ability_type == AbilityType.TOGGLE:
                ability_type = KG.ToggleAbility

            graph.add((ability_uri, RDF.type, ability_type))
            graph.add((ability_uri, KG.name, Literal(ability.name)))
            graph.add((ability_uri, KG.description, Literal(ability.description)))

            if ability.cooldown is not None:
                graph.add(
                    (
                        ability_uri,
                        KG.cooldown,
                        Literal(ability.cooldown, datatype=XSD.integer),
                    )
                )
            if ability.mana_cost is not None:
                graph.add(
                    (
                        ability_uri,
                        KG.manaCost,
                        Literal(ability.mana_cost, datatype=XSD.integer),
                    )
                )

            if ability.stats:
                for stat_name, stat_value in ability.stats.asdict().items():
                    if stat_name == "additional_stats":
                        continue
                    logger.debug(
                        f"adding ability stat {stat_name}={stat_value} for ability {ability.name}"
                    )
                    stat_prop = KG[snake_case_to_camel_case(stat_name)]
                    graph.add(
                        (
                            ability_uri,
                            stat_prop,
                            Literal(stat_value, datatype=XSD.decimal),
                        )
                    )

            # Link ability to item
            graph.add((item_uri, KG.hasAbility, ability_uri))


def build_ontology(graph: Graph) -> None:
    graph.bind("kg-dota", KG)

    # Classes
    for c in ONTO_CLASSES:
        graph.add((KG[c], RDF.type, OWL.Class))

    # Class inheritance
    inheritance = [
        (KG["PassiveAbility"], KG["Ability"]),
        (KG["ActiveAbility"], KG["Ability"]),
        (KG["NoTargetActiveAbility"], KG["ActiveAbility"]),
        (KG["PointTargetActiveAbility"], KG["ActiveAbility"]),
        (KG["UnitTargetActiveAbility"], KG["ActiveAbility"]),
        (KG["AuraAbility"], KG["Ability"]),
        (KG["ToggleAbility"], KG["Ability"]),
        (KG["NeutralItem"], KG["Item"]),
        (KG["DotaItem"], KG["Item"]),
    ]
    for subclass, superclass in inheritance:
        graph.add((subclass, RDFS.subClassOf, superclass))

    # Object properties
    graph.add((KG.hasBuildSchema, RDF.type, OWL.ObjectProperty))
    graph.add((KG.hasBuildSchema, RDFS.domain, KG.DotaItem))
    graph.add((KG.hasBuildSchema, RDFS.range, KG.BuildSchema))

    graph.add((KG.hasSlot, RDF.type, OWL.ObjectProperty))
    graph.add((KG.hasSlot, RDFS.domain, KG.BuildSchema))
    graph.add((KG.hasSlot, RDFS.range, KG.BuildSchemaSlot))
    graph.add((KG.hasSlot, RDFS.range, KG.DotaItem))  # for slots with qty=1

    graph.add((KG.hasAbility, RDF.type, OWL.ObjectProperty))
    graph.add((KG.hasAbility, RDFS.domain, KG.Item))
    graph.add((KG.hasAbility, RDFS.range, KG.Ability))

    graph.add((KG.hasItem, RDF.type, OWL.ObjectProperty))
    graph.add((KG.hasItem, RDFS.domain, KG.BuildSchemaSlot))
    graph.add((KG.hasItem, RDFS.range, KG.DotaItem))

    # Datatype properties: buffs
    for k in Buffs.__annotations__:
        buff_name = snake_case_to_camel_case(k)
        graph.add((KG[buff_name], RDF.type, OWL.DatatypeProperty))
        graph.add((KG[buff_name], RDFS.domain, KG.Item))

    # initialize ability stats data properties
    for k in list(AbilityStats.__annotations__.keys()) + ["mana_cost", "cooldown"]:
        if k == "additional_stats":
            continue
        stat_name = snake_case_to_camel_case(k)
        graph.add((KG[stat_name], RDF.type, OWL.DatatypeProperty))
        graph.add((KG[stat_name], RDFS.domain, KG.Ability))
        graph.add((KG[stat_name], RDFS.range, XSD.integer))

    # Other datatype properties
    graph.add((KG.cost, RDF.type, OWL.DatatypeProperty))
    graph.add((KG.cost, RDFS.domain, KG.DotaItem))
    graph.add((KG.cost, RDFS.range, XSD.integer))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate KG-Dota RDF ontology from item JSON."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to input JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default="kg-dota.rdf",
        help="Path to output RDF file (default: kg-dota.rdf)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
        default=False,
    )
    args = parser.parse_args()

    # Configure logger
    setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Build graph
    g = Graph()
    build_ontology(g)

    # Load and process data
    logger.info(f"Loading items from {args.input}")
    data = parse_from_json(str(args.input))

    if data.dota_items:
        for item in data.dota_items.values():
            build_item(g, item)

    # Serialize
    logger.info(f"Writing RDF to {args.output}")
    g.serialize(str(args.output), format="xml")


if __name__ == "__main__":
    main()
