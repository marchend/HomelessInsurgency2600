; Bank 0: startup, frame loop, game logic, text composer.

VB_TIMER    = 38        ; VBLANK lines before the kernel's setup lines
OS_TIMER    = 34        ; overscan lines

PLAYER_X0   = 76
PLAYER_Y0   = 52        ; bottom row inside the top street
X_MAX       = 152
Y_MAX       = 78 - PLAYER_H
SIGN_X      = 76
NPC_X_MIN   = 8         ; the HMOVE border hides x < 8
NPC_X_MAX   = 152
TALK_DX     = 10        ; how close (pixels) the player must be to talk
SIGN_NEAR_LO = 17       ; p0y range touching the middle band's building:
SIGN_NEAR_HI = 51       ;   bottom of street 1 or top of street 2
PORTRAIT_X0 = 44        ; encounter portraits
PORTRAIT_X1 = 100
ENERGY_MAX  = ENERGY_BLOCKS * 14
ENERGY_STEP = 31        ; moves per energy point (mask, power of two - 1)

    BANK_START 0

    include "kernel.h"

Start
    SUBROUTINE
    sei
    cld
    ldx #0
    txa
    tay
.clearRam
    dex
    txs
    pha
    bne .clearRam       ; clears TIA + RAM, leaves SP = $FF
    ldx #127
.clearSc
    sta SC_W,x
    dex
    bpl .clearSc
    lda INTIM
    ora #1
    sta rng             ; LFSR seed, never zero
    jsr TitleInit

; ---------------------------------------------------------------------------
; Frame loop: 3 VSYNC + 37 VBLANK + 192 visible + 30 overscan = 262 lines
; ---------------------------------------------------------------------------
MainLoop
    SUBROUTINE
    lda #2
    sta WSYNC
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC
    lda #VB_TIMER
    sta TIM64T
    inc frame
    jsr Random

    lda screen
    cmp #SCREEN_CITY
    beq .vbCity
    bcs .vbOther
    jsr TitleLogic
    jmp .vbPosition
.vbCity
    jsr CityLogic
    jmp .vbPosition
.vbOther
    cmp #SCREEN_FIGHT
    beq .vbFight
    CALL_FAR 5, EncounterLogic
    jmp .vbPosition
.vbFight
    CALL_FAR 4, FightLogic
.vbPosition             ; position sprites for whichever screen is next
    lda screen
    cmp #SCREEN_CITY
    beq .posCity
    bcc .vbWait
    cmp #SCREEN_FIGHT
    beq .posFight
    jsr PositionEncounterSprites
    jmp .vbWait
.posFight
    jsr PositionFightSprites
    jmp .vbWait
.posCity
    jsr PositionCitySprites
.vbWait
    lda INTIM
    bne .vbWait

    lda screen
    cmp #SCREEN_CITY
    beq .kCity
    bcs .kOther
    CALL_FAR 6, TitleKernel
    jmp .overscan
.kCity
    CALL_FAR 1, CityKernel
    jmp .overscan
.kOther
    cmp #SCREEN_FIGHT
    beq .kFight
    CALL_FAR 2, EncounterKernel
    jmp .overscan
.kFight
    CALL_FAR 4, FightKernel

.overscan
    lda #2
    sta VBLANK
    lda #OS_TIMER
    sta TIM64T
    lda pending
    beq .osScreen
    jsr HandlePending
    jmp .osWait
.osScreen
    lda screen
    cmp #SCREEN_CITY
    bne .osWait
    jsr CityOverscan
.osWait
    lda INTIM
    bne .osWait
    jmp MainLoop

; 8-bit Galois LFSR (taps $B8): period 255.
Random
    SUBROUTINE
    lda rng
    lsr
    bcc .noEor
    eor #$B8
.noEor
    sta rng
    rts

; ---------------------------------------------------------------------------
; Title
; ---------------------------------------------------------------------------
TitleInit
    SUBROUTINE
    lda #SCREEN_TITLE
    sta screen
    lda #<StrPressFire  ; compose into TXT1, then copy it to TXT2
    sta textPtr
    lda #>StrPressFire
    sta textPtr+1
    jsr ComposeText
    ldx #29
.copy
    lda SC_R+TXT1,x
    sta SC_W+TXT2,x
    dex
    bpl .copy
    lda #<StrAct1
    sta textPtr
    lda #>StrAct1
    sta textPtr+1
    jsr ComposeText
    lda #0
    sta firePrev        ; "pressed": a button held at power-on must be released first
    rts

TitleLogic
    SUBROUTINE
    ldx frame           ; reroll one homeless person's type per title frame,
.mod40                  ; so the types depend on when the player presses fire
    cpx #HOMELESS_COUNT
    bcc .roll
    txa
    sbc #HOMELESS_COUNT
    tax
    bcs .mod40
.roll
    lda rng
    and #3
    sta SC_W+SC_PEOPLE,x
    lda #0
    bit frame           ; blink PRESS FIRE every 32 frames
    bvs .dark
    lda #COL_PRESS_FIRE
.dark
    sta tcolor
    jsr FirePressed
    bcc .done
    lda #PENDING_START_CITY ; city setup is too slow for VBLANK: done in overscan
    sta pending
.done
    rts

; Carry set on the frame the fire button goes down.
FirePressed
    SUBROUTINE
    lda INPT4
    tax
    eor #$80            ; bit 7 = 1 when pressed now
    and firePrev        ; ... and not pressed last frame
    stx firePrev
    asl                 ; into carry
    rts

; ---------------------------------------------------------------------------
; City
; ---------------------------------------------------------------------------
CityInit
    SUBROUTINE
    lda #SCREEN_CITY
    sta screen
    lda #START_ROOM
    sta room
    lda #PLAYER_X0
    sta p0x
    lda #PLAYER_Y0
    sta p0y
    lda #ENERGY_MAX
    sta energy
    lda #0
    sta money
    sta money+1
    sta recruits
    sta heat
    sta weapon
    sta itemsTaken
    sta shelters
    sta followers
    sta CXCLR
    lda #1
    sta hudDirty        ; composing text is too slow for VBLANK
    jsr LoadRoom
    jsr SetEnergyBar
    jsr SetSpritePointers
    jmp SetSlotSprites

CityLogic
    SUBROUTINE
    lda SWCHA           ; P0 joystick: bit 7 right, 6 left, 5 down, 4 up (0 = pushed)
    sta joy
    ldx #0              ; X = moved flag
    asl joy
    bcs .notRight
    jsr MoveRight
.notRight
    asl joy
    bcs .notLeft
    jsr MoveLeft
.notLeft
    asl joy
    bcs .notDown
    jsr MoveDown
.notDown
    asl joy
    bcs .notUp
    jsr MoveUp
.notUp
    txa
    beq .still
    inc moveTick        ; walking burns energy
    lda moveTick
    and #ENERGY_STEP
    bne .still
    lda energy
    beq .still
    dec energy
.still
    lda frame           ; police heat cools down: 1 point per 64 frames
    and #63
    bne .warm
    lda heat
    beq .warm
    dec heat
.warm
    jsr SetEnergyBar
    jsr SetSpritePointers
    jsr FirePressed     ; fire next to someone (or something) interacts
    bcc .done
    jsr FindNpcAtPlayer
    bcc .done
    lda SC_R+SC_SLOT_KIND,x
    cmp #KIND_ITEM
    beq PickUp
    stx encSlot
    CALL_FAR 5, EncounterStart
.done
    rts

; X = slot holding a weapon: take it (replacing the one you carry).
PickUp
    SUBROUTINE
    ldy SC_R+SC_SLOT_PERSON,x   ; weapon number 1-3
    sty weapon
    lda itemsTaken
    ora ItemBit-1,y
    sta itemsTaken
    lda #KIND_NONE
    sta SC_W+SC_SLOT_KIND,x
    rts

ItemBit
    .byte 1, 2, 4

; Each move steps one unit and undoes it if the player would overlap a
; building; off the edge of the room it flips to the neighbouring room.
MoveRight
    SUBROUTINE
    inx
    lda p0x
    cmp #X_MAX
    bcs .edge
    inc p0x
    jsr HitsBuilding
    bcc .done
    dec p0x
.done
    rts
.edge
    lda room
    and #7
    cmp #7
    beq .done
    inc room
    lda #0
    sta p0x
    jmp LoadRoom

MoveLeft
    SUBROUTINE
    inx
    lda p0x
    beq .edge
    dec p0x
    jsr HitsBuilding
    bcc .done
    inc p0x
.done
    rts
.edge
    lda room
    and #7
    beq .done
    dec room
    lda #X_MAX
    sta p0x
    jmp LoadRoom

MoveUp
    SUBROUTINE
    inx
    lda p0y
    cmp #Y_MAX
    bcs .edge
    inc p0y
    jsr HitsBuilding
    bcc .done
    dec p0y
.done
    rts
.edge
    lda room
    cmp #8
    bcc .done
    sbc #8
    sta room
    lda #0
    sta p0y
    jmp LoadRoom

MoveDown
    SUBROUTINE
    inx
    lda p0y
    beq .edge
    dec p0y
    jsr HitsBuilding
    bcc .done
    inc p0y
.done
    rts
.edge
    lda room
    cmp #56
    bcs .done
    adc #8
    sta room
    lda #Y_MAX
    sta p0y
    jmp LoadRoom

; Carry set if the player's box overlaps a building in any band it touches.
; Bands: C = pairs 0-11, B = 30-47, A = 66-77. Preserves X.
HitsBuilding
    SUBROUTINE
    txa
    pha
    lda p0y
    clc
    adc #PLAYER_H-1
    sta tRight          ; top row
    ldy room
    lda p0y
    cmp #12
    bcs .notC
    lda RoomBandC,y
    jsr BandHit
    bcs .hit
.notC
    lda p0y
    cmp #48
    bcs .notB
    lda tRight
    cmp #30
    bcc .notB
    lda RoomBandB,y
    jsr BandHit
    bcs .hit
.notB
    lda tRight
    cmp #66
    bcc .miss
    lda RoomBandA,y
    jsr BandHit
    bcs .hit
.miss
    pla
    tax
    clc
    rts
.hit
    pla
    tax
    sec
    rts

; A = pattern index. Carry set if any column under p0x..p0x+7 is a building.
; Preserves Y.
BandHit
    SUBROUTINE
    sty tdst
    sta ttmp
    asl
    asl
    adc ttmp            ; pattern * 5 (carry clear: small index)
    sta tLeft
    lda p0x
    lsr
    lsr
    sta tcol            ; first column
    lda p0x
    clc
    adc #7
    lsr
    lsr
    sta trow            ; last column
.col
    lda tcol
    lsr
    lsr
    lsr
    clc
    adc tLeft
    tay
    lda tcol
    and #7
    tax
    lda PatBits,y
    and BitMask,x
    bne .yes
    lda tcol
    cmp trow
    beq .no
    inc tcol
    bne .col
.no
    ldy tdst
    clc
    rts
.yes
    ldy tdst
    sec
    rts

; Screen changes requested through `pending` (by bank 3, 4 or the title).
HandlePending
    SUBROUTINE
    lda pending
    ldx #PENDING_NONE
    stx pending
    cmp #PENDING_START_CITY
    bne .notStart
    jmp CityInit
.notStart
    cmp #PENDING_FIGHT
    bne .notFight
    CALL_FAR 4, FightInit
    jmp ComposeFightFooter
.notFight
    cmp #PENDING_TELEPORT
    bne .resume
    jsr LoadRoom
.resume
    lda #1
    sta hudDirty
    lda #SCREEN_CITY
    sta screen
    jsr SetSpritePointers
    jmp SetSlotSprites  ; the encounter / fight reused the slot pointers

; Fight footer "WEAPN CREW N" into TXT1 (the HUD is recomposed afterwards).
ComposeFightFooter
    SUBROUTINE
    lda weapon
    sta ttmp
    asl
    asl
    adc ttmp            ; weapon * 5
    tax
    ldy #0
.name
    lda WeaponGlyphs,x
    sta hudStr,y
    inx
    iny
    cpy #5
    bne .name
    ldx #0
.crew
    lda CrewGlyphs,x
    sta hudStr,y
    inx
    iny
    cpx #6
    bne .crew
    lda followers
    jsr DigitGlyph
    sta hudStr+11
    lda #<hudStr
    sta textPtr
    lda #>hudStr
    sta textPtr+1
    jmp ComposeText

; Overscan: the new room's NPCs (on a room change) or the HUD text (when it
; changed), then NPC movement and sprite setup for the next frame.
CityOverscan
    SUBROUTINE
    lda roomDirty
    beq .hud
    lda #0
    sta roomDirty
    jsr SetupRoomNpcs
    jmp .sprites
.hud
    lda hudDirty
    beq .sprites
    lda #0
    sta hudDirty
    jsr UpdateHud
.sprites
    jsr UpdateNpcs
    jmp SetSlotSprites

; Copy the current room's three building bands into pfA/pfB/pfC.
LoadRoom
    SUBROUTINE
    txa
    pha
    ldy room
    ldx #0              ; X = offset into pfA..pfC
    lda RoomBandA,y
    jsr .band
    lda RoomBandB,y
    jsr .band
    lda RoomBandC,y
    jsr .band
    lda #1
    sta roomDirty       ; NPCs are set up in overscan (too slow for VBLANK)
    lda #KIND_NONE      ; ... so the slots stay empty for this one frame
    ldx #4
.clearSlots
    sta SC_W+SC_SLOT_KIND,x
    dex
    bpl .clearSlots
    jsr SetSlotSprites
    pla
    tax
    rts
.band
    sty ttmp
    tay
    lda PatPF0,y
    sta pfA+0,x
    lda PatPF1,y
    sta pfA+1,x
    lda PatPF2,y
    sta pfA+2,x
    lda PatCtrl,y
    sta pfA+3,x
    lda ttmp            ; roof color: (map row + band) & 7
    lsr
    lsr
    lsr
    sta tLeft
    txa                 ; band index = X / 5 -> 0, 1, 2
    ldy #0
.div5
    cmp #5
    bcc .gotBand
    sbc #5
    iny
    bne .div5
.gotBand
    tya
    clc
    adc tLeft
    and #7
    tay
    lda BandColors,y
    sta pfA+4,x
    txa
    clc
    adc #5
    tax
    ldy ttmp
    rts

; Position P0 (player) and P1 (sign) during VBLANK: the divide loop takes
; longer for large x, and the VBLANK timer absorbs that.
PositionCitySprites
    SUBROUTINE
    lda p0x
    ldx #0
    jsr PosObject0
    lda SC_R+SC_SLOT_X  ; slot 0; slots 1-4 are positioned by the kernel
    ldx #1
    jsr PosObject0
    sta WSYNC
    sta HMOVE           ; the kernel does HMCLR
    rts

    POS_OBJECT_SUB PosObject0

; Point the kernel's sprite pointers at graphics minus the bottom row, so
; (ptr),y with Y = line pair reads the right row (zero padding elsewhere).
SetSpritePointers
    SUBROUTINE
    lda #<PlayerGfx
    sec
    sbc p0y
    sta p0gPtr
    lda #>PlayerGfx
    sbc #0
    sta p0gPtr+1
    lda #<PlayerCol
    sec
    sbc p0y
    sta p0cPtr
    lda #>PlayerCol
    sbc #0
    sta p0cPtr+1

    rts

; ---------------------------------------------------------------------------
; City NPCs: one per screen section ("slot"), see bank1_city.asm.
; ---------------------------------------------------------------------------

; Fill the five slots for the current room: placed homeless people, a sign
; in the middle band, random passersby and police in empty streets.
SetupRoomNpcs
    SUBROUTINE
    ldy room
    lda RoomBandA,y
    tax
    lda PatAlleyX,x
    sta tLeft
    lda RoomSlot0Person,y
    ldx #0
    jsr AlleySlot
    ldy room
    lda RoomSign,y
    beq .noSign
    sta SC_W+SC_SLOT_KIND+2     ; KIND_SHELTER / KIND_FOOD
    lda #SIGN_X
    sta SC_W+SC_SLOT_X+2
    lda #NO_PERSON
    sta SC_W+SC_SLOT_PERSON+2
    bne .slot4
.noSign
    lda RoomBandB,y
    tax
    lda PatAlleyX,x
    sta tLeft
    lda RoomItem,y      ; a weapon nobody has picked up yet?
    beq .noItem
    tax
    lda ItemBit-1,x
    and itemsTaken
    bne .noItem
    stx SC_W+SC_SLOT_PERSON+2
    lda #KIND_ITEM
    sta SC_W+SC_SLOT_KIND+2
    lda tLeft
    sta SC_W+SC_SLOT_X+2
    bne .slot4
.noItem
    ldy room
    lda RoomSlot2Person,y
    ldx #2
    jsr AlleySlot
.slot4
    ldy room
    lda RoomBandC,y
    tax
    lda PatAlleyX,x
    sta tLeft
    lda RoomSlot4Person,y
    ldx #4
    jsr AlleySlot
    ldy room
    lda RoomSlot1Person,y
    ldx #1
    jsr StreetSlot
    ldy room
    lda RoomSlot3Person,y
    ldx #3
    ; fall through

; A = person (or NO_PERSON), X = street slot: a homeless person walks here,
; otherwise a random passerby, police officer or nobody.
StreetSlot
    SUBROUTINE
    sta SC_W+SC_SLOT_PERSON,x
    cmp #NO_PERSON
    bne .homeless
    jsr Random
    cmp #64
    bcc .nobody
    cmp #192
    bcc .passerby
    lda #KIND_POLICE
    bne .kind
.passerby
    lda #KIND_PASSERBY
    bne .kind
.nobody
    lda #KIND_NONE
    beq .kind
.homeless
    lda #KIND_HOMELESS
.kind
    sta SC_W+SC_SLOT_KIND,x
    jsr Random
    and #127
    clc
    adc #16
    sta SC_W+SC_SLOT_X,x
    lda #1
    bit rng
    bpl .dir
    lda #$FF
.dir
    sta SC_W+SC_SLOT_DIR,x
    rts

; A = person (or NO_PERSON), X = band slot, tLeft = the band's alley x.
AlleySlot
    SUBROUTINE
    sta SC_W+SC_SLOT_PERSON,x
    cmp #NO_PERSON
    beq .empty
    lda #KIND_HOMELESS
    bne .kind
.empty
    lda #KIND_NONE
.kind
    sta SC_W+SC_SLOT_KIND,x
    lda tLeft
    sta SC_W+SC_SLOT_X,x
    lda #0
    sta SC_W+SC_SLOT_DIR,x      ; people in alleys stand still
    rts

; Street walkers take a step every other frame, turning at the edges and
; now and then at random.
UpdateNpcs
    SUBROUTINE
    lda frame
    lsr
    bcs .done
    ldx #1
    jsr .walk
    ldx #3
.walk
    lda SC_R+SC_SLOT_KIND,x
    cmp #KIND_HOMELESS
    bcc .done
    lda SC_R+SC_SLOT_X,x
    clc
    adc SC_R+SC_SLOT_DIR,x
    cmp #NPC_X_MIN
    bcc .turn
    cmp #NPC_X_MAX+1
    bcs .turn
    sta SC_W+SC_SLOT_X,x
    jsr Random
    cmp #2
    bcs .done
.turn
    lda #0
    sec
    sbc SC_R+SC_SLOT_DIR,x
    sta SC_W+SC_SLOT_DIR,x
.done
    rts

; Per slot: sprite pointers (kind's graphics minus the slot's bottom row)
; and, for slots 1-4, the kernel's reposition delay and fine motion
; (SlotCoarseTab / SlotFineTab, see tools/build_assets.py).
SetSlotSprites
    SUBROUTINE
    ldx #4
.slot
    stx tcol
    lda SC_R+SC_SLOT_KIND,x
    tay
    lda SlotY,x
    sta ttmp
    txa
    asl
    tax
    lda KindGfxLo,y
    sec
    sbc ttmp
    sta slotG,x
    lda KindGfxHi,y
    sbc #0
    sta slotG+1,x
    lda KindColLo,y
    sec
    sbc ttmp
    sta slotC,x
    lda KindColHi,y
    sbc #0
    sta slotC+1,x
    ldx tcol
    beq .next
    ldy SC_R+SC_SLOT_X,x
    lda SlotCoarseTab,y
    sta slotCoarse-1,x
    lda SlotFineTab,y
    sta slotHM-1,x
.next
    dex
    bpl .slot
    rts

; Carry set and X = slot if someone or something is close enough to use.
FindNpcAtPlayer
    SUBROUTINE
    ldx #4
.slot
    lda SC_R+SC_SLOT_KIND,x
    cmp #KIND_FOOD      ; food places, people and weapons (not shelters yet)
    bcc .next
    lda p0x
    sec
    sbc SC_R+SC_SLOT_X,x
    bcs .abs
    eor #$FF
    adc #1
.abs
    cmp #TALK_DX
    bcs .next
    lda SC_R+SC_SLOT_KIND,x
    cmp #KIND_HOMELESS
    bcs .person
    lda p0y             ; a sign: stand in the street next to its building
    cmp #SIGN_NEAR_LO
    bcc .next
    cmp #SIGN_NEAR_HI+1
    bcs .next
    sec
    rts
.person
    lda SlotY,x         ; rows overlap: p0y < slotY + 10 and slotY < p0y + 10
    clc
    adc #10
    cmp p0y
    beq .next
    bcc .next
    lda p0y
    clc
    adc #10
    cmp SlotY,x
    beq .next
    bcc .next
    sec
    rts
.next
    dex
    bpl .slot
    clc
    rts

; ---------------------------------------------------------------------------
; Encounter and fight sprites (their logic lives in banks 3 and 4)
; ---------------------------------------------------------------------------

PositionEncounterSprites
    SUBROUTINE
    lda #PORTRAIT_X0
    ldx #0
    jsr PosObject0
    lda #PORTRAIT_X1
    ldx #1
    jsr PosObject0
    sta WSYNC
    sta HMOVE           ; the kernel does HMCLR
    rts

; Fighters, the player's pipe (ball) and the opponent's swing (missile 1).
PositionFightSprites
    SUBROUTINE
    lda fx0
    ldx #0
    jsr PosObject0
    lda fx1
    ldx #1
    jsr PosObject0
    lda fx0
    clc
    adc #16
    ldx #4
    jsr PosObject0
    lda fx1
    sec
    sbc #4
    ldx #3
    jsr PosObject0
    sta WSYNC
    sta HMOVE           ; the kernel does HMCLR
    rts

; energy -> blocks (energy / 14) -> bar playfield bytes
SetEnergyBar
    SUBROUTINE
    lda energy
    ldy #0
.div14
    cmp #14
    bcc .gotBlocks
    sbc #14
    iny
    bne .div14
.gotBlocks
    lda BarPF0,y
    sta barPF
    lda BarPF1,y
    sta barPF+1
    lda BarPF2,y
    sta barPF+2
    rts

; HUD text "$DD.CC RR/??" composed into SuperChip buffer TXT1.
UpdateHud
    SUBROUTINE
    lda #GLYPH_DOLLAR
    sta hudStr+0
    lda money
    ldx #1
    jsr .bcd
    lda #GLYPH_DOT
    sta hudStr+3
    lda money+1
    ldx #4
    jsr .bcd
    lda #GLYPH_SPACE
    sta hudStr+6
    lda recruits
    ldx #7
    jsr .bcd
    lda #GLYPH_SLASH
    sta hudStr+9
    lda #GLYPH_QUESTION
    sta hudStr+10
    sta hudStr+11
    lda #<hudStr
    sta textPtr
    lda #>hudStr
    sta textPtr+1
    jmp ComposeText
.bcd                    ; A = BCD byte -> two digit glyphs at hudStr+X
    pha
    lsr
    lsr
    lsr
    lsr
    jsr .digit
    sta hudStr,x
    pla
    and #$0F
    jsr .digit
    sta hudStr+1,x
    rts
.digit
    ; fall through

; A = 0-9 -> glyph offset. Clobbers ttmp.
DigitGlyph
    sta ttmp
    asl
    asl
    adc ttmp            ; * 5 (carry clear: small values)
    adc #GLYPH_0
    rts

; Text composer: 12 glyph offsets at (textPtr) -> SuperChip buffer TXT1.
ComposeText
    SUBROUTINE
    COMPOSE_COLUMN TXT1, 0, FontHi, FontLo
    COMPOSE_COLUMN TXT1, 1, FontHi, FontLo
    COMPOSE_COLUMN TXT1, 2, FontHi, FontLo
    COMPOSE_COLUMN TXT1, 3, FontHi, FontLo
    COMPOSE_COLUMN TXT1, 4, FontHi, FontLo
    COMPOSE_COLUMN TXT1, 5, FontHi, FontLo
    rts

    include "generated/bank0_data.asm"

    ECHO "Bank 0 free:", ($FFE0 - *)d, "bytes"
    BANK_END 0
