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
- [ ] M2 NPC multiplexing
- [ ] M3 Encounter kernel + text
- [ ] M4 Dialogue pipeline + odds
- [ ] M5 Combat
- [ ] M6 Act 1 loop
- [ ] M7 Sound and polish

## Review
- Mockup renderer checks per-scanline TIA limits (one color per object per line, one owner per object per line, sprite reposition gaps, 12-char text and line-compose gaps). All 5 scenes pass.

## Stage A review (walk the city)
- ROM: `make` → bin/hi.bin (32K F4SC). `make run` opens Stella; `make test` runs 17 tests.
- tools/vcs_sim.py: py65 + F4SC + TIA/RIOT simulator; tests assert 262 lines / 192 visible every frame, walls, room flips, energy drain, fire debounce.
- Bugs caught by tests while building: first title line over budget (+1 line), VBLANK overrun when entering the city (HUD compose moved to overscan), PosObject overrun at large x (positioning moved into VBLANK), joystick bits clobbered by a shared temp (player bounced back after a room flip), fire held at power-on skipped the title.
- Trade-offs vs mockup: building bands mirrored/repeated instead of fully asymmetric; no roof vents or edge shading yet; sprites move vertically in 2-line steps.
- Not verified: Stella screenshots (no screen-capture access here) — needs a play-test.
