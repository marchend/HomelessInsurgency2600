"""What happens after each encounter choice. Edit freely; `make` rebuilds.

Each choice lists its possible outcomes from best to worst for the player.
`odds` are percentages per temperament of the person you're talking to:
    police:   calm, less calm, angry, really angry
    passerby: patient, less patient, impatient, angry-impatient
    homeless: calm-rational, calm-irrational, angry-rational, angry-irrational
The last outcome takes whatever is left (its odds are None).

`follower_shift` / `heat_shift` push the roll toward later (worse) outcomes:
follower_shift is percent per follower (negative pulls toward earlier ones);
heat_shift = True adds up to 25% as police heat rises.

Lines are two screen lines of up to 12 characters ("" for none).

Effects:
    ("money", cents)       add money          ("energy", -n)   lose energy
    ("heat", n)            raise police heat   ("shelter",)    learn a shelter
    ("outskirts",)         dumped at the edge of the city (energy halved)
    ("combat",)            start a fight (no response screen)
    ("leave",)             end the conversation (no response screen)
"""

CHOICES = {
    "homeless": ["I'M ONE OF U", "SHARE FOOD", "BIG PLAN...", "WALK AWAY"],
    "police": ["ASK CHANGE", "ASK SHELTER", "YELL AT COP", "ATTACK"],
    "passerby": ["ASK CHANGE", "ROB", "WALK AWAY"],
}

LEAVE = {"name": "leave", "odds": None, "lines": ("", ""), "effects": [("leave",)]}

OUTCOMES = {
    ("passerby", "ASK CHANGE"): {
        "follower_shift": 3, "heat_shift": False,
        "outcomes": [
            {"name": "give", "odds": [15, 5, 0, 0], "lines": ("HERE, TAKE", "A QUARTER."),
             "effects": [("money", 25)]},
            {"name": "nice", "odds": [45, 20, 5, 0], "lines": ("SORRY, I'VE", "GOT NOTHING."),
             "effects": []},
            {"name": "rude", "odds": [5, 15, 35, 70], "lines": ("GET A JOB,", "LOSER!"),
             "effects": []},
            {"name": "ignore", "odds": None, "lines": ("...", ""), "effects": []},
        ],
    },
    ("passerby", "ROB"): {
        "follower_shift": -10, "heat_shift": False,
        "outcomes": [
            {"name": "hand_over", "odds": [20, 10, 5, 0], "lines": ("TAKE IT! ALL", "OF IT!"),
             "effects": [("money", 300), ("heat", 8)]},
            {"name": "fight", "odds": None, "lines": ("", ""),
             "effects": [("heat", 16), ("combat",)]},
        ],
    },
    ("passerby", "WALK AWAY"): {"follower_shift": 0, "heat_shift": False, "outcomes": [LEAVE]},

    ("police", "ASK CHANGE"): {
        "follower_shift": 3, "heat_shift": True,
        "outcomes": [
            {"name": "change", "odds": [15, 5, 2, 0], "lines": ("HERE. NOW", "BEAT IT."),
             "effects": [("money", 25)]},
            {"name": "ignored", "odds": [60, 50, 38, 30], "lines": ("NOT MY JOB.", ""),
             "effects": []},
            {"name": "shoved", "odds": None, "lines": ("MOVE IT,", "BUM!"),
             "effects": [("energy", -10)]},
        ],
    },
    ("police", "ASK SHELTER"): {
        "follower_shift": 3, "heat_shift": True,
        "outcomes": [
            {"name": "directions", "odds": [85, 55, 30, 10], "lines": ("THERE'S ONE", "UPTOWN. GO."),
             "effects": [("shelter",)]},
            {"name": "brush_off", "odds": None, "lines": ("DO I LOOK", "LIKE A MAP?"),
             "effects": []},
        ],
    },
    ("police", "YELL AT COP"): {
        "follower_shift": 3, "heat_shift": True,
        "outcomes": [
            {"name": "shoved", "odds": [70, 40, 20, 5], "lines": ("WATCH IT!", ""),
             "effects": [("energy", -10), ("heat", 8)]},
            {"name": "beaten", "odds": None, "lines": ("THAT'S IT.", "GET IN."),
             "effects": [("heat", 16), ("outskirts",)]},
        ],
    },
    ("police", "ATTACK"): {
        "follower_shift": 0, "heat_shift": False,
        "outcomes": [{"name": "fight", "odds": None, "lines": ("", ""),
                      "effects": [("heat", 32), ("combat",)]}],
    },

    # Recruiting homeless people comes in Stage D; for now they hedge.
    ("homeless", "I'M ONE OF U"): {"follower_shift": 0, "heat_shift": False, "outcomes": [
        {"name": "maybe", "odds": None, "lines": ("MAYBE.", "WE'LL SEE."), "effects": []}]},
    ("homeless", "SHARE FOOD"): {"follower_shift": 0, "heat_shift": False, "outcomes": [
        {"name": "maybe", "odds": None, "lines": ("MAYBE.", "WE'LL SEE."), "effects": []}]},
    ("homeless", "BIG PLAN..."): {"follower_shift": 0, "heat_shift": False, "outcomes": [
        {"name": "maybe", "odds": None, "lines": ("MAYBE.", "WE'LL SEE."), "effects": []}]},
    ("homeless", "WALK AWAY"): {"follower_shift": 0, "heat_shift": False, "outcomes": [LEAVE]},
}

# Food places: greeting, menu and prices (cents) / energy gained.
FOOD_GREETING = ("WHAT'LL IT", "BE?")
FOOD_MENU = [
    {"choice": "COFFEE $0.50", "cents": 50, "energy": 40},
    {"choice": "MEAL   $2.00", "cents": 200, "energy": 120},
    {"choice": "FEED CREW", "cents": 100, "energy": 0},      # per follower
    {"choice": "LEAVE", "cents": 0, "energy": 0},
]
FOOD_LINES = {
    "bought": ("ENJOY.", ""),
    "broke": ("NO MONEY,", "NO FOOD."),
    "no_crew": ("WHAT CREW?", ""),
}

# Fixed screens.
MESSAGES = {
    "jail": ("A NIGHT IN", "THE CELLS."),
    "arrest": ("YOU'RE UNDER", "ARREST."),
    "fled": ("YOU GOT", "AWAY!"),
    "took_cash": ("YOU TOOK", "THEIR CASH."),
    "they_fled": ("THEY GOT", "AWAY."),
    "continue": ("CONTINUE", None),       # a choice line
}

# Fights. Damage is in energy points (the player's energy bar is 252).
FIGHTERS = {
    "police": {"hp": 10, "damage": 24, "speed": 1},
    "passerby": {"hp": 6, "damage": 14, "speed": 2},     # moves every `speed` frames
}
WEAPONS = [  # name shown in the fight (5 chars max), extra damage per hit
    ("FISTS", 0), ("PIPE", 2), ("BAT", 2), ("BOARD", 1),
]
ROB_CASH_CENTS = 300          # winning a robbery fight
JAIL_FINE_CENTS = 200         # taken when you leave jail (or all you have)
PASSERBY_CALLS_COPS = 30      # percent: losing a robbery fight brings police
