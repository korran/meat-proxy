# Render and assemble the whole music video.
#
#   make                 everything: data, every section (lossless), then video/build/full_song.mov
#   make data            just the lyrics, stems, drum hits and mouth shapes
#   make office | yacht | news | drone | cyber | wake | credits     one section's renders
#   make video           re-assemble from whatever's rendered (no rendering)
#
# Renders take hours (cyberspace alone is ~1.5 h on a fast GPU). A target is rebuilt when its
# inputs change, not when the scripts do: after editing a script, force the section with e.g.
# `make -B cyber` (or delete its outputs). See README.md.

BLENDER ?= blender
PYTHON  ?= python3
# Python with demucs + torch, for the vocal/drum separation (a venv is fine)
DEMUCS_PYTHON ?= $(PYTHON)
RES ?= 1440

B      := video/build
AUDIO  := assets/audio
RPP    := $(AUDIO)/we_need_a_meat_proxy.rpp
SONG   := $(AUDIO)/we_need_a_meat_proxy_mix.wav
STEMS  := $(AUDIO)/stems/we_need_a_meat_proxy_mix_
VOCALS := $(STEMS)vocals.wav
DRUMS  := $(STEMS)drums.wav
LYRICS := $(B)/lyrics.json
MUSIC  := $(B)/music_mix.json
BL     := $(BLENDER) -b --factory-startup --python
DATA   := --lyrics $(LYRICS) --music $(MUSIC)

.PHONY: all data office yacht news drone cyber wake credits video clean-renders
.DELETE_ON_ERROR:

all: $(B)/full_song.mov

# ---------------------------------------------------------------- data
data: $(LYRICS) $(MUSIC) $(B)/visemes_v1c1_full.json $(B)/visemes_v2c2.json $(B)/visemes_bridge.json \
      $(B)/visemes_v3c3.json $(B)/visemes_outro.json $(B)/visemes_credits.json

$(B):
	mkdir -p $@

# word, line and beat timings, from the REAPER project
$(LYRICS): $(RPP) | $(B)
	$(PYTHON) tools/rpp_lyrics.py $(RPP) --format json > $@

# vocals and drums, separated from REAPER's mix
$(VOCALS) $(DRUMS) &: $(SONG)
	$(DEMUCS_PYTHON) tools/separate.py $(SONG) $(AUDIO)/stems --prefix we_need_a_meat_proxy_mix_

# kick and snare hits (the dancers stomp and hit on them)
$(MUSIC): $(DRUMS) $(SONG) | $(B)
	$(PYTHON) tools/music_features.py $(DRUMS) $(SONG) --fps 60 > $@

# mouth shapes per performance: each file's start/end is also that render's span
define visemes
$(B)/visemes_$(1).json: $(LYRICS) $(VOCALS)
	$(PYTHON) tools/lipsync.py $(LYRICS) $(VOCALS) --start $(2) --end $(3) --fps 60 > $$@
endef
$(eval $(call visemes,v1c1_full,0,66.6))
$(eval $(call visemes,v2c2,66.4,129.8))
$(eval $(call visemes,bridge,129.4,148.6))
$(eval $(call visemes,v3c3,162.6,245.6))
$(eval $(call visemes,outro,245.6,283.01))
$(eval $(call visemes,credits,263.6468,283.01))

# ---------------------------------------------------------------- office: intro, verse 1, chorus 1
OFFICE := --part v1c1 --set office --screen $(B)/screen_v1c1.mkv --visemes $(B)/visemes_v1c1_full.json \
          $(DATA) --res $(RES) --lossless
office: $(B)/office_v1c1_final.mkv $(B)/office_v1c1_screen_final.mkv

$(B)/screen_v1c1.mkv: $(LYRICS) $(MUSIC)
	$(BL) video/screen_graphics.py -- $(DATA) --start 0 --end 66.6 --out $(B)/screen_v1c1 --res $(RES) --final --lossless
$(B)/office_v1c1_final.mkv: $(B)/screen_v1c1.mkv $(B)/visemes_v1c1_full.json
	$(BL) video/dance_demo.py -- $(OFFICE) --pass main --out $(B)/office_v1c1_final
$(B)/office_v1c1_screen_final.mkv: $(B)/screen_v1c1.mkv $(B)/visemes_v1c1_full.json
	$(BL) video/dance_demo.py -- $(OFFICE) --pass screen --out $(B)/office_v1c1_screen_final

# ---------------------------------------------------------------- yacht: verse 2, chorus 2
YACHT := --part v2c2 --set yacht --screen $(B)/screen_v2c2_final.mkv --screen-start 66.4 \
         --visemes $(B)/visemes_v2c2.json $(DATA) --res $(RES) --lossless
yacht: $(B)/yacht_v2c2_final.mkv $(B)/yacht_v2c2_screen_final.mkv

$(B)/screen_v2c2_final.mkv: $(LYRICS) $(MUSIC)
	$(BL) video/screen_graphics.py -- --part v2c2 $(DATA) --start 66.4 --end 129.8 --out $(B)/screen_v2c2_final \
	    --res $(RES) --final --lossless
$(B)/yacht_v2c2_final.mkv: $(B)/screen_v2c2_final.mkv $(B)/visemes_v2c2.json
	$(BL) video/dance_demo.py -- $(YACHT) --pass main --out $(B)/yacht_v2c2_final
$(B)/yacht_v2c2_screen_final.mkv: $(B)/screen_v2c2_final.mkv $(B)/visemes_v2c2.json
	$(BL) video/dance_demo.py -- $(YACHT) --pass screen --out $(B)/yacht_v2c2_screen_final

# ---------------------------------------------------------------- news: the bridge
news: $(B)/news_bridge_final.mkv $(B)/news_overlay_bridge_final.mkv

$(B)/news_overlay_bridge_final.mkv: $(LYRICS)
	$(BL) video/news_overlay.py -- --lyrics $(LYRICS) --out $(B)/news_overlay_bridge_final --res $(RES)
$(B)/news_bridge_final.mkv: $(B)/visemes_bridge.json $(MUSIC)
	$(BL) video/dance_demo.py -- --part bridge --set news --visemes $(B)/visemes_bridge.json $(DATA) \
	    --res $(RES) --lossless --out $(B)/news_bridge_final

# ---------------------------------------------------------------- cyberspace: verse 3, chorus 3
cyber: $(B)/cyber_v3c3_final.mkv

# (the phone holograms: 1440 px tall, so each phone has more pixels than it ever fills on screen)
$(B)/screen_v3c3_final.mkv: $(LYRICS)
	$(BL) video/screen_v3.py -- --lyrics $(LYRICS) --out $(B)/screen_v3c3_final --res $(RES)
$(B)/cyber_v3c3_final.mkv: $(B)/screen_v3c3_final.mkv $(B)/visemes_v3c3.json $(MUSIC)
	$(BL) video/dance_demo.py -- --part v3c3 --set cyber --screen $(B)/screen_v3c3_final.mkv --screen-start 162.6 \
	    --visemes $(B)/visemes_v3c3.json $(DATA) --res $(RES) --lossless --out $(B)/cyber_v3c3_final

# ---------------------------------------------------------------- drone: the instrumental (its iPad plays cyberspace)
drone: $(B)/drone_final.mkv $(B)/drone_screen_final.mkv

$(B)/drone_final.mkv:
	$(BL) video/suburb_set.py -- --fly --res $(RES) --pass main --out $(B)
$(B)/drone_screen_final.mkv: $(B)/cyber_v3c3_final.mkv
	$(BL) video/suburb_set.py -- --fly --res $(RES) --screen $(B)/cyber_v3c3_final.mkv --pass screen --out $(B)

# ---------------------------------------------------------------- wake-up: the outro
wake: $(B)/wake_final.mkv $(B)/wake_screen_final.mkv $(B)/wake_lids.mkv

$(B)/wake_v9.mkv: $(B)/visemes_outro.json $(MUSIC)
	$(BL) video/dance_demo.py -- --part outro --set void --visemes $(B)/visemes_outro.json $(DATA) \
	    --res 1920 --lossless --out $(B)/wake_v9
$(B)/wake_phone.mkv: $(B)/wake_v9.mkv $(LYRICS)
	$(PYTHON) video/wake_phone.py --video $(B)/wake_v9.mkv --out $@
$(B)/wake_final.mkv: $(B)/wake_phone.mkv
	$(BL) video/wake_set.py -- --fly --res $(RES) --pass main --screen $(B)/wake_phone.mkv --out $(B)
$(B)/wake_screen_final.mkv: $(B)/wake_phone.mkv
	$(BL) video/wake_set.py -- --fly --res $(RES) --pass screen --screen $(B)/wake_phone.mkv --out $(B)
$(B)/wake_lids.mkv:
	$(PYTHON) video/wake_lids.py --res $(RES) --out $@

# ---------------------------------------------------------------- end credits, on the yacht
credits: $(B)/credits_final.mkv $(B)/credits_screen_final.mkv

# the Manager's and the Founder's dances, as motion curves (credits_set keys them onto both)
$(B)/credits_dance_%.json: $(B)/visemes_credits.json $(MUSIC)
	DANCE_DUMP=$@ $(BL) video/dance_demo.py -- --part credits_$* --visemes $(B)/visemes_credits.json $(DATA) \
	    --res 270 --preview --out $(B)/credits_dump_tmp
$(B)/credits_v9.mkv: $(B)/visemes_credits.json $(MUSIC)
	$(BL) video/dance_demo.py -- --part credits_v9 --set void --wide --bare --visemes $(B)/visemes_credits.json \
	    $(DATA) --res 1080 --lossless --out $(B)/credits_v9
$(B)/credits_screen.mkv: $(B)/credits_v9.mkv
	$(PYTHON) video/credits_screen.py --video $(B)/credits_v9.mkv --out $@
CREDITS_IN := $(B)/credits_screen.mkv $(B)/credits_dance_manager.json $(B)/credits_dance_founder.json
$(B)/credits_final.mkv: $(CREDITS_IN)
	$(BL) video/credits_set.py -- --res $(RES) --pass main --screen $(B)/credits_screen.mkv --out $(B)
$(B)/credits_screen_final.mkv: $(CREDITS_IN)
	$(BL) video/credits_set.py -- --res $(RES) --pass screen --screen $(B)/credits_screen.mkv --out $(B)

# ---------------------------------------------------------------- the whole thing
SECTIONS := $(B)/office_v1c1_final.mkv $(B)/office_v1c1_screen_final.mkv \
            $(B)/yacht_v2c2_final.mkv $(B)/yacht_v2c2_screen_final.mkv \
            $(B)/news_bridge_final.mkv $(B)/news_overlay_bridge_final.mkv \
            $(B)/drone_final.mkv $(B)/drone_screen_final.mkv $(B)/cyber_v3c3_final.mkv \
            $(B)/wake_final.mkv $(B)/wake_screen_final.mkv $(B)/wake_lids.mkv \
            $(B)/credits_final.mkv $(B)/credits_screen_final.mkv

# H.264 (CRF 12) with the song's own 16-bit PCM, in a .mov (YouTube takes it)
$(B)/full_song.mov: $(SECTIONS) $(SONG)
	$(PYTHON) video/assemble.py --res $(RES) --out $@

video:
	$(PYTHON) video/assemble.py --res $(RES) --out $(B)/full_song.mov

clean-renders:
	rm -f $(SECTIONS) $(B)/full_song.mov
