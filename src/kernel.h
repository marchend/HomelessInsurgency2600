; Kernel building blocks shared by the screen banks.

TEXT_X      = 56        ; left edge of the 48-pixel text block
KERNEL_SETUP_LINES = 4  ; lines every kernel spends (VBLANK on) before line 0

    ; Position an object horizontally. A = x (0-159), X = object
    ; (0 P0, 1 P1, 2 M0, 3 M1, 4 BL). Starts with WSYNC; follow all calls
    ; with WSYNC + HMOVE, and HMCLR at least 24 cycles after HMOVE.
    MAC POS_OBJECT_SUB  ; {1} = routine name (one copy per bank)
{1}
        sec
        sta WSYNC
.divide
        sbc #15
        bcs .divide
        eor #7
        asl
        asl
        asl
        asl
        sta.wx HMP0,x
        sta RESP0,x
        rts
    ENDM

    ; One scanline of 12-character text from a SuperChip buffer, Y = glyph
    ; row (0-4). Players must be at TEXT_X / TEXT_X+8, NUSIZ 3 copies close,
    ; VDELP0/VDELP1 on. The four stores after cycle 42 must land at cycles
    ; 45, 48, 51, 54 to feed copies 2-3 of each player in time.
    MAC TEXT_LINE       ; {1} = buffer offset
        lda SC_R+{1}+0,y    ;  4
        sta GRP0            ;  7
        lda SC_R+{1}+5,y    ; 11
        sta GRP1            ; 14
        lda SC_R+{1}+10,y   ; 18
        sta GRP0            ; 21
        lda SC_R+{1}+25,y   ; 25
        sta ttmp            ; 28
        ldx SC_R+{1}+20,y   ; 32
        lda SC_R+{1}+15,y   ; 36
        sty trow            ; 39
        ldy ttmp            ; 42
        sta GRP1            ; 45
        stx GRP0            ; 48
        sty GRP1            ; 51
        sta GRP0            ; 54
        ldy trow            ; 57
    ENDM

    ; Ten scanlines: five glyph rows, each drawn twice. Clobbers A, X, Y.
    MAC TEXT_KERNEL     ; {1} = buffer offset
        ldy #0
.row
        sta WSYNC
        TEXT_LINE {1}
        sta WSYNC
        TEXT_LINE {1}
        iny
        cpy #5
        bne .row
    ENDM

    ; Turn the text players off again (two GRP0 writes flush VDEL).
    MAC TEXT_OFF
        lda #0
        sta GRP0
        sta GRP1
        sta GRP0
        sta VDELP0
        sta VDELP1
        sta NUSIZ0
        sta NUSIZ1
    ENDM

    ; Position both text players (3 lines) and set them up for TEXT_KERNEL.
    MAC TEXT_SETUP      ; {1} = PosObject routine, {2} = color
        lda #TEXT_X
        ldx #0
        jsr {1}
        lda #TEXT_X+8
        ldx #1
        jsr {1}
        sta WSYNC
        sta HMOVE
        lda #3
        sta NUSIZ0
        sta NUSIZ1
        lda #1
        sta VDELP0
        sta VDELP1
        lda #{2}
        sta COLUP0
        sta COLUP1
    ENDM

    ; Compose two characters of a 12-character line at (textPtr) into
    ; column {2} of SuperChip buffer {1}. The line holds glyph offsets
    ; (character code * 5); font tables {3}/{4} hold glyph rows in the high /
    ; low nibble. About 80 cycles per column.
    MAC COMPOSE_COLUMN  ; {1} = buffer, {2} = column 0-5, {3} = FontHi, {4} = FontLo
        ldy #{2} * 2
        lda (textPtr),y
        tax
        iny
        lda (textPtr),y
        tay
        lda {3}+0,x
        ora {4}+0,y
        sta SC_W+{1}+{2}*5+0
        lda {3}+1,x
        ora {4}+1,y
        sta SC_W+{1}+{2}*5+1
        lda {3}+2,x
        ora {4}+2,y
        sta SC_W+{1}+{2}*5+2
        lda {3}+3,x
        ora {4}+3,y
        sta SC_W+{1}+{2}*5+3
        lda {3}+4,x
        ora {4}+4,y
        sta SC_W+{1}+{2}*5+4
    ENDM
