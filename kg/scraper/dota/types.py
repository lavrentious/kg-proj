from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from kg.scraper.dota.consts import STATS_MAPPING
from kg.utils import normalize_name, parse_value


@dataclass
class Buffs:
    # Основные атрибуты
    strength: Optional[float] = None  # к силе
    agility: Optional[float] = None  # к ловкости
    intelligence: Optional[float] = None  # к интеллекту
    all_attributes: Optional[float] = None  # ко всем атрибутам

    # Здоровье и мана
    health: Optional[float] = None  # к здоровью
    mana: Optional[float] = None  # к мане / максимальному запасу маны
    health_regen: Optional[float] = None  # к восстановлению здоровья
    health_replenish_amp: Optional[float] = (
        None  # к пополнению здоровья (Abyssal Blade)
    )
    mana_regen: Optional[float] = None  # к восстановлению маны

    # Скорости
    move_speed: Optional[float] = None  # к скорости передвижения
    move_speed_melee: Optional[float] = (
        None  # к скорости передвижения героям ближнего боя
    )
    move_speed_ranged: Optional[float] = (
        None  # к скорости передвижения героям дальнего боя
    )
    attack_speed: Optional[float] = None  # к скорости атаки
    cast_speed: Optional[float] = None  # к скорости применения заклинаний
    projectile_speed: Optional[float] = None  # к скорости снарядов (атак)

    # Радиусы / дальности
    attack_range_ranged: Optional[float] = (
        None  # к дальности атаки (для героев дальнего боя)
    )
    cast_range: Optional[float] = None  # к дальности применения заклинаний
    spell_radius: Optional[float] = None  # к радиусу заклинаний

    # Вампиризм
    lifesteal: Optional[float] = None  # к вампиризму
    spell_lifesteal_heroes: Optional[float] = (
        None  # к вампиризму от заклинаний против героев
    )
    spell_lifesteal_creeps: Optional[float] = (
        None  # к вампиризму от заклинаний против крипов
    )
    spell_lifesteal_amp: Optional[float] = None  # к усилению вампиризма

    # Урон
    damage: Optional[float] = None  # к урону (от атаки)
    damage_melee: Optional[float] = None  # к урону (ближний бой)
    damage_ranged: Optional[float] = None  # к урону (дальний бой)
    spell_damage: Optional[float] = None  # к урону от заклинаний
    spell_damage_amp: Optional[float] = None  # к усилению урона от заклинаний
    ability_damage_amp: Optional[float] = None  # к усилению урона способностей

    # Сопротивления и защита
    armor: Optional[float] = None  # к броне
    magic_resist: Optional[float] = None  # к сопротивлению магии
    slow_resist: Optional[float] = None  # к сопротивлению замедлению / замедлениям
    status_resist: Optional[float] = None  # к сопротивлению эффектам
    evasion: Optional[float] = None  # к уклонению

    # Прочее
    mana_efficiency: Optional[float] = (
        None  # к уменьшению затрат и потерь маны (Kaya & Sange)
    )
    mana_regen_amp: Optional[float] = None  # к усилению восстановления маны (Kaya)
    max_health_per_sec: Optional[float] = (
        None  # макс. здоровья в секунду (Heart of Tarrasque)
    )

    def __str__(self) -> str:
        return (
            "Buffs("
            + ", ".join(f"{k}={v}" for k, v in self.__dict__.items() if v is not None)
            + ")"
        )

    def asdict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class AbilityType(str, Enum):
    # active subtypes
    UNIT_TARGET = "UNIT TARGET"
    POINT_TARGET = "POINT TARGET"
    NO_TARGET = "NO TARGET"
    # rest
    PASSIVE = "PASSIVE"
    TOGGLE = "TOGGLE"
    AURA = "AURA"


@dataclass
class AbilityStats:
    additional_stats: Optional[Dict[str, Any]] = None

    # specific properties
    # --- Damage amplification / magic ---
    spell_damage_amp: Optional[float] = None
    bonus_magical_damage: Optional[float] = None
    spell_damage_bonus: Optional[float] = None
    magic_resistance_reduction: Optional[float] = None
    dmg_dealt_as_bonus_dmg: Optional[float] = None
    int_as_dps: Optional[float] = None
    damage_per_second: Optional[float] = None

    # --- Physical damage / armor ---
    armor_reduction: Optional[float] = None
    attack_damage_bonus: Optional[float] = None
    critical_damage: Optional[float] = None

    # --- Healing ---
    heal_amp: Optional[float] = None
    health_restored: Optional[float] = None
    health_regen_bonus: Optional[float] = None

    # --- Anti-heal ---
    heal_reduction: Optional[float] = None
    enemy_heal_reduction: Optional[float] = None

    def asdict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class AbilityEffect(Enum):
    STUN = "stun"
    ROOT = "root"
    SILENCE = "silence"
    HEAL = "heal"
    DAMAGE = "damage"
    SLOW = "slow"
    BASIC_DISPEL = "basic_dispel"
    STRONG_DISPEL = "strong_dispel"
    BUFF = "buff"
    DEBUFF = "debuff"
    MANA_RESTORE = "mana_restore"


class ItemRole(Enum):
    DEFENSE = "defense"
    OFFENSE = "offense"
    SAVE = "save"
    UTILITY = "utility"
    CONTROL = "control"
    MANA = "mana"
    MOBILITY = "mobility"


@dataclass
class Ability:
    name: str
    description: Optional[str]

    ability_type: AbilityType
    mana_cost: Optional[int] = None
    cooldown: Optional[float] = None
    cast_range: Optional[float] = None

    effects: List[AbilityEffect] | None = None
    stats: AbilityStats | None = None

    def __str__(self) -> str:
        return (
            "Abilities("
            + ", ".join(f"{k}={v}" for k, v in self.__dict__.items() if v is not None)
            + ")"
        )

    def apply_stats(self, stats: Dict[str, Any]) -> None:
        if self.stats is None:
            self.stats = AbilityStats()

        for key, value in stats.items():
            normalized_key = key.strip().lower()

            if normalized_key == "cast range":
                self.cast_range = parse_value(value)
                continue

            if normalized_key in STATS_MAPPING:
                field_name = STATS_MAPPING[normalized_key]
                setattr(self.stats, field_name, parse_value(value))
            else:
                if self.stats.additional_stats is None:
                    self.stats.additional_stats = {}
                self.stats.additional_stats[normalize_name(normalized_key)] = value

    def asdict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class GenericItem:
    name: str  # unique
    image: str  # image url
    url: str  # wiki url
    abilities: List[Ability] | None
    buffs: Buffs | None
    roles: List[ItemRole] | None


@dataclass
class DotaItem(GenericItem):
    cost: int
    recipe: List[str]
    order: int | None = None  # abstract variable to assess item coolness


@dataclass
class NeutralItem(GenericItem):
    tier: int  # 1-5
