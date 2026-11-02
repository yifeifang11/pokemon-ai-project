"""Run ten fixed-team Charizard-versus-Blastoise battles on local Showdown."""

import asyncio

from poke_env.player import RandomPlayer
from teams import MATCHUPS, TEAMS


def verify_fixed_teams(
    player: RandomPlayer, expected_species: str, expected_moves: set[str]
) -> None:
    """Check each completed battle used the expected one-Pokémon team."""
    if len(player.battles) != 10:
        raise RuntimeError(f"Expected 10 battle records, got {len(player.battles)}.")

    for battle in player.battles.values():
        if len(battle.team) != 1:
            raise RuntimeError("A battle did not have exactly one Pokémon on the team.")
        pokemon = next(iter(battle.team.values()))
        if (pokemon.species or "").lower() != expected_species:
            raise RuntimeError(f"Expected {expected_species}, got {pokemon.species}.")
        actual_moves = set(pokemon.moves)
        if actual_moves != expected_moves:
            raise RuntimeError(
                f"Expected moves {sorted(expected_moves)}, got {sorted(actual_moves)}."
            )


async def main() -> None:
    """Run fixed-team battles and print each player's final record."""
    charizard_player = RandomPlayer(
        battle_format="gen9customgame",
        team=TEAMS["charizard"],
        max_concurrent_battles=1,
    )
    blastoise_player = RandomPlayer(
        battle_format="gen9customgame",
        team=TEAMS["blastoise"],
        max_concurrent_battles=1,
    )

    try:
        await charizard_player.battle_against(blastoise_player, n_battles=10)

        print(f"Completed battles: {charizard_player.n_finished_battles}")
        print(
            "Charizard player — "
            f"wins: {charizard_player.n_won_battles}, "
            f"losses: {charizard_player.n_lost_battles}, "
            f"ties: {charizard_player.n_tied_battles}"
        )
        print(
            "Blastoise player — "
            f"wins: {blastoise_player.n_won_battles}, "
            f"losses: {blastoise_player.n_lost_battles}, "
            f"ties: {blastoise_player.n_tied_battles}"
        )

        if charizard_player.n_finished_battles != 10:
            raise RuntimeError(
                "Expected 10 finished battles, but got "
                f"{charizard_player.n_finished_battles}."
            )
        charizard, blastoise = MATCHUPS[0]
        verify_fixed_teams(
            charizard_player,
            charizard,
            {"flamethrower", "fireblast", "airslash", "dragonpulse"},
        )
        verify_fixed_teams(
            blastoise_player,
            blastoise,
            {"surf", "hydropump", "icebeam", "darkpulse"},
        )
        print("Verified: one assigned Pokémon and all four assigned moves per battle.")
    finally:
        await asyncio.gather(
            charizard_player.ps_client.stop_listening(),
            blastoise_player.ps_client.stop_listening(),
        )


if __name__ == "__main__":
    asyncio.run(main())
