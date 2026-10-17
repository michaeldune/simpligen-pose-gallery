"""Build the gallery's assets/ and manifest.json from the framed dolls and their example results.

Two collections, each made with frame_dolls.py and run_examples.py in its work folder:
  General Poses   F:/Claude-Work/pose-dolls-20261015   Totemistyk's General Poses (@23468b2b), pose files as published
  Krea2 Library   F:/Claude-Work/krea2-pose-library-20261016/{test6,full}   u/Afraid_Ambassador_43's 120 Krea2 pose
                  prompts; each reference picture was turned into a doll by Pose Studio's pose_image import (SAM 3D
                  Body). The reference pictures themselves are not published.
Per work folder:
  state.json                       one entry per pose, final square render
  renders/framing/doll_pgp_<k>_00001_.png   the 864x1152 portrait doll of each pose
  examples/square/<k>.png          the woman in that pose (Pose Studio card, seed 7)
  examples/portrait/<k>.png        the man in that pose
Dolls are copied as lossless PNG (the file people download and upload as picture 2); results and the example photos
are JPEG (q88 full size + 480 px thumbnails) because they are only for viewing. Poses without an example yet are
skipped, so the build can run before every render is done.
usage: uv run --no-project --with pillow python scripts/build_gallery.py
"""
import json, os, shutil
from collections import Counter
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERAL = "F:/Claude-Work/pose-dolls-20261015"
KREA = "F:/Claude-Work/krea2-pose-library-20261016"
KREA_DIRS = [KREA + "/test6", KREA + "/full"]
KREA_LIST = KREA + "/extracted/comfyui_krea2_pose_library/poses.json"
PEOPLE = {"square": ("Woman, plaza", "F:/Claude-Work/vnccs-pose-test-20261014/chars/woman.png"),
          "portrait": ("Man, rooftop", "F:/Claude-Work/vnccs-pose-test-20261014/chars/man34.png")}
SHAPES = {"square": ("Square 1:1", "1 / 1", "1024 x 1024"), "portrait": ("Portrait 3:4", "3 / 4", "864 x 1152")}
COLLECTIONS = {"general": "General Poses (Totemistyk)", "krea2": "Krea2 Pose Library (u/Afraid_Ambassador_43)"}
# Krea2 categories folded into the gallery's existing families
KREA_FAMILY = {"standing": "Standing", "seated on floor": "Sitting", "fetal": "Sitting", "kneeling": "Kneeling",
               "squatting": "Crouching", "crawling": "Crawling", "prone": "Lying", "lying on back": "Lying"}
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


def slugify(s):
    return "_".join(w for w in "".join(c if c.isalnum() else " " for c in s.lower()).split())


def general_poses():
    """(key, family, name, slug, work dir, state entry) for Totemistyk's poses, sorted by family and name"""
    st = json.load(open(os.path.join(GENERAL, "state.json"), encoding="utf-8"))
    out = []
    for k, s in st.items():
        # "Standing__Arms Behind Back - Side View.json" -> family "Standing", name "Arms Behind Back - Side View"
        family, name = os.path.basename(s["src"])[:-5].split("__", 1)
        family = family.capitalize() if family.islower() else family
        if family == "Uncategorized":
            family = "Crouching"
        out.append((k, family, name, k.split("-", 1)[1], GENERAL, s))
    return sorted(out, key=lambda x: (x[1], x[2]))


def krea_poses():
    """the same tuples for the Krea2 library, in the library's own order; names follow the gallery's style"""
    meta = {p["id"][5:]: p for p in json.load(open(KREA_LIST, encoding="utf-8"))}
    st = {}
    for d in KREA_DIRS:
        p = os.path.join(d, "state.json")
        if os.path.exists(p):
            for k, s in json.load(open(p, encoding="utf-8")).items():
                st[k] = (d, s)
    rows = []
    for k in sorted(st):
        pid = k[-3:]
        m = meta[pid]
        parts = [x.strip() for x in m["name"].split("|")]
        view = parts[1].replace("Profile View", "Side View")
        desc = " - ".join(x.strip() for x in parts[2].replace("\u2013", "|").replace("\u2014", "|").replace(".", "|").split("|") if x.strip())
        rows.append([k, KREA_FAMILY.get(m["category"], m["category"].title()), desc + " - " + view, pid, st[k]])
    seen = Counter(r[2] for r in rows); n = Counter()
    out = []
    for k, family, name, pid, (d, s) in rows:
        if seen[name] > 1:
            n[name] += 1
            name = "%s (%d)" % (name, n[name])
        out.append((k, family, name, "k2_%s_%s" % (pid, slugify(name)), d, s))
    return out


if os.path.isdir(ASSETS):
    shutil.rmtree(ASSETS)
manifest = {"title": "Pose Studio Doll Gallery", "lora": "VNCCS Pose Studio for Qwen Image 2.1 (V2)",
            "poses_source": "Totemistyk/General_Poses_PoseStudio @23468b2b; Krea2 pose prompts by u/Afraid_Ambassador_43",
            "collections": COLLECTIONS, "sections": {}}
sources = [("general", general_poses()), ("krea2", krea_poses())]
for shape, (title, aspect, size) in SHAPES.items():
    label, photo_src = PEOPLE[shape]
    d = os.path.join(ASSETS, shape)
    photo = os.path.join(d, "photos", "person.jpg")
    jpeg(photo_src, photo)
    poses = []
    for coll, rows in sources:
        for k, family, name, slug, work, s in rows:
            res_src = os.path.join(work, "examples", shape, k + ".png")
            if not os.path.exists(res_src):
                continue
            if shape == "square":
                doll_src = s["final"]
            else:
                renders = GENERAL if coll == "general" else KREA
                doll_src = os.path.join(renders, "renders", "framing", "doll_pgp_%s_00001_.png" % k)
            doll = os.path.join(d, "dolls", slug + ".png")
            os.makedirs(os.path.dirname(doll), exist_ok=True)
            shutil.copyfile(doll_src, doll)
            dthumb = os.path.join(d, "thumbs", slug + "_doll.jpg")
            jpeg(doll, dthumb, THUMB)
            res = os.path.join(d, "results", slug + ".jpg")
            jpeg(res_src, res)
            rthumb = os.path.join(d, "thumbs", slug + ".jpg")
            jpeg(res, rthumb, THUMB)
            poses.append({"name": name, "family": family, "collection": coll, "doll": rel(doll), "doll_thumb": rel(dthumb),
                          "download_name": "pose_%s_%s.png" % (slug, shape),
                          "examples": [{"label": label, "photo": rel(photo), "result": rel(res), "thumb": rel(rthumb)}]})
    manifest["sections"][shape] = {"title": title, "aspect": aspect, "size": size, "poses": poses}

with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
total = sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(ASSETS) for f in fs)
print("poses:", {k: dict(Counter(p["collection"] for p in v["poses"])) for k, v in manifest["sections"].items()},
      "assets: %.1f MB" % (total / 1e6))
