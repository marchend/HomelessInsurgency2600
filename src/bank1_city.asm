; Bank 1: top-down city kernel.
;
; The map is 156 lines = 78 line pairs, Y counting down from 77 (top) to 0.
; Each pair is line A (background + P0) and line B (P1). Sprite pointers
; are pre-offset by the sprite's bottom row and padded with zero rows, so
; every pair just does lda (ptr),y.
;
;   pairs 77-66  band A (buildings)      pairs 29-21  street 2, upper half
;   pairs 65-57  street 1, upper half    pair  20     street 2 lane dashes
;   pair  56     street 1 lane dashes    pairs 19-12  street 2, lower half
;   pairs 55-48  street 1, lower half    pairs 11-0   band C (buildings)
;   pairs 47-30  band B (buildings)
;
; Building bands use a mirrored or repeated playfield (no mid-line writes),
; so the playfield only changes on the first line of each section.
;
; Below the map: a 36-line HUD (text line + energy bar).

    BANK_START 1

    include "kernel.h"

    ; Line A of a normal pair.
    MAC LINE_A
        sta WSYNC
        lda CityBK,y        ;  4
        sta COLUBK          ;  7
        lda (p0gPtr),y      ; 12
        sta GRP0            ; 15
        lda (p0cPtr),y      ; 20
        sta COLUP0          ; 23
    ENDM

    ; Line B of every pair, then loop while Y (next pair) != {2}.
    MAC LINE_B_LOOP
        sta WSYNC
        lda (p1gPtr),y      ;  5
        sta GRP1            ;  8
        lda (p1cPtr),y      ; 13
        sta COLUP1          ; 16
        dey                 ; 18
        cpy #{2}            ; 20
        bne {1}             ; 23
    ENDM

    ; First line A of a building band: new playfield from zero page {1}.
    MAC BAND_START
        sta WSYNC
        lda {1}+4
        sta COLUPF          ;  6
        lda {1}+0
        sta PF0             ; 12
        lda {1}+1
        sta PF1             ; 18
        lda {1}+2
        sta PF2             ; 24
        lda {1}+3
        sta CTRLPF          ; 30
        lda CityBK,y
        sta COLUBK          ; 37
        lda (p0gPtr),y
        sta GRP0            ; 45
        lda (p0cPtr),y
        sta COLUP0          ; 53
    ENDM

    ; First line A of a street section: empty playfield or lane dashes.
    MAC STREET_START        ; {1} = PF0, {2} = PF1, {3} = PF2
        sta WSYNC
        lda #COL_DASH
        sta COLUPF          ;  5
        lda #{1}
        sta PF0             ; 10
        lda #{2}
        sta PF1             ; 15
        lda #{3}
        sta PF2             ; 20
        lda #0
        sta CTRLPF          ; 25
        lda CityBK,y
        sta COLUBK          ; 32
        lda (p0gPtr),y
        sta GRP0            ; 40
        lda (p0cPtr),y
        sta COLUP0          ; 48
    ENDM

CityKernel
    SUBROUTINE
    sta WSYNC               ; setup line 1 (sprites were positioned in VBLANK)
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
    lda #0
    sta VBLANK
    jmp .aFirst

Ck_aLoop
    LINE_A
    jmp .aB
.aFirst
    lda CityBK,y
    sta COLUBK
    lda (p0gPtr),y
    sta GRP0
    lda (p0cPtr),y
    sta COLUP0
.aB
    LINE_B_LOOP Ck_aLoop, 65

    STREET_START 0, 0, 0
    jmp .s1aB
Ck_s1aLoop
    LINE_A
.s1aB
    LINE_B_LOOP Ck_s1aLoop, 56

    STREET_START DASH_PF0, DASH_PF1, DASH_PF2
    LINE_B_LOOP Ck_never1, 55   ; one pair: always falls through
Ck_never1

    STREET_START 0, 0, 0
    jmp .s1bB
Ck_s1bLoop
    LINE_A
.s1bB
    LINE_B_LOOP Ck_s1bLoop, 47

    BAND_START pfB
    jmp .bB
Ck_bLoop
    LINE_A
.bB
    LINE_B_LOOP Ck_bLoop, 29

    STREET_START 0, 0, 0
    jmp .s2aB
Ck_s2aLoop
    LINE_A
.s2aB
    LINE_B_LOOP Ck_s2aLoop, 20

    STREET_START DASH_PF0, DASH_PF1, DASH_PF2
    LINE_B_LOOP Ck_never2, 19
Ck_never2

    STREET_START 0, 0, 0
    jmp .s2bB
Ck_s2bLoop
    LINE_A
.s2bB
    LINE_B_LOOP Ck_s2bLoop, 11

    BAND_START pfC
    jmp .cB
Ck_cLoop
    LINE_A
.cB
    LINE_B_LOOP Ck_cLoop, $FF

; --- HUD: lines 156-191 ------------------------------------------------------
    sta WSYNC               ; 156
    lda #0
    sta GRP0
    sta GRP1
    sta PF0
    sta PF1
    sta PF2
    sta COLUBK
    sta CTRLPF
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
