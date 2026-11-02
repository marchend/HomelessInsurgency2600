; Homeless Insurgency - Atari 2600, 32K F4SC (8 x 4K banks + SuperChip RAM)
;
; Bank map
;   0  main loop, game logic, text composer, room data
;   1  city kernel + city sprites
;   2  encounter screen + encounter text
;   3-5, 7  reserved (combat, more dialogue, audio)
;   6  title screen

    processor 6502
    include "vcs.h"
    include "macros.h"
    include "ram.h"

    SEG CODE
    include "bank0.asm"
    include "bank1_city.asm"

    include "bank2_encounter.asm"
    BANK_START 3
    BANK_END 3
    BANK_START 4
    BANK_END 4
    BANK_START 5
    BANK_END 5

    include "bank6_title.asm"

    BANK_START 7
    BANK_END 7
