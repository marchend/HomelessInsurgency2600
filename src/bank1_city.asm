; Bank 1: top-down city kernel.
;
; The map is 156 lines = 78 line pairs, Y counting down from 77 (top) to 0.
; Each pair is line A (background + P0) and line B (P1). Sprite pointers
; are pre-offset by the sprite's bottom row and padded with zero rows, so
; every pair just does lda (ptr),y.
;
;   slot 0  pairs 77-66  band A (buildings)
;   slot 1  pairs 65-48  street 1 (upper half, lane dashes at 56, lower half)
;   slot 2  pairs 47-30  band B (buildings)
;   slot 3  pairs 29-12  street 2 (lane dashes at 20)
;   slot 4  pairs 11-0   band C (buildings)
;
; P1 is shared: each slot (section) has its own pointers and x position.
; Slot 0 is positioned in VBLANK; the others on line B of their first
; pair, which therefore never shows P1. Every line starts with HMOVE so
; a mid-screen reposition is possible; that leaves the usual 8-pixel black
; HMOVE border on the left of the map.
;
; Building bands are mirrored or repeated (no mid-line playfield writes),
; so the playfield only changes on the first line of each section.
;
; Below the map: a 36-line HUD (text line + energy bar).

    BANK_START 1

    include "kernel.h"

    ; Line A of a normal pair.
    MAC LINE_A
        sta WSYNC
        sta HMOVE           ;  3
        lda CityBK,y
        sta COLUBK          ; 10
        lda (p0gPtr),y
        sta GRP0            ; 18
        lda (p0cPtr),y
        sta COLUP0          ; 26
        sta HMCLR           ; 29  (>= 24 cycles after HMOVE)
    ENDM

    ; Line B of every pair: P1 from slot {3}, then loop while Y != {2}.
    MAC LINE_B_LOOP         ; {1} = loop label, {2} = end pair, {3} = slot
        sta WSYNC
        sta HMOVE           ;  3
        lda (slotG+{3}*2),y
        sta GRP1            ; 11
        lda (slotC+{3}*2),y
        sta COLUP1          ; 19
        dey                 ; 21
        cpy #{2}            ; 23
        bne {1}             ; 26
    ENDM

    ; Line B of a section's first pair: move P1 to this slot's x.
    ; RESP1 lands at cycle 21 + 5 * coarse, then HMOVE on the next line
    ; applies the fine offset (coarse 1-10 covers x = 8-158).
    MAC REPOSITION_B        ; {1} = slot (1-4)
        sta WSYNC
        sta HMOVE           ;  3
        dey                 ;  5
        lda slotHM+{1}-1
        sta HMP1            ; 11
        ldx slotCoarse+{1}-1 ; 14
.wait
        dex
        bpl .wait           ; 18 + 5 * coarse
        sta RESP1           ; 21 + 5 * coarse (<= 71), next WSYNC by 76
    ENDM

    ; First line A of a building band: new playfield from zero page {1}.
    MAC BAND_START
        sta WSYNC
        sta HMOVE           ;  3
        lda {1}+4
        sta COLUPF          ;  9
        lda {1}+0
        sta PF0             ; 15
        lda {1}+1
        sta PF1             ; 21
        lda {1}+2
        sta PF2             ; 27
        lda {1}+3
        sta CTRLPF          ; 33
        lda CityBK,y
        sta COLUBK          ; 40
        lda (p0gPtr),y
        sta GRP0            ; 48
        lda (p0cPtr),y
        sta COLUP0          ; 56
        lda #0
        sta GRP1            ; 61  previous slot's sprite off
        sta HMCLR           ; 64
    ENDM

    ; First line A of a street section: empty playfield or lane dashes.
    MAC STREET_START        ; {1} = PF0, {2} = PF1, {3} = PF2, {4} = clear P1
        sta WSYNC
        sta HMOVE           ;  3
        lda #COL_DASH
        sta COLUPF          ;  8
        lda #{1}
        sta PF0             ; 13
        lda #{2}
        sta PF1             ; 18
        lda #{3}
        sta PF2             ; 23
        lda #0
        sta CTRLPF          ; 28
        IF {4}
        sta GRP1            ; 31
        ENDIF
        lda CityBK,y
        sta COLUBK          ; 38
        lda (p0gPtr),y
        sta GRP0            ; 46
        lda (p0cPtr),y
        sta COLUP0          ; 54
        sta HMCLR           ; 57
    ENDM

CityKernel
    SUBROUTINE
    sta WSYNC               ; setup line 1 (P0, slot 0 P1 positioned in VBLANK)
    sta WSYNC               ; setup line 2
    sta WSYNC               ; setup line 3
    lda #0
    sta NUSIZ0
    sta NUSIZ1
    sta VDELP0
    sta VDELP1
    sta REFP0
    sta REFP1
    sta GRP0
    sta GRP1
    lda pfA+0
    sta PF0
    lda pfA+1
    sta PF1
    lda pfA+2
    sta PF2
    lda pfA+3
    sta CTRLPF
    lda pfA+4
    sta COLUPF
    ldy #77
    sta WSYNC               ; setup line 4
    sta HMCLR

    ; line 0: screen on
    sta WSYNC
    sta HMOVE               ;  3
    lda #0
    sta VBLANK              ;  8
    lda CityBK,y
    sta COLUBK
    lda (p0gPtr),y
    sta GRP0
    lda (p0cPtr),y
    sta COLUP0
    sta HMCLR               ; 34
    jmp Ck_aB

Ck_aLoop
    LINE_A
Ck_aB
    LINE_B_LOOP Ck_aLoop, 65, 0

    ; street 1 (slot 1)
    STREET_START 0, 0, 0, 1
    REPOSITION_B 1
Ck_s1aLoop
    LINE_A
    LINE_B_LOOP Ck_s1aLoop, 56, 1

    STREET_START DASH_PF0, DASH_PF1, DASH_PF2, 0
    LINE_B_LOOP Ck_never1, 55, 1    ; one pair: always falls through
Ck_never1

    STREET_START 0, 0, 0, 0
    jmp Ck_s1bB
Ck_s1bLoop
    LINE_A
Ck_s1bB
    LINE_B_LOOP Ck_s1bLoop, 47, 1

    ; band B (slot 2)
    BAND_START pfB
    REPOSITION_B 2
Ck_bLoop
    LINE_A
    LINE_B_LOOP Ck_bLoop, 29, 2

    ; street 2 (slot 3)
    STREET_START 0, 0, 0, 1
    REPOSITION_B 3
Ck_s2aLoop
    LINE_A
    LINE_B_LOOP Ck_s2aLoop, 20, 3

    STREET_START DASH_PF0, DASH_PF1, DASH_PF2, 0
    LINE_B_LOOP Ck_never2, 19, 3
Ck_never2

    STREET_START 0, 0, 0, 0
    jmp Ck_s2bB
Ck_s2bLoop
    LINE_A
Ck_s2bB
    LINE_B_LOOP Ck_s2bLoop, 11, 3

    ; band C (slot 4)
    BAND_START pfC
    REPOSITION_B 4
Ck_cLoop
    LINE_A
    LINE_B_LOOP Ck_cLoop, $FF, 4

; --- HUD: lines 156-191 ------------------------------------------------------
    sta WSYNC               ; 156
    lda #0
    sta GRP1                ; GRP1, GRP0, GRP1: empties both VDEL copies too
    sta GRP0
    sta GRP1
    sta PF0
    sta PF1
    sta PF2
    sta COLUBK
    sta CTRLPF
    sta HMCLR
    TEXT_SETUP PosObject1, COL_HUD  ; 157-159
    sta WSYNC               ; 160
    sta HMCLR
    sta WSYNC               ; 161
    sta WSYNC               ; 162
    sta WSYNC               ; 163
    TEXT_KERNEL TXT1        ; 164-173
    sta WSYNC               ; 174
    TEXT_OFF
    lda #COL_ENERGY
    sta COLUPF
    ldx #5
.gap
    sta WSYNC               ; 175-179
    dex
    bne .gap
    ldx #6
.bar
    sta WSYNC               ; 180-185: energy bar, left half only
    lda barPF               ;  3
    sta PF0                 ;  6
    lda barPF+1             ;  9
    sta PF1                 ; 12
    lda barPF+2             ; 15
    sta PF2                 ; 18
    lda #0                  ; 20
    SLEEP 8                 ; 28
    sta PF0                 ; 31
    SLEEP 8                 ; 39
    sta PF1                 ; 42
    SLEEP 6                 ; 48
    sta PF2                 ; 51
    dex
    bne .bar
    sta WSYNC               ; 186
    lda #0
    sta PF0
    sta PF1
    sta PF2
    ldx #6
.end
    sta WSYNC               ; 187-191, then the first overscan line
    dex
    bne .end
    jmp BankReturn1

    POS_OBJECT_SUB PosObject1

    include "generated/bank1_data.asm"

    ECHO "Bank 1 free:", ($FFE0 - *)d, "bytes"
    BANK_END 1
