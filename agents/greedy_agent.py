"""Immediate-damage Greedy baseline for single battles."""

from poke_env.player import Player
from poke_env.data import GenData


def _boosted_stat(pokemon, stat: str) -> float:
    """Return a battle stat after the standard stage multiplier.

    Opponent stats can be unknown before Showdown reveals them; use neutral
    100 in that case so move selection remains available.
    """
    value = pokemon.stats[stat]
    if value is None:
        value = 100
    stage = pokemon.boosts.get(stat, 0)
    multiplier = (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)
    return value * multiplier


def expected_damage(move, attacker, defender, level: int = 50) -> float:
    """Approximate expected damage using the level-based damage formula.

    This estimates one hit before random damage variation, then weights by
    accuracy, STAB, type effectiveness, and applicable attack/defense stages.
    It omits field, item, ability, critical-hit, and weather effects.
    """
    if move is None or move.base_power <= 0 or move.accuracy is None:
        return 0.0
    if move.category.name.lower() == "physical":
        attack = _boosted_stat(attacker, "atk")
        defense = _boosted_stat(defender, "def")
    elif move.category.name.lower() == "special":
        attack = _boosted_stat(attacker, "spa")
        defense = _boosted_stat(defender, "spd")
    else:
        return 0.0
    if not defense:
        return 0.0
    base = (((2 * level / 5 + 2) * move.base_power * attack / defense) / 50) + 2
    stab = 1.5 if move.type in attacker.types else 1.0
    defender_types = defender.types
    effectiveness = (
        move.type.damage_multiplier(
            *defender_types,
            type_chart=GenData.from_gen(9).type_chart,
        )
        if defender_types
        else 1.0
    )
    accuracy = move.accuracy / 100 if move.accuracy > 1 else move.accuracy
    return base * stab * effectiveness * accuracy


class GreedyPlayer(Player):
    """Select the legal move with the highest immediate expected damage."""

    def choose_move(self, battle):
        moves = battle.available_moves
        if not moves:
            # Covers forced switches and incomplete requests without inventing
            # an illegal move; poke-env's default order handles the request.
            return self.choose_random_move(battle)

        attacker = battle.active_pokemon
        defender = battle.opponent_active_pokemon
        if attacker is None or defender is None:
            return self.create_order(moves[0], terastallize=False)

        # max() is stable, so equal scores resolve by server-provided move order.
        scored_moves = [
            (candidate, expected_damage(candidate, attacker, defender))
            for candidate in moves
        ]
        move, self._last_estimated_damage = max(
            scored_moves, key=lambda scored: scored[1]
        )
        return self.create_order(move, terastallize=False)
