"""Step-6 gate: a blind rebrew project hides scope from members. A member (untrusted agent)
sees only functions they have claimed; the host (trusted) sees everything."""
import sys
import shutil
from pathlib import Path

from decompnet.app.engine import RomNetwork


def main() -> int:
    ws = Path("/home/dev/blind-ws")
    shutil.rmtree(ws, ignore_errors=True)
    ws.mkdir(parents=True)
    net = RomNetwork(ws / "d.db", ws)

    slug = net.rebrew.import_binary(Path("/home/dev/targets/toy"), toolchain="gcc-14.2.0",
                                    confirmed=True, name="toy", blind=True, log=lambda *a: None)
    total = net.store.one("SELECT COUNT(*) c FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=?", slug)["c"]

    host = net.authenticate(net.register_agent("host", trusted=True))
    member = net.authenticate(net.register_agent("member", trusted=False))

    host_view = net.list_functions(slug, "all", 100, host)
    host_sees = host_view.count("@0x")
    member_before = net.list_functions(slug, "open", 100, member)

    # member claims one function (by strategy — the coordinator hands one out)
    claimed = net.claim(member, project=slug)
    member_after = net.list_functions(slug, "open", 100, member)
    member_sees = member_after.count("@0x")

    ok = True
    print(f"total functions in project: {total}")
    print(f"host sees: {host_sees} (expect {total})"); ok &= host_sees == total
    print(f"member before any claim: {member_before.count('@0x')} listed (expect 0)"); ok &= member_before.count("@0x") == 0
    print(f"  member message: {member_before.splitlines()[0][:70]}")
    print(f"member after claiming: sees {member_sees} (expect 1)"); ok &= member_sees == 1
    print(f"  claim result: {claimed.splitlines()[0][:70]}")
    # member must NOT be able to list the whole set via status=all either
    member_all = net.list_functions(slug, "all", 100, member)
    leaked = member_all.count("@0x")
    print(f"member status=all: sees {leaked} (expect 1 — no scope leak)"); ok &= leaked == 1

    # no REAL symbol name (toy_*) may reach the member — only opaque fcn_<va>
    member_text = member_after + "\n" + claimed + "\n" + member_all
    name_leak = "toy_" in member_text
    print(f"real-name leak to member: {name_leak} (expect False); names seen: "
          f"{[w for w in member_text.split() if w.startswith(('fcn_','toy_'))][:3]}")
    ok &= not name_leak
    # In blind mode real names live ONLY in the host's binary, never in the shared DB — so the host's
    # decomp.wtf view is opaque too (stronger: nothing stored carries the real identity).
    print(f"shared DB carries real names: {'toy_' in host_view} (expect False — names only in the binary)")
    ok &= "toy_" not in host_view

    print(f"\nBLIND MODE {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
