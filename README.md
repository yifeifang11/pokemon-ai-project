# Pokémon Showdown Agent Comparison

A small Python project for comparing Random, Greedy, and Monte Carlo Tree Search
(MCTS) agents in restricted 1v1 Pokémon Showdown battles. `poke-env` connects
agents to the real Showdown server. MCTS will use a separate lightweight forward
model rather than the Showdown battle engine.

## Requirements

- Python 3.10 or newer
- Node.js and Git, if you want to run a local Pokémon Showdown server

## Install the Python project

From the project root, create a virtual environment and install the dependencies:

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

On Windows, use `.venv\Scripts\python.exe` in place of `./.venv/bin/python`.
Using the virtual environment's Python path directly also avoids shell aliases
that might point `python` somewhere else.

Run the tests:

```sh
./.venv/bin/python -m unittest discover -s tests
```

## Install and start Pokémon Showdown locally

The battle scripts need a local Showdown server at
`ws://localhost:8000/showdown/websocket`. The server is separate from this
Python project. In another terminal, clone and prepare the official server:

```sh
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
cp config/config-example.js config/config.js
```

Start it for local bot testing and leave this terminal open:

```sh
node pokemon-showdown start --no-security
```

Keep `--no-security` for local development only; do not expose this server to the
internet.

## Run battles

In a second terminal, return to this project directory. To run one random-team
battle as a basic connection check:

```sh
./.venv/bin/python -m experiments.run_random_battle
```

To run the fixed Charizard-versus-Blastoise connectivity test (10 battles):

```sh
./.venv/bin/python -m experiments.test_fixed_battle
```

To run the reusable experiment runner and save results to CSV:

```sh
./.venv/bin/python -m experiments.run_battles \
  --matchup charizard-vs-blastoise \
  --battles 10 \
  --output results/charizard-blastoise.csv
```

The matchup is required, so another listed matchup must be selected explicitly.
Results are created as a new file; an existing output path is never overwritten.
Choose a different `--output` path for each run. For example:

```sh
./.venv/bin/python -m experiments.run_battles \
  --matchup charizard-vs-blastoise \
  --battles 10 \
  --output results/charizard-blastoise-run-2.csv
```

The runner accepts `--agent-1` and `--agent-2` values `random`, `greedy`, and
`enhanced_greedy`.
Greedy selects the legal move with the highest immediate expected damage using
power, accuracy, physical or special stats, stat stages, STAB, and type
effectiveness. It does not model future turns or secondary effects. Each CSV
row comes from one completed `poke-env` battle object. `winner` is `agent_1`,
`agent_2`, or `tie`; turn counts are read from the battle. Decision-time and
remaining-HP metrics are included when available. The experiment runner also
appends per-decision data to `experiments/results/move_log.csv`; pass
`--move-log PATH` to select a different log. Repeated runs append with a unique
`experiment_id`, while battle result files are created without overwriting.

Enhanced Greedy first evaluates expected damage with the same heuristic as
Basic Greedy. It estimates KO probability from move accuracy and 16 equally
likely damage rolls (0.85 through 1.00 times estimated on-hit damage). If any
move has at least 95% KO probability, it selects the move with the highest KO
probability, breaking ties by expected damage. Otherwise it makes the same
maximum-expected-damage choice as Basic Greedy. For each Enhanced decision,
the move log also records Basic Greedy's counterfactual pick from the same
legal moves, whether the policies disagree, and the KO selection reason.

Run the Enhanced Greedy Lucario comparisons with distinct result files:

```sh
./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 50 \
  --agent-1 enhanced_greedy --agent-2 random \
  --output results/lucario-enhanced-random.csv \
  --move-log experiments/results/lucario-enhanced-moves.csv

./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 50 \
  --agent-1 random --agent-2 enhanced_greedy \
  --output results/lucario-random-enhanced.csv \
  --move-log experiments/results/lucario-enhanced-moves.csv

./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 50 \
  --agent-1 enhanced_greedy --agent-2 greedy \
  --output results/lucario-enhanced-basic.csv \
  --move-log experiments/results/lucario-enhanced-moves.csv

./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 50 \
  --agent-1 greedy --agent-2 enhanced_greedy \
  --output results/lucario-basic-enhanced.csv \
  --move-log experiments/results/lucario-enhanced-moves.csv
```

Analyze these results and the counterfactual policy comparisons:

```sh
./.venv/bin/python -m experiments.analyze_results \
  --battle-results results/lucario-enhanced-random.csv \
                   results/lucario-random-enhanced.csv \
                   results/lucario-enhanced-basic.csv \
                   results/lucario-basic-enhanced.csv \
  --move-log experiments/results/lucario-enhanced-moves.csv
```

Analyze the battle result files and default move log with:

```sh
./.venv/bin/python -m experiments.analyze_results
```

Choose a different log or explicit result files with `--move-log PATH` and
`--battle-results PATH [PATH ...]`.

### Lucario mirror matchup

Both players receive the identical level 50 Lucario set: Serious nature, Inner
Focus, 0 EVs in every stat, 31 IVs in every stat, and Aura Sphere, Focus Blast,
Flash Cannon, and Dark Pulse. There are no items or Terastallization. Both have
the same effective Speed. These moves have the same priority, so Showdown
resolves Speed ties randomly through its normal battle rules; the runner does
not choose which player moves first.

Run a five-battle smoke test first, then the requested 50-battle comparisons
(each result file is new; the shared move log appends rows with unique
experiment IDs):

```sh
./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 5 \
  --agent-1 greedy --agent-2 random \
  --output results/lucario-greedy-random-smoke.csv \
  --move-log experiments/results/lucario-mirror-move-log.csv

./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 50 \
  --agent-1 greedy --agent-2 random \
  --output results/lucario-greedy-random.csv \
  --move-log experiments/results/lucario-mirror-move-log.csv

./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 50 \
  --agent-1 random --agent-2 greedy \
  --output results/lucario-random-greedy.csv \
  --move-log experiments/results/lucario-mirror-move-log.csv
```

Optional Random versus Random:

```sh
./.venv/bin/python -m experiments.run_battles \
  --matchup lucario-vs-lucario --battles 50 \
  --agent-1 random --agent-2 random \
  --output results/lucario-random-random.csv \
  --move-log experiments/results/lucario-mirror-move-log.csv
```

Analyze the mirror runs and decisions by player position:

```sh
./.venv/bin/python -m experiments.analyze_results \
  --battle-results results/lucario-greedy-random.csv \
                   results/lucario-random-greedy.csv \
  --move-log experiments/results/lucario-mirror-move-log.csv
```

Move rows include `player_slot` (`p1` or `p2`) and are joined to the matching
battle using both `experiment_id` and `battle_tag`. When the logger encounters
an older move-log header, it preserves a `.pre-enhanced-greedy.bak` copy before
adding the new slot and KO counterfactual fields.

## Project layout

- `teams.py`: fixed Showdown teams and the available matchup list.
- `agents/`: Random and Greedy baseline implementations; MCTS is a placeholder.
- `simulation/`: battle state and the independent forward-model stub.
- `experiments/`: battle and experiment entry points.
- `tests/`: small project tests.

The planned MCTS/forward-model interface is:

```python
simulate_turn(state, my_move, opponent_move) -> new_state
```

The forward model will represent only the restricted battle and will not call the
live Showdown battle engine.

## Planned milestones

1. Complete repeatable fixed-team battles and save experiment results.
2. Define the restricted battle rules and simplified forward model.
3. Implement and compare Random and Greedy agents.
4. Implement MCTS and compare budgets of 25, 100, and 500 simulations.
