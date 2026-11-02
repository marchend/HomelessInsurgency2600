; Bank layout and bank-switching macros for the 32K F4SC cartridge.
;
; Every 4K bank is assembled at RORG $F000. Its first 256 bytes are the
; SuperChip RAM window (write $F000-$F07F, read $F080-$F0FF), so code starts
; at $F100. The last 32 bytes hold an identical stub in every bank:
;   $FFE0 BankCall   - X = target bank; jumps to (bankTarget) in that bank
;   $FFE6 BankReturn - switches back to bank 0 and RTSes to the caller
;   $FFEA Reset      - switches to bank 0 and jumps to Start
; Hotspots $FFF4-$FFFB select banks 0-7.

SC_W    = $F000         ; SuperChip write port
SC_R    = $F080         ; SuperChip read port
BANK0   = $FFF4         ; first bank-select hotspot

    MAC BANK_START      ; {1} = bank number
        ORG {1} * $1000
        RORG $F000
        ds 256, 0       ; SuperChip window: never code here
    ENDM

    MAC BANK_END        ; {1} = bank number
        ORG {1} * $1000 + $FE0
        RORG $FFE0
BankCall{1}
        lda BANK0,x
        jmp (bankTarget)
BankReturn{1}
        lda BANK0
        rts
Reset{1}
        lda BANK0
        jmp Start
        ORG {1} * $1000 + $FFC
        RORG $FFFC
        .word Reset{1}
        .word Reset{1}
    ENDM

    ; Call a routine in another bank from bank 0. The routine must end with
    ; `jmp BankReturn0`, which returns here in bank 0.
    MAC CALL_FAR        ; {1} = bank, {2} = routine
        lda #<{2}
        sta bankTarget
        lda #>{2}
        sta bankTarget+1
        ldx #{1}
        jsr BankCall0
    ENDM

    ; Busy-wait an exact number of cycles (2..9) without touching registers.
    MAC SLEEP           ; {1} = cycles
        IF {1} & 1
            bit $80     ; 3 cycles
            REPEAT ({1} - 3) / 2
                nop
            REPEND
        ELSE
            REPEAT {1} / 2
                nop
            REPEND
        ENDIF
    ENDM

    ; Routines several banks need their own copy of (no far call back to bank 0).

    ; 8-bit Galois LFSR (taps $B8): period 255. Returns the new value in A.
    MAC RANDOM_SUB      ; {1} = routine name
{1}
        lda rng
        lsr
        bcc .noEor
        eor #$B8
.noEor
        sta rng
        rts
    ENDM

    ; Carry set on the frame the fire button goes down. Clobbers A, X.
    MAC FIRE_PRESSED_SUB ; {1} = routine name
{1}
        lda INPT4
        tax
        eor #$80        ; bit 7 = 1 when pressed now
        and firePrev    ; ... and not pressed last frame
        stx firePrev
        asl             ; into carry
        rts
    ENDM

    ; Encounter text composer stubs, at the same address in banks 2 and 3:
    ; bank 2 jumps in, the code continues in bank 3 (which composes text line
    ; X into buffer A or B), then switches back and returns in bank 2.
    MAC COMPOSE_STUBS   ; {1} = bank
        ORG {1} * $1000 + $FC0
        RORG $FFC0
ComposeFarA{1}
        lda BANK0+3
        jsr ComposeLineA
        lda BANK0+2
        rts
ComposeFarB{1}
        lda BANK0+3
        jsr ComposeLineB
        lda BANK0+2
        rts
    ENDM
