; Bank 6: title screen. An asymmetric playfield picture from per-line tables
; (title letters + skyline) with two 12-character text lines.

    BANK_START 6

    include "kernel.h"

    ; One line of the playfield picture, Y = line, X = this line's background
    ; (loaded at the end of the previous line so it lands in HBLANK). Tables
    ; are page-aligned, so every load is 4 cycles and the right-half writes
    ; land in their windows.
    MAC TITLE_LINE
        stx COLUBK          ;  3
        lda TitlePFC,y
        sta COLUPF          ; 10
        lda TitlePF0L,y
        sta PF0             ; 17
        lda TitlePF1L,y
        sta PF1             ; 24
        lda TitlePF2L,y
        sta PF2             ; 31
        lda TitlePF0R,y
        sta PF0             ; 38  (28-49)
        lda TitlePF1R,y
        sta PF1             ; 45  (39-54)
        nop
        nop
        lda TitlePF2R,y
        sta PF2             ; 56  (49-65)
        ldx TitleBK+1,y     ; 60  next line's background
    ENDM

TitleKernel
    SUBROUTINE
    TEXT_SETUP PosObject6, COL_TITLE_TEXT   ; setup lines 1-3
    lda #0
    sta CTRLPF
    sta GRP0
    sta GRP1
    sta GRP0
    sta WSYNC               ; setup line 4
    sta HMCLR

    sta WSYNC               ; line 0 (blank in the tables): screen on
    lda #0
    sta VBLANK
    ldy #1
    ldx TitleBK+1
.top
    sta WSYNC
    TITLE_LINE
    iny
    cpy #TITLE_TEXT1_LINE
    bne .top

    TEXT_KERNEL TXT1        ; 86-95 "ACT I: RALLY"

    sta WSYNC               ; 96 (blank in the tables)
    lda #0
    sta GRP0
    sta GRP1
    sta GRP0
    lda tcolor
    sta COLUP0
    sta COLUP1
    ldy #TITLE_TEXT1_LINE + 11
    ldx TitleBK + TITLE_TEXT1_LINE + 11
.bottom
    sta WSYNC
    TITLE_LINE
    iny
    cpy #TITLE_LINES
    bne .bottom

    sta WSYNC               ; 178: clear playfield before the text
    lda #0
    sta PF0
    sta PF1
    sta PF2
    sta COLUBK
    TEXT_KERNEL TXT2        ; 179-188 "PRESS FIRE"
    sta WSYNC               ; 189
    TEXT_OFF
    sta WSYNC               ; 190
    sta WSYNC               ; 191
    sta WSYNC               ; first overscan line
    jmp BankReturn6

    POS_OBJECT_SUB PosObject6

    include "generated/bank6_data.asm"

    ECHO "Bank 6 free:", ($FFE0 - *)d, "bytes"
    BANK_END 6
