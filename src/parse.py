import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Set

from scraper.dota.types import Buffs, DotaItem
from utils import snake_case_to_camel_case


def normalize_name(name: str) -> str:
    return name.replace(" ", "_").replace("'", "")


def dota_item_to_rdf_entry(item: DotaItem) -> str | None:
    normalized_name = normalize_name(item.name)
    ans = ""
    if len(set(item.recipe)) != len(item.recipe):
        for r in item.recipe:
            quantity = item.recipe.count(r)
            if quantity < 2:
                continue
            r_normalized = normalize_name(r)
            ans += f"""
            <!-- http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{r_normalized}_{quantity}x -->

            <owl:NamedIndividual rdf:about="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{r_normalized}_{quantity}x">
                <rdf:type rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#BuildSchemaSlot"/>
                <kg-dota:hasItem rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{r_normalized}"/>
                <kg-dota:quantity rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">{quantity}</kg-dota:quantity>
            </owl:NamedIndividual>
            """

    if item.recipe:
        ans += f"""
        <!-- http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{normalized_name}_BS -->

        <owl:NamedIndividual rdf:about="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{normalized_name}_BS">
            <rdf:type rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#BuildSchema"/>
        """

        processed_components: Set[str] = set()
        for r in item.recipe:
            quantity = item.recipe.count(r)
            r_normalized = normalize_name(r)
            if r_normalized in processed_components:
                continue
            processed_components.add(r_normalized)
            if quantity == 1:
                ans += f'<kg-dota:hasSlot rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{r_normalized}"/>\n'
            else:
                ans += f'<kg-dota:hasSlot rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{r_normalized}_{quantity}x"/>\n'
        ans += "</owl:NamedIndividual>\n"

    ans += f"""
    <!-- http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{normalized_name} -->

    <owl:NamedIndividual rdf:about="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{normalized_name}">
        <rdf:type rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#DotaItem"/>
        {f'<kg-dota:hasBuildSchema rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{normalized_name}_BS"/>' if item.recipe else ''}
        <kg-dota:cost rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">{item.cost}</kg-dota:cost>
    """
    if item.buffs:
        for k, v in item.buffs.items():  # type: ignore
            if not v:
                continue
            buff_name = snake_case_to_camel_case(k)
            ans += f'<kg-dota:{buff_name} rdf:datatype="http://www.w3.org/2001/XMLSchema#decimal">{v}</kg-dota:{buff_name}>\n'
    ans += f"""    
        <kg-dota:name>{item.name}</kg-dota:name>
        <kg-dota:imageUrl>{item.image}</kg-dota:imageUrl>
        <kg-dota:wikiUrl>{item.url}</kg-dota:wikiUrl>
    </owl:NamedIndividual>
    """

    return ans


def main() -> None:
    # 0. create data properties for buffs
    for k in Buffs.__annotations__.keys():
        buff_name = snake_case_to_camel_case(k)
        entry = f"""
        <!-- http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{buff_name} -->

        <owl:DatatypeProperty rdf:about="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#{buff_name}">
            <rdfs:domain rdf:resource="http://www.semanticweb.org/lavrent/ontologies/2025/9/kg-dota#Item"/>
        </owl:DatatypeProperty>
        """
        print(entry)

    # 1. load items
    d = json.load(open("items.json"))
    data: Dict[str, DotaItem] = {}
    for k, v in d.items():
        data[k] = DotaItem(**v)

    # 2. init recipes
    for item in sorted(data.values(), key=lambda x: x.order or 0):
        if "Recipe" not in item.recipe:
            continue
        recipe_name = normalize_name(item.name) + "_Recipe"
        item.recipe.remove("Recipe")
        recipe_cost = item.cost - sum([data[r].cost for r in item.recipe])
        item.recipe.append(recipe_name)
        data[recipe_name] = DotaItem(
            name=recipe_name,
            cost=recipe_cost,
            image="https://dota2.ru/img/items/recipe.jpg",
            url="",
            recipe=[],
            order=None,
        )

    # 3. generate rdf
    failed: List[DotaItem] = []
    for item in data.values():
        rdf_entry = dota_item_to_rdf_entry(item)
        if rdf_entry is None:
            failed.append(item)
        else:
            print(rdf_entry)

    # print("failed items:")
    # for i in range(len(failed)):
    #     print(f"{i+1}: {failed[i]}")


if __name__ == "__main__":
    main()
