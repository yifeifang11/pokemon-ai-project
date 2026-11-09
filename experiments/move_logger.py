"""Shared per-decision CSV logging for poke-env players."""

import csv
import inspect
from pathlib import Path
import threading
from time import perf_counter_ns

from poke_env.battle import Move, Pokemon
from poke_env.player.battle_order import SingleBattleOrder
from poke_env.player import RandomPlayer
from agents.greedy_agent import GreedyPlayer


MOVE_LOG_FIELDS = [
    "experiment_id",
    "battle_tag",
    "turn",
    "agent",
    "agent_slot",
    "pokemon",
    "opponent",
    "selected_move",
    "own_hp_pct",
    "opponent_hp_pct",
    "estimated_damage",
    "move_accuracy",
    "decision_time_ms",
    "action_type",
]


def _hp_percent(pokemon) -> float | str:
    if pokemon is None or not pokemon.max_hp:
        return ""
    fraction = pokemon.current_hp_fraction
    if not 0 <= fraction <= 1:
        return ""
    return round(fraction * 100, 2)


class MoveLogger:
    """Append decision rows without replacing previous experiment data."""

    _file_lock = threading.Lock()

    def __init__(self, output_path: Path, experiment_id: str):
        self.output_path = Path(output_path)
        self.experiment_id = experiment_id
        self.rows: list[dict[str, object]] = []
        self._lock = self._file_lock
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self.output_path.exists():
                with self.output_path.open(newline="", encoding="utf-8") as source:
                    header = next(csv.reader(source), [])
                if header != MOVE_LOG_FIELDS:
                    raise ValueError(f"Unexpected move-log header in {self.output_path}")
            else:
                with self.output_path.open("x", newline="", encoding="utf-8") as output:
                    csv.writer(output).writerow(MOVE_LOG_FIELDS)

    def record_decision(
        self,
        *,
        battle,
        agent: str,
        agent_slot: str,
        pokemon: str,
        opponent: str,
        order,
        decision_time_ms: float,
        estimated_damage: float | str = "",
    ) -> None:
        """Record one order at decision time; switches are not attack rows."""
        selected = order.order if isinstance(order, SingleBattleOrder) else None
        if isinstance(selected, Move):
            move_name = selected.id
            accuracy = selected.accuracy
            move_accuracy = (
                round(accuracy * 100 if accuracy <= 1 else accuracy, 2)
                if accuracy is not None
                else ""
            )
            action_type = "move"
        elif isinstance(selected, Pokemon):
            move_name = ""
            move_accuracy = ""
            estimated_damage = ""
            action_type = "switch"
        else:
            move_name = ""
            move_accuracy = ""
            estimated_damage = ""
            action_type = "other"

        row = {
            "experiment_id": self.experiment_id,
            "battle_tag": battle.battle_tag,
            "turn": battle.turn,
            "agent": agent,
            "agent_slot": agent_slot,
            "pokemon": pokemon,
            "opponent": opponent,
            "selected_move": move_name,
            "own_hp_pct": _hp_percent(battle.active_pokemon),
            "opponent_hp_pct": _hp_percent(battle.opponent_active_pokemon),
            "estimated_damage": estimated_damage,
            "move_accuracy": move_accuracy,
            "decision_time_ms": round(max(0.0, decision_time_ms), 4),
            "action_type": action_type,
        }
        with self._lock:
            with self.output_path.open("a", newline="", encoding="utf-8") as output:
                csv.DictWriter(output, fieldnames=MOVE_LOG_FIELDS).writerow(row)
            self.rows.append(row)

    def average_decision_ms(
        self, battle_tag: str, agent: str, agent_slot: str | None = None
    ) -> float | str:
        values = [
            float(row["decision_time_ms"])
            for row in self.rows
            if row["battle_tag"] == battle_tag
            and row["agent"] == agent
            and (agent_slot is None or row["agent_slot"] == agent_slot)
            and row["decision_time_ms"] != ""
        ]
        return round(sum(values) / len(values), 4) if values else ""


class DecisionLoggingMixin:
    """Wrap an agent's chooser and send its result to the shared logger."""

    def __init__(
        self,
        *args,
        move_logger: MoveLogger,
        agent_name: str,
        agent_slot: str,
        pokemon_name: str,
        opponent_name: str,
        **kwargs,
    ):
        self.move_logger = move_logger
        self.agent_name = agent_name
        self.agent_slot = agent_slot
        self.pokemon_name = pokemon_name
        self.opponent_name = opponent_name
        super().__init__(*args, **kwargs)

    def choose_move(self, battle):
        started = perf_counter_ns()
        if hasattr(self, "_last_estimated_damage"):
            self._last_estimated_damage = ""
        order = super().choose_move(battle)

        def record(selected_order):
            elapsed_ms = (perf_counter_ns() - started) / 1_000_000
            estimated = getattr(self, "_last_estimated_damage", "")
            self.move_logger.record_decision(
                battle=battle,
                agent=self.agent_name,
                agent_slot=self.agent_slot,
                pokemon=self.pokemon_name,
                opponent=self.opponent_name,
                order=selected_order,
                decision_time_ms=elapsed_ms,
                estimated_damage=estimated,
            )
            return selected_order

        if inspect.isawaitable(order):
            async def finish():
                return record(await order)

            return finish()
        return record(order)


class LoggedRandomPlayer(DecisionLoggingMixin, RandomPlayer):
    """RandomPlayer with shared experiment decision logging."""


class LoggedGreedyPlayer(DecisionLoggingMixin, GreedyPlayer):
    """GreedyPlayer with shared experiment decision logging."""
