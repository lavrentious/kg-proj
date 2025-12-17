import argparse
import logging
from collections import defaultdict
from difflib import get_close_matches
from typing import Dict, Optional, Set, Tuple

from rdflib import RDF, Literal, URIRef

from kg.logger import getLogger, setLevel
from kg.onto.builder import DotaOntoBuilder
from kg.utils import normalize_name

logger = getLogger(__name__)


def get_name_from_uri(uri: URIRef) -> str:
    return uri.split("#", 1)[-1]


def get_full_recipe_with_subitems(
    builder: DotaOntoBuilder, item_uri: URIRef, visited: Optional[Set[URIRef]] = None
) -> Tuple[Dict[str, int], Set[str]]:
    """
    Returns:
        - leaves: dict of leaf components -> count
        - sub_items: set of direct or indirect sub-items (includes intermediate items)
    """
    if visited is None:
        visited = set()
    if item_uri in visited:
        return {}, set()
    visited.add(item_uri)

    leaves: Dict[str, int] = defaultdict(int)
    sub_items: Set[str] = set()

    graph = builder.graph
    KG = builder.KG

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

                sub_leaves, sub_sub_items = get_full_recipe_with_subitems(
                    builder, slot_item_uri, visited
                )
                for k, v in sub_leaves.items():
                    leaves[k] += v * qty
                sub_items.add(get_name_from_uri(slot_item_uri))
                sub_items.update(sub_sub_items)
            else:
                # Slot directly points to a DotaItem
                sub_leaves2, sub_sub_items2 = get_full_recipe_with_subitems(
                    builder, slot_uri, visited
                )
                for k, v in sub_leaves2.items():
                    leaves[k] += v
                sub_items.add(get_name_from_uri(slot_uri))
                sub_items.update(sub_sub_items2)
    else:
        # Leaf item
        leaves[get_name_from_uri(item_uri)] += 1

    return dict(leaves), sub_items


def get_full_recipe_cached(
    builder: DotaOntoBuilder,
    item_uri: URIRef,
    cache: Dict[URIRef, Tuple[Dict[str, int], Set[str]]],
) -> Tuple[Dict[str, int], Set[str]]:
    if item_uri in cache:
        return cache[item_uri]
    leaves, sub_items = get_full_recipe_with_subitems(builder, item_uri)
    cache[item_uri] = (leaves, sub_items)
    return leaves, sub_items


def build_all_recipes_with_subitems(
    builder: DotaOntoBuilder,
) -> Dict[str, Tuple[Dict[str, int], Set[str]]]:
    """
    Precompute full recipes + sub_items for all DotaItems.
    """
    cache: Dict[URIRef, Tuple[Dict[str, int], Set[str]]] = {}
    all_recipes: Dict[str, Tuple[Dict[str, int], Set[str]]] = {}

    for s in builder.graph.subjects(predicate=RDF.type, object=builder.KG.DotaItem):
        if not isinstance(s, URIRef):
            continue
        item_name = get_name_from_uri(s)
        all_recipes[item_name] = get_full_recipe_cached(builder, s, cache)

    return all_recipes


def find_item_uri(builder: DotaOntoBuilder, name: str) -> Optional[URIRef]:
    KG = builder.KG
    normalized_input = normalize_name(name).lower()

    item_map = {}
    for s in builder.graph.subjects(predicate=RDF.type, object=KG.DotaItem):
        if not isinstance(s, URIRef):
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
        print(f"Item '{name}' not found. Did you mean one of these?")
        for match in close_matches:
            print(f"  - {item_map[match]}")
    else:
        print(f"Item '{name}' not found. Available DotaItems:")
        for actual_name in sorted(item_map.values()):
            print(f"  - {actual_name}")
    return None


def find_crafts_into(
    all_recipes_with_subitems: Dict[str, Tuple[Dict[str, int], Set[str]]],
    item_name: str,
) -> list[str]:
    """
    Find all items that can be crafted from the given item (directly or transitively).
    """
    targets = [
        target
        for target, (_, sub_items) in all_recipes_with_subitems.items()
        if item_name in sub_items
    ]
    return sorted(targets)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find items that a Dota item can be crafted into"
    )
    parser.add_argument("item_name", type=str, help="Name of the Dota item")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--ontology", type=str, default="kg-dota.rdf", help="Path to ontology RDF file"
    )
    args = parser.parse_args()

    if args.verbose:
        setLevel(logging.DEBUG)
    else:
        setLevel(logging.INFO)

    builder = DotaOntoBuilder()
    builder.load_from_file(args.ontology)

    item_uri = find_item_uri(builder, args.item_name)
    if not item_uri:
        return

    item_name_normalized = get_name_from_uri(item_uri)
    print(f"Building full recipes cache for all items...")
    all_recipes_with_subitems = build_all_recipes_with_subitems(builder)

    targets = find_crafts_into(all_recipes_with_subitems, item_name_normalized)
    if not targets:
        print(f"\nNo items can be crafted from {item_name_normalized}.")
    else:
        print(f"\nItems that can be crafted from {item_name_normalized}:")
        for t in targets:
            print(f"  - {t}")


if __name__ == "__main__":
    main()
