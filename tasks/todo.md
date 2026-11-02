# Homeless Insurgency 2600 — todo

## Concept phase
- [x] Technical concept for Act 1 — [docs/CONCEPT.md](../docs/CONCEPT.md)
- [x] Hardware-accurate scene mockups — [docs/mockups/](../docs/mockups/), regenerate with `python3 tools/mockups/render_mockups.py`
- [x] Round 1 feedback: F4SC, 12-char lines, greeting tell, 40/26, robbing passersby, food costs money, 1 follower per 5 recruits
- [x] Mockups updated: neutral headers, followers in city, passerby encounter with ROB
- [x] Round 2 feedback: failed-robbery penalty kept, followers must be fed, followers help in fights (combat mockup shows crew)
- [x] Unfed-crew penalty confirmed (one recruit leaves per unfed day)
- [ ] Write the full greeting pools (3–4 per homeless type)
- [ ] Flesh out Acts 2 and 3

## Build — plan: ~/.claude/plans/curried-hopping-sonnet.md (stages A-D, play-test after each)
- [x] M0 Toolchain: DASM, Makefile, Stella, stable 262-line frame
- [x] M1 City kernel (Stage A: walk the city)
- [x] M2 NPC multiplexing (Stage B)
- [x] M3 Encounter kernel + text (Stage B)
- [x] M4 Dialogue pipeline + odds (Stage C)
- [x] M5 Combat (Stage C)
- [x] M6 Act 1 loop (Stage D)
- [x] M7 Sound (Stage D; polish after play-testing)

## Review
- Mockup renderer checks per-scanline TIA limits (one color per object per line, one owner per object per line, sprite reposition gaps, 12-char text and line-compose gaps). All 5 scenes pass.

## Stage A review (walk the city)
- ROM: `make` → bin/hi.bin (32K F4SC). `make run` opens Stella; `make test` runs 17 tests.
- tools/vcs_sim.py: py65 + F4SC + TIA/RIOT simulator; tests assert 262 lines / 192 visible every frame, walls, room flips, energy drain, fire debounce.
- Bugs caught by tests while building: first title line over budget (+1 line), VBLANK overrun when entering the city (HUD compose moved to overscan), PosObject overrun at large x (positioning moved into VBLANK), joystick bits clobbered by a shared temp (player bounced back after a room flip), fire held at power-on skipped the title.
- Trade-offs vs mockup: building bands mirrored/repeated instead of fully asymmetric; no roof vents or edge shading yet; sprites move vertically in 2-line steps.
- Not verified: Stella screenshots (no screen-capture access here) — needs a play-test.

## Stage B review (meet people)
- City: one NPC or sign per screen section (5 per room), P1 repositioned mid-screen; HMOVE every line (8-px black left border). 40 homeless placed by tools/build_assets.py (shelter rooms crowded, start room guaranteed one); empty streets get passersby/police at random. Walkers stroll the streets.
- Encounter (bank 2): header word, portraits on a scene per kind, greeting picked from the speaker's temperament pool, up to 4 choices with a cursor. Fire ends the conversation (outcomes are Stage C).
- Text: 6 lines composed into 2 alternating SuperChip buffers in RIOT-timed gaps. Strings stored as glyph offsets (not 5-bit packed: not needed yet, and faster to compose).
- Timing fixes found by tests/profiling: VBLANK overrun (NPC work moved to overscan; table-driven positions), title->city setup moved to title overscan, HUD composer 4x faster, header line overrun, first text gap too short, VDEL leftovers drawing garbage.
- 26 tests pass (frame timing every frame, per-section NPC x positions, greeting matches temperament, choices per kind, cursor limits, return to city).
- Deferred: follower row (Stage D, needs recruits); bank 2 has 44 bytes left - encounter text moves to its own bank in Stage C.
- Not verified: Stella screenshots (no capture access) - needs a play-test.

## Stage C review (consequences)
- Every choice rolls an outcome from assets/outcomes.py (odds per temperament, shifted by followers and heat): money, energy, heat, shelter tips, outskirts, fights. Passersby give change 1 in 20 at baseline.
- Food places (stand by the sign): coffee $0.50 (+40 energy), meal $2.00 (+120), FEED CREW (per follower; Stage D), leave.
- Fights (bank 4): side view, move/swing/block, energy bars in score mode, weapon + crew damage, opponent AI. Win vs cop: you get away; win a robbery: $3.00. Lose to a cop: arrested -> jail (fine $2.00, weapon lost, energy restored, heat halved, released at the start room). Lose a robbery: they flee, 30% the police come.
- Yelling at police can get you beaten and dumped at the south edge (energy halved).
- Three weapons lie in alleys (pipe, bat, board); walk into the alley and press fire.
- Banks: 3 = encounter text + composer (called from the bank 2 kernel through same-address stubs), 4 = fights, 5 = encounter logic + odds tables. Screen changes needing bank 0 go through `pending`, handled in overscan.
- Bugs caught by tests: branch after `ldy #0` (won fights ended in jail), signs unreachable on rooftops, VDEL leftovers above the fight footer.
- 47 tests pass, including an exhaustive check of the outcome roller against the odds tables for every random value, choice and temperament.
- Not verified: Stella screenshots - needs a play-test. Bank 0 has ~150 bytes left; Stage D logic should go in bank 5 / 7.

## Stage D review (Act 1 complete)
- Recruiting: the right opener for the person's type, then the right answer to their question (assets/outcomes.py RECRUIT). Wrong answers get that type's refusal; SHARE FOOD costs $0.50. Recruits leave the streets.
- Known count in the HUD ("RR/KK", "??" until you meet anyone): first meetings, plus everyone at a shelter the police point out.
- Followers: 1 per 5 recruits, drawn as a row under the player with sprite copies (NUSIZ0 per row in the kernel); 4-5 use a two-figure graphic (shows 4 / 6 figures).
- Crew hunger: +1 per 256 frames; at 32 they won't fight; at 64 one recruit leaves (notice screen). FEED CREW resets it.
- Collapse at 0 energy: wake at the first known shelter (or the outskirts) with some energy, $1.00 poorer.
- Recruit 26 -> "RALLIED / 26 OF US AND RISING!" -> back to the title.
- Sound effects (bank 7): coin, hit, recruit, eat, bad, pickup, blip, desertion.
- Bank 7 now holds the HUD/title/footer text (freed ~800 bytes of bank 0).
- Bugs caught: overscan overruns (city start, return to title) that hung in the timer wait; DASM truncating long .byte lines; band-start line over 76 cycles on page crossings.
- 53 tests pass. Not verified in Stella (needs a play-test). Known quirk: the follower row overlaps a roof when the player stands at the bottom of a street, and spreads to the right of the player.
