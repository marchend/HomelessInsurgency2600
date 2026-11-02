; Bank 7: services far-called from bank 0.
;
;   ComposeTitle        title text into TXT1 / TXT2
;   UpdateHud           "$DD.CC RR/KK" into TXT1 (KK = "??" until you know anyone)
;   ComposeFightFooter  "WEAPN CREW N" into TXT1
;   SoundTick           every frame: plays the effect requested in SC_SFX
;                       (any bank sets it: lda #SFX_x / sta SC_W+SC_SFX)

    BANK_START 7

    include "kernel.h"

ComposeTitle
    SUBROUTINE
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
    jmp BankReturn7

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
    lda SC_R+SC_KNOWN
    bne .known
    lda #GLYPH_QUESTION
    sta hudStr+10
    sta hudStr+11
    jmp .compose
.known
    ldx #10
    jsr .bcd
.compose
    lda #<hudStr
    sta textPtr
    lda #>hudStr
    sta textPtr+1
    jsr ComposeText
    jmp BankReturn7
.bcd                    ; A = BCD byte -> two digit glyphs at hudStr+X
    pha
    lsr
    lsr
    lsr
    lsr
    jsr DigitGlyph
    sta hudStr,x
    pla
    and #$0F
    jsr DigitGlyph
    sta hudStr+1,x
    rts

; Footer for fights: weapon, and the crew that fights with you (only fed
; followers help).
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
    lda #0
    ldx SC_R+SC_HUNGER
    cpx #HUNGRY_AT
    bcs .hungry
    lda followers
.hungry
    jsr DigitGlyph
    sta hudStr+11
    lda #<hudStr
    sta textPtr
    lda #>hudStr
    sta textPtr+1
    jsr ComposeText
    jmp BankReturn7

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

; One step per call: start a requested effect, count down the current step,
; move to the next step; a step of 0 frames ends the effect.
SoundTick
    SUBROUTINE
    ldx SC_R+SC_SFX
    beq .playing
    lda #0
    sta SC_W+SC_SFX
    lda SfxFirst,x
    tax
    jsr .load
    jmp BankReturn7
.playing
    ldx SC_R+SC_SFX_POS
    beq .done
    lda SC_R+SC_SFX_TIME
    sec
    sbc #1
    sta SC_W+SC_SFX_TIME
    bne .done
    inx
    jsr .load
.done
    jmp BankReturn7
.load                   ; X = step
    stx SC_W+SC_SFX_POS
    lda SfxFrames,x
    beq .end
    sta SC_W+SC_SFX_TIME
    lda SfxTone,x
    sta AUDC0
    lda SfxPitch,x
    sta AUDF0
    lda SfxVol,x
    sta AUDV0
    rts
.end
    lda #0
    sta SC_W+SC_SFX_POS
    sta AUDV0
    rts

    include "generated/bank7_data.asm"

    ECHO "Bank 7 free:", ($FFE0 - *)d, "bytes"
    BANK_END 7
