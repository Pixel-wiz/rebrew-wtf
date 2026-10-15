"""x86 autopilot gate: run the rebrew autopilot on the toy project (needs an r2ghidra/ghidra backend) and
report outcomes — how many functions got a compilable draft, a seed, a near, or a byte-match."""
import shutil
import sys
import time
from pathlib import Path

from decompnet.app.engine import RomNetwork


def main():
    ws = Path("/home/dev/ap-run"); shutil.rmtree(ws, ignore_errors=True); ws.mkdir()
    net = RomNetwork(ws / "d.db", ws)
    slug = net.rebrew.import_binary(Path("/home/dev/targets/toy"), toolchain="gcc-14.2.0",
                                    confirmed=True, name="toy", log=lambda *a: None)
    proj = net.store.one("SELECT * FROM projects WHERE slug=?", slug)
    try:
        st = net.start_autopilot(slug, workers=2)
    except Exception as e:  # noqa: BLE001
        print("autopilot could not start:", str(e)[:120]); return 1
    for _ in range(1200):
        s = net.autopilot_status(slug)
        if s and s.get("state") in ("done", "stopped"):
            break
        time.sleep(0.5)
    s = net.autopilot_status(slug)
    seeded = net.store.one("SELECT COUNT(*) c FROM functions WHERE project_id=? AND seed IS NOT NULL AND seed != ''", proj["id"])["c"]
    matched = net.store.one("SELECT COUNT(*) c FROM functions WHERE project_id=? AND status='matched'", proj["id"])["c"]
    best = net.store.one("SELECT COUNT(*) c FROM functions WHERE project_id=? AND best_score IS NOT NULL", proj["id"])["c"]
    print(f"autopilot: tried={s.get('tried')} matched={s.get('matched')} near={s.get('near')}")
    print(f"functions with a draft seed: {seeded}; with a compiled best attempt: {best}; matched: {matched}")
    # success = it RAN and produced seeds (drafts for agents); matches are a bonus
    ok = (s.get("tried") or 0) > 0 and seeded > 0
    print(f"\nAUTOPILOT {'PASS (ran + seeded drafts)' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
