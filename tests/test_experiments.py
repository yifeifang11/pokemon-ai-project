"""Tests for fixed-team lookup and experiment CSV output."""

import csv
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from poke_env.teambuilder import Teambuilder
from poke_env.data import GenData
from poke_env.stats import compute_raw_stats

from experiments.run_battles import CSV_FIELDS, completed_battle_rows, write_results
from teams import MATCHUPS, TEAMS


class ExperimentScaffoldTests(unittest.TestCase):
    def test_teams_and_matchups_are_available(self) -> None:
        self.assertIn("charizard", TEAMS)
        self.assertIn("blastoise", TEAMS)
        self.assertEqual(MATCHUPS[0], ("charizard", "blastoise"))
        self.assertIn("- Flamethrower", TEAMS["charizard"])
        self.assertIn(("lucario", "lucario"), MATCHUPS)

    def test_lucario_mirror_teams_are_identical_and_valid(self) -> None:
        p1 = Teambuilder.parse_showdown_team(TEAMS["lucario"])[0]
        p2 = Teambuilder.parse_showdown_team(TEAMS["lucario"])[0]
        self.assertEqual(p1.ability, "Inner Focus")
        self.assertEqual(p1.moves, ["Aura Sphere", "Focus Blast", "Flash Cannon", "Dark Pulse"])
        self.assertEqual(p1.level, 50)
        self.assertEqual(p1.nature, "Serious")
        self.assertIsNone(p1.item)
        self.assertIsNone(p1.tera_type)
        self.assertEqual(p1.evs, [0, 0, 0, 0, 0, 0])
        self.assertEqual(p1.ivs, [31, 31, 31, 31, 31, 31])
        self.assertEqual(p1.__dict__, p2.__dict__)
        data = GenData.from_gen(9)
        stats_1 = compute_raw_stats(
            "lucario", p1.evs, p1.ivs, p1.level, p1.nature.lower(), data
        )
        stats_2 = compute_raw_stats(
            "lucario", p2.evs, p2.ivs, p2.level, p2.nature.lower(), data
        )
        self.assertEqual(stats_1, stats_2)
        self.assertEqual(stats_1[-1], stats_2[-1])

    def test_csv_is_written_once_with_expected_fields(self) -> None:
        row = {field: "" for field in CSV_FIELDS}
        row.update(
            experiment_id="run-1",
            battle_tag="battle-gen9customgame-1",
            agent_1="random",
            pokemon_1="Charizard",
            agent_2="random",
            pokemon_2="Blastoise",
            winner="agent_1",
            turns=12,
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "results.csv"
            write_results(output_path, [row])

            with output_path.open(newline="", encoding="utf-8") as output_file:
                reader = csv.DictReader(output_file)
                self.assertEqual(reader.fieldnames, CSV_FIELDS)
                written_rows = list(reader)
            self.assertEqual(written_rows, [{field: str(row[field]) for field in CSV_FIELDS}])

            with self.assertRaises(FileExistsError):
                write_results(output_path, [row])

    def test_battle_rows_use_each_battle_outcome(self) -> None:
        battle_objects = [
            SimpleNamespace(finished=True, won=True, battle_tag="battle-1", turn=8),
            SimpleNamespace(finished=True, won=False, battle_tag="battle-2", turn=11),
            SimpleNamespace(finished=True, won=None, battle_tag="battle-3", turn=14),
            SimpleNamespace(finished=False, won=None, battle_tag="battle-4", turn=0),
        ]
        player = SimpleNamespace(
            battles={battle.battle_tag: battle for battle in battle_objects}
        )

        rows = completed_battle_rows(
            player,
            experiment_id="run-1",
            agent_1="random",
            pokemon_1="Charizard",
            agent_2="random",
            pokemon_2="Blastoise",
        )

        self.assertEqual([row["winner"] for row in rows], ["agent_1", "agent_2", "tie"])
        self.assertEqual([row["turns"] for row in rows], [8, 11, 14])

    def test_battle_summary_metrics_use_each_side(self) -> None:
        def mon(percent):
            return SimpleNamespace(
                max_hp=100,
                current_hp_fraction=percent / 100,
            )

        battle_1 = SimpleNamespace(
            finished=True,
            won=True,
            battle_tag="battle-1",
            turn=3,
            team={"charizard": mon(40)},
        )
        battle_2 = SimpleNamespace(
            battle_tag="battle-1",
            team={"blastoise": mon(100)},
        )

        class Logger:
            def average_decision_ms(self, tag, agent, player_slot):
                return {"p1": 1.5, "p2": 2.5}[player_slot]

        rows = completed_battle_rows(
            SimpleNamespace(battles={"battle-1": battle_1}),
            experiment_id="run",
            agent_1="random",
            pokemon_1="Charizard",
            agent_2="random",
            pokemon_2="Blastoise",
            opposing_player=SimpleNamespace(battles={"battle-1": battle_2}),
            move_logger=Logger(),
        )
        self.assertEqual(rows[0]["agent_1_avg_decision_ms"], 1.5)
        self.assertEqual(rows[0]["agent_2_avg_decision_ms"], 2.5)
        self.assertEqual(rows[0]["agent_1_remaining_hp_pct"], 40.0)
        self.assertEqual(rows[0]["agent_2_remaining_hp_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
