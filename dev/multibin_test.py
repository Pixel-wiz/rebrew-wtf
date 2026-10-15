"""Multi-binary project gate: one project spanning two binaries (simulating an exe + its DLL). Import both,
then match one self-contained function from EACH, proving functions from different binaries coexist and judge
against the right bytes."""
import re
import sys
import shutil
from pathlib import Path

from decompnet.app.engine import RomNetwork

TOY = Path("/home/dev/targets/toy")
LIB = Path("/home/dev/targets/lib")
TOY_C = Path("/home/dev/targets/toy.c").read_text()
LIB_C = Path("/home/dev/targets/lib.c").read_text()


def slice_fn(text, name):
    m = re.search(rf"(^|\n)([A-Za-z_][\w \*]*\b{name}\s*\([^;]*?\)\s*\{{)", text)
    i = text.index("{", m.start(2)); depth = 0; j = i
    while j < len(text):
        depth += 1 if text[j] == "{" else -1 if text[j] == "}" else 0
        if depth == 0:
            return text[m.start(2):j + 1]
        j += 1


def main():
    ws = Path("/home/dev/multibin-ws"); shutil.rmtree(ws, ignore_errors=True); ws.mkdir()
    net = RomNetwork(ws / "d.db", ws)
    slug = net.rebrew.import_binaries([TOY, LIB], toolchain="gcc-14.2.0", confirmed=True,
                                      name="suite", blind=False, log=print)
    proj = net.store.one("SELECT * FROM projects WHERE slug=?", slug)
    units = net.store.all("SELECT DISTINCT unit FROM functions WHERE project_id=?", proj["id"])
    total = net.store.one("SELECT COUNT(*) c FROM functions WHERE project_id=?", proj["id"])["c"]
    print(f"project {slug}: {total} functions across units {[u['unit'] for u in units]}")

    agent = net.authenticate(net.register_agent("tester"))
    ok = True
    # one self-contained function from each binary; claim handles are prefixed by binary stem (non-blind)
    checks = [("toy_toy_clamp", slice_fn(TOY_C, "toy_clamp").replace("toy_clamp", "toy_toy_clamp")),
              ("lib_lib_mix", slice_fn(LIB_C, "lib_mix").replace("lib_mix", "lib_lib_mix"))]
    for handle, body in checks:
        res = net.attempt(agent, handle, body, project=slug)
        print(f"  {handle:18} matched={res['matched']} score={res['score']} :: {res['text'].splitlines()[0][:44]}")
        ok &= bool(res["matched"])
        if not res["matched"]:
            try:
                net.release(agent, handle, "", project=slug)
            except Exception:
                pass
    # confirm the two came from different binaries
    rows = {r["name"]: r["unit"] for r in net.store.all("SELECT name, unit FROM functions WHERE project_id=? AND name IN (?,?)", proj["id"], checks[0][0], checks[1][0])}
    print(f"  units: {rows}")
    ok &= rows.get("toy_toy_clamp") != rows.get("lib_lib_mix") and all(rows.values())
    print(f"\nMULTI-BINARY {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
