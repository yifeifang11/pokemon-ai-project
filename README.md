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

The matchup is required, so another listed matchup will not run unless selected
explicitly. Charizard versus Blastoise is the only matchup battle-tested so far.
Results are created as a new file; an existing output path is never overwritten.
Choose a different `--output` path for each run. For example:

```sh
./.venv/bin/python -m experiments.run_battles \
  --matchup charizard-vs-blastoise \
  --battles 10 \
  --output results/charizard-blastoise-run-2.csv
```

The runner accepts `--agent-1` and `--agent-2` values `random` and `greedy`.
Greedy selects the legal move with the highest immediate expected damage using
power, accuracy, physical or special stats, stat stages, STAB, and type
effectiveness. It does not model future turns or secondary effects. Each CSV row comes from one
completed `poke-env` battle object. `winner` is `agent_1`, `agent_2`, or `tie`;
turn counts are read from the battle. `simulation_budget` and
`duration_seconds` are blank for Random battles. The installed `poke-env` API
does not provide reliable per-battle start and end timestamps for a batch.

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
