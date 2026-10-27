# We Need a Meat Proxy

A music video made entirely in code: toy-brick sets and minifig characters rendered in Blender,
with the graphics on the screens inside the sets generated the same way. What each shot shows is
in [video/SHOTLIST.md](video/SHOTLIST.md).

**Watch it on YouTube:** https://www.youtube.com/watch?v=kQyxcaBmYEk

## Requirements

- **Blender 4.3** (`blender` on the `PATH`, or `make BLENDER=/path/to/blender`), with a GPU for EEVEE
- **Python 3** with numpy, scipy and Pillow
- **ffmpeg**
- **Fonts**: Inter, Bebas Neue, IBM Plex, URW base35, DejaVu (Debian/Ubuntu: `fonts-inter
  fonts-bebas-neue fonts-ibm-plex fonts-urw-base35 fonts-dejavu`)
- For separating the vocals and drums: **demucs** (`pip install demucs`, e.g. in a venv; pass it
  as `make DEMUCS_PYTHON=/path/to/venv/bin/python`)

## Building

```
make            # everything: data, every section, then video/build/full_song.mov
```

The output is `video/build/full_song.mov`: 2560×1440, 60 fps, H.264 (CRF 12) with the song's
own 16-bit PCM audio. Every section is rendered losslessly first (`video/build/*_final.mkv`),
so a full build takes many hours and a lot of disk (about 65 GB).

Smaller steps:

```
make data                                   # lyrics/beat timings, stems, drum hits, mouth shapes
make office | yacht | news | drone | cyber | wake | credits     # one section
make video                                  # just re-assemble from what's rendered
make RES=1080                               # a lower resolution
```

A target is rebuilt when its inputs (the song, the REAPER project, the data files) change, not
when a script does. After editing a script, force its section, e.g. `make -B cyber`. To mark
existing renders as up to date without rendering, `make -t`.

## How it fits together

- **The song** is `assets/audio/we_need_a_meat_proxy.rpp` (REAPER), rendered to
  `assets/audio/we_need_a_meat_proxy_mix.wav`. Audio is edited in REAPER and rendered with it,
  not by the build. The lyric, word and beat timings all come from the project
  (`tools/rpp_lyrics.py`).
- **Data** (`video/build/*.json`): word timings, kick/snare hits from the separated drums
  (`tools/music_features.py`), and mouth shapes per performance from the separated vocals
  (`tools/lipsync.py`).
- **Sections** (`video/*.py`): `dance_demo.py` is the performance engine (singing, dancing,
  gestures from `dance_moves.py`) used with each set; `office_set.py`, `yacht_set.py`,
  `news_set.py`, `suburb_set.py`, `cyber_set.py`, `wake_set.py`, `credits_set.py` build the
  sets; `screen_graphics.py`, `screen_v2.py`, `news_overlay.py`, `screen_v3.py`,
  `wake_phone.py`, `credits_screen.py` make what plays on their screens. Screens are rendered as
  a separate pass and added in assembly, so the graphics keep their exact pixels.
- **Assembly**: `video/assemble.py` splices the sections over the song.

Most scripts take `--preview` for a quick low-quality check; see each script's docstring.
