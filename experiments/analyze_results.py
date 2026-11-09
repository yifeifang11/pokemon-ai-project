"""Print compact summaries from battle-result and per-decision CSV files."""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def read_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows = []
    for path in paths:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as source:
            rows.extend(csv.DictReader(source))
    return rows


def expand_paths(inputs: list[str] | None, default_pattern: str) -> list[Path]:
    patterns = inputs or [default_pattern]
    paths = []
    for pattern in patterns:
        candidate = Path(pattern)
        matches = sorted(candidate.parent.glob(candidate.name))
        paths.extend(matches or ([candidate] if candidate.is_file() else []))
    return list(dict.fromkeys(paths))


def configuration(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("agent_1", ""),
        row.get("pokemon_1", ""),
        row.get("agent_2", ""),
        row.get("pokemon_2", ""),
    )


def _mean(values: list[float]) -> str:
    return f"{sum(values) / len(values):.2f}" if values else "n/a"


def analyze(battle_rows: list[dict[str, str]], move_rows: list[dict[str, str]]) -> None:
    # Join decisions to completed battles by both identifiers, keeping repeated
    # runs and identical Pokémon in the two player positions separate.
    battle_keys = {
        (row.get("experiment_id", ""), row.get("battle_tag", ""))
        for row in battle_rows
    }
    joined_moves = [
        row
        for row in move_rows
        if (row.get("experiment_id", ""), row.get("battle_tag", "")) in battle_keys
    ]

    print("Win rates by configuration and player position; average battle length")
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in battle_rows:
        grouped[configuration(row)].append(row)
    for config, rows in sorted(grouped.items()):
        n = len(rows)
        w1 = sum(row.get("winner") == "agent_1" for row in rows)
        w2 = sum(row.get("winner") == "agent_2" for row in rows)
        ties = sum(row.get("winner") == "tie" for row in rows)
        turns = [float(row["turns"]) for row in rows if row.get("turns", "")]
        name = f"P1 {config[0]} ({config[1]}) vs P2 {config[2]} ({config[3]})"
        print(
            f"  {name}: n={n}; P1 wins={w1} ({w1/n:.1%}), "
            f"P2 wins={w2} ({w2/n:.1%}), ties={ties}, avg turns={_mean(turns)}"
        )

    print("Move selection frequencies by player position, agent, and Pokémon")
    choices: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    for row in joined_moves:
        if not row.get("selected_move") or row.get("action_type", "move") != "move":
            continue
        player_slot = row.get("player_slot") or {
            "agent_1": "p1",
            "agent_2": "p2",
        }.get(row.get("agent_slot", ""), "unknown")
        key = (player_slot, row.get("agent", ""), row.get("pokemon", ""))
        choices[key][row["selected_move"]] += 1
        totals[key] += 1
    for key, counts in sorted(choices.items()):
        descriptions = ", ".join(
            f"{move}: {count} ({count/totals[key]:.1%})"
            for move, count in counts.most_common()
        )
        print(
            f"  {key[0]} {key[1]} {key[2]} (n={totals[key]}): {descriptions}"
        )

    decision_times: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in joined_moves:
        try:
            player_slot = row.get("player_slot") or {
                "agent_1": "p1",
                "agent_2": "p2",
            }.get(row.get("agent_slot", ""), "unknown")
            decision_times[(player_slot, row.get("agent", ""))].append(
                float(row["decision_time_ms"])
            )
        except (KeyError, ValueError):
            continue
    print("Average decision time by player position and agent (ms)")
    for (player_slot, agent), values in sorted(decision_times.items()):
        print(f"  {player_slot} {agent}: {_mean(values)}")

    hp_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in battle_rows:
        for side, player_slot in ((1, "p1"), (2, "p2")):
            agent = row.get(f"agent_{side}", "")
            raw = row.get(f"agent_{side}_remaining_hp_pct", "")
            try:
                hp_values[(player_slot, agent)].append(float(raw))
            except ValueError:
                pass
    print("Average remaining HP by player position and agent (%)")
    for (player_slot, agent), values in sorted(hp_values.items()):
        print(f"  {player_slot} {agent}: {_mean(values)}")

    enhanced_rows = [row for row in joined_moves if row.get("agent") == "enhanced_greedy"]
    disagreements = [
        row
        for row in enhanced_rows
        if row.get("policies_disagree", "").strip().lower() in {"true", "1", "yes"}
    ]
    reliable_ko_rows = [
        row
        for row in enhanced_rows
        if row.get("selection_reason") == "reliable_ko"
        or row.get("ko_threshold_met", "").strip().lower() in {"true", "1", "yes"}
    ]
    total_enhanced = len(enhanced_rows)
    print("Enhanced Greedy KO-aware decisions")
    print(
        f"  reliable-KO selections: {len(reliable_ko_rows)}/{total_enhanced} "
        f"({len(reliable_ko_rows)/total_enhanced:.1%})"
        if total_enhanced
        else "  no Enhanced Greedy decisions in the joined logs"
    )
    print(
        f"  Basic/Enhanced disagreements: {len(disagreements)}/{total_enhanced} "
        f"({len(disagreements)/total_enhanced:.1%})"
        if total_enhanced
        else "  Basic/Enhanced disagreements: n/a"
    )

    alternative_moves: Counter = Counter(
        (row.get("basic_greedy_move", ""), row.get("enhanced_greedy_move", ""))
        for row in disagreements
    )
    print("  Enhanced choices when policies disagree (Basic → Enhanced)")
    if alternative_moves:
        for (basic_move, enhanced_move), count in alternative_moves.most_common():
            print(f"    {basic_move} → {enhanced_move}: {count}")
    else:
        print("    none")

    aura_alternatives = [
        row
        for row in enhanced_rows
        if row.get("basic_greedy_move", "").lower() == "focusblast"
        and row.get("enhanced_greedy_move", "").lower() == "aurasphere"
    ]
    print(
        f"  Aura Sphere instead of Focus Blast: {len(aura_alternatives)}/"
        f"{total_enhanced} Enhanced decisions"
        + (f" ({len(aura_alternatives)/total_enhanced:.1%})" if total_enhanced else "")
    )

    head_to_head = [
        row
        for row in battle_rows
        if {row.get("agent_1"), row.get("agent_2")}
        == {"greedy", "enhanced_greedy"}
    ]
    print("Basic Greedy vs Enhanced Greedy head-to-head")
    if not head_to_head:
        print("  no direct-comparison battles found")
    else:
        direct_groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
        for row in head_to_head:
            direct_groups[configuration(row)].append(row)
        for config, rows in sorted(direct_groups.items()):
            n = len(rows)
            basic_wins = sum(
                row.get("winner") == ("agent_1" if row.get("agent_1") == "greedy" else "agent_2")
                for row in rows
            )
            enhanced_wins = sum(
                row.get("winner")
                == ("agent_1" if row.get("agent_1") == "enhanced_greedy" else "agent_2")
                for row in rows
            )
            print(
                f"  P1 {config[0]} vs P2 {config[2]}: "
                f"Basic {basic_wins}/{n} ({basic_wins/n:.1%}); "
                f"Enhanced {enhanced_wins}/{n} ({enhanced_wins/n:.1%})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--battle-results",
        nargs="*",
        help="Battle CSV paths or glob patterns (default: results/*.csv).",
    )
    parser.add_argument(
        "--move-log",
        type=Path,
        default=Path("experiments/results/move_log.csv"),
    )
    args = parser.parse_args()
    battle_paths = expand_paths(args.battle_results, "results/*.csv")
    if not battle_paths:
        print("No battle result CSV files found.")
    analyze(read_rows(battle_paths), read_rows([args.move_log]))


if __name__ == "__main__":
    main()
