# The glossary

Whatever translates the game - a person, a model here, a model somewhere else -
has to be handed this first. The campaign runs to fourteen missions and the
same names come back in most of them; decided once, they stay consistent, and
decided per file they will not.

The counts are how often a term appears and in how many missions, taken from
the English text with `tools/translate.py`.

## Leave as they are

Acronyms and organisation names carry no meaning to translate, and a player who
sees NOAH in mission 2 needs to see NOAH in mission 9.

| term | uses | missions |
|---|---|---|
| NOAH | 112 | 10 |
| COTUC | 95 | 5 |
| SGDS | 51 | 12 |
| TFR | 43 | 7 |

## Names of people and places

Also unchanged, bar Czech declension where a sentence needs it.

| term | uses | missions |
|---|---|---|
| Solensk | 13 | 5 |
| Czeko | 8 | 4 |
| McNowell | 6 | 2 |
| Tao | 7 | 2 |
| Gregor | 4 | 3 |

## The factions and the cult - kept

**Settled: the faction names stay as they are.** They read as names rather than
as descriptions, and a player who meets the Slingers in one mission should meet
the Slingers in the next. The rest of a sentence around them is Czech and they
decline with it where the sentence needs it.

| term | uses | missions | note |
|---|---|---|---|
| Slingers | 31 | 4 | a faction |
| Claws / Claw | 44 | 5 | a faction |
| Blessed | 15 | 3 | a cult's word for itself |
| Undead | 15 | 4 | |
| Undying | 12 | 5 | |
| Knights / Knight | 15 | 4 | |
| Seeker | 12 | 4 | |
| Church | 12 | 5 | |
| Monk | 4 | 2 | |
| Base | 50 | 13 | the player's own bunker |

## Equipment that already has a Czech habit

Vehicles and weapons mostly keep their names in Czech usage - Humvee, Vulcan -
and the catalog in the launcher already carries the whole list, so it is the
place to check a name against.

| term | uses | missions |
|---|---|---|
| Humvee | 6 | 2 |
| Vulcan | 4 | 2 |
| Thumper | 4 | 3 |

## The speakers

The speaker field of a mission record names who says the line, and the same
handful carry the campaign. Each wants one voice and one register kept
throughout - the outpost is not polite to the base in one mission and formal in
the next.

| speaker | lines |
|---|---|
| Außenposten (outpost) | 425 |
| Basis (base) | 130 |
| Ausbilder (instructor) | 79 |
| NOAH Wissenschaftler (scientist) | 54 |
| Aussenteam (field team) | 41 |
| McNowell | 37 |

The field is German and carries stage directions with the name - laughing,
annoyed, over the radio. `tools/dub.py --voices` folds those together.

## Two things that are not glossary but decide the tone

**Whom the game addresses. Settled: informal throughout.** Most lines are radio
traffic between a field team and their base, and a unit talking to itself in
Czech does not use the formal address. It holds for the interface as well -
the option descriptions say what you will see, not what one might observe.

**Length.** The panels are fixed rectangles and Czech runs longer than English.
`translate.py --list NAME --longest` puts the longest lines first, which is
where an overrun would show.
