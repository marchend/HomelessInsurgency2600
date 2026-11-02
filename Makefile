PYTHON ?= .venv/bin/python
DASM   ?= dasm
STELLA ?= stella

ROM     = bin/hi.bin
SOURCES = $(wildcard src/*.asm src/*.h)
ASSETS  = $(wildcard assets/*.py assets/rooms/*.txt assets/dialogue/*.txt) tools/build_assets.py tools/rooms.py tools/build_dialogue.py tools/dialogue.py
GEN     = src/generated/bank0_data.asm src/generated/bank1_data.asm src/generated/bank2_data.asm src/generated/bank6_data.asm

.PHONY: all assets run test mockups clean

all: $(ROM)

$(GEN): $(ASSETS)
	$(PYTHON) tools/build_assets.py

assets: $(GEN)

$(ROM): $(SOURCES) $(GEN)
	@mkdir -p bin
	cd src && $(DASM) main.asm -f3 -o../$(ROM) -l../bin/hi.lst -s../bin/hi.sym -E2

run: $(ROM)
	$(STELLA) $(ROM)

test: $(ROM)
	$(PYTHON) -m unittest discover -s tests

mockups:
	$(PYTHON) tools/mockups/render_mockups.py

clean:
	rm -rf bin src/generated
