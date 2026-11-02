"""Minimal state representation for the restricted 1v1 battle model."""

from dataclasses import dataclass


@dataclass
class BattleState:
    """Hit points and move power points for both active Pokémon.

    PP values are listed in move order for each player. This intentionally
    leaves out damage, status, switching, and other battle mechanics for now.
    """

    my_hp: int
    opponent_hp: int
    my_pp: list[int]
    opponent_pp: list[int]
