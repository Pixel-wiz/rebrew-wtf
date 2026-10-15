"""End-to-end step-4 gate: import the toy binary as a REBREW project through the decomp.wtf
engine, then run attempt() (the same path agents/MCP/rooms use) with known-good and known-bad
source. Proves the project kind is wired into the engine, not just the bridge."""
import re
import sys
from pathlib import Path

from decompnet.app.engine import RomNetwork


def slice_fn(text: str, name: str) -> str:
    m = re.search(rf"(^|\n)([A-Za-z_][\w \*]*\b{name}\s*\([^;]*?\)\s*\{{)", text)
    start = m.start(2)
    i = text.index("{", start)
    depth, j = 0, i
    while j < len(text):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
        j += 1
    raise ValueError(name)


def main() -> int:
    ws = Path("/home/dev/e2e-ws")
    import shutil
    shutil.rmtree(ws, ignore_errors=True)
    ws.mkdir(parents=True)
    net = RomNetwork(ws / "decomp.db", ws)

    slug = net.rebrew.import_binary(Path("/home/dev/targets/toy"), toolchain="gcc-14.2.0",
                                    confirmed=True, name="toy", log=print)
    proj = net.store.one("SELECT * FROM projects WHERE slug=?", slug)
    total = net.store.one("SELECT COUNT(*) c FROM functions WHERE project_id=?", proj["id"])["c"]
    print(f"imported {slug}: {total} functions")

    agent = net.authenticate(net.register_agent("tester"))

    src = Path("/home/dev/targets/toy.c").read_text()
    ok = 0
    checks = [("toy_clamp", True), ("toy_count_char", True), ("toy_state", True)]
    for name, expect in checks:
        res = net.attempt(agent, name, slice_fn(src, name), project=slug)
        got = res["matched"]
        flag = "OK " if got == expect else "BAD"
        ok += got == expect
        print(f"{flag} {name:16} matched={got} score={res['score']} :: {res['text'].splitlines()[0][:60]}")
        if not got:  # release so the next claim is allowed (a match auto-releases)
            try:
                net.release(agent, name, "", project=slug)
            except Exception:
                pass
    # negative control: wrong body must NOT match
    res = net.attempt(agent, "toy_clamp", "int toy_clamp(int v,int lo,int hi){return v;}", project=slug)
    neg_ok = not res["matched"]
    print(f"{'OK ' if neg_ok else 'BAD'} negative-control    matched={res['matched']} (want False)")
    passed = ok == len(checks) and neg_ok
    print(f"\nE2E {'PASS' if passed else 'FAIL'}: {ok}/{len(checks)} known-good matched, negative control {'held' if neg_ok else 'FAILED'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
