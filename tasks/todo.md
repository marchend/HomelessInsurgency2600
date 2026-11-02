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

## Build (after concept sign-off) — see CONCEPT.md §7
- [ ] M0 Toolchain: DASM, Makefile, Stella, stable 262-line frame
- [ ] M1 City kernel
- [ ] M2 NPC multiplexing
- [ ] M3 Encounter kernel + text
- [ ] M4 Dialogue pipeline + odds
- [ ] M5 Combat
- [ ] M6 Act 1 loop
- [ ] M7 Sound and polish

## Review
- Mockup renderer checks per-scanline TIA limits (one color per object per line, one owner per object per line, sprite reposition gaps, 12-char text and line-compose gaps). All 5 scenes pass.
