# Homeless Insurgency (Atari 2600) — Technical Concept

Status: draft v0.3 — covers Act 1 in detail; Acts 2 and 3 are placeholders.
v0.2 decisions: 32K F4SC locked; 12-char lines confirmed; homeless type is told by the greeting, not a label; regular people can be robbed; visible followers (1 per 5 recruits) that change how the city reacts; food costs money.
v0.3 decisions: failed-robbery penalty confirmed; followers must be fed (more followers = more money needed); followers help in fights.
Mockups: [docs/mockups/](mockups/) (rendered by [tools/mockups/render_mockups.py](../tools/mockups/render_mockups.py)).

---

## 1. Platform target

| Decision | Recommendation | Why |
|---|---|---|
| Video standard | NTSC (PAL60 build later is cheap) | Larger homebrew audience, Stella default |
| Cartridge format | **32K F4SC** — 8 × 4K banks + 128 bytes "SuperChip" RAM (**decided**) | An RPG needs ROM for text and RAM for NPC state. F4SC is a standard board AtariAge can manufacture, and runs on every emulator and flash cart |
| Language | 6502 assembly, DASM assembler | Custom kernels (text, multiplexed NPCs) are hard to do well in batari Basic |
| Emulator / debugger | Stella | Best debugger; cycle-exact |

Total RAM budget is 256 bytes (128 console RAM + 128 SuperChip). Everything below is designed around that.

## 2. Toolchain and repo layout

```
src/            6502 source, one file per bank + shared macros/equates
  bank0_main.asm      boot, main loop, bank-switch trampolines, RNG, game state
  bank1_city.asm      top-down city kernel + room data
  bank2_encounter.asm encounter kernel (portraits + text) + dialogue engine
  bank3_combat.asm    side-view combat kernel + fight logic
  bank4_text.asm      compressed dialogue text, part 1
  bank5_text.asm      compressed dialogue text, part 2 + dialogue trees
  bank6_screens.asm   title, act cards, jail, outskirts, game over
  bank7_audio.asm     sound effects/music + reserve for Acts 2/3
assets/
  sprites/*.png       sprite sheets, 8px wide, one color per row
  rooms/city.txt      ASCII city map (one char per room template)
  dialogue/*.yaml     dialogue trees and outcome odds, human-editable
tools/
  png2sprite.py       PNG → .byte tables (graphics + per-row color)
  build_rooms.py      city map → packed room table
  build_dialogue.py   YAML → packed text + node tables, enforces 12-char lines
  mockups/            the mockup renderer used for these concept images
tests/
  test_tools.py       asset pipeline tests
  test_logic.py       6502 game logic run under py65 (odds, recruitment, energy)
Makefile            dasm → bin/HomelessInsurgency.bin, then optional `stella` run
```

Testing approach: game rules (dice odds, recruitment math, energy drain) live in small 6502 routines that are unit-tested by running them in the py65 6502 simulator. Kernels are verified in Stella (scanline count must be exactly 262).

## 3. Frame anatomy

NTSC frame = 262 scanlines × 76 CPU cycles:

| Region | Lines | Use |
|---|---|---|
| VSYNC | 3 | sync |
| VBLANK | 37 | ~2,800 cycles: input, movement, NPC AI, prepare kernel pointers |
| Kernel | 192 | drawing only — no game logic |
| Overscan | 30 | ~2,200 cycles: collisions, dialogue/RNG rolls, sound, bank switching |

Game logic that can't fit in one frame (e.g., building a dialogue screen) is spread over several frames while the screen shows black or holds the previous image.

## 4. Screens (kernels)

Mockups for each are in [docs/mockups/](mockups/). Every mockup is drawn with only the objects the TIA has — playfield (PF), background (BK), two players (P0, P1), two missiles (M0, M1) and the ball (BL) — and the renderer refuses a frame that breaks per-scanline limits.

### 4.1 City (top-down exploration)

- **Flip-screen rooms**, Adventure-style. The city is an 8 × 8 grid = 64 rooms.
- **Playfield** draws buildings (asymmetric, 40 blocks across, 4 px each). **Background** color per scanline draws asphalt and sidewalks.
- **P0** = player, plus a second P0 band right behind the player for **followers** (see 5.6). **P1** = everyone else, *multiplexed vertically*: one NPC or sign per horizontal band, repositioned between bands. Up to ~6 NPCs/signs per room with no flicker, as long as no two share scanlines.
- Horizontal streets are 36 lines tall so the player (20 lines) and the follower row (12 lines) fit in one street.
- NPC kind is readable at a glance by color: police = blue, regular people = green/varied, homeless = brown. **Homeless types all look the same** in the city — the player learns the type from their greeting (4.2).
- **HUD** (bottom 32 lines): money + `recruited/known` using the 12-char text kernel, energy bar drawn with playfield.
- Bumping an NPC and pressing fire starts an encounter.

Room data: 2 bytes per room in ROM (template index for the three building bands + feature flags: shelter, food, police beat, outskirts edge) → 128 bytes for the whole city.

### 4.2 Encounter (close-up side view + dialogue)

- Top: a header naming only the kind of person (HOMELESS / POLICE / PASSERBY — never the homeless type), then a 64-line scene: **P0** = player portrait, **P1** = NPC portrait, both 2× wide, 30 rows tall (one color per row, 2 scanlines per row). Same art reused in combat.
- Bottom: 6 text lines — NPC speech (2 lines) and up to 4 choices. **M0** is the selection cursor.
- **Text kernel**: 12 characters per line, 4-px font, drawn by both players with 3 copies each (the classic 48-pixel trick). Each line is assembled into a RAM buffer during the ~7 blank scanlines before it, which is why the mockups have gaps between lines.
- **Hard writing constraint: 12 characters per line** (confirmed). The build tool rejects anything longer.
- **The greeting is the tell.** Each homeless type has its own pool of greetings (2 lines × 12 chars), so a careful player learns to read the type from the first thing a person says. See 5.3.

### 4.3 Combat (side view)

- **P0** player vs **P1** opponent — police (attacked) or a passerby (robbed) — reusing encounter portraits plus 1–2 action frames each. Passersby are weaker and slower than police.
- **Crew help:** fed followers add damage and can block hits (5.6). Followers stand in a row behind the fight (a second P0 band above the fighters, using copies), and the footer shows weapon + crew count.
- **Playfield score mode** draws two energy bars at the top, automatically colored with each fighter's color.
- **BL** = weapon (pipe/bottle/board), **M1** = opponent's baton.
- Background color per line = night-sky gradient; playfield skyline.

### 4.4 Other screens

Title, act cards, jail, "dumped at the outskirts", game over, act win. All simple playfield + text screens in bank 6.

## 5. Act 1 game systems

### 5.1 Player stats (RAM)

| Stat | Size | Notes |
|---|---|---|
| Money | 2 bytes BCD | cents. **Required**: the only way to get food |
| Energy | 1 byte | drains with walking + time; only food restores it; affects combat damage and how many hits you can take |
| Weapon | 1 byte | none / bottle / board / pipe — found in certain rooms, lost in jail |
| Heat | 1 byte | police hostility; rises with yelling, attacking, robbing. Hook for Act 2 |
| Recruits | 1 byte | 0–40; visible followers = recruits ÷ 5 |
| Crew hunger | 1 byte | 0 = fed; rises each hour; reset by feeding the crew (5.5) |
| Room / x / y | 3 bytes | position |
| Day / clock | 2 bytes | jail and beatings cost time |

### 5.2 Homeless population

- Fixed population of **40** homeless people (confirmed). 65% → **26 recruits** to finish Act 1.
- Each has a fixed home room in ROM: most cluster in **4 shelters**, the rest scattered on streets.
- Per-person state in SuperChip RAM: `met` bit, `recruited` bit, `type` (2 bits), `trust` (2–3 bits) → ~25 bytes total.
- **Types are rolled at game start** from the RNG, so each playthrough differs.
- The player doesn't know the total. HUD shows `recruited/known`; the `known` count grows as you meet people or learn shelter locations, so `??` turns into a number over time.

### 5.3 Homeless types and the greeting tell

The encounter header only says HOMELESS. The **greeting** is how the player works out the type. Each type gets a pool of 3–4 greetings in its own voice; one is picked at random each time you meet someone new. Draft lines (12 chars max per line):

| Type | Voice | Example greetings | Responds to | Fails on |
|---|---|---|---|---|
| Calm-rational | polite, wary, precise | `EVENING. YOU` / `NEW AROUND?` · `GOT A MINUTE` / `TO SPARE?` | a plan, facts, shelter info | yelling, vague promises |
| Calm-irrational | dreamy, odd, gentle | `PIGEONS SAID` / `YOU'D COME.` · `SHH. THE SKY` / `IS LISTENING` | listening, empathy, patience | pressure, logic |
| Angry-rational | blunt, suspicious | `WHO SENT YA?` / `TALK FAST?` · `WHAT. SAY IT` / `OR SCRAM.` | respect, directness, shared grievance | small talk, pity |
| Angry-irrational | hostile, paranoid | `BACK OFF MY` / `CART! BACK!` · `YOU'RE ONE` / `OF THEM!` | food, money, showing strength | arguing — may start a fight |

A recruitment is 2–3 exchanges. Right answers raise trust; at the threshold they join. Wrong answers lower trust; at zero they refuse for the rest of the day (or fight, for angry-irrational).

### 5.4 Encounters and odds

Odds are data tables (out of 256) in ROM so they can be tuned without touching code. All tables are then shifted by the follower count (5.6) and heat.

**Regular people (passersby)** — choices `ASK CHANGE` / `ROB` / `WALK AWAY`:

| Choice | Outcomes (draft, 0 followers) |
|---|---|
| ASK CHANGE | give money 5% (1 in 20), rude/hostile 15%, nice but no money 20%, ignore 60% |
| ROB | hand it over without a fight 10%, otherwise → **combat** with the passerby |
| — robbery won | take their money (bigger payout than begging), heat + |
| — robbery lost | they escape, you lose energy; 30% chance a cop arrives → jail (confirmed) |

**Police** (player-initiated):

| Choice | Outcomes (draft) |
|---|---|
| ASK CHANGE | change 5%, shoved aside 45%, ignored/hostile words 50% |
| ASK SHELTER | directions 55% (reveals a shelter on the map), hostile brush-off 45% |
| YELL AT COP | driven to outskirts + beaten 60% (energy loss, time loss), shoved 40% |
| ATTACK | always → combat. Win → flee, heat +; lose → jail |

### 5.5 Money, food and energy

- Energy drains steadily while walking and with the clock. **Food is the only way to restore it, and food costs money** — there is no free meal.
- Food places (marked with a sign on the map) sell 2–3 items at different prices and energy amounts, plus **FEED CREW**, priced per follower.
- **Followers must be fed.** Crew hunger rises over time; FEED CREW resets it. The more followers you have, the more money you need — a constant push toward begging more or robbing.
- Hungry crew: they stop helping in fights. After a full day unfed, one recruit leaves (recruits −1, so the follower count can drop and the 65% goal slips).
- Money comes from begging (slow, safe) or robbing (fast, raises heat, risks jail). That's the core Act 1 tension.
- Energy zero: collapse, wake in nearest known shelter (or outskirts), lose some money.

### 5.6 Followers

- **One visible follower per 5 recruits** (max 5 at 26 recruits). Every recruit still counts toward the 65%; followers are the visible part of your movement.
- **On screen:** followers walk in a row right behind the player, drawn as a second P0 band with the hardware copy feature (1–3 figures in a row). 4 and 5 followers use a "two people" follower graphic so 2–3 copies show 4–6 people. No flicker, no extra objects.
- **Effects** (applied as shifts to the odds tables, per follower):

| Who | Effect per follower (draft) |
|---|---|
| Police | +8% hostile outcomes, +5% chance they approach you first |
| Passersby, ASK CHANGE | −1% give money (5% → 0% at 5 followers), +4% rude |
| Passersby, ROB | +10% hand-it-over without a fight |
| Combat (fed crew only) | +1 damage per hit, 8% chance to block an incoming hit |

### 5.7 Failure states

- **Jail** (lose a fight with police, or caught after a failed robbery): weapon and some money lost, clock jumps forward, energy restored; heat drops a little. Followers stay recruited.
- **Outskirts** (yelled at police): moved to an edge room, energy heavily reduced.

## 6. RAM map (first pass)

| Block | Bytes |
|---|---|
| Kernel scratch (pointers, colors, text line buffer 6×5) | ~48 |
| Player stats | ~12 |
| Room NPC slots (5 × kind/x/y/state) | ~20 |
| RNG, frame counter, input, bank/state machine | ~8 |
| Sound | ~6 |
| Stack | ~16 |
| **Console RAM subtotal** | **~110 / 128** |
| SuperChip: homeless population (40 people) | ~25 |
| SuperChip: follower count, crew hunger, robbery/heat counters | ~4 |
| SuperChip: shelters known, food visited, flags | ~8 |
| SuperChip: dialogue state, current node, choice | ~8 |
| SuperChip: reserved for Acts 2/3 | ~83 |

## 7. Milestones

1. **M0 Toolchain** — DASM + Makefile + Stella; a stable 262-line frame.
2. **M1 City kernel** — playfield rooms, player movement, flip screens, collision.
3. **M2 NPCs** — P1 multiplexing, NPC wander AI, bump detection.
4. **M3 Encounter kernel** — portraits + 12-char text kernel + choice cursor.
5. **M4 Dialogue pipeline** — YAML → packed text; odds tables; outcomes wired to game state.
6. **M5 Combat** — side-view fight, energy bars, weapons, jail/flee.
7. **M6 Act 1 loop** — energy/food, shelters, police directions, 65% win, failure screens.
8. **M7 Sound and polish**, then Acts 2 and 3.

## 8. Decisions and open questions

Decided (v0.2): 32K F4SC · 12-char lines · greeting is the type tell · 40 homeless / 26 needed · passersby can be robbed (→ combat) · food costs money · 1 visible follower per 5 recruits, changing police and passerby odds.

Decided (v0.3): failed robbery = they escape, 30% a cop arrives → jail · followers must be fed (FEED CREW, priced per follower) · fed followers help in fights.

Decided: unfed crew — one recruit leaves per full unfed day.

Still open:
1. **Greeting pools:** final 3–4 greetings per homeless type, and the 2–3 exchange dialogue trees behind them.
2. **Acts 2 and 3:** heat, money and the follower count are the natural hooks.
