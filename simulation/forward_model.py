"""Simplified forward model used for planning, separate from Showdown."""

from .battle_state import BattleState


def simulate_turn(
    state: BattleState, my_move: int, opponent_move: int
) -> BattleState:
    """Return the state after both players choose a move for one turn.

    The move arguments are indices into the respective player's PP lists.
    This is a scaffold only: it does not yet apply damage or consume PP.

    Interface expected by MCTS: ``simulate_turn(state, my_move,
    opponent_move) -> new_state``. The function will model only the project's
    restricted rules and will not call the live Pokémon Showdown engine.
    """

    # TODO: Define simplified turn order, PP use, and damage behavior.
    raise NotImplementedError("The forward model has not been implemented yet.")
