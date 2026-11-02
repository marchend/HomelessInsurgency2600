"""Sprite art shared by the mockup renderer and the ROM asset builder.

One letter = one color key; every row may use only one key (one color per
scanline). Rows are 8 pixels wide at most. Colors are TIA (hue, luminance)
pairs: hue 0-15, luminance 0-7, i.e. color byte = hue << 4 | lum << 1.
"""


def c(hue, lum):
    return (hue, lum)



PLAYER_TOP = ["..RRRR..", ".RRRRRR.", "..SSSS..", "..SSSS..", ".CCCCCC.",
              "CCCCCCCC", "C.CCCC.C", "..CCCC..", "..P..P..", "..B..B.."]
HOMELESS_TOP = ["...HHH..", "..HHHHH.", "..SSSS..", ".HHHHHH.", "HHHHHHHH",
                "HHHHHHH.", ".HHHHHH.", ".HHHHH..", "..D..D..", "..D..D.."]
POLICE_TOP = ["..KKKK..", ".KKKKKK.", "..SSSS..", "..SSSS..", ".UUUUUU.",
              "UUUUUUUU", "Y.YYYY.Y", "..NNNN..", "..N..N..", "..K..K.."]
PERSON_TOP = ["..AAAA..", "..SSSS..", "..SSSS..", ".GGGGGG.", "GGGGGGGG",
              "G.GGGG.G", "..GGGG..", "..LLLL..", "..L..L..", "..B..B.."]
FOLLOWER_TOP = ["..HHHH..", "..SSSS..", ".CCCCCC.", "CCCCCCCC", "..CCCC..",
                "..C..C.."]
SIGN_SHELTER = ["...WW...", "..WWWW..", ".WWWWWW.", "WWWWWWWW", ".W....W.",
                ".W.WW.W.", ".WWWWWW."]
SIGN_FOOD = [".F..F...", "..F..F..", "........", "MMMMMM..", "MMMMMMMM",
             "MMMMMM.M", "MMMMMMM.", ".MMMM..."]

# Side-view portraits, authored facing right (reflect for facing left).
PLAYER_SIDE = [
    "...RRR..", "..RRRRR.", ".RRRRRR.", ".RRRRRRR", "..SSSSS.", "..SSSS.S",
    "..SSSSSS", "..SSSSS.", "..GGGG..", "...GGG..", "...SS...", "..CCCC..",
    ".CCCCCC.", "CCCCCCCC", "CCCCCCCC", "CCCCCCC.", "CCCCCCC.", "CCCCCCC.",
    ".CCCCCC.", ".CCCCCC.", ".CCCCCC.", "..PPPP..", "..PPPP..", "..PP.PP.",
    "..PP.PP.", "..PP..PP", ".PP...PP", ".PP...PP", ".BB...BB", "BBB..BBB",
]
PASSERBY_SIDE = [
    "..AAAA..", ".AAAAAA.", ".AAAAA..", "..SSSS..", "..SSS.S.", "..SSSSSS",
    "..SSSSS.", "..SSSS..", "...SSS..", "..WWWW..", ".JJJJJJ.", "JJJJJJJJ",
    "JJJJJJJJ", "JJJJJJJ.", "JJJJJJJ.", "JJJJJJJ.", "JJJJJJJ.", "JJJJJJJJ",
    ".JJJJJJ.", "..LLLL..", "..LLLL..", "..LL.LL.", "..LL.LL.", "..LL.LL.",
    "..LL..LL", ".LL...LL", ".LL...LL", ".LL...LL", ".BB...BB", "BBB..BBB",
]
HOMELESS_SIDE = [
    "..TTTT..", ".TTTTTT.", "TTTTTTTT", "..SSSS..", "..SSS.S.", "..SSSSSS",
    "..SSSSS.", "..WWWWW.", "..WWWWWW", "...WWWW.", "....WW..", "..OOOO..",
    ".OOOOOO.", "OOOOOOOO", "OOOOOOOO", "OOOOOOO.", "OOOOOOO.", "OOOOOOO.",
    "OOOOOOOO", ".OOOOOO.", ".OOOOOO.", "..DDDD..", "..DDDD..", "..DD.DD.",
    "..DD.DD.", "..DD..DD", ".DD...DD", ".DD...DD", ".KK...KK", "KKK..KKK",
]
COP_SIDE = [
    "..KKKK..", ".KKKKKK.", ".KKKKKKK", "..SSSS..", "..SSS.S.", "..SSSSSS",
    "..SSSSS.", "..SSSS..", "...SSS..", "..UUUU..", ".UUUUUU.", "UUUUUUUU",
    "UUUUUUUU", "UUUUUUU.", "UUUUUUU.", "UUUUUUU.", "YYYYYYY.", "UUUUUUU.",
    ".NNNNNN.", ".NNNNNN.", "..NNNN..", "..NN.NN.", "..NN.NN.", "..NN.NN.",
    "..NN..NN", ".NN...NN", ".NN...NN", ".NN...NN", ".KK...KK", "KKK..KKK",
]
BARREL = ["..F..F..", ".F.FF.F.", ".FFFFFF.", "..OOOO..", "..YYYY..",
          ".DDDDDD.", ".GGGGGG.", ".DDDDDD.", ".DDDDDD.", ".GGGGGG.",
          ".DDDDDD.", ".DDDDDD."]
BYSTANDER = ["..XXXX..", "..XXXX..", "...XX...", ".XXXXXX.", "XXXXXXXX",
             "X.XXXX.X", "X.XXXX.X", "..XXXX..", "..X..X..", "..X..X..",
             "..X..X..", ".XX..XX."]

SKIN_A, SKIN_B, SKIN_C = c(3, 6), c(2, 4), c(3, 5)
PLAYER_COLORS = {"R": c(4, 2), "S": SKIN_A, "C": c(14, 2), "P": c(9, 2),
                 "B": c(15, 1), "G": c(0, 3)}
HOMELESS_COLORS = {"H": c(15, 2), "S": SKIN_B, "D": c(15, 1), "T": c(15, 1),
                   "W": c(0, 4), "O": c(13, 2), "K": c(0, 1)}
POLICE_COLORS = {"K": c(8, 1), "S": SKIN_C, "U": c(8, 3), "Y": c(1, 5),
                 "N": c(8, 1)}
FOLLOWER_COLORS = {"H": c(15, 1), "S": SKIN_B, "C": c(2, 3)}
PASSERBY_COLORS = {"A": c(15, 1), "S": SKIN_A, "W": c(0, 7), "J": c(10, 3),
                   "L": c(0, 3), "B": c(0, 0)}
PERSON_COLORS = {"A": c(15, 1), "S": SKIN_B, "G": c(12, 4), "L": c(0, 2),
                 "B": c(0, 1)}
