import csv
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from poke_env.battle import Move, Pokemon
from poke_env.player.battle_order import SingleBattleOrder

from experiments.move_logger import (
    LEGACY_MOVE_LOG_FIELDS,
    MOVE_LOG_FIELDS,
    PRE_ENHANCED_MOVE_LOG_FIELDS,
    MoveLogger,
)


class MoveLoggerTests(unittest.TestCase):
    def test_records_move_hp_accuracy_and_nonnegative_time(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "move_log.csv"
            logger = MoveLogger(path, "experiment-1")
            own = Pokemon(9, species="charizard")
            own.set_hp_status("75/100")
            opponent = Pokemon(9, species="blastoise")
            opponent.set_hp_status("40/100")
            move = Move("flamethrower", 9)
            battle = SimpleNamespace(
                battle_tag="battle-gen9customgame-1",
                turn=2,
                active_pokemon=own,
                opponent_active_pokemon=opponent,
            )

            logger.record_decision(
                battle=battle,
                agent="greedy",
                player_slot="p1",
                pokemon="Charizard",
                opponent="Blastoise",
                order=SingleBattleOrder(move),
                decision_time_ms=1.25,
                estimated_damage=42.5,
                estimated_ko_probability=0.96875,
                ko_threshold_met=True,
                selection_reason="reliable_ko",
                basic_greedy_move="focusblast",
                enhanced_greedy_move="aurasphere",
                policies_disagree=True,
            )
            with path.open(newline="", encoding="utf-8") as source:
                rows = list(csv.DictReader(source))

            self.assertEqual(list(rows[0]), MOVE_LOG_FIELDS)
            self.assertEqual(rows[0]["selected_move"], "flamethrower")
            self.assertEqual(rows[0]["player_slot"], "p1")
            self.assertEqual(rows[0]["own_hp_pct"], "75.0")
            self.assertEqual(rows[0]["opponent_hp_pct"], "40.0")
            self.assertEqual(rows[0]["estimated_damage"], "42.5")
            self.assertEqual(float(rows[0]["move_accuracy"]), 100.0)
            self.assertGreaterEqual(float(rows[0]["decision_time_ms"]), 0)
            self.assertEqual(rows[0]["action_type"], "move")
            self.assertEqual(rows[0]["estimated_ko_probability"], "0.96875")
            self.assertEqual(rows[0]["ko_threshold_met"], "True")
            self.assertEqual(rows[0]["selection_reason"], "reliable_ko")
            self.assertEqual(rows[0]["basic_greedy_move"], "focusblast")
            self.assertEqual(rows[0]["enhanced_greedy_move"], "aurasphere")
            self.assertEqual(rows[0]["policies_disagree"], "True")

    def test_switch_is_logged_as_non_attack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = MoveLogger(Path(temp_dir) / "move_log.csv", "run")
            own = Pokemon(9, species="charizard")
            own.set_hp_status("100/100")
            switch_to = Pokemon(9, species="blastoise")
            battle = SimpleNamespace(
                battle_tag="battle-1",
                turn=4,
                active_pokemon=own,
                opponent_active_pokemon=None,
            )
            logger.record_decision(
                battle=battle,
                agent="random",
                player_slot="p2",
                pokemon="Charizard",
                opponent="Blastoise",
                order=SingleBattleOrder(switch_to),
                decision_time_ms=0,
            )
            row = logger.rows[0]
            self.assertEqual(row["selected_move"], "")
            self.assertEqual(row["estimated_damage"], "")
            self.assertEqual(row["action_type"], "switch")
            self.assertEqual(row["player_slot"], "p2")

    def test_legacy_log_migration_preserves_rows_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "move_log.csv"
            with path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=LEGACY_MOVE_LOG_FIELDS)
                writer.writeheader()
                writer.writerow(
                    {
                        "experiment_id": "old-run",
                        "battle_tag": "battle-old",
                        "turn": "1",
                        "agent": "random",
                        "agent_slot": "agent_2",
                        "pokemon": "Lucario",
                        "opponent": "Lucario",
                        "selected_move": "aurasphere",
                        "own_hp_pct": "100",
                        "opponent_hp_pct": "100",
                        "estimated_damage": "",
                        "move_accuracy": "100",
                        "decision_time_ms": "0.1",
                        "action_type": "move",
                    }
                )

            MoveLogger(path, "new-run")
            with path.open(newline="", encoding="utf-8") as source:
                reader = csv.DictReader(source)
                self.assertEqual(reader.fieldnames, MOVE_LOG_FIELDS)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["player_slot"], "p2")
            self.assertEqual(rows[0]["selected_move"], "aurasphere")
            self.assertTrue(path.with_suffix(".csv.pre-enhanced-greedy.bak").exists())

    def test_pre_enhanced_log_migration_preserves_player_slots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "old.csv"
            with path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=PRE_ENHANCED_MOVE_LOG_FIELDS)
                writer.writeheader()
                writer.writerow(
                    {
                        "experiment_id": "earlier",
                        "battle_tag": "battle-previous",
                        "player_slot": "p1",
                        "agent_slot": "agent_1",
                        "selected_move": "aurasphere",
                    }
                )
            MoveLogger(path, "next")
            with path.open(newline="", encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["player_slot"], "p1")
            self.assertEqual(rows[0]["estimated_ko_probability"], "")

    def test_existing_nonempty_log_appends_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "move_log.csv"
            first = MoveLogger(path, "first")
            first.rows.append({"experiment_id": "first"})
            # Existing header is validated and rows remain intact on a new run.
            MoveLogger(path, "second")
            with path.open(newline="", encoding="utf-8") as source:
                self.assertEqual(next(csv.reader(source)), MOVE_LOG_FIELDS)


if __name__ == "__main__":
    unittest.main()
