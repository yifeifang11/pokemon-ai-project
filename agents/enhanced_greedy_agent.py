"""KO-aware Greedy policy using the Basic Greedy damage estimate."""

from dataclasses import dataclass

from poke_env.player import Player

from agents.greedy_agent import GreedyPlayer, expected_damage


KO_THRESHOLD = 0.95
DAMAGE_ROLLS = tuple(0.85 + index * 0.01 for index in range(16))


def _accuracy_probability(move) -> float:
    accuracy = move.accuracy
    if accuracy is None:
        return 0.0
    return accuracy / 100 if accuracy > 1 else accuracy


def ko_probability(move, attacker, defender, opponent_hp: float | None = None) -> float:
    """Estimate one-turn KO probability with accuracy and 16 damage rolls.

    Basic Greedy's expected damage includes accuracy but not a damage roll.
    Dividing by hit probability estimates the conditional hit damage; the
    standard 0.85..1.00 roll multipliers are applied to that value.
    """
    if opponent_hp is None:
        opponent_hp = getattr(defender, "current_hp", None)
    if opponent_hp is None or opponent_hp <= 0:
        return 0.0

    accuracy = _accuracy_probability(move)
    if accuracy <= 0:
        return 0.0
    expected = expected_damage(move, attacker, defender)
    if expected <= 0:
        # Includes type immunities and unsupported/status moves.
        return 0.0

    damage_on_hit = expected / accuracy
    successful_rolls = sum(
        damage_on_hit * multiplier >= opponent_hp for multiplier in DAMAGE_ROLLS
    )
    return accuracy * successful_rolls / len(DAMAGE_ROLLS)


@dataclass(frozen=True)
class EnhancedDecision:
    move: object
    basic_move: object
    expected_damage: float
    ko_probability: float
    ko_threshold_met: bool
    selection_reason: str


def evaluate_enhanced_move(moves, attacker, defender) -> EnhancedDecision:
    """Compare both policies over the same legal move list and battle state."""
    scored = [
        (
            move,
            expected_damage(move, attacker, defender),
            ko_probability(move, attacker, defender),
        )
        for move in moves
    ]
    if not scored:
        raise ValueError("At least one legal move is required")

    # max() keeps the first move for complete ties, matching Basic Greedy.
    basic_move, _, _ = max(scored, key=lambda result: result[1])
    reliable_kos = [result for result in scored if result[2] >= KO_THRESHOLD]
    if reliable_kos:
        selected, damage, probability = max(
            reliable_kos, key=lambda result: (result[2], result[1])
        )
        reason = "reliable_ko"
    else:
        selected, damage, probability = max(scored, key=lambda result: result[1])
        reason = "max_expected_damage"

    return EnhancedDecision(
        move=selected,
        basic_move=basic_move,
        expected_damage=damage,
        ko_probability=probability,
        ko_threshold_met=probability >= KO_THRESHOLD,
        selection_reason=reason,
    )


class EnhancedGreedyPlayer(GreedyPlayer):
    """Greedy agent that prefers moves with at least 95% KO probability."""

    def choose_move(self, battle):
        self._last_estimated_damage = ""
        self._last_estimated_ko_probability = ""
        self._last_ko_threshold_met = ""
        self._last_selection_reason = "fallback"
        self._last_basic_greedy_move = ""
        self._last_enhanced_greedy_move = ""
        self._last_policies_disagree = ""

        moves = battle.available_moves
        if not moves:
            return self.choose_random_move(battle)

        attacker = battle.active_pokemon
        defender = battle.opponent_active_pokemon
        if attacker is None or defender is None:
            move = moves[0]
            self._last_basic_greedy_move = move.id
            self._last_enhanced_greedy_move = move.id
            self._last_policies_disagree = False
            return self.create_order(move, terastallize=False)

        decision = evaluate_enhanced_move(moves, attacker, defender)
        self._last_estimated_damage = decision.expected_damage
        self._last_estimated_ko_probability = decision.ko_probability
        self._last_ko_threshold_met = decision.ko_threshold_met
        self._last_selection_reason = decision.selection_reason
        self._last_basic_greedy_move = decision.basic_move.id
        self._last_enhanced_greedy_move = decision.move.id
        self._last_policies_disagree = decision.basic_move.id != decision.move.id
        return self.create_order(decision.move, terastallize=False)
