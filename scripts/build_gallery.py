"""Build the gallery's assets/ and manifest.json from the framed dolls and their example results.

Source: F:/Claude-Work/pose-dolls-20261015 (made with frame_dolls.py and run_examples.py there):
  state.json                       one entry per pose (Totemistyk's General Poses, @23468b2b), final square render
  renders/framing/doll_pgp_<k>_00001_.png   the 864x1152 portrait doll of each pose
  examples/square/<k>.png          the woman in that pose (Pose Studio card, seed 7)
  examples/portrait/<k>.png        the man in that pose
Dolls are copied as lossless PNG (the file people download and upload as picture 1); results and the example photos
are JPEG (q88 full size + 480 px thumbnails) because they are only for viewing. Poses without an example yet are
skipped, so the build can run before every render is done.
usage: uv run --no-project --with pillow python scripts/build_gallery.py
"""
import json, os, shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "F:/Claude-Work/pose-dolls-20261015"
PEOPLE = {"square": ("Woman, plaza", "F:/Claude-Work/vnccs-pose-test-20261014/chars/woman.png"),
          "portrait": ("Man, rooftop", "F:/Claude-Work/vnccs-pose-test-20261014/chars/man34.png")}
SHAPES = {"square": ("Square 1:1", "1 / 1", "1024 x 1024"), "portrait": ("Portrait 3:4", "3 / 4", "864 x 1152")}
THUMB = 480
ASSETS = os.path.join(ROOT, "assets")


def jpeg(src, dst, max_side=None):
    im = Image.open(src).convert("RGB")
    if max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, quality=88, optimize=True)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def pretty(src_path):
    # "Standing__Arms Behind Back - Side View.json" -> family "Standing", name "Arms Behind Back - Side View"
    base = os.path.basename(src_path)[:-5]
    family, name = base.split("__", 1)
    family = family.capitalize() if family.islower() else family
    if family == "Uncategorized":
        family = "Crouching"
    return family, name


st = json.load(open(os.path.join(SRC, "state.json"), encoding="utf-8"))
if os.path.isdir(ASSETS):
    shutil.rmtree(ASSETS)
manifest = {"title": "Pose Studio Doll Gallery", "lora": "VNCCS Pose Studio for Qwen Image 2.1 (V2)",
            "poses_source": "Totemistyk/General_Poses_PoseStudio @23468b2b", "sections": {}}
order = sorted(st, key=lambda k: pretty(st[k]["src"]))
for shape, (title, aspect, size) in SHAPES.items():
    label, photo_src = PEOPLE[shape]
    d = os.path.join(ASSETS, shape)
    photo = os.path.join(d, "photos", "person.jpg")
    jpeg(photo_src, photo)
    poses = []
    for k in order:
        family, name = pretty(st[k]["src"])
        doll_src = st[k]["final"] if shape == "square" else os.path.join(SRC, "renders", "framing", "doll_pgp_%s_00001_.png" % k)
        res_src = os.path.join(SRC, "examples", shape, k + ".png")
        if not os.path.exists(res_src):
            continue
        slug = k.split("-", 1)[1]
        doll = os.path.join(d, "dolls", slug + ".png")
        os.makedirs(os.path.dirname(doll), exist_ok=True)
        shutil.copyfile(doll_src, doll)
        dthumb = os.path.join(d, "thumbs", slug + "_doll.jpg")
        jpeg(doll, dthumb, THUMB)
        res = os.path.join(d, "results", slug + ".jpg")
        jpeg(res_src, res)
        rthumb = os.path.join(d, "thumbs", slug + ".jpg")
        jpeg(res, rthumb, THUMB)
        poses.append({"name": name, "family": family, "doll": rel(doll), "doll_thumb": rel(dthumb),
                      "download_name": "pose_%s_%s.png" % (slug, shape),
                      "examples": [{"label": label, "photo": rel(photo), "result": rel(res), "thumb": rel(rthumb)}]})
    manifest["sections"][shape] = {"title": title, "aspect": aspect, "size": size, "poses": poses}

with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
total = sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(ASSETS) for f in fs)
print("poses:", {k: len(v["poses"]) for k, v in manifest["sections"].items()}, "assets: %.1f MB" % (total / 1e6))
