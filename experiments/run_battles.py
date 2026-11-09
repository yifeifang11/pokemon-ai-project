"""Run fixed-team Showdown battles and save one CSV row per finished battle."""

import argparse
import asyncio
import csv
from pathlib import Path
import uuid

from poke_env.player import RandomPlayer

from experiments.move_logger import LoggedGreedyPlayer, LoggedRandomPlayer, MoveLogger
from teams import MATCHUPS, TEAMS


CSV_FIELDS = [
    "experiment_id",
    "battle_tag",
    "agent_1",
    "pokemon_1",
    "agent_2",
    "pokemon_2",
    "winner",
    "turns",
    "simulation_budget",
    "duration_seconds",
    "agent_1_avg_decision_ms",
    "agent_2_avg_decision_ms",
    "agent_1_remaining_hp_pct",
    "agent_2_remaining_hp_pct",
]
AGENT_CHOICES = ("random", "greedy")
DEFAULT_OUTPUT = Path("results/experiment.csv")
DEFAULT_MOVE_LOG = Path("experiments/results/move_log.csv")


def matchup_name(matchup: tuple[str, str]) -> str:
    """Return the command-line name for a team matchup."""
    return f"{matchup[0]}-vs-{matchup[1]}"


def create_player(
    agent_name: str,
    team: str,
    opponent_team: str,
    move_logger: MoveLogger,
    agent_slot: str,
) -> LoggedRandomPlayer | LoggedGreedyPlayer:
    """Build a configured baseline player for a fixed team."""
    player_class = {
        "random": LoggedRandomPlayer,
        "greedy": LoggedGreedyPlayer,
    }.get(agent_name)
    if player_class is None:
        raise ValueError(f"Unknown agent: {agent_name!r}")
    return player_class(
        battle_format="gen9customgame",
        team=team,
        max_concurrent_battles=1,
        move_logger=move_logger,
        agent_name=agent_name,
        agent_slot=agent_slot,
        pokemon_name=team.splitlines()[0],
        opponent_name=opponent_team.splitlines()[0],
    )


def remaining_hp_pct(battle) -> float | str:
    """Return exact remaining HP for the fixed one-Pokémon team, if known."""
    team = getattr(battle, "team", {})
    if len(team) != 1:
        return ""
    pokemon = next(iter(team.values()))
    if not pokemon.max_hp:
        return ""
    fraction = pokemon.current_hp_fraction
    if not 0 <= fraction <= 1:
        return ""
    return round(fraction * 100, 2)


def completed_battle_rows(
    player: RandomPlayer,
    *,
    experiment_id: str,
    agent_1: str,
    pokemon_1: str,
    agent_2: str,
    pokemon_2: str,
    opposing_player=None,
    move_logger: MoveLogger | None = None,
) -> list[dict[str, object]]:
    """Convert finished poke-env battle objects into one row per battle."""
    rows = []
    for battle in player.battles.values():
        if not battle.finished:
            continue
        other_battle = (
            opposing_player.battles.get(battle.battle_tag)
            if opposing_player is not None
            else None
        )
        if battle.won is True:
            winner = "agent_1"
        elif battle.won is False:
            winner = "agent_2"
        else:
            winner = "tie"

        rows.append(
            {
                "experiment_id": experiment_id,
                "battle_tag": battle.battle_tag,
                "agent_1": agent_1,
                "pokemon_1": pokemon_1,
                "agent_2": agent_2,
                "pokemon_2": pokemon_2,
                "winner": winner,
                "turns": battle.turn,
                # MCTS budget and per-battle timing do not apply to this run.
                "simulation_budget": "",
                "duration_seconds": "",
                "agent_1_avg_decision_ms": (
                    move_logger.average_decision_ms(
                        battle.battle_tag, agent_1, "agent_1"
                    )
                    if move_logger
                    else ""
                ),
                "agent_2_avg_decision_ms": (
                    move_logger.average_decision_ms(
                        battle.battle_tag, agent_2, "agent_2"
                    )
                    if move_logger
                    else ""
                ),
                "agent_1_remaining_hp_pct": remaining_hp_pct(battle),
                "agent_2_remaining_hp_pct": (
                    remaining_hp_pct(other_battle) if other_battle else ""
                ),
            }
        )
    return rows


def write_results(output_path: Path, rows: list[dict[str, object]]) -> None:
    """Create a new CSV file without replacing an existing experiment result."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except FileExistsError as error:
        raise FileExistsError(
            f"{output_path} already exists; choose a new --output path to preserve it."
        ) from error


def print_summary(rows: list[dict[str, object]], agent_1: str, agent_2: str) -> None:
    """Print results derived from the per-battle battle-object outcomes."""
    wins_1 = sum(row["winner"] == "agent_1" for row in rows)
    wins_2 = sum(row["winner"] == "agent_2" for row in rows)
    ties = sum(row["winner"] == "tie" for row in rows)
    total = len(rows)
    rate_1 = wins_1 / total if total else 0.0
    rate_2 = wins_2 / total if total else 0.0
    print(f"Completed battles: {total}")
    print(
        f"Agent 1 ({agent_1}) — wins: {wins_1}, losses: {wins_2}, "
        f"ties: {ties}, win rate: {rate_1:.1%}"
    )
    print(
        f"Agent 2 ({agent_2}) — wins: {wins_2}, losses: {wins_1}, "
        f"ties: {ties}, win rate: {rate_2:.1%}"
    )


async def run_experiment(
    matchup: tuple[str, str],
    battle_count: int,
    output_path: Path,
    agent_1: str = "random",
    agent_2: str = "random",
    move_log_path: Path = DEFAULT_MOVE_LOG,
) -> list[dict[str, object]]:
    """Run a matchup, save completed battles, and close both client connections."""
    if output_path.resolve() == move_log_path.resolve():
        raise ValueError("Battle results and move logs must use different CSV paths.")
    team_1, team_2 = matchup
    experiment_id = uuid.uuid4().hex
    move_logger = MoveLogger(move_log_path, experiment_id)
    player_1 = create_player(
        agent_1, TEAMS[team_1], TEAMS[team_2], move_logger, "agent_1"
    )
    player_2 = create_player(
        agent_2, TEAMS[team_2], TEAMS[team_1], move_logger, "agent_2"
    )
    rows: list[dict[str, object]] = []

    try:
        await player_1.battle_against(player_2, n_battles=battle_count)
    finally:
        rows = completed_battle_rows(
            player_1,
            experiment_id=experiment_id,
            agent_1=agent_1,
            pokemon_1=team_1.title(),
            agent_2=agent_2,
            pokemon_2=team_2.title(),
            opposing_player=player_2,
            move_logger=move_logger,
        )
        try:
            if rows:
                write_results(output_path, rows)
                print_summary(rows, agent_1, agent_2)
                print(f"Saved results to {output_path}")
            else:
                print("No completed battles; no CSV was created.")
        finally:
            await asyncio.gather(
                player_1.ps_client.stop_listening(),
                player_2.ps_client.stop_listening(),
                return_exceptions=True,
            )

    if len(rows) != battle_count:
        raise RuntimeError(
            f"Requested {battle_count} battles, but only {len(rows)} completed."
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matchup",
        required=True,
        choices=[matchup_name(matchup) for matchup in MATCHUPS],
        help="Explicit team matchup to run (for example: charizard-vs-blastoise).",
    )
    parser.add_argument(
        "--battles", type=int, default=10, help="Number of battles (default: 10)."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="New CSV output path."
    )
    parser.add_argument(
        "--move-log",
        type=Path,
        default=DEFAULT_MOVE_LOG,
        help="Append per-decision rows to this CSV path.",
    )
    parser.add_argument("--agent-1", choices=AGENT_CHOICES, default="random")
    parser.add_argument("--agent-2", choices=AGENT_CHOICES, default="random")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.battles < 1:
        raise SystemExit("--battles must be at least 1.")
    selected_matchup = next(
        matchup for matchup in MATCHUPS if matchup_name(matchup) == args.matchup
    )
    if args.output.exists():
        raise SystemExit(f"{args.output} already exists; choose a new --output path.")

    asyncio.run(
        run_experiment(
            selected_matchup,
            args.battles,
            args.output,
            args.agent_1,
            args.agent_2,
            args.move_log,
        )
    )


if __name__ == "__main__":
    main()
