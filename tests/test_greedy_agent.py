import unittest
from types import SimpleNamespace

from agents.greedy_agent import GreedyPlayer, expected_damage


class Type:
    def __init__(self, name, matchups=None):
        self.name = name
        self.matchups = matchups or {}

    def damage_multiplier(self, *defender_types, **kwargs):
        result = 1.0
        for defender_type in defender_types:
            result *= self.matchups.get(defender_type.name, 1.0)
        return result


def pokemon(atk=100, defense=100, spa=100, spd=100, boosts=None, types=()):
    return SimpleNamespace(
        stats={"atk": atk, "def": defense, "spa": spa, "spd": spd},
        boosts=boosts or {},
        types=types,
    )


def move(power, category="physical", accuracy=100, move_type=None):
    return SimpleNamespace(
        base_power=power,
        category=SimpleNamespace(name=category),
        accuracy=accuracy,
        type=move_type or Type("neutral"),
    )


class GreedyScoringTests(unittest.TestCase):
    def setUp(self):
        self.attacker = pokemon(types=(Type("fire"),))
        self.defender = pokemon(types=(Type("grass"),))

    def test_super_effective_beats_resisted(self):
        fire = Type("fire", {"grass": 2.0})
        water = Type("water", {"grass": 0.5})
        self.assertGreater(expected_damage(move(40, move_type=fire), self.attacker, self.defender),
                           expected_damage(move(40, move_type=water), self.attacker, self.defender))

    def test_accuracy_tradeoff(self):
        self.assertGreater(expected_damage(move(100, accuracy=100), self.attacker, self.defender),
                           expected_damage(move(120, accuracy=70), self.attacker, self.defender))

    def test_stab(self):
        stab_move = move(50, move_type=self.attacker.types[0])
        neutral_move = move(50, move_type=Type("water"))
        self.assertGreater(expected_damage(stab_move, self.attacker, self.defender),
                           expected_damage(neutral_move, self.attacker, self.defender))

    def test_physical_and_special_stats_and_boosts(self):
        attacker = pokemon(atk=200, spa=60, boosts={"atk": 1})
        defender = pokemon(defense=120, spd=60)
        physical = expected_damage(move(60), attacker, defender)
        special = expected_damage(move(60, "special"), attacker, defender)
        self.assertGreater(physical, special)

    def test_selects_highest_scoring_move(self):
        player = object.__new__(GreedyPlayer)
        player.create_order = lambda selected, **kwargs: selected
        battle = SimpleNamespace(
            available_moves=[move(30), move(80)],
            active_pokemon=self.attacker,
            opponent_active_pokemon=self.defender,
        )
        self.assertEqual(player.choose_move(battle).base_power, 80)

    def test_unknown_opponent_stat_uses_safe_fallback(self):
        defender = pokemon(spd=None)
        score = expected_damage(move(80, "special"), self.attacker, defender)
        self.assertGreater(score, 0)


if __name__ == "__main__":
    unittest.main()
