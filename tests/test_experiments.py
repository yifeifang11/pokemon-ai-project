"""Tests for fixed-team lookup and experiment CSV output."""

import csv
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from experiments.run_battles import CSV_FIELDS, completed_battle_rows, write_results
from teams import MATCHUPS, TEAMS


class ExperimentScaffoldTests(unittest.TestCase):
    def test_teams_and_matchups_are_available(self) -> None:
        self.assertIn("charizard", TEAMS)
        self.assertIn("blastoise", TEAMS)
        self.assertEqual(MATCHUPS[0], ("charizard", "blastoise"))
        self.assertIn("- Flamethrower", TEAMS["charizard"])

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


if __name__ == "__main__":
    unittest.main()
