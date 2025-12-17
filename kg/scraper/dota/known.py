from typing import Dict, List, Set

from kg.scraper.dota.types import Ability, AbilityEffect, Buffs, GenericItem, ItemRole

ABILITY_EFFECTS: Dict[AbilityEffect, List[str]] = {
    AbilityEffect.STUN: ["stun", "stuns"],
    AbilityEffect.ROOT: ["root", "roots", "rooted"],
    AbilityEffect.SILENCE: ["silence", "silences", "silenced"],
    AbilityEffect.HEAL: ["heal", "heals", "restore health"],
    AbilityEffect.DAMAGE: ["damage", "deals"],
    AbilityEffect.SLOW: ["slow", "slows", "movement speed"],
    AbilityEffect.BASIC_DISPEL: ["dispel"],
    AbilityEffect.STRONG_DISPEL: ["strong dispel"],
    AbilityEffect.BUFF: ["grants", "bonus", "increases"],
    AbilityEffect.DEBUFF: ["reduces", "decrease", "penalty"],
    AbilityEffect.MANA_RESTORE: ["restore mana", "mana"],
}


def derive_ability_effects(ability: Ability) -> Set[AbilityEffect]:
    effects: Set[AbilityEffect] = set()
    if ability.description is None:
        return effects
    description = ability.description.lower()

    for effect, keywords in ABILITY_EFFECTS.items():
        for kw in keywords:
            if kw in description:
                effects.add(effect)
                break

    return effects


def derive_item_roles(item: GenericItem) -> Set[ItemRole]:
    abilities = item.abilities or []
    roles: Set[ItemRole] = set()
    buffs = item.buffs or Buffs()

    ability_effects = set()
    for ab in abilities:
        ability_effects |= derive_ability_effects(ab)

    # Save / Defense
    if (
        AbilityEffect.STRONG_DISPEL in ability_effects
        or AbilityEffect.BASIC_DISPEL in ability_effects
    ):
        roles.add(ItemRole.SAVE)

    if any(
        k in buffs.asdict().keys()
        for k in ["health", "armor", "magic_resistance", "status_resistance"]
    ):
        roles.add(ItemRole.DEFENSE)

    # Control
    if any(
        e in ability_effects
        for e in [
            AbilityEffect.STUN,
            AbilityEffect.ROOT,
            AbilityEffect.SILENCE,
            AbilityEffect.SLOW,
        ]
    ):
        roles.add(ItemRole.CONTROL)

    # Offense
    if "damage" in buffs.asdict().keys() or AbilityEffect.DAMAGE in ability_effects:
        roles.add(ItemRole.OFFENSE)

    # Mana / Utility
    if (
        "mana" in buffs.asdict().keys()
        or "mana_regen" in buffs.asdict().keys()
        or AbilityEffect.MANA_RESTORE in ability_effects
    ):
        roles.add(ItemRole.MANA)
        roles.add(ItemRole.UTILITY)

    # Mobility (редко, но полезно)
    if any(
        word
        in " ".join(
            ab.description.lower() for ab in abilities if ab.description is not None
        )
        for word in ["blink", "teleport", "movement speed"]
    ):
        roles.add(ItemRole.MOBILITY)

    # Fallback
    if not roles:
        roles.add(ItemRole.UTILITY)

    return roles
