import json
import logging
import re
from dataclasses import asdict, is_dataclass
from difflib import get_close_matches
from typing import Any, Dict, List, Tuple

from scraper.dota.consts import BUFF_KEYWORDS
from scraper.dota.types import Ability, AbilityStats, AbilityType, Buffs, DotaItem

logger = logging.getLogger(__name__)


def raw_to_name_cost(raw: str) -> Tuple[str, int] | None:
    if not isinstance(raw, str):
        return None

    m = re.search(r"^(.+) \((\d+)\)$", raw)
    if m is None:
        logger.error(f"no match at {raw}")
        return None

    name, cost = m.groups()
    if not name or not cost:
        logger.error(f"no name or cost at {raw}")
        return None
    return name, int(cost)


def set_orders(items: Dict[str, DotaItem]) -> Dict[str, DotaItem]:
    ans: Dict[str, DotaItem] = items.copy()
    orders: Dict[str, int] = {}

    def get_order(name: str) -> int:
        if name.endswith("Recipe"):
            return 0
        if name in orders:
            return orders[name]
        orders[name] = max([get_order(i) for i in items[name].recipe], default=0) + 1
        return orders[name]

    for name, item in ans.items():
        item.order = get_order(name)

    return ans


def parse_from_json(path: str) -> Dict[str, DotaItem]:
    with open(path, "r") as f:
        data: Dict[str, Dict[str, Any]] = json.load(f)
        assert type(data) == dict
        return {
            item["name"]: DotaItem(
                **{k: v for k, v in item.items() if k != "buffs" and k != "abilities"},
                buffs=Buffs(**item["buffs"]) if "buffs" in item else Buffs(),
                abilities=(
                    [
                        Ability(
                            **{k: v for k, v in ability.items() if k != "stats"},
                            stats=(
                                AbilityStats(**ability["stats"])
                                if "stats" in ability
                                else AbilityStats()
                            ),
                        )
                        for ability in item["abilities"]
                    ]
                    if "abilities" in item
                    else None
                ),
            )
            for item in data.values()
        }


def dataclass_to_clean_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        obj = asdict(obj)  # type: ignore
    if isinstance(obj, dict):
        return {k: dataclass_to_clean_dict(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [dataclass_to_clean_dict(v) for v in obj if v is not None]
    else:
        return obj


def save_to_json(path: str, data: Dict[str, DotaItem]) -> None:
    with open(path, "w") as f:
        json.dump(
            {k: dataclass_to_clean_dict(v) for k, v in data.items()},
            f,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )


BUFF_PATTERN = r"([+-]?\d+(\.\d+)?)%? (\D+)"
FUZZY_THRESHOLD = 0.6


def parse_buffs(lines: List[str]) -> Buffs:
    ans = Buffs()
    logger.debug("parsing buffs from %s", lines)

    for line in lines:
        line = line.strip()
        line = re.sub(r"(\d)\s+(\d)", r"\1\2", line)
        line = re.sub(r"(\d+),(\d+)", r"\1.\2", line)
        line = re.sub(r"\s+", " ", line)
        line = re.sub(r"\s+%", "%", line)

        if not line:
            logger.warning(f"skipping unparsable buff: {line}")
            continue

        match = re.search(BUFF_PATTERN, line)
        if not match:
            logger.warning(f"no match for buff: {line}")
            continue

        value_str, label = match.groups()[0], match.groups()[2]
        try:
            value = float(value_str)
        except ValueError:
            logger.warning(f"invalid float value {value_str} in {line}")
            continue

        label = label.strip().lower()

        if label in BUFF_KEYWORDS:
            field = BUFF_KEYWORDS[label]
        else:
            close = get_close_matches(
                label, BUFF_KEYWORDS.keys(), n=1, cutoff=FUZZY_THRESHOLD
            )
            if close:
                field = BUFF_KEYWORDS[close[0]]
            else:
                logger.warning(f"unknown buff: '{label}'")
                continue

        setattr(ans, field, value)

    return ans


def parse_ability_type(value: str) -> AbilityType | None:
    value = value.strip().lower()

    d = {
        "unit target": AbilityType.UNIT_TARGET,
        "target unit": AbilityType.UNIT_TARGET,
        "point target": AbilityType.POINT_TARGET,
        "target point": AbilityType.POINT_TARGET,
        "target area": AbilityType.POINT_TARGET,
        "area target": AbilityType.POINT_TARGET,
        "no target": AbilityType.NO_TARGET,
        "passive": AbilityType.PASSIVE,
        "toggle": AbilityType.TOGGLE,
        "aura": AbilityType.AURA,
    }
    for k, v in d.items():
        if k in value:
            return v

    return None


def set_distinct_recipes(items: Dict[str, DotaItem]) -> Dict[str, DotaItem]:
    ans: Dict[str, DotaItem] = {}
    for name, item in sorted(items.items(), key=lambda x: (x[1].order, x[0])):
        if "recipe" in name.lower():
            continue
        if item.recipe and any("recipe" in comp.lower() for comp in item.recipe):
            recipe_name = f"{name} Recipe"
            item.recipe = [recipe_name if r == "Recipe" else r for r in item.recipe]
            recipe_cost = item.cost - sum(
                [items[r].cost for r in item.recipe if r != recipe_name]
            )
            ans[recipe_name] = DotaItem(
                name=recipe_name,
                cost=recipe_cost,
                url=item.url,
                image="https://dota2.ru/img/items/recipe.jpg",
                recipe=[],
                buffs=Buffs(),
            )
        ans[name] = item
    return ans


def remove_distinct_recipes(items: Dict[str, DotaItem]) -> Dict[str, DotaItem]:
    ans: Dict[str, DotaItem] = {}
    for name, item in items.items():
        if "recipe" in name.lower():
            continue
        if item.recipe:
            item.recipe = ["Recipe" if r.endswith("Recipe") else r for r in item.recipe]
        ans[name] = item
    return ans


def get_recipes_count(items: Dict[str, DotaItem]) -> int:
    count = 0
    for name in items.keys():
        if "recipe" in name.lower():
            count += 1
    return count
