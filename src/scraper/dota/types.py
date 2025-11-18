from dataclasses import dataclass
from typing import List

"""
1. к cиле
2. к броне
3. к вампиризму
4. к вампиризму заклинаниями по героям
5. к вампиризму заклинаниями по крипам
6. к вампиризму от заклинаний против героев
7. к вампиризму от заклинаний против крипов
8. к восстановлению здоровью
9. к восстановлению здоровья
10. к восстановлению маны
11. к дальности атаки (для героев дальнего боя)
12. к дальности применения заклинаний
13. к здоровью
14. к интеллекту
15. к ловкости
16. к максимальному запасу маны
17. к мане
18. к пополнению здоровья
19. к радиусу заклинаний
20. 
21. к скорости атаки
22. к скорости передвижения
23. к скорости передвижения героям ближнего боя
24. к скорости передвижения героям дальнего боя
25. к скорости передвиженияко всем атрибутам
26. к скорости применения заклинаний
27. к скорости снарядов
28. к скорости снарядов атак
29. к сопротивлению замедлению
30. к сопротивлению замедлениям
31. к сопротивлению магии
32. к сопротивлению эффектам
33. к уклонению
34. к уменьшению затрат и потерь маны
35. к урону
36. к урону (ближний бой)
37. к урону (дальний бой)
38. к урону от атаки
39. к урону от заклинаний
40. к усилению вампиризма
41. к усилению восстановлению маны
42. к усилению восстановления маны
43. к усилению урона от заклинаний
44. к усилению урона способностей
45. ко всем атрибутам
46. макс. здоровья в секунду
"""
from dataclasses import dataclass
from typing import Optional


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


@dataclass
class DotaItem:
    name: str  # unique
    cost: int
    image: str
    url: str
    recipe: List[str]
    order: int | None = None  # abstract variable to assess item coolness
    buffs: Buffs | None = None
