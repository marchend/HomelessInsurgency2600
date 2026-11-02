; RAM map. Console RAM is $80-$FF (stack grows down from $FF);
; SuperChip RAM is 128 bytes at SC_W/SC_R (see macros.h).

    SEG.U VARS
    ORG $80

bankTarget  ds 2        ; far-call target (not at $xxFF: JMP (ind) bug)
frame       ds 1
screen      ds 1        ; SCREEN_*
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
p0nPtr      ds 2        ; NUSIZ0 per row: copies for the follower row
slotG       ds 10       ; P1 graphics pointer per city section (slot 0-4)
slotC       ds 10       ; P1 color pointer per slot
slotCoarse  ds 4        ; slots 1-4: P1 reposition delay loop count
slotHM      ds 4        ; slots 1-4: P1 fine motion

; Encounter and fight screens reuse the city's 28 slot bytes (slotG ..
; slotHM+3) for their own state; returning to the city recomputes them.
encP0g      = slotG     ; portrait pointers (encounter and fight)
encP1g      = slotG+2
encP0c      = slotC
encP1c      = slotC+2
fx0         = slotG+4   ; fight: player x
fx1         = slotG+5   ; fight: opponent x
foeHP       = slotG+6
plAtk       = slotG+7   ; frames left in the player's swing
foeAtk      = slotG+8   ; frames left in the opponent's swing
foeCool     = slotG+9   ; frames until the opponent swings again
hitFlash    = slotC+4   ; frames of red background after a hit
foe         = slotC+5   ; 0 police, 1 passerby
blocking    = slotC+6   ; nonzero while the player holds down
fightEnd    = slotC+7   ; frames left showing the result (0 = fighting)
fightWon    = slotC+8
fightBK     = slotC+9   ; fighter area background this frame
barYou      = slotCoarse    ; 3 bytes: player bar PF0-2 (left half)
barFoe      = slotCoarse+3  ; 3 bytes: opponent bar PF0-2 (right half)
ballOn      = slotHM+2      ; ENABL value on the arm rows (player's pipe)
batonOn     = slotHM+3      ; ENAM1 value on the arm rows (opponent's swing)

encPhase    ds 1        ; PHASE_CHOOSE / PHASE_RESPONSE
encAction   ds 1        ; ACT_*: what CONTINUE does after a response
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
heat        ds 1        ; police hostility 0-255, cools down over time
weapon      ds 1        ; 0 fists, 1 pipe, 2 bat, 3 board (WEAPONS)
itemsTaken  ds 1        ; bit n set: weapon n+1 has been picked up
shelters    ds 1        ; shelters the police have pointed out (0-4)
followers   ds 1        ; visible followers = recruits / 5 (Stage D)
hudDirty    ds 1        ; nonzero: recompose the HUD text in overscan
roomDirty   ds 1        ; nonzero: set up the room's NPCs in overscan
pending     ds 1        ; PENDING_*: screen change for bank 0's overscan

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
                        ;   angry-rational, angry-irrational), PERSON_* flags
SC_SFX         = 120    ; sound effect to start (SFX_*), 0 = none
SC_SFX_POS     = 121    ; step of the playing sound (0 = silent)
SC_SFX_TIME    = 122    ; frames left in that step
SC_KNOWN       = 123    ; homeless people you know of (BCD), 0 = "??"
SC_HUNGER      = 124    ; crew hunger (see HUNGRY_AT / DESERT_AT)

PERSON_MET       = 4
PERSON_RECRUITED = 8

SCREEN_TITLE     = 0
SCREEN_CITY      = 1
SCREEN_ENCOUNTER = 2
SCREEN_FIGHT     = 3

; Screen changes that need bank 0 (city setup, sprite pointers, text) are
; requested by setting `pending`; bank 0 carries them out in overscan.
PENDING_NONE       = 0
PENDING_START_CITY = 1  ; title -> city
PENDING_RESUME     = 2  ; encounter / fight -> city, same place
PENDING_TELEPORT   = 3  ; encounter -> city at room/p0x/p0y (jail, outskirts)
PENDING_FIGHT      = 4  ; encounter -> fight
PENDING_TITLE      = 5  ; Act 1 won -> title

ENC_HOMELESS = 0        ; encKind: what the encounter screen shows
ENC_POLICE   = 1
ENC_PASSERBY = 2
ENC_FOOD     = 3
ENC_JAIL     = 4
ENC_COLLAPSE = 5
ENC_CREW     = 6
ENC_WON      = 7

PHASE_CHOOSE   = 0
PHASE_RESPONSE = 1
PHASE_ROUND2   = 2      ; recruiting: answering their question

ACT_CITY      = 0       ; back to the city
ACT_OUTSKIRTS = 1       ; dumped at the edge of the city
ACT_JAIL      = 2       ; show the jail screen next
ACT_JAIL_DONE = 3       ; serve the sentence
ACT_FOOD      = 4       ; back to the food menu
ACT_WAKE      = 5       ; after collapsing: wake up somewhere safer
ACT_TITLE     = 6       ; Act 1 won: back to the title

KIND_NONE     = 0
KIND_SHELTER  = 1
KIND_FOOD     = 2
KIND_HOMELESS = 3       ; KIND_HOMELESS and up are people you can talk to
KIND_POLICE   = 4
KIND_PASSERBY = 5
KIND_ITEM     = 6       ; a weapon lying in an alley (SC_SLOT_PERSON = weapon)
