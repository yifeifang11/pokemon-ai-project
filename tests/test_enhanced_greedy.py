import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agents.enhanced_greedy_agent import (
    KO_THRESHOLD,
    EnhancedGreedyPlayer,
    evaluate_enhanced_move,
    ko_probability,
)
from agents.greedy_agent import GreedyPlayer


class FakeType:
    def __init__(self, name, effectiveness=1.0):
        self.name = name
        self.effectiveness = effectiveness

    def damage_multiplier(self, *types, **kwargs):
        return self.effectiveness


def fake_pokemon(hp=80, stats=None):
    return SimpleNamespace(
        current_hp=hp,
        stats=stats or {"atk": 100, "def": 100, "spa": 100, "spd": 100},
        boosts={"atk": 0, "def": 0, "spa": 0, "spd": 0},
        types=(FakeType("normal"),),
    )


def fake_move(move_id, accuracy=1.0, power=100, effectiveness=1.0):
    return SimpleNamespace(
        id=move_id,
        accuracy=accuracy,
        base_power=power,
        category=SimpleNamespace(name="special"),
        type=FakeType("normal", effectiveness),
    )


class EnhancedGreedyTests(unittest.TestCase):
    def test_reliable_ko_beats_riskier_higher_expected_damage(self):
        aura = fake_move("aurasphere", 1.0)
        focus = fake_move("focusblast", 0.7)
        scores = {"aurasphere": 100.0, "focusblast": 120.0}
        with patch(
            "agents.enhanced_greedy_agent.expected_damage",
            side_effect=lambda move, *_: scores[move.id],
        ):
            decision = evaluate_enhanced_move([focus, aura], fake_pokemon(80), fake_pokemon(80))
        self.assertEqual(decision.basic_move.id, "focusblast")
        self.assertEqual(decision.move.id, "aurasphere")
        self.assertEqual(decision.ko_probability, 1.0)
        self.assertTrue(decision.ko_threshold_met)
        self.assertEqual(decision.selection_reason, "reliable_ko")

    def test_seventy_percent_accuracy_is_not_guaranteed_ko(self):
        focus = fake_move("focusblast", 0.7)
        with patch("agents.enhanced_greedy_agent.expected_damage", return_value=70.0):
            probability = ko_probability(focus, fake_pokemon(), fake_pokemon(80))
        self.assertAlmostEqual(probability, 0.7)
        self.assertLess(probability, 1.0)

    def test_without_reliable_ko_matches_basic_expected_damage_choice(self):
        accurate = fake_move("accurate", 1.0)
        risky = fake_move("risky", 0.7)
        scores = {"accurate": 60.0, "risky": 70.0}
        moves = [accurate, risky]
        with patch(
            "agents.enhanced_greedy_agent.expected_damage",
            side_effect=lambda move, *_: scores[move.id],
        ):
            decision = evaluate_enhanced_move(moves, fake_pokemon(), fake_pokemon(200))
        self.assertLess(decision.ko_probability, KO_THRESHOLD)
        self.assertEqual(decision.move.id, decision.basic_move.id)
        self.assertEqual(decision.move.id, "risky")
        self.assertEqual(decision.selection_reason, "max_expected_damage")

    def test_damage_roll_variation_changes_ko_probability(self):
        move = fake_move("roll-sensitive", 1.0)
        with patch("agents.enhanced_greedy_agent.expected_damage", return_value=70.0):
            probability = ko_probability(move, fake_pokemon(), fake_pokemon(69))
        self.assertAlmostEqual(probability, 2 / 16)

    def test_type_immunity_has_zero_ko_probability(self):
        move = fake_move("immune", effectiveness=0.0)
        self.assertEqual(ko_probability(move, fake_pokemon(), fake_pokemon(1)), 0.0)

    def test_equal_scores_use_move_order_deterministically(self):
        first = fake_move("first", 1.0)
        second = fake_move("second", 1.0)
        scores = {"first": 100.0, "second": 100.0}
        with patch(
            "agents.enhanced_greedy_agent.expected_damage",
            side_effect=lambda move, *_: scores[move.id],
        ):
            decisions = [
                evaluate_enhanced_move([first, second], fake_pokemon(), fake_pokemon(80))
                for _ in range(3)
            ]
        self.assertEqual([d.move.id for d in decisions], ["first"] * 3)

    def test_basic_greedy_still_uses_highest_expected_damage(self):
        aura = fake_move("aurasphere")
        focus = fake_move("focusblast")
        player = object.__new__(GreedyPlayer)
        player.create_order = lambda selected, **kwargs: selected
        scores = {"aurasphere": 100.0, "focusblast": 120.0}
        battle = SimpleNamespace(
            available_moves=[aura, focus],
            active_pokemon=fake_pokemon(),
            opponent_active_pokemon=fake_pokemon(80),
        )
        with patch(
            "agents.greedy_agent.expected_damage",
            side_effect=lambda move, *_: scores[move.id],
        ):
            self.assertEqual(player.choose_move(battle).id, "focusblast")

    def test_counterfactual_comparison_does_not_mutate_battle_state(self):
        aura = fake_move("aurasphere", 1.0)
        focus = fake_move("focusblast", 0.7)
        scores = {"aurasphere": 100.0, "focusblast": 120.0}
        attacker = fake_pokemon()
        defender = fake_pokemon(80)
        battle = SimpleNamespace(
            available_moves=[focus, aura],
            active_pokemon=attacker,
            opponent_active_pokemon=defender,
        )
        before = {
            "moves": list(battle.available_moves),
            "attacker_stats": copy.deepcopy(attacker.stats),
            "attacker_boosts": copy.deepcopy(attacker.boosts),
            "defender_stats": copy.deepcopy(defender.stats),
            "defender_boosts": copy.deepcopy(defender.boosts),
            "defender_hp": defender.current_hp,
        }
        player = object.__new__(EnhancedGreedyPlayer)
        player.create_order = lambda selected, **kwargs: selected
        with patch(
            "agents.enhanced_greedy_agent.expected_damage",
            side_effect=lambda move, *_: scores[move.id],
        ):
            player.choose_move(battle)
        self.assertEqual(battle.available_moves, before["moves"])
        self.assertEqual(attacker.stats, before["attacker_stats"])
        self.assertEqual(attacker.boosts, before["attacker_boosts"])
        self.assertEqual(defender.stats, before["defender_stats"])
        self.assertEqual(defender.boosts, before["defender_boosts"])
        self.assertEqual(defender.current_hp, before["defender_hp"])
        self.assertEqual(player._last_basic_greedy_move, "focusblast")
        self.assertEqual(player._last_enhanced_greedy_move, "aurasphere")
        self.assertTrue(player._last_policies_disagree)

    def test_policies_agree_when_no_reliable_ko_exists(self):
        aura = fake_move("aurasphere", 1.0)
        focus = fake_move("focusblast", 0.7)
        scores = {"aurasphere": 60.0, "focusblast": 70.0}
        battle = SimpleNamespace(
            available_moves=[aura, focus],
            active_pokemon=fake_pokemon(),
            opponent_active_pokemon=fake_pokemon(200),
        )
        player = object.__new__(EnhancedGreedyPlayer)
        player.create_order = lambda selected, **kwargs: selected
        with patch(
            "agents.enhanced_greedy_agent.expected_damage",
            side_effect=lambda move, *_: scores[move.id],
        ):
            selected = player.choose_move(battle)
        self.assertEqual(selected.id, "focusblast")
        self.assertEqual(player._last_basic_greedy_move, player._last_enhanced_greedy_move)
        self.assertFalse(player._last_policies_disagree)

    def test_policies_disagree_when_reliable_ko_changes_choice(self):
        aura = fake_move("aurasphere", 1.0)
        focus = fake_move("focusblast", 0.7)
        scores = {"aurasphere": 100.0, "focusblast": 120.0}
        battle = SimpleNamespace(
            available_moves=[focus, aura],
            active_pokemon=fake_pokemon(),
            opponent_active_pokemon=fake_pokemon(80),
        )
        player = object.__new__(EnhancedGreedyPlayer)
        player.create_order = lambda selected, **kwargs: selected
        with patch(
            "agents.enhanced_greedy_agent.expected_damage",
            side_effect=lambda move, *_: scores[move.id],
        ):
            selected = player.choose_move(battle)
        self.assertEqual(selected.id, "aurasphere")
        self.assertEqual(player._last_basic_greedy_move, "focusblast")
        self.assertTrue(player._last_policies_disagree)


if __name__ == "__main__":
    unittest.main()
