; Bank 3: encounter text. Holds every screen line and composes line X of
; encStr into the bank 2 kernel's buffers (called through COMPOSE_STUBS).

    BANK_START 3

    include "kernel.h"

ComposeLineA
    SUBROUTINE
    ldy encStr,x
    lda StrLo,y
    sta textPtr
    lda StrHi,y
    sta textPtr+1
    COMPOSE_COLUMN TXTA, 0, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTA, 1, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTA, 2, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTA, 3, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTA, 4, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTA, 5, EncFontHi, EncFontLo
    rts

ComposeLineB
    SUBROUTINE
    ldy encStr,x
    lda StrLo,y
    sta textPtr
    lda StrHi,y
    sta textPtr+1
    COMPOSE_COLUMN TXTB, 0, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTB, 1, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTB, 2, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTB, 3, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTB, 4, EncFontHi, EncFontLo
    COMPOSE_COLUMN TXTB, 5, EncFontHi, EncFontLo
    rts

    include "generated/bank3_data.asm"

    ECHO "Bank 3 free:", ($FFC0 - *)d, "bytes"
    COMPOSE_STUBS 3
    BANK_END 3
