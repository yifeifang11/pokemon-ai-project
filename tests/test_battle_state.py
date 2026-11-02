"""Basic tests for the battle state dataclass."""

import unittest

from simulation.battle_state import BattleState


class BattleStateTests(unittest.TestCase):
    def test_stores_hp_and_pp(self) -> None:
        state = BattleState(
            my_hp=100,
            opponent_hp=90,
            my_pp=[10, 15],
            opponent_pp=[8, 12],
        )

        self.assertEqual(state.my_hp, 100)
        self.assertEqual(state.opponent_hp, 90)
        self.assertEqual(state.my_pp, [10, 15])
        self.assertEqual(state.opponent_pp, [8, 12])


if __name__ == "__main__":
    unittest.main()
