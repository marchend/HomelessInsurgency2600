; Bank 0: startup, frame loop, game logic, text composer.

VB_TIMER    = 38        ; VBLANK lines before the kernel's setup lines
OS_TIMER    = 34        ; overscan lines

PLAYER_X0   = 76
PLAYER_Y0   = 52        ; bottom row inside the top street
X_MAX       = 152
Y_MAX       = 78 - PLAYER_H
SIGN_X      = 76
SIGN_Y      = 36        ; bottom row of a roof sign in the middle band
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
    bne .vbCity
    jsr TitleLogic
    jmp .vbWait
.vbCity
    jsr CityLogic
    jsr PositionCitySprites
.vbWait
    lda INTIM
    bne .vbWait

    lda screen
    bne .kCity
    CALL_FAR 6, TitleKernel
    jmp .overscan
.kCity
    CALL_FAR 1, CityKernel

.overscan
    lda #2
    sta VBLANK
    lda #OS_TIMER
    sta TIM64T
    lda screen
    beq .osWait
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
    lda #<StrAct1
    sta textPtr
    lda #>StrAct1
    sta textPtr+1
    lda #TXT1
    jsr ComposeText
    lda #<StrPressFire
    sta textPtr
    lda #>StrPressFire
    sta textPtr+1
    lda #TXT2
    jsr ComposeText
    lda #0
    sta firePrev        ; "pressed": a button held at power-on must be released first
    rts

TitleLogic
    SUBROUTINE
    lda #0
    bit frame           ; blink PRESS FIRE every 32 frames
    bvs .dark
    lda #COL_PRESS_FIRE
.dark
    sta tcolor
    jsr FirePressed
    bcc .done
    jsr CityInit
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
    sta CXCLR
    lda #1
    sta hudDirty        ; composing text is too slow for VBLANK
    jsr LoadRoom
    jsr SetEnergyBar
    jmp SetSpritePointers

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
    jsr SetEnergyBar
    jmp SetSpritePointers

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

; Overscan: recompose the HUD text when it changed.
CityOverscan
    SUBROUTINE
    lda hudDirty
    beq .done
    lda #0
    sta hudDirty
    jmp UpdateHud
.done
    rts

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
    lda p1x
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

    lda #SIGN_X
    sta p1x
    ldy room
    lda RoomSign,y
    beq .noSign
    cmp #1
    bne .food
    lda #<(ShelterGfx - SIGN_Y)
    sta p1gPtr
    lda #>(ShelterGfx - SIGN_Y)
    sta p1gPtr+1
    lda #<(ShelterCol - SIGN_Y)
    sta p1cPtr
    lda #>(ShelterCol - SIGN_Y)
    sta p1cPtr+1
    rts
.food
    lda #<(FoodGfx - SIGN_Y)
    sta p1gPtr
    lda #>(FoodGfx - SIGN_Y)
    sta p1gPtr+1
    lda #<(FoodCol - SIGN_Y)
    sta p1cPtr
    lda #>(FoodCol - SIGN_Y)
    sta p1cPtr+1
    rts
.noSign
    lda #<BlankGfx
    sta p1gPtr
    lda #>BlankGfx
    sta p1gPtr+1
    lda #<BlankCol
    sta p1cPtr
    lda #>BlankCol
    sta p1cPtr+1
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
    lda #CHAR_DOLLAR
    sta hudStr+0
    lda money
    ldx #1
    jsr .bcd
    lda #CHAR_DOT
    sta hudStr+3
    lda money+1
    ldx #4
    jsr .bcd
    lda #CHAR_SPACE
    sta hudStr+6
    lda recruits
    ldx #7
    jsr .bcd
    lda #CHAR_SLASH
    sta hudStr+9
    lda #CHAR_QUESTION
    sta hudStr+10
    sta hudStr+11
    lda #<hudStr
    sta textPtr
    lda #>hudStr
    sta textPtr+1
    lda #TXT1
    jmp ComposeText
.bcd                    ; A = BCD byte -> two digit codes at hudStr+X
    pha
    lsr
    lsr
    lsr
    lsr
    clc
    adc #CHAR_0
    sta hudStr,x
    pla
    and #$0F
    clc
    adc #CHAR_0
    sta hudStr+1,x
    rts

; ---------------------------------------------------------------------------
; Text composer: 12 char codes at (textPtr) -> 6 columns x 5 rows of
; two-glyph bytes in SuperChip RAM at offset A (TXT1 / TXT2).
; ---------------------------------------------------------------------------
ComposeText
    SUBROUTINE
    sta tdst
    lda #0
    sta tcol
.col
    lda tcol
    asl
    tay
    lda (textPtr),y
    jsr .times5
    sta tLeft
    iny
    lda (textPtr),y
    jsr .times5
    sta tRight
    ldx tdst
    lda #5
    sta trow
.row
    ldy tLeft
    lda FontHi,y
    ldy tRight
    ora FontLo,y
    sta SC_W,x
    inc tLeft
    inc tRight
    inx
    dec trow
    bne .row
    stx tdst
    inc tcol
    lda tcol
    cmp #6
    bne .col
    rts
.times5
    sta ttmp
    asl
    asl
    clc
    adc ttmp
    rts

    include "generated/bank0_data.asm"

    ECHO "Bank 0 free:", ($FFE0 - *)d, "bytes"
    BANK_END 0
