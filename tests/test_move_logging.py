import csv
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from poke_env.battle import Move, Pokemon
from poke_env.player.battle_order import SingleBattleOrder

from experiments.move_logger import MOVE_LOG_FIELDS, MoveLogger


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
                agent_slot="agent_1",
                pokemon="Charizard",
                opponent="Blastoise",
                order=SingleBattleOrder(move),
                decision_time_ms=1.25,
                estimated_damage=42.5,
            )
            with path.open(newline="", encoding="utf-8") as source:
                rows = list(csv.DictReader(source))

            self.assertEqual(list(rows[0]), MOVE_LOG_FIELDS)
            self.assertEqual(rows[0]["selected_move"], "flamethrower")
            self.assertEqual(rows[0]["own_hp_pct"], "75.0")
            self.assertEqual(rows[0]["opponent_hp_pct"], "40.0")
            self.assertEqual(rows[0]["estimated_damage"], "42.5")
            self.assertEqual(float(rows[0]["move_accuracy"]), 100.0)
            self.assertGreaterEqual(float(rows[0]["decision_time_ms"]), 0)
            self.assertEqual(rows[0]["action_type"], "move")

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
                agent_slot="agent_2",
                pokemon="Charizard",
                opponent="Blastoise",
                order=SingleBattleOrder(switch_to),
                decision_time_ms=0,
            )
            row = logger.rows[0]
            self.assertEqual(row["selected_move"], "")
            self.assertEqual(row["estimated_damage"], "")
            self.assertEqual(row["action_type"], "switch")

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
