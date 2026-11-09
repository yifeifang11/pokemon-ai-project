"""Fixed, one-Pokémon teams used by the Showdown experiments."""

_BASE_STATS = "EVs: 0 HP / 0 Atk / 0 Def / 0 SpA / 0 SpD / 0 Spe\n" \
    "IVs: 31 HP / 31 Atk / 31 Def / 31 SpA / 31 SpD / 31 Spe"

_LUCARIO = f"""Lucario
Level: 50
Ability: Inner Focus
Serious Nature
{_BASE_STATS}
- Aura Sphere
- Focus Blast
- Flash Cannon
- Dark Pulse"""

TEAMS = {
    "charizard": f"""Charizard
Level: 50
Ability: Blaze
Serious Nature
{_BASE_STATS}
- Flamethrower
- Fire Blast
- Air Slash
- Dragon Pulse""",
    "blastoise": f"""Blastoise
Level: 50
Ability: Torrent
Serious Nature
{_BASE_STATS}
- Surf
- Hydro Pump
- Ice Beam
- Dark Pulse""",
    "venusaur": f"""Venusaur
Level: 50
Ability: Overgrow
Serious Nature
{_BASE_STATS}
- Giga Drain
- Sludge Bomb
- Earth Power
- Sleep Powder""",
    "lucario": _LUCARIO,
}

# Mirror matchup teams are identical, so their effective Speed is identical.
# Showdown resolves same-priority Speed ties randomly as part of normal play.
MATCHUPS = [
    ("charizard", "blastoise"),
    ("blastoise", "venusaur"),
    ("lucario", "venusaur"),
    ("lucario", "lucario"),
]
