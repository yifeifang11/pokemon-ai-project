"""Play one local Showdown battle between two poke-env RandomPlayers."""

import asyncio

from poke_env.player import RandomPlayer


async def main() -> None:
    """Run one battle against a locally running Pokémon Showdown server."""
    player_one = RandomPlayer(battle_format="gen9randombattle")
    player_two = RandomPlayer(battle_format="gen9randombattle")
    await player_one.battle_against(player_two, n_battles=1)
    print("Battle completed.")


if __name__ == "__main__":
    asyncio.run(main())
