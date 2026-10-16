"""One example result per framed doll, for the gallery: the shipped Pose Studio card workflow
(packs/qwen-image-21/workflows/image_qwen_image_21_pose_studio.json) submitted to SimpliGen's engine (8199) with the
placeholders filled the way the app fills them (numbers bare). The card itself passed 8/8 through the app first.
Square dolls get the woman (1:1 photo), portrait dolls the man (3:4 photo); seed 7, 25 steps, CFG 1, no notes.
Resumable: skips results already on disk. Stops if the engine is busy with a job that is not ours.
usage: run_examples.py square|portrait
"""
import json, os, re, sys, time, urllib.parse, urllib.request, uuid

E = "http://127.0.0.1:8199"
HERE = os.path.dirname(os.path.abspath(__file__))
WF = "C:/Users/micha/Projects/dune/simpligen-presets/packs/qwen-image-21/workflows/image_qwen_image_21_pose_studio.json"
SHAPE = sys.argv[1]
PERSON = {"square": "F:/Claude-Work/vnccs-pose-test-20261014/chars/woman.png",
          "portrait": "F:/Claude-Work/vnccs-pose-test-20261014/chars/man34.png"}[SHAPE]
PREFIX = {"square": "doll_pg_%s_r", "portrait": "doll_pgp_%s_00001_.png"}[SHAPE]
OUT = os.path.join(HERE, "examples", SHAPE)
st = json.load(open(os.path.join(HERE, "state.json"), encoding="utf-8"))


def call(p, d=None):
    r = urllib.request.Request(E + p, data=json.dumps(d).encode() if d is not None else None, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as x:
        b = x.read()
        return json.loads(b) if b.strip() else {}


def upload(path, name):
    data = open(path, "rb").read(); bd = uuid.uuid4().hex
    body = (("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\nContent-Type: image/png\r\n\r\n" % (bd, name)).encode()
            + data + ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n" % (bd, bd)).encode())
    r = urllib.request.Request(E + "/upload/image", data=body, headers={"Content-Type": "multipart/form-data; boundary=" + bd})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())["name"]


def graph(doll, person, name):
    t = open(WF, encoding="utf-8").read()
    for k, v in {"unet": "qwen_image_2.1_int8_convrot.safetensors", "clip": "qwen3vl_8b_int8_convrot.safetensors",
                 "vae": "qwen_image_2.1_vae_bf16.safetensors", "prompt": "", "negative_prompt": "",
                 "ref_image_1": doll, "ref_image_2": person}.items():
        t = t.replace("{{%s}}" % k, json.dumps(v)[1:-1])
    for k, v in {"seed": 7, "steps": 25, "cfg": 1}.items():
        t = t.replace('"{{%s}}"' % k, str(v)).replace("{{%s}}" % k, str(v))
    assert "{{" not in t, re.findall(r"\{\{\w+\}\}", t)
    g = json.loads(t)
    g["sg_save"]["inputs"]["filename_prefix"] = "claude_pose_examples/" + name
    return g


os.makedirs(OUT, exist_ok=True)
person = upload(PERSON, "pose_example_person_%s.png" % SHAPE)
for k, s in st.items():
    dst = os.path.join(OUT, k + ".png")
    if os.path.exists(dst):
        continue
    doll = s["final"] if SHAPE == "square" else os.path.join(HERE, "renders", "framing", PREFIX % k)
    q = call("/queue")
    if q["queue_running"] or q["queue_pending"]:
        mine = all(e[2].get("sg_save", {}).get("inputs", {}).get("filename_prefix", "").startswith("claude_pose_examples/")
                   for e in q["queue_running"] + q["queue_pending"])
        if not mine:
            print("ENGINE BUSY with another job - stopping", flush=True); sys.exit(2)
    dn = upload(doll, "pose_doll_%s_%s.png" % (SHAPE, k))
    t0 = time.time()
    pid = call("/prompt", {"prompt": graph(dn, person, "%s_%s" % (SHAPE, k)), "client_id": "claude-pose-examples"})["prompt_id"]
    while True:
        time.sleep(2)
        h = call("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 600:
            call("/interrupt", {}); print(k, "STALLED > 600 s", flush=True); sys.exit(3)
    stt = h[pid]["status"]
    if stt["status_str"] != "success":
        print(k, "FAILED", json.dumps(stt["messages"])[-600:], flush=True); sys.exit(1)
    img = [o for o in h[pid]["outputs"].values() if "images" in o][0]["images"][0]
    b = urllib.request.urlopen(E + "/view?" + urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]}), timeout=120).read()
    open(dst, "wb").write(b)
    print("%-44s %.0f s" % (k, time.time() - t0), flush=True)
print("DONE", SHAPE)
