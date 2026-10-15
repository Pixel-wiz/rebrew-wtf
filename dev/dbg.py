import sys; from pathlib import Path
from decompnet.app.engine import RomNetwork
ws = Path("/home/dev/e2e-ws2"); import shutil; shutil.rmtree(ws, ignore_errors=True); ws.mkdir(parents=True)
net = RomNetwork(ws/"d.db", ws)
slug = net.rebrew.import_binary(Path("/home/dev/targets/toy"), toolchain="gcc-14.2.0", confirmed=True, name="toy", log=lambda *a:None)
proj = net.store.one("SELECT * FROM projects WHERE slug=?", slug)
fn = net.store.one("SELECT * FROM functions WHERE project_id=? AND name='toy_clamp'", proj["id"])
import json
print("stored: va", hex(fn["vram"]), "size", fn["size"], "symbol", json.loads(fn["relocs"]), "target", bytes(fn["target"]).hex())
hdr = net._context(proj["id"], fn["unit"])["header"]
src = "int toy_clamp(int v, int lo, int hi) {\n    if (v < lo) return lo;\n    if (v > hi) return hi;\n    return v;\n}"
cr = net.rebrew.compile(proj, hdr, src)
print("compile ok", cr.ok, "obj", len(cr.obj) if cr.obj else None, "log", cr.log[:120])
cand, verdict, problems = net.rebrew.evaluate(fn, proj, cr.obj)
print("evaluate verdict", verdict, "problems", problems, "cand.code", cand.code.hex() if cand else None)
