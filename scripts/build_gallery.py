"""Build the gallery's assets/ and manifest.json from rendered dolls and example results.

Mock-up source: the 2026-10-14 pose-transfer tests in F:/Claude-Work/vnccs-pose-test-20261014 (four poses, two shapes,
two example people per shape, VNCCS Pose Studio LoRA V2, seed 7).
Dolls are copied as lossless PNG (the file people download and upload as picture 1); results and example photos are
JPEG (q88 full size + 480 px thumbnails) because they are only for viewing.
usage: uv run --no-project --with pillow python scripts/build_gallery.py
"""
import json, os, shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "F:/Claude-Work/vnccs-pose-test-20261014"
ASSETS = os.path.join(ROOT, "assets")

# pose key -> display name, family (Totemistyk's folder names), source names in the test folder
POSES = [
    ("boxing", "Boxing Stance", "Fighting"),
    ("kneeling", "Kneeling - Side View", "Kneeling"),
    ("crawling", "Crawling", "Crawling"),
    ("seated", "Seated on Floor", "Sitting"),
]
SHAPES = {
    "square": {"title": "Square 1:1", "aspect": "1 / 1", "size": "1024 x 1024",
               "doll": "out/doll_framed_{p}_00001_.png",
               "people": [("Woman, plaza", "chars/woman.png", "out/res/woman_framed_{p}_v2_s7_00001_.png"),
                          ("Man, rooftop", "chars/man.png", "out/res/man_framed_{p}_v2_s7_00001_.png")]},
    "portrait": {"title": "Portrait 3:4", "aspect": "3 / 4", "size": "864 x 1152",
                 "doll": "out/doll_portrait_{p}_00001_.png",
                 "people": [("Woman, plaza", "chars/woman34.png", "out/res/woman34_portrait_{p}_v2_s7_00001_.png"),
                            ("Man, rooftop", "chars/man34.png", "out/res/man34_portrait_{p}_v2_s7_00001_.png")]},
}
THUMB = 480


def jpeg(src, dst, max_side=None):
    im = Image.open(src).convert("RGB")
    if max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, quality=88, optimize=True)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


if os.path.isdir(ASSETS):
    shutil.rmtree(ASSETS)
manifest = {
    "title": "Pose Studio Doll Gallery",
    "lora": "VNCCS Pose Studio for Qwen Image 2.1 (V2)",
    "mockup": True,
    "sections": {},
}
for skey, s in SHAPES.items():
    poses = []
    seen_photos = {}
    for pkey, name, family in POSES:
        d = os.path.join(ASSETS, skey)
        doll_png = os.path.join(d, "dolls", pkey + ".png")
        os.makedirs(os.path.dirname(doll_png), exist_ok=True)
        shutil.copyfile(os.path.join(SRC, s["doll"].format(p=pkey)), doll_png)
        doll_thumb = os.path.join(d, "thumbs", pkey + "_doll.jpg")
        jpeg(doll_png, doll_thumb, THUMB)
        examples = []
        for i, (label, photo, result) in enumerate(s["people"]):
            if photo not in seen_photos:
                ph = os.path.join(d, "photos", "person%d.jpg" % (i + 1))
                jpeg(os.path.join(SRC, photo), ph)
                seen_photos[photo] = rel(ph)
            res = os.path.join(d, "results", "%s_person%d.jpg" % (pkey, i + 1))
            jpeg(os.path.join(SRC, result.format(p=pkey)), res)
            res_t = os.path.join(d, "thumbs", "%s_person%d.jpg" % (pkey, i + 1))
            jpeg(res, res_t, THUMB)
            examples.append({"label": label, "photo": seen_photos[photo], "result": rel(res), "thumb": rel(res_t)})
        poses.append({"name": name, "family": family, "doll": rel(doll_png), "doll_thumb": rel(doll_thumb),
                      "download_name": "%s_%s.png" % (name.replace(" - ", "_").replace(" ", "_").lower(), skey),
                      "examples": examples})
    manifest["sections"][skey] = {"title": s["title"], "aspect": s["aspect"], "size": s["size"], "poses": poses}

with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
total = sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(ASSETS) for f in fs)
print("poses:", {k: len(v["poses"]) for k, v in manifest["sections"].items()}, "assets: %.1f MB" % (total / 1e6))
