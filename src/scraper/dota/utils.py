import json
import logging
import re
from dataclasses import asdict, is_dataclass
from difflib import get_close_matches
from typing import Any, Dict, List, Tuple

from scraper.dota.types import Buffs, DotaItem

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
                **{k: v for k, v in item.items() if k != "buffs"},
                buffs=Buffs(**item["buffs"]) if "buffs" in item else Buffs(),
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


BUFF_KEYWORDS = {
    "к силе": "strength",
    "к ловкости": "agility",
    "к интеллекту": "intelligence",
    "ко всем атрибутам": "all_attributes",
    "к здоровью": "health",
    "к мане": "mana",
    "к максимальному запасу маны": "mana",
    "к восстановлению здоровья": "health_regen",
    "к пополнению здоровья": "health_replenish_amp",
    "к восстановлению маны": "mana_regen",
    "к скорости передвижения": "move_speed",
    "к скорости передвижения героям ближнего боя": "move_speed_melee",
    "к скорости передвижения героям дальнего боя": "move_speed_ranged",
    "к скорости атаки": "attack_speed",
    "к скорости применения заклинаний": "cast_speed",
    "к скорости снарядов": "projectile_speed",
    "к скорости снарядов атак": "projectile_speed",
    "к дальности атаки": "attack_range_ranged",
    "к дальности применения заклинаний": "cast_range",
    "к радиусу заклинаний": "spell_radius",
    "к вампиризму": "lifesteal",
    "к вампиризму от заклинаний против героев": "spell_lifesteal_heroes",
    "к вампиризму от заклинаний против крипов": "spell_lifesteal_creeps",
    "к усилению вампиризма": "spell_lifesteal_amp",
    "к урону": "damage",
    "к урону (ближний бой)": "damage_melee",
    "к урону (дальний бой)": "damage_ranged",
    "к урону от заклинаний": "spell_damage",
    "к усилению урона от заклинаний": "spell_damage_amp",
    "к усилению урона способностей": "ability_damage_amp",
    "к броне": "armor",
    "к сопротивлению магии": "magic_resist",
    "к сопротивлению замедлению": "slow_resist",
    "к сопротивлению замедлениям": "slow_resist",
    "к сопротивлению эффектам": "status_resist",
    "к уклонению": "evasion",
    "к уменьшению затрат и потерь маны": "mana_efficiency",
    "к усилению восстановления маны": "mana_regen_amp",
    "макс. здоровья в секунду": "max_health_per_sec",
}

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
