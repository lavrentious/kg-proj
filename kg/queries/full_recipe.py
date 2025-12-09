import logging
from collections import defaultdict
from typing import Dict, Optional, List

import argparse
from difflib import get_close_matches
from rdflib import RDF, Literal, URIRef
from kg.logger import getLogger, setLevel
from kg.onto.builder import DotaOntoBuilder
from kg.utils import normalize_name

logger = getLogger(__name__)


def get_name_from_uri(uri: URIRef) -> str:
    return uri.split("#", 1)[-1]


def get_full_recipe(
    builder: DotaOntoBuilder, item_uri: URIRef, visited: Optional[set[URIRef]] = None
) -> Dict[str, int]:
    """
    Recursively fetches the full recipe for a Dota item from the ontology.
    """
    if visited is None:
        visited = set()

    if item_uri in visited:
        return {}  # prevent infinite recursion
    visited.add(item_uri)

    graph = builder.graph
    KG = builder.KG
    recipe: dict[str, int] = defaultdict(int)

    schema_uris = list(graph.objects(item_uri, KG.hasBuildSchema))
    if schema_uris:
        schema_uri = schema_uris[0]
        for slot_uri in graph.objects(schema_uri, KG.hasSlot):
            if not isinstance(slot_uri, URIRef):
                logger.warning(f"Invalid slot URI: {slot_uri}")
                continue

            slot_items = list(graph.objects(slot_uri, KG.hasItem))
            if slot_items:
                slot_item_uri = slot_items[0]
                if not isinstance(slot_item_uri, URIRef):
                    logger.warning(f"Invalid slot item URI: {slot_item_uri}")
                    continue

                qty_objs = list(graph.objects(slot_uri, KG.quantity))
                qty = (
                    int(qty_objs[0])
                    if qty_objs and isinstance(qty_objs[0], Literal)
                    else 1
                )

                logger.debug(
                    f"Slot {get_name_from_uri(slot_uri)} has item {get_name_from_uri(slot_item_uri)} x {qty}"
                )

                sub_recipe = get_full_recipe(builder, slot_item_uri, visited)
                if sub_recipe:
                    for name, count in sub_recipe.items():
                        recipe[name] += count * qty
                else:
                    recipe[get_name_from_uri(slot_item_uri)] += qty
            else:
                sub_recipe = get_full_recipe(builder, slot_uri, visited)
                if sub_recipe:
                    for name, count in sub_recipe.items():
                        recipe[name] += count
                else:
                    recipe[get_name_from_uri(slot_uri)] += 1
    else:
        logger.debug(
            f"Item {get_name_from_uri(item_uri)} has no build schema, counting as leaf"
        )

    return dict(recipe)


def find_item_uri(builder: DotaOntoBuilder, name: str) -> Optional[URIRef]:
    KG = builder.KG
    normalized_input = normalize_name(name).lower()

    item_map = {}  # normalized_name -> actual_name
    for s in builder.graph.subjects(predicate=RDF.type, object=KG.DotaItem):
        if not isinstance(s, URIRef):
            logger.warning(f"Invalid DotaItem URI: {s}")
            continue
        actual_name = get_name_from_uri(s)
        normalized_name = normalize_name(actual_name).lower()
        item_map[normalized_name] = actual_name

    if normalized_input in item_map:
        return KG[item_map[normalized_input]]

    close_matches = get_close_matches(
        normalized_input, item_map.keys(), n=5, cutoff=0.75
    )
    if close_matches:
        print(f"item '{name}' not found. did you mean one of these?")
        for match in close_matches:
            print(f"  - {item_map[match]}")
    else:
        print(f"item '{name}' not found. available DotaItems:")
        for actual_name in sorted(item_map.values()):
            print(f"  - {actual_name}")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch full Dota item recipe from ontology"
    )
    parser.add_argument("item_name", type=str, help="Name of the Dota item")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        setLevel(logging.DEBUG)
    else:
        setLevel(logging.INFO)

    builder = DotaOntoBuilder()
    builder.load_from_file("kg-dota.rdf")

    item_uri = find_item_uri(builder, args.item_name)
    if not item_uri:
        return

    full_recipe = get_full_recipe(builder, item_uri)
    print(f"\nFull recipe for {args.item_name}:")
    for name, qty in full_recipe.items():
        print(f"{name} x {qty}")


if __name__ == "__main__":
    main()
