"""Live SF64 second-member session, host side (installed decomp.wtf in decomp-wtf distro). Works on a COPY of
the Star Fox 64 project — never the live joined project. Resets one known function to 'open', hosts a room with
a real cloudflare tunnel, and judges with IDO 5.3 until the guest is done."""
import json, re, shutil, sqlite3, subprocess, sys, threading, time
from pathlib import Path
import uvicorn
from decompnet.app import collab
from decompnet.app.engine import RomNetwork

H = Path("/home/decomp/sf-host"); PORT = 6841
CF = "cloudflared"
LINK = Path("/home/decomp/sf-live-link.json")
FUNC = "func_80010800"


def main():
    shutil.rmtree(H, ignore_errors=True); (H / ".decomp").mkdir(parents=True)
    shutil.copytree("/home/decomp/Decomp/starfox64", H / "starfox64")
    shutil.copy("/home/decomp/Decomp/.decomp/decomp.db", H / ".decomp" / "decomp.db")
    LINK.unlink(missing_ok=True); Path("/home/decomp/sf-live-done").unlink(missing_ok=True)
    con = sqlite3.connect(H / ".decomp" / "decomp.db")
    row = con.execute("select id,config from projects where slug='starfox64'").fetchone()
    pid, cfg = row[0], json.loads(row[1]); cfg.pop("link", None)
    con.execute("update projects set root=?, config=? where id=?", (str(H / "starfox64"), json.dumps(cfg), pid))
    con.execute("update functions set status='open', matched_source=NULL, matched_agent_id=NULL, matched_at=NULL, "
                "best_source=NULL, best_score=NULL where name=? and project_id=?", (FUNC, pid))
    con.execute("delete from claims"); con.execute("delete from agents"); con.commit(); con.close()

    net = RomNetwork(H / ".decomp" / "decomp.db", H)
    slug = "starfox64"
    net.rooms[slug] = collab.Room(net, slug)
    code = net.rooms[slug].open_invite()
    server = uvicorn.Server(uvicorn.Config(collab.host_app(net, net.rooms), host="127.0.0.1", port=PORT, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started: break
        time.sleep(0.1)
    proc = subprocess.Popen([CF, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    public, t0 = None, time.time()
    while time.time() - t0 < 60:
        line = proc.stdout.readline()
        if not line: time.sleep(0.1); continue
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m: public = m.group(0); break
    if not public:
        print("SF-HOST: no tunnel"); proc.terminate(); return 1
    time.sleep(8)  # let the edge propagate
    LINK.write_text(json.dumps({"link": f"{public}/join/{code}#room={slug}", "func": FUNC}))
    print(f"SF-HOST: Star Fox 64 room live at {public}; {FUNC} open for a member to match")
    for _ in range(1200):
        if Path("/home/decomp/sf-live-done").exists(): break
        time.sleep(0.5)
    st = net.store.one("SELECT status, matched_agent_id FROM functions WHERE name=? AND project_id=?", FUNC, pid)
    who = net.store.one("SELECT name FROM agents WHERE id=?", st["matched_agent_id"]) if st and st["matched_agent_id"] else None
    print(f"SF-HOST: members={len(net.rooms[slug].members())} {FUNC} status={st['status'] if st else '?'} "
          f"matched_by={who['name'] if who else None}")
    proc.terminate(); server.should_exit = True
    return 0


if __name__ == "__main__":
    sys.exit(main())
