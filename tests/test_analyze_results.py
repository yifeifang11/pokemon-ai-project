import io
import unittest
from contextlib import redirect_stdout

from experiments.analyze_results import analyze


class AnalyzeMirrorTests(unittest.TestCase):
    def test_mirror_players_stay_separate_and_logs_join_by_both_ids(self):
        battle = {
            "experiment_id": "mirror-run",
            "battle_tag": "battle-1",
            "agent_1": "random",
            "pokemon_1": "Lucario",
            "agent_2": "random",
            "pokemon_2": "Lucario",
            "winner": "agent_2",
            "turns": "3",
            "agent_1_remaining_hp_pct": "0",
            "agent_2_remaining_hp_pct": "55",
        }
        logs = [
            {
                "experiment_id": "mirror-run",
                "battle_tag": "battle-1",
                "player_slot": "p1",
                "agent": "random",
                "pokemon": "Lucario",
                "selected_move": "aurasphere",
                "action_type": "move",
                "decision_time_ms": "1",
            },
            {
                "experiment_id": "mirror-run",
                "battle_tag": "battle-1",
                "player_slot": "p2",
                "agent": "random",
                "pokemon": "Lucario",
                "selected_move": "darkpulse",
                "action_type": "move",
                "decision_time_ms": "3",
            },
            {
                "experiment_id": "other-run",
                "battle_tag": "battle-1",
                "player_slot": "p1",
                "agent": "random",
                "pokemon": "Lucario",
                "selected_move": "focusblast",
                "action_type": "move",
                "decision_time_ms": "100",
            },
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            analyze([battle], logs)
        report = output.getvalue()
        self.assertIn("P1 random (Lucario) vs P2 random (Lucario)", report)
        self.assertIn("p1 random Lucario (n=1): aurasphere", report)
        self.assertIn("p2 random Lucario (n=1): darkpulse", report)
        self.assertNotIn("focusblast", report)
        self.assertIn("p1 random: 1.00", report)
        self.assertIn("p2 random: 3.00", report)

    def test_enhanced_policy_differences_and_head_to_head_are_reported(self):
        battle = {
            "experiment_id": "direct-run",
            "battle_tag": "battle-direct",
            "agent_1": "enhanced_greedy",
            "pokemon_1": "Lucario",
            "agent_2": "greedy",
            "pokemon_2": "Lucario",
            "winner": "agent_1",
            "turns": "2",
        }
        decision = {
            "experiment_id": "direct-run",
            "battle_tag": "battle-direct",
            "agent": "enhanced_greedy",
            "player_slot": "p1",
            "pokemon": "Lucario",
            "selected_move": "aurasphere",
            "action_type": "move",
            "decision_time_ms": "0.1",
            "estimated_ko_probability": "1.0",
            "ko_threshold_met": "True",
            "selection_reason": "reliable_ko",
            "basic_greedy_move": "focusblast",
            "enhanced_greedy_move": "aurasphere",
            "policies_disagree": "True",
        }
        output = io.StringIO()
        with redirect_stdout(output):
            analyze([battle], [decision])
        report = output.getvalue()
        self.assertIn("reliable-KO selections: 1/1 (100.0%)", report)
        self.assertIn("Basic/Enhanced disagreements: 1/1 (100.0%)", report)
        self.assertIn("focusblast → aurasphere: 1", report)
        self.assertIn("Aura Sphere instead of Focus Blast: 1/1", report)
        self.assertIn("Basic 0/1 (0.0%); Enhanced 1/1 (100.0%)", report)


if __name__ == "__main__":
    unittest.main()
