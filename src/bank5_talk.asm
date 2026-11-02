; Bank 5: encounter logic.
;
;   EncounterStart  (far, from bank 0) set up a conversation with encSlot
;   EncounterLogic  (far, each VBLANK) cursor, choices, outcomes, food, jail
;
; Outcomes come from tables generated from assets/outcomes.py. Anything that
; needs bank 0 (back to the city, a teleport, starting a fight) is requested
; through `pending` and done in bank 0's overscan.

OUTSKIRTS_ROW = 56      ; first room of the bottom map row

    BANK_START 5

    include "kernel.h"

; ---------------------------------------------------------------------------
; Starting a conversation
; ---------------------------------------------------------------------------
EncounterStart
    SUBROUTINE
    ldx encSlot
    lda SC_R+SC_SLOT_KIND,x
    cmp #KIND_FOOD
    bne .person
    jsr FoodMenu
    jmp .common
.person
    sec
    sbc #KIND_HOMELESS
    sta encKind
    bne .stranger
    lda SC_R+SC_SLOT_PERSON,x   ; homeless: their fixed type
    tay
    lda SC_R+SC_PEOPLE,y
    and #3
    sta encTemp
    jmp .greet
.stranger
    jsr Random5                 ; police / passerby: a fresh mood, and a
    and #3                      ; chance of one step angrier that grows
    sta encTemp                 ; with heat and followers
    lda followers
    asl
    asl
    asl
    asl
    clc
    adc heat
    bcs .angrier
    sta ttmp
    jsr Random5
    cmp ttmp
    bcs .greet
.angrier
    lda encTemp
    cmp #3
    beq .greet
    inc encTemp
.greet
    lda encKind                 ; greeting pool = kind * 4 + temperament
    asl
    asl
    ora encTemp
    tax
    jsr Random5
.mod
    cmp GreetCount,x
    bcc .pick
    sbc GreetCount,x
    bcs .mod
.pick
    clc
    adc GreetStart,x
    tay
    lda GreetLine1,y
    sta encStr
    lda GreetLine2,y
    sta encStr+1
    lda encKind
    jsr LoadChoices
.common
    jsr SetPortraits
    lda SWCHA
    sta joyPrev
    lda #SCREEN_ENCOUNTER
    sta screen
    jmp BankReturn5

; Food place: greeting and menu.
FoodMenu
    SUBROUTINE
    lda #ENC_FOOD
    sta encKind
    lda #0
    sta encTemp
    lda #STR_FOOD_GREET1
    sta encStr
    lda #STR_FOOD_GREET2
    sta encStr+1
    lda #ENC_FOOD
    ; fall through

; A = choice table row (encounter kind): choices into encStr+2..5.
LoadChoices
    SUBROUTINE
    tax
    lda ChoiceCount,x
    sta nChoices
    txa
    asl
    asl
    tax
    ldy #0
.choice
    lda ChoiceTab,x
    sta encStr+2,y
    inx
    iny
    cpy #4
    bne .choice
    lda #0
    sta cursor
    lda #PHASE_CHOOSE
    sta encPhase
    rts

SetPortraits
    SUBROUTINE
    lda #<PlayerSideGfx
    sta encP0g
    lda #>PlayerSideGfx
    sta encP0g+1
    lda #<PlayerSideCol
    sta encP0c
    lda #>PlayerSideCol
    sta encP0c+1
    ldx encKind
    lda PortraitGfxLo,x
    sta encP1g
    lda PortraitGfxHi,x
    sta encP1g+1
    lda PortraitColLo,x
    sta encP1c
    lda PortraitColHi,x
    sta encP1c+1
    rts

; ---------------------------------------------------------------------------
; Each frame
; ---------------------------------------------------------------------------
EncounterLogic
    SUBROUTINE
    lda pending
    bne .done                   ; a screen change is already on its way
    jsr FirePressed5
    bcs .fire
    lda SWCHA                   ; up / down move the cursor
    tax
    eor #$FF
    and joyPrev
    stx joyPrev
    sta joy
    and #$10
    beq .notUp
    lda cursor
    beq .notUp
    dec cursor
.notUp
    lda joy
    and #$20
    beq .done
    lda cursor
    clc
    adc #1
    cmp nChoices
    bcs .done
    sta cursor
.done
    jmp BankReturn5
.fire
    lda encPhase
    bne .respond
    lda encKind
    cmp #ENC_FOOD
    beq .food
    jsr Outcome
    jmp BankReturn5
.food
    jsr FoodChoice
    jmp BankReturn5
.respond
    jsr Respond
    jmp BankReturn5

; CONTINUE after a response.
Respond
    SUBROUTINE
    lda encAction
    cmp #ACT_OUTSKIRTS
    beq .outskirts
    cmp #ACT_JAIL
    beq ShowJail
    cmp #ACT_JAIL_DONE
    beq .jailDone
    cmp #ACT_FOOD
    beq .food
    lda #PENDING_RESUME
    sta pending
    rts
.food
    jsr FoodMenu
    jmp SetPortraits
.outskirts                      ; beaten and dumped on the city's south edge
    jsr Random5
    and #7
    ora #OUTSKIRTS_ROW
    sta room
    lsr energy
    jmp .teleport
.jailDone                       ; released at the start room, without weapon
    lda #0                      ; and $2.00 poorer, rested, heat halved
    sta weapon
    lda #ENERGY_MAX
    sta energy
    lsr heat
    ldx #FINE_INDEX
    jsr SubMoney
    bcs .paid
    lda #0
    sta money
    sta money+1
.paid
    lda #START_ROOM
    sta room
.teleport
    lda #PLAYER_X0
    sta p0x
    lda #PLAYER_Y0
    sta p0y
    lda #1
    sta hudDirty
    lda #PENDING_TELEPORT
    sta pending
    rts

; The jail screen (also used by bank 4 after losing to the police).
ShowJail
    SUBROUTINE
    lda #ENC_JAIL
    sta encKind
    jsr SetPortraits
    lda #STR_JAIL1
    ldx #STR_JAIL2
    ldy #ACT_JAIL_DONE
    ; fall through

; A / X = response lines, Y = ACT_* for CONTINUE.
ShowResponse
    SUBROUTINE
    sta encStr
    stx encStr+1
    sty encAction
    lda #STR_CONTINUE
    sta encStr+2
    lda #0
    sta encStr+3
    sta encStr+4
    sta encStr+5
    sta cursor
    lda #1
    sta nChoices
    sta hudDirty
    lda #PHASE_RESPONSE
    sta encPhase
    rts

; ---------------------------------------------------------------------------
; Outcomes
; ---------------------------------------------------------------------------

; Roll the outcome of the chosen line (row = kind * 4 + cursor) and apply it.
Outcome
    SUBROUTINE
    lda encKind
    asl
    asl
    ora cursor
    sta tcol                    ; row
    tax
    lda #0                      ; shift = followers * row shift (+ heat / 4)
    ldy followers
    beq .noFollowers
.perFollower
    clc
    adc RowFollowerShift,x
    dey
    bne .perFollower
.noFollowers
    sta ttmp
    lda RowHeatShift,x
    beq .noHeat
    lda heat
    lsr
    lsr
    clc
    adc ttmp
    sta ttmp
.noHeat
    jsr Random5                 ; roll + shift, clamped to 0-255
    clc
    adc ttmp
    bit ttmp
    bmi .negative
    bcc .rolled
    lda #255
    bne .rolled
.negative
    bcs .rolled
    lda #0
.rolled
    sta tLeft
    lda tcol                    ; thresholds at (row * 4 + temperament) * 3
    asl
    asl
    ora encTemp
    sta ttmp
    asl
    adc ttmp
    tay
    ldx tcol
    lda RowCount,x
    sta trow
    dec trow                    ; the last outcome takes the rest
    lda #0
    sta tRight
.threshold
    lda tRight
    cmp trow
    bcs .found
    lda tLeft
    cmp RowThresholds,y
    bcc .found
    iny
    inc tRight
    bne .threshold
.found
    lda RowFirst,x
    clc
    adc tRight
    tax                         ; X = outcome
    jsr AddMoney
    lda energy
    sec
    sbc OutEnergy,x
    bcs .energy
    lda #0
.energy
    sta energy
    lda heat
    clc
    adc OutHeat,x
    bcc .heat
    lda #255
.heat
    sta heat
    lda OutFlags,x
    sta ttmp
    and #OUT_SHELTER
    beq .noShelter
    lda shelters
    cmp #4
    bcs .noShelter
    inc shelters
.noShelter
    lda ttmp
    and #OUT_LEAVE
    beq .notLeave
    lda #PENDING_RESUME
    sta pending
    rts
.notLeave
    lda ttmp
    and #OUT_COMBAT
    beq .respond
    lda #PENDING_FIGHT
    sta pending
    rts
.respond
    ldy #ACT_CITY
    lda ttmp
    and #OUT_OUTSKIRTS
    beq .show
    ldy #ACT_OUTSKIRTS
.show
    lda OutLine2,x
    sta tRight
    lda OutLine1,x
    ldx tRight
    jmp ShowResponse

; money += outcome X's amount (BCD), capped at $99.99. Preserves X.
AddMoney
    SUBROUTINE
    sed
    clc
    lda money+1
    adc OutMoneyLo,x
    sta money+1
    lda money
    adc OutMoneyHi,x
    sta money
    cld
    bcc .done
    lda #$99
    sta money
    sta money+1
.done
    rts

; money -= FoodPrice X (BCD). Carry clear (and money unchanged) if short.
SubMoney
    SUBROUTINE
    sed
    sec
    lda money+1
    sbc FoodPriceLo,x
    sta ttmp
    lda money
    sbc FoodPriceHi,x
    cld
    bcc .short
    sta money
    lda ttmp
    sta money+1
.short
    rts

; Food menu: buy, feed the crew, or leave.
FoodChoice
    SUBROUTINE
    ldx cursor
    cpx #3
    bne .notLeave
    lda #PENDING_RESUME
    sta pending
    rts
.notLeave
    cpx #2
    bne .buy
    ldy followers               ; feed the crew: price per follower
    bne .feed
    lda #STR_NO_CREW1
    ldx #STR_NO_CREW2
    ldy #ACT_FOOD
    jmp ShowResponse
.feed
    lda money                   ; pay one share per follower, or nothing
    pha
    lda money+1
    pha
.share
    jsr SubMoney
    bcc .cantFeed
    dey
    bne .share
    pla
    pla
    jmp .bought
.cantFeed
    pla
    sta money+1
    pla
    sta money
    jmp .broke
.buy
    jsr SubMoney
    bcc .broke
    lda energy
    clc
    adc FoodEnergy,x
    bcs .full
    cmp #ENERGY_MAX+1
    bcc .ate
.full
    lda #ENERGY_MAX
.ate
    sta energy
.bought
    lda #STR_BOUGHT1
    ldx #STR_BOUGHT2
    ldy #ACT_FOOD
    jmp ShowResponse
.broke
    lda #STR_BROKE1
    ldx #STR_BROKE2
    ldy #ACT_FOOD
    jmp ShowResponse

    RANDOM_SUB Random5
    FIRE_PRESSED_SUB FirePressed5

; portrait for each encounter kind: homeless, police, passerby, food, jail
PortraitGfxLo
    .byte <HomelessSideGfx, <CopSideGfx, <PasserbySideGfx, <PasserbySideGfx, <CopSideGfx
PortraitGfxHi
    .byte >HomelessSideGfx, >CopSideGfx, >PasserbySideGfx, >PasserbySideGfx, >CopSideGfx
PortraitColLo
    .byte <HomelessSideCol, <CopSideCol, <PasserbySideCol, <PasserbySideCol, <CopSideCol
PortraitColHi
    .byte >HomelessSideCol, >CopSideCol, >PasserbySideCol, >PasserbySideCol, >CopSideCol

    include "generated/bank5_data.asm"

    ECHO "Bank 5 free:", ($FFE0 - *)d, "bytes"
    BANK_END 5
