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
    print("Win rates and average battle length by configuration")
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in battle_rows:
        grouped[configuration(row)].append(row)
    for config, rows in sorted(grouped.items()):
        n = len(rows)
        w1 = sum(row.get("winner") == "agent_1" for row in rows)
        w2 = sum(row.get("winner") == "agent_2" for row in rows)
        ties = sum(row.get("winner") == "tie" for row in rows)
        turns = [float(row["turns"]) for row in rows if row.get("turns", "")]
        name = f"{config[0]} {config[1]} vs {config[2]} {config[3]}"
        print(
            f"  {name}: n={n}, wins={w1}/{w2}, ties={ties}, "
            f"rates={w1/n:.1%}/{w2/n:.1%}, avg turns={_mean(turns)}"
        )

    print("Move selection frequencies by agent and Pokémon")
    choices: dict[tuple[str, str], Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    for row in move_rows:
        if not row.get("selected_move") or row.get("action_type", "move") != "move":
            continue
        key = (row.get("agent", ""), row.get("pokemon", ""))
        choices[key][row["selected_move"]] += 1
        totals[key] += 1
    for key, counts in sorted(choices.items()):
        descriptions = ", ".join(
            f"{move}: {count} ({count/totals[key]:.1%})"
            for move, count in counts.most_common()
        )
        print(f"  {key[0]} {key[1]} (n={totals[key]}): {descriptions}")

    decision_times: dict[str, list[float]] = defaultdict(list)
    for row in move_rows:
        try:
            decision_times[row.get("agent", "")].append(float(row["decision_time_ms"]))
        except (KeyError, ValueError):
            continue
    print("Average decision time by agent (ms)")
    for agent, values in sorted(decision_times.items()):
        print(f"  {agent}: {_mean(values)}")

    hp_values: dict[str, list[float]] = defaultdict(list)
    for row in battle_rows:
        for side in (1, 2):
            agent = row.get(f"agent_{side}", "")
            raw = row.get(f"agent_{side}_remaining_hp_pct", "")
            try:
                hp_values[agent].append(float(raw))
            except ValueError:
                pass
    print("Average remaining HP by agent (%)")
    for agent, values in sorted(hp_values.items()):
        print(f"  {agent}: {_mean(values)}")


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
