; Bank 2: encounter screen.
;
;   line  0       blank (screen on)
;   lines 1-10    header word (HOMELESS, POLICE, PASSERBY, FOOD, JAIL)
;   lines 11-70   scene: 30 rows of 2 lines, both portraits double width
;   lines 71-84   gap: sidewalk (3 lines), text players positioned, line 0
;                 composed
;   then six text lines (10 lines each) with 9-line gaps: 85, 104, 123,
;   142, 161, 180 - two speech lines, then up to four choices
;   lines 190-191 blank
;
; Six lines of text don't fit in SuperChip RAM, so each line is composed into
; one of two buffers (TXTA / TXTB) during the gap before it, by bank 3 (which
; holds the text) through COMPOSE_STUBS. The gaps are timed with the RIOT
; timer, so the line count never depends on the text.

TEXT_GAP     = 9                ; lines between text lines
CURSOR_X     = TEXT_X - 6       ; ball marks the selected choice

    BANK_START 2

    include "kernel.h"

    ; Start a timed gap: the TEXT_KERNEL that follows the matching GAP_END
    ; starts exactly {1} lines after this line began. Must be the first code
    ; after a WSYNC.
    MAC GAP_START       ; {1} = lines
        lda #(76 * ({1} - 1) + 24) / 8
        sta TIM8T       ; expires about 30 cycles into the gap's last line
    ENDM

    MAC GAP_END
.wait
        lda INTIM
        bne .wait
    ENDM

    ; One text line: gap with compose, then 10 lines of text.
    MAC TEXT_BLOCK      ; {1} = text line 0-5, {2} = compose, {3} = draw routine
        sta WSYNC
        GAP_START TEXT_GAP
        ldx #{1}
        jsr PrepareLine
        jsr {2}
        GAP_END
        jsr {3}
    ENDM

EncounterKernel
    SUBROUTINE
    sta WSYNC               ; setup line 1 (portraits positioned in VBLANK)
    lda #5                  ; double-width players
    sta NUSIZ0
    sta NUSIZ1
    lda #8
    sta REFP1               ; the other person faces the player
    lda #0
    sta REFP0
    sta VDELP0
    sta VDELP1
    sta GRP0
    sta GRP1
    sta ENABL
    sta CTRLPF
    sta COLUBK
    sta WSYNC               ; setup line 2
    ldx encKind
    lda HdrColor,x
    sta COLUPF
    lda HdrBase,x
    sta tLeft               ; first header row
    lda SceneBase,x
    sta tRight              ; first scene row
    lda SceneCtrl,x
    sta tcol                ; scene CTRLPF (header needs 0)
    sta WSYNC               ; setup line 3
    sta WSYNC               ; setup line 4
    sta HMCLR

    sta WSYNC               ; line 0
    lda #0
    sta VBLANK

    ; header: 5 rows x 2 lines, asymmetric playfield
    lda #5
    sta trow
    ldx tLeft
.hdrRow
    ldy #2
.hdrLine
    sta WSYNC
    lda HdrPF0L,x
    sta PF0                 ;  7
    lda HdrPF1L,x
    sta PF1                 ; 14
    lda HdrPF2L,x
    sta PF2                 ; 21
    SLEEP 7                 ; 28
    lda HdrPF0R,x
    sta PF0                 ; 35  (28-49)
    lda HdrPF1R,x
    sta PF1                 ; 42  (39-54)
    SLEEP 2
    lda HdrPF2R,x
    sta PF2                 ; 51  (49-65)
    dey
    bne .hdrLine
    inx
    dec trow
    bne .hdrRow

    ; scene: line A colors + portraits, line B playfield. The first pair is
    ; special: its line A clears the header playfield and switches CTRLPF
    ; (no time left on the header's last line), so the portraits' top row
    ; is drawn on line B only.
    ldx tRight              ; 67
    ldy #29                 ; 69
    sta WSYNC
    lda SceneBK,x
    sta COLUBK              ;  7
    lda #0
    sta PF0
    sta PF1
    sta PF2                 ; 16
    lda tcol
    sta CTRLPF              ; 22
    lda ScenePFC,x
    sta COLUPF              ; 29
    sta WSYNC
    lda ScenePF0,x
    sta PF0                 ;  7
    lda ScenePF1,x
    sta PF1                 ; 14
    lda ScenePF2,x
    sta PF2                 ; 21
    lda (encP0g),y
    sta GRP0                ; 29
    lda (encP0c),y
    sta COLUP0              ; 37
    lda (encP1g),y
    sta GRP1                ; 45
    lda (encP1c),y
    sta COLUP1              ; 53
    inx
    dey
.scene
    sta WSYNC
    lda SceneBK,x
    sta COLUBK              ;  7
    lda ScenePFC,x
    sta COLUPF              ; 14
    lda (encP0g),y
    sta GRP0                ; 22  (P0 starts at cycle ~37)
    lda (encP0c),y
    sta COLUP0              ; 30
    lda (encP1g),y
    sta GRP1                ; 38  (P1 starts at cycle ~56)
    lda (encP1c),y
    sta COLUP1              ; 46
    sta WSYNC
    lda ScenePF0,x
    sta PF0                 ;  7
    lda ScenePF1,x
    sta PF1                 ; 14
    lda ScenePF2,x
    sta PF2                 ; 21
    inx
    dey
    bpl .scene

    ; first gap: 14 lines. Its first three lines are the sidewalk; it also
    ; moves the players into text position and composes text line 0.
    sta WSYNC
    GAP_START 14
    lda SceneBK,x
    sta COLUBK
    lda #0
    sta GRP1                ; GRP1, GRP0, GRP1: empties both VDEL copies too
    sta GRP0
    sta GRP1
    sta PF0
    sta PF1
    sta PF2
    sta REFP1
    lda #TEXT_X
    ldx #0
    jsr PosObject2
    lda #TEXT_X+8
    ldx #1
    jsr PosObject2
    lda #CURSOR_X
    ldx #4
    jsr PosObject2
    sta WSYNC
    sta HMOVE
    lda #0
    sta COLUBK              ; sidewalk done (3 lines)
    lda #3
    sta NUSIZ0
    sta NUSIZ1
    lda #1
    sta VDELP0
    sta VDELP1
    lda #$20                ; ball 4 pixels wide
    sta CTRLPF
    lda #COL_SELECT
    sta COLUPF
    ldx #0
    jsr PrepareLine
    sta HMCLR
    jsr ComposeFarA2
    GAP_END
    jsr DrawTextA

    TEXT_BLOCK 1, ComposeFarB2, DrawTextB
    TEXT_BLOCK 2, ComposeFarA2, DrawTextA
    TEXT_BLOCK 3, ComposeFarB2, DrawTextB
    TEXT_BLOCK 4, ComposeFarA2, DrawTextA
    TEXT_BLOCK 5, ComposeFarB2, DrawTextB

    sta WSYNC               ; 190
    TEXT_OFF
    sta ENABL
    sta WSYNC               ; 191
    sta WSYNC               ; first overscan line
    jmp BankReturn2

; X = text line 0-5 (kept for the composer): clear the text players (the
; previous line's last glyph row, or the portraits' last row, must not show
; in the gap), set the line's color, and turn the cursor (ball) on for the
; selected choice.
PrepareLine
    SUBROUTINE
    lda #0
    sta GRP0
    sta GRP1
    sta GRP0                ; twice: VDEL keeps a delayed copy
    lda #COL_SPEECH
    ldy #0
    cpx #2
    bcc .set
    txa
    sbc #2
    cmp cursor
    bne .choice
    lda #COL_SELECT
    ldy #2
    bne .set
.choice
    lda #COL_CHOICE
.set
    sta COLUP0
    sta COLUP1
    sty ENABL
    rts

DrawTextA
    SUBROUTINE
    TEXT_KERNEL TXTA
    rts

DrawTextB
    SUBROUTINE
    TEXT_KERNEL TXTB
    rts

    POS_OBJECT_SUB PosObject2

HdrBase                     ; per encounter kind (ENC_*)
    .byte 0, 5, 10, 15, 20
SceneBase
    .byte 0, SCENE_PAIRS, SCENE_PAIRS * 2, SCENE_PAIRS * 3, SCENE_PAIRS * 4

    include "generated/bank2_data.asm"

    ECHO "Bank 2 free:", ($FFC0 - *)d, "bytes"
    COMPOSE_STUBS 2
    BANK_END 2
