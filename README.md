# Pose Studio Doll Gallery

A static gallery of framed Pose Studio dolls for SimpliGen's pose card (Qwen Image 2.1 + the VNCCS Pose Studio LoRA).
Pick a pose, download the doll PNG, and give the card the doll as picture 1 and a full-body photo as picture 2: the
person is moved into the doll's pose and keeps their face, outfit and background. Each pose opens in a split-slider
view comparing the doll with real results.

46 poses from Totemistyk's General Poses library (pinned at `23468b2b`), each as a square 1024 x 1024 doll and a
3:4 864 x 1152 doll, each with one example made by the SimpliGen card (seed 7). Live at
https://michaeldune.github.io/simpligen-pose-gallery/. Left out: the four close-up and overhead poses, whose camera
cannot stand on a floor line.

## Layout

| Path | What |
|---|---|
| `index.html` | the whole front end (no dependencies), reads `manifest.json` |
| `manifest.json` | sections (shapes) -> poses -> doll PNG, thumbnails, example photo and result per person |
| `assets/<shape>/dolls/*.png` | the dolls people download (lossless) |
| `assets/<shape>/results`, `photos`, `thumbs` | example renders and the photos used for them (JPEG) |
| `scripts/build_gallery.py` | copies dolls and results in and writes the manifest |

## Run it locally

```
uv run --no-project python -m http.server 8899 --bind 127.0.0.1
```
then open http://127.0.0.1:8899/ (`file://` cannot load the manifest).

## How the dolls are framed

Every doll is rendered at the same camera zoom (1.3) with its lowest point (feet, knees or hands) at about 93% of the
frame height, so people land on the floor of a full-body photo instead of floating. Square dolls are 1024 x 1024 and
portrait dolls 864 x 1152; the same zoom and offsets give the same framing in both shapes. Tested 32/32 grounded with
the V2 LoRA (two people, two seeds, four poses, both shapes).

## Credits

- Pose Studio and its Qwen Image 2.1 pose LoRA: MiuProject (VNCCS), https://github.com/AHEKOT/ComfyUI_VNCCS_Utils, MIT;
  use of the LoRA and of doll renders confirmed by the author (2026-10-14). The doll is built on MakeHuman.
- Poses: Totemistyk, https://huggingface.co/Totemistyk/General_Poses_PoseStudio, used with permission (2026-10-14).
- Front end adapted from lumenastrum/clio-style-preview `gallery/index.html`, MIT; see `LICENSE-clio-style-preview`.
