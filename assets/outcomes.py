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

    # Homeless people are recruited instead (RECRUIT below); only WALK AWAY
    # goes through the outcome tables.
    ("homeless", "WALK AWAY"): {"follower_shift": 0, "heat_shift": False, "outcomes": [LEAVE]},
}

# Recruiting homeless people: two exchanges. The opener (CHOICES["homeless"])
# and then their question, answered from ROUND2_CHOICES. Two right answers
# and they join. Types: calm-rational, calm-irrational, angry-rational,
# angry-irrational. SHARE FOOD costs SHARE_FOOD_CENTS.
ROUND2_CHOICES = ["WE ORGANIZE", "SAFE AND FED", "HIT 'EM BACK", "WALK AWAY"]
RECRUIT = [
    {"type": "calm_rational", "opener": "BIG PLAN...", "answer": "WE ORGANIZE",
     "question": ("NUMBERS WIN.", "HOW, THOUGH?"), "no": ("THAT'S NO", "PLAN. NO.")},
    {"type": "calm_irrational", "opener": "I'M ONE OF U", "answer": "SAFE AND FED",
     "question": ("MOON SAYS WE", "NEED A HOME."), "no": ("THE PIGEONS", "SAY NO.")},
    {"type": "angry_rational", "opener": "I'M ONE OF U", "answer": "HIT 'EM BACK",
     "question": ("FINE. AND?", "THEN WHAT?"), "no": ("WASTE OF MY", "TIME. SCRAM.")},
    {"type": "angry_irrational", "opener": "SHARE FOOD", "answer": "HIT 'EM BACK",
     "question": ("FOOD! MORE!", "WHAT ELSE?"), "no": ("GET LOST", "OR ELSE!")},
]
RECRUIT_LINES = {
    "joined": ("I'M IN.", "LEAD ON."),
    "no_food": ("YOU GOT", "NOTHING!"),
}
SHARE_FOOD_CENTS = 50
RECRUITS_TO_WIN = 26          # 65% of the 40 homeless people
PEOPLE_PER_FOLLOWER = 5       # one visible follower per this many recruits

# The crew gets hungry: +1 every 256 frames (~4 s). Hungry crews don't fight;
# after a further while unfed one recruit leaves (and hunger drops back).
HUNGRY_AT = 32                # ~2 minutes after the last FEED CREW
DESERT_AT = 64                # ~4 minutes: one recruit walks away
COLLAPSE_ENERGY = 56          # energy after waking up from a collapse
COLLAPSE_COST_CENTS = 100     # money lost when you collapse

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
    "collapse": ("YOU PASSED", "OUT COLD."),
    "deserted": ("ONE OF YOUR", "CREW LEFT."),
    "won": ("26 OF US", "AND RISING!"),
    "continue": ("CONTINUE", None),       # a choice line
    "the_end": ("THE END", None),
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

# Sound effects: (AUDC tone, AUDF pitch 0-31, AUDV volume 0-15, frames).
SOUNDS = {
    "coin": [(4, 12, 8, 4), (4, 8, 8, 6)],
    "hit": [(8, 20, 10, 3), (8, 28, 6, 3)],
    "recruit": [(4, 20, 8, 5), (4, 15, 8, 5), (4, 11, 8, 10)],
    "eat": [(6, 25, 6, 4), (6, 20, 6, 4)],
    "bad": [(1, 25, 8, 10), (1, 31, 8, 14)],
    "pickup": [(4, 10, 8, 3), (4, 6, 8, 5)],
    "blip": [(4, 8, 4, 2)],
    "desert": [(4, 11, 8, 5), (4, 15, 8, 5), (4, 22, 8, 10)],
}
