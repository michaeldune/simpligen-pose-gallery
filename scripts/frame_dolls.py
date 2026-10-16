"""Frame Totemistyk's General Poses as gallery dolls: same zoom for every pose, lowest point at ~93% of the frame height,
centred horizontally. Pose Studio only renders in ComfyUI's web page, so each round is:
  1. python frame_dolls.py prepare <round>   -> writes and uploads one pose file per unfinished pose
  2. in the browser page: await renderDolls(names)   (one at a time; the capture uses whatever is loaded when it runs)
  3. python frame_dolls.py measure <round>   -> measures each render, updates offsets in state.json
Offsets move the doll about 4.4% of the frame per unit (measured 2026-10-14); after two renders each pose uses its own
measured slope (secant). Zoom 1.3 matches the tested convention (32/32 grounded).
Then: python frame_dolls.py portrait   -> writes 864x1152 copies with the final offsets (same framing, verified after).
"""
import json, glob, os, sys, urllib.request, uuid
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "poses_src")
WORK = os.path.join(HERE, "poses_framed")
OUT = "F:/Claude-Work/pose-dolls-20261015/renders"   # vanilla's --output-directory points here
STATE = os.path.join(HERE, "state.json")
E = "http://127.0.0.1:8188"
ZOOM, TARGET_BOTTOM, TARGET_CX, TOL = 1.3, 0.93, 0.50, 0.012
SLOPE = 0.0437  # frame fraction per offset unit, sign: more negative offset_y -> lower doll
SKIP = ("Close Up", "Overhead")


def key(path):
    return os.path.basename(path)[:-5].replace(" ", "_").replace("__", "-").lower()


def write_pose(src, out, ox, oy, w=1024, h=1024):
    d = json.load(open(src, encoding="utf-8"))
    def setcam(c):
        c["zoom"] = ZOOM; c["offset_x"] = ox; c["offset_y"] = oy
    setcam(d["cameraParams"])
    ch = d["characters"][0]
    ch["transform"].update({"zoom": ZOOM, "x": ox, "y": oy})
    for p in ch.get("poses", []):
        setcam(p.setdefault("cameraParams", {}))
    d["export"] = {**d.get("export", {}), "view_width": w, "view_height": h, "cam_zoom": ZOOM, "cam_offset_x": ox, "cam_offset_y": oy}
    open(out, "w", encoding="utf-8").write(json.dumps(d))


def upload(path):
    name = os.path.basename(path); data = open(path, "rb").read(); bd = uuid.uuid4().hex
    body = (("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\nContent-Type: application/json\r\n\r\n" % (bd, name)).encode()
            + data + ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n" % (bd, bd)).encode())
    r = urllib.request.Request(E + "/upload/image", data=body, headers={"Content-Type": "multipart/form-data; boundary=" + bd})
    urllib.request.urlopen(r, timeout=60).read()


def bbox(png):
    a = np.asarray(Image.open(png).convert("L"), dtype=np.int16)
    ys, xs = np.where(a < 235)
    H, W = a.shape
    return dict(top=ys.min() / H, bottom=ys.max() / H, left=xs.min() / W, right=xs.max() / W, cx=(xs.min() + xs.max()) / 2 / W)


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    st = {}
    for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        if any(s in os.path.basename(f) for s in SKIP):
            continue
        st[key(f)] = {"src": f, "ox": 0.0, "oy": -6.0, "hist": [], "done": False}
    return st


def save(st):
    json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)


def secant(hist, axis, measure, target, default_slope):
    """next offset from this pose's own history: slope from the last two renders, else the default.
    Renders cut off at the bottom edge are not real positions, so they never feed the vertical slope."""
    if axis == "oy":
        hist = [h for h in hist if h["bottom"] <= 0.995] or hist
    o_now, m_now = hist[-1][axis], hist[-1][measure]
    slope = default_slope
    if len(hist) >= 2:
        o_prev, m_prev = hist[-2][axis], hist[-2][measure]
        if abs(o_now - o_prev) > 1e-6 and abs(m_now - m_prev) > 1e-4:
            slope = (m_now - m_prev) / (o_now - o_prev)
    return o_now + (target - m_now) / slope


cmd = sys.argv[1]
st = load()
os.makedirs(WORK, exist_ok=True)
if cmd == "prepare":
    rnd = int(sys.argv[2]); names = []
    for k, s in st.items():
        if s["done"]:
            continue
        n = "pg_%s_r%d" % (k, rnd)
        p = os.path.join(WORK, n + ".json")
        write_pose(s["src"], p, s["ox"], s["oy"])
        upload(p); names.append(n)
    save(st)
    print(json.dumps(names))
elif cmd == "measure":
    rnd = int(sys.argv[2]); left = 0
    for k, s in st.items():
        if s["done"]:
            continue
        png = os.path.join(OUT, "framing", "doll_pg_%s_r%d_00001_.png" % (k, rnd))
        if not os.path.exists(png):
            print("MISSING", k); left += 1; continue
        b = bbox(png)
        s["hist"].append({"ox": s["ox"], "oy": s["oy"], **b})
        clipped = b["bottom"] > 0.995
        ok_y = abs(b["bottom"] - TARGET_BOTTOM) <= TOL and not clipped
        ok_x = abs(b["cx"] - TARGET_CX) <= 0.03
        if ok_y and ok_x:
            s["done"] = True; s["final"] = png
        else:
            if clipped:
                s["oy"] += 3.0
            elif not ok_y:
                s["oy"] = secant(s["hist"], "oy", "bottom", TARGET_BOTTOM, -SLOPE)
            if not ok_x:
                s["ox"] = secant(s["hist"], "ox", "cx", TARGET_CX, SLOPE)
            left += 1
        print("%-44s bottom %.3f cx %.3f top %.3f %s" % (k, b["bottom"], b["cx"], b["top"], "DONE" if s["done"] else "-> oy %.2f ox %.2f" % (s["oy"], s["ox"])))
    save(st)
    print("remaining", left)
elif cmd == "recompute":
    # redo the next offsets of unfinished poses from their history with the current secant rule
    for k, s in st.items():
        if s["done"] or not s["hist"]:
            continue
        last = s["hist"][-1]
        if last["bottom"] > 0.995:
            s["oy"] = last["oy"] + 3.0
        elif abs(last["bottom"] - TARGET_BOTTOM) > TOL:
            s["oy"] = secant(s["hist"], "oy", "bottom", TARGET_BOTTOM, -SLOPE)
        print("%-44s -> oy %.2f ox %.2f" % (k, s["oy"], s["ox"]))
    save(st)
elif cmd == "portrait":
    names = []
    for k, s in st.items():
        n = "pgp_%s" % k
        p = os.path.join(WORK, n + ".json")
        write_pose(s["src"], p, s["ox"], s["oy"], 864, 1152)
        upload(p); names.append(n)
    print(json.dumps(names))
