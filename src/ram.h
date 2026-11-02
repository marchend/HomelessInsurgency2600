; RAM map. Console RAM is $80-$FF (stack grows down from $FF);
; SuperChip RAM is 128 bytes at SC_W/SC_R (see macros.h).

    SEG.U VARS
    ORG $80

bankTarget  ds 2        ; far-call target (not at $xxFF: JMP (ind) bug)
frame       ds 1
screen      ds 1        ; SCREEN_TITLE / SCREEN_CITY
rng         ds 1
firePrev    ds 1        ; fire button last frame (bit 7, 0 = pressed)
joy         ds 1        ; joystick bits being processed this frame

; player
p0x         ds 1        ; pixel x
p0y         ds 1        ; bottom row, in line pairs from the bottom (0..)
room        ds 1        ; row * 8 + column
moveTick    ds 1

; current room: per building band PF0, PF1, PF2, CTRLPF, COLUPF
pfA         ds 5
pfB         ds 5
pfC         ds 5

; kernel sprite pointers (graphics/colors minus bottom row, see CityKernel)
p0gPtr      ds 2
p0cPtr      ds 2
p1gPtr      ds 2
p1cPtr      ds 2
p1x         ds 1

; stats
money       ds 2        ; BCD: dollars, cents
recruits    ds 1        ; BCD
energy      ds 1        ; 0..ENERGY_MAX
barPF       ds 3        ; energy bar PF0/PF1/PF2 (left half)
hudDirty    ds 1        ; nonzero: recompose the HUD text in overscan

; text
hudStr      ds 12       ; char codes for the HUD line
textPtr     ds 2
tcol        ds 1
ttmp        ds 1
tLeft       ds 1
tRight      ds 1
trow        ds 1
tdst        ds 1
tcolor      ds 1        ; title PRESS FIRE color (blinks)

RAM_END     ds 0
    ECHO "Console RAM free:", ($100 - RAM_END - 16)d, "bytes (16 kept for stack)"

; SuperChip buffers: 6 columns x 5 rows of composed 4px-glyph pairs
TXT1        = 0
TXT2        = 30

SCREEN_TITLE = 0
SCREEN_CITY  = 1
