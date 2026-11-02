; RAM map. Console RAM is $80-$FF (stack grows down from $FF);
; SuperChip RAM is 128 bytes at SC_W/SC_R (see macros.h).

    SEG.U VARS
    ORG $80

bankTarget  ds 2        ; far-call target (not at $xxFF: JMP (ind) bug)
frame       ds 1
screen      ds 1        ; SCREEN_TITLE / SCREEN_CITY / SCREEN_ENCOUNTER
rng         ds 1
firePrev    ds 1        ; fire button last frame (bit 7, 0 = pressed)
joy         ds 1        ; joystick bits being processed this frame
joyPrev     ds 1        ; last frame's SWCHA (menu edge detection)

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
slotG       ds 10       ; P1 graphics pointer per city section (slot 0-4)
slotC       ds 10       ; P1 color pointer per slot
slotCoarse  ds 4        ; slots 1-4: P1 reposition delay loop count
slotHM      ds 4        ; slots 1-4: P1 fine motion

; encounter screen (shares the city's slot pointers: never active together)
encP0g      = slotG
encP1g      = slotG+2
encP0c      = slotC
encP1c      = slotC+2
encStr      ds 6        ; string ids: 2 speech lines + 4 choices
encKind     ds 1        ; KIND_HOMELESS.. minus KIND_HOMELESS (0-2)
encTemp     ds 1        ; temperament 0-3
encSlot     ds 1
cursor      ds 1
nChoices    ds 1

; stats
money       ds 2        ; BCD: dollars, cents
recruits    ds 1        ; BCD
energy      ds 1        ; 0..ENERGY_MAX
barPF       ds 3        ; energy bar PF0/PF1/PF2 (left half)
hudDirty    ds 1        ; nonzero: recompose the HUD text in overscan
roomDirty   ds 1        ; nonzero: set up the room's NPCs in overscan
startCity   ds 1        ; nonzero: title overscan starts the city

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

; SuperChip RAM (offsets; read SC_R+n, write SC_W+n - never INC/DEC it)
TXT1        = 0         ; text buffers: 6 columns x 5 rows of glyph pairs
TXT2        = 30
TXTA        = TXT1      ; encounter double buffer
TXTB        = TXT2
SC_SLOT_KIND   = 60     ; 5 bytes: KIND_* per city slot
SC_SLOT_X      = 65     ; 5 bytes
SC_SLOT_PERSON = 70     ; 5 bytes: homeless id or NO_PERSON
SC_SLOT_DIR    = 75     ; 5 bytes: walk direction (1 / $FF)
SC_PEOPLE      = 80     ; 40 bytes, one per homeless person:
                        ;   bits 0-1 type (calm-rational, calm-irrational,
                        ;   angry-rational, angry-irrational)

SCREEN_TITLE     = 0
SCREEN_CITY      = 1
SCREEN_ENCOUNTER = 2

KIND_NONE     = 0
KIND_SHELTER  = 1
KIND_FOOD     = 2
KIND_HOMELESS = 3       ; KIND_HOMELESS and up are people you can talk to
KIND_POLICE   = 4
KIND_PASSERBY = 5
