; Bank 4: side-view fights (attacking a cop, or robbing a passerby).
;
;   line  0        blank (screen on)
;   lines 1-10     "FIGHT!" in playfield
;   lines 13-18    energy bars, playfield score mode: yours (left) in your
;                  color, theirs (right) in theirs
;   lines 21-92    night sky and skyline (36 pairs)
;   lines 93-152   the fighters (30 rows of 2 lines), double width; on the
;                  arm rows the ball is your pipe/bat/board, missile 1 their
;                  swing
;   lines 153-156  sidewalk
;   lines 176-185  footer: weapon and crew
;
; Controls: left/right move, fire swings, down blocks (takes a quarter of
; the damage). Your energy bar is your real energy: food matters.

FIGHT_X0     = 32       ; starting positions
FIGHT_X1     = 104
FIGHT_XMIN   = 16
FIGHT_GAP    = 20       ; closest the fighters can stand
REACH        = 26       ; a swing lands if the gap is smaller than this
SWING_FRAMES = 16
STRIKE_FRAME = 8        ; frame of the swing that hits (counting down)
HIT_FRAMES   = 4
END_FRAMES   = 60       ; pause on the result before the response screen
ARM_LO       = 15       ; arm rows (row 29 = top of the portraits)
ARM_HI       = 16
LOST_ENERGY  = 28       ; energy left after losing a fight

    BANK_START 4

    include "kernel.h"

; ---------------------------------------------------------------------------
; Setup (far, from bank 0 overscan): opponent from encKind / encTemp
; ---------------------------------------------------------------------------
FightInit
    SUBROUTINE
    lda encKind
    sec
    sbc #ENC_POLICE
    sta foe
    tax
    lda FoeHP,x
    clc
    adc encTemp                 ; angrier people are tougher
    sta foeHP
    lda #FIGHT_X0
    sta fx0
    lda #FIGHT_X1
    sta fx1
    lda #0
    sta plAtk
    sta foeAtk
    sta hitFlash
    sta blocking
    sta fightEnd
    sta fightWon
    lda #40
    sta foeCool
    lda #<FightPlayerGfx
    sta encP0g
    lda #>FightPlayerGfx
    sta encP0g+1
    lda #<FightPlayerCol
    sta encP0c
    lda #>FightPlayerCol
    sta encP0c+1
    lda FoeGfxLo,x
    sta encP1g
    lda FoeGfxHi,x
    sta encP1g+1
    lda FoeColLo,x
    sta encP1c
    lda FoeColHi,x
    sta encP1c+1
    jsr FightVisuals
    lda #SCREEN_FIGHT
    sta screen
    jmp BankReturn4

; ---------------------------------------------------------------------------
; Each frame (far, VBLANK)
; ---------------------------------------------------------------------------
FightLogic
    SUBROUTINE
    lda fightEnd
    beq .fighting
    dec fightEnd
    bne .show
    jsr FightOver
    jmp BankReturn4
.show
    jsr FightVisuals
    jmp BankReturn4
.fighting
    jsr FirePressed4
    bcc .noSwing
    lda plAtk
    bne .noSwing
    lda #SWING_FRAMES
    sta plAtk
.noSwing
    lda #0
    sta blocking
    lda SWCHA
    sta joy
    and #$20                    ; down: block (and stand still)
    bne .notDown
    inc blocking
    bne .moved
.notDown
    lda joy
    bmi .notRight
    lda fx0
    clc
    adc #FIGHT_GAP
    cmp fx1
    bcs .notRight
    inc fx0
.notRight
    lda joy
    and #$40
    bne .moved
    lda fx0
    cmp #FIGHT_XMIN+1
    bcc .moved
    dec fx0
.moved
    lda plAtk                   ; your swing
    beq .foeTurn
    dec plAtk
    lda plAtk
    cmp #STRIKE_FRAME
    bne .foeTurn
    jsr InReach
    bcc .foeTurn
    lda #0                      ; each follower adds 1, if the crew is fed
    ldx SC_R+SC_HUNGER
    cpx #HUNGRY_AT
    bcs .hungry
    lda followers
.hungry
    ldx weapon
    sec                         ; +1: fists hit for 1
    adc WeaponDamage,x
    sta ttmp
    lda foeHP
    sec
    sbc ttmp
    bcs .foeHurt
    lda #0
.foeHurt
    sta foeHP
    lda #HIT_FRAMES
    sta hitFlash
    lda #SFX_HIT
    sta SC_W+SC_SFX
.foeTurn
    lda foeAtk                  ; their swing
    beq .foeIdle
    dec foeAtk
    lda foeAtk
    cmp #STRIKE_FRAME
    bne .checkEnd
    jsr InReach
    bcc .checkEnd
    ldx foe
    lda encTemp
    asl
    clc
    adc FoeDamage,x             ; angrier people hit harder
    ldy blocking
    beq .fullHit
    lsr
    lsr
.fullHit
    sta ttmp
    lda energy
    sec
    sbc ttmp
    bcs .youHurt
    lda #0
.youHurt
    sta energy
    lda #HIT_FRAMES
    sta hitFlash
    lda #SFX_HIT
    sta SC_W+SC_SFX
    bne .checkEnd
.foeIdle
    lda fx1                     ; close in, then wind up
    sec
    sbc fx0
    cmp #REACH
    bcc .close
    ldx foe
    lda frame
    and FoeStepMask,x
    bne .checkEnd
    dec fx1
    bne .checkEnd
.close
    dec foeCool
    bne .checkEnd
    lda #SWING_FRAMES
    sta foeAtk
    jsr Random4
    and #31
    clc
    adc #24
    sta foeCool
.checkEnd
    lda foeHP
    bne .foeStands
    lda #1
    sta fightWon
    bne .over
.foeStands
    lda energy
    bne .visuals
    sta fightWon
.over
    lda #END_FRAMES
    sta fightEnd
.visuals
    jsr FightVisuals
    jmp BankReturn4

; Carry set if the fighters are close enough for a swing to land.
InReach
    SUBROUTINE
    lda fx1
    sec
    sbc fx0
    cmp #REACH
    lda #0
    rol                         ; carry clear = in reach
    eor #1
    lsr
    rts

; Background flash, weapon visibility and both energy bars.
FightVisuals
    SUBROUTINE
    lda #COL_FIGHT_ROAD
    ldx hitFlash
    beq .bk
    dec hitFlash
    lda #COL_HIT
.bk
    sta fightBK
    ldx #0                      ; the pipe shows in the second half of a swing
    lda plAtk
    beq .ball
    cmp #STRIKE_FRAME+1
    bcs .ball
    ldx #2
.ball
    stx ballOn
    ldx #0
    lda foeAtk
    beq .baton
    cmp #STRIKE_FRAME+1
    bcs .baton
    ldx #2
.baton
    stx batonOn
    lda energy                  ; your bar: energy / 14 blocks
    ldy #0
.div14
    cmp #14
    bcc .yours
    sbc #14
    iny
    bne .div14
.yours
    lda BarLeftPF0,y
    sta barYou
    lda BarLeftPF1,y
    sta barYou+1
    lda BarLeftPF2,y
    sta barYou+2
    ldy foeHP                   ; theirs: one block per hit point
    lda BarRightPF0,y
    sta barFoe
    lda BarRightPF1,y
    sta barFoe+1
    lda BarRightPF2,y
    sta barFoe+2
    rts

; The fight is over: hand over to the encounter screen with the result.
FightOver
    SUBROUTINE
    lda fightWon
    beq .lost
    lda foe
    bne .robbed
    lda #STR_FLED1              ; beat a cop: you got away
    ldx #STR_FLED2
    ldy #ACT_CITY
    jmp .respond
.robbed                         ; beat a passerby: their cash
    sed
    clc
    lda money+1
    adc #ROB_CASH_LO
    sta money+1
    lda money
    adc #ROB_CASH_HI
    sta money
    cld
    bcc .cash
    lda #$99
    sta money
    sta money+1
.cash
    lda #STR_TOOK_CASH1
    ldx #STR_TOOK_CASH2
    ldy #ACT_CITY
    jmp .respond
.lost
    lda #LOST_ENERGY
    sta energy
    lda foe
    bne .theyFled
    lda #STR_ARREST1            ; lost to a cop: arrested
    ldx #STR_ARREST2
    ldy #ACT_JAIL
    jmp .respond
.theyFled                       ; lost a robbery: they run, maybe to a cop
    jsr Random4
    ldy #ACT_CITY
    cmp #CALLS_COPS
    bcs .noCops
    ldy #ACT_JAIL
.noCops
    lda #STR_THEY_FLED1
    ldx #STR_THEY_FLED2
.respond
    sta encStr
    stx encStr+1
    sty encAction
    lda #STR_CONTINUE
    sta encStr+2
    lda #0
    sta encStr+3
    sta encStr+4
    sta encStr+5
    sta cursor
    lda #1
    sta nChoices
    sta hudDirty
    lda #PHASE_RESPONSE
    sta encPhase
    lda #<PlayerSideGfx         ; encounter portraits (bank 2)
    sta encP0g
    lda #>PlayerSideGfx
    sta encP0g+1
    lda #<PlayerSideCol
    sta encP0c
    lda #>PlayerSideCol
    sta encP0c+1
    ldx foe
    lda EncFoeGfxLo,x
    sta encP1g
    lda EncFoeGfxHi,x
    sta encP1g+1
    lda EncFoeColLo,x
    sta encP1c
    lda EncFoeColHi,x
    sta encP1c+1
    lda SWCHA
    sta joyPrev
    lda #SCREEN_ENCOUNTER
    sta screen
    rts

; ---------------------------------------------------------------------------
; Kernel
; ---------------------------------------------------------------------------
FightKernel
    SUBROUTINE
    sta WSYNC               ; setup line 1 (sprites positioned in VBLANK)
    lda #5                  ; double-width fighters
    sta NUSIZ0
    lda #$25                ; ... and a 4-pixel missile 1
    sta NUSIZ1
    lda #8
    sta REFP1               ; the opponent faces you
    lda #0
    sta REFP0
    sta VDELP0
    sta VDELP1
    sta GRP0
    sta GRP1
    sta ENABL
    sta ENAM1
    sta CTRLPF
    sta COLUBK
    sta WSYNC               ; setup line 2
    lda #COL_FIGHT_HDR
    sta COLUPF
    sta WSYNC               ; setup line 3
    sta WSYNC               ; setup line 4
    sta HMCLR

    sta WSYNC               ; line 0
    lda #0
    sta VBLANK

    ldx #0                  ; header: 5 rows x 2 lines
.hdrRow
    ldy #2
.hdrLine
    sta WSYNC
    lda FightPF0L,x
    sta PF0                 ;  7
    lda FightPF1L,x
    sta PF1                 ; 14
    lda FightPF2L,x
    sta PF2                 ; 21
    SLEEP 7                 ; 28
    lda FightPF0R,x
    sta PF0                 ; 35
    lda FightPF1R,x
    sta PF1                 ; 42
    SLEEP 2
    lda FightPF2R,x
    sta PF2                 ; 51
    dey
    bne .hdrLine
    inx
    cpx #5
    bne .hdrRow

    sta WSYNC               ; 11: score mode for the bars
    lda #0
    sta PF0
    sta PF1
    sta PF2
    lda #2
    sta CTRLPF
    lda #COL_BAR_YOU
    sta COLUP0
    lda #COL_BAR_FOE
    sta COLUP1
    sta WSYNC               ; 12
    ldx #6
.bar
    sta WSYNC               ; 13-18
    lda barYou
    sta PF0                 ;  6
    lda barYou+1
    sta PF1                 ; 12
    lda barYou+2
    sta PF2                 ; 18
    lda barFoe              ; 21
    SLEEP 7                 ; 28
    sta PF0                 ; 31  (28-49)
    lda barFoe+1            ; 34
    SLEEP 5                 ; 39
    sta PF1                 ; 42  (39-54)
    lda barFoe+2            ; 45
    SLEEP 4                 ; 49
    sta PF2                 ; 52  (49-65)
    dex
    bne .bar
    sta WSYNC               ; 19
    lda #0
    sta PF0
    sta PF1
    sta PF2
    lda #1                  ; mirrored skyline
    sta CTRLPF
    lda #COL_SKYLINE
    sta COLUPF
    sta WSYNC               ; 20

    ldx #0                  ; sky: line A background, line B skyline
.sky
    sta WSYNC
    lda SkyBK,x
    sta COLUBK
    sta WSYNC
    lda SkyPF0,x
    sta PF0
    lda SkyPF1,x
    sta PF1
    lda SkyPF2,x
    sta PF2
    inx
    cpx #FIGHT_SKY_PAIRS
    bne .sky

    ; fighters. First line: road, no playfield, ball 8 pixels wide.
    ldy #29
    sta WSYNC
    lda fightBK
    sta COLUBK              ;  6
    lda #0
    sta PF0
    sta PF1
    sta PF2                 ; 17
    lda #$30
    sta CTRLPF              ; 22
    lda #COL_PIPE
    sta COLUPF              ; 27
    jmp .fighterRow
.fighters
    sta WSYNC
.fighterRow
    lda (encP0g),y
    sta GRP0                ;  8
    lda (encP0c),y
    sta COLUP0              ; 16
    lda (encP1g),y
    sta GRP1                ; 24
    lda (encP1c),y
    sta COLUP1              ; 32
    sta WSYNC
    ldx #0                  ; arm rows: pipe and baton
    cpy #ARM_HI+1
    bcs .armOff
    cpy #ARM_LO
    bcc .armOff
    lda ballOn
    sta ENABL
    lda batonOn
    sta ENAM1
    jmp .armDone
.armOff
    stx ENABL
    stx ENAM1
.armDone
    dey
    bpl .fighters

    sta WSYNC               ; 153-156 sidewalk
    lda #0
    sta GRP1                ; GRP1, GRP0, GRP1: empties both VDEL copies too
    sta GRP0
    sta GRP1
    lda #COL_SIDEWALK
    sta COLUBK
    sta WSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC               ; 157
    lda #0
    sta COLUBK
    sta CTRLPF
    sta REFP1
    TEXT_SETUP PosObject4, COL_FOOTER  ; 158-160
    sta WSYNC               ; 161
    sta HMCLR
    ldx #14
.gap
    sta WSYNC               ; 162-175
    dex
    bne .gap
    TEXT_KERNEL TXT1        ; 176-185
    sta WSYNC               ; 186
    TEXT_OFF
    ldx #6
.end
    sta WSYNC               ; 187-191, then the first overscan line
    dex
    bne .end
    jmp BankReturn4

    POS_OBJECT_SUB PosObject4
    RANDOM_SUB Random4
    FIRE_PRESSED_SUB FirePressed4

; opponents: police, passerby
FoeGfxLo
    .byte <FightCopGfx, <FightPasserbyGfx
FoeGfxHi
    .byte >FightCopGfx, >FightPasserbyGfx
FoeColLo
    .byte <FightCopCol, <FightPasserbyCol
FoeColHi
    .byte >FightCopCol, >FightPasserbyCol
EncFoeGfxLo                 ; their encounter portraits (bank 2)
    .byte <CopSideGfx, <PasserbySideGfx
EncFoeGfxHi
    .byte >CopSideGfx, >PasserbySideGfx
EncFoeColLo
    .byte <CopSideCol, <PasserbySideCol
EncFoeColHi
    .byte >CopSideCol, >PasserbySideCol
FoeStepMask                 ; walk every frame / every other frame
    .byte 0, 1

    include "generated/bank4_data.asm"

    ECHO "Bank 4 free:", ($FFE0 - *)d, "bytes"
    BANK_END 4
