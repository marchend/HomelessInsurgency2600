; Homeless Insurgency - Atari 2600, 32K F4SC (8 x 4K banks + SuperChip RAM)
;
; Bank map
;   0  main loop, city logic, room data
;   1  city kernel + city sprites
;   2  encounter screen kernel
;   3  encounter text (all screen lines + composer)
;   4  fights
;   5  encounter logic: outcomes, food, jail, recruiting, crew, collapse
;   6  title screen
;   7  HUD / title / fight footer text, sound effects

    processor 6502
    include "vcs.h"
    include "macros.h"
    include "ram.h"

    SEG CODE
    include "bank0.asm"
    include "bank1_city.asm"

    include "bank2_encounter.asm"
    include "bank3_text.asm"
    include "bank4_fight.asm"
    include "bank5_talk.asm"

    include "bank6_title.asm"

    include "bank7_services.asm"
