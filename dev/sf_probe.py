import sqlite3, json, urllib.request, urllib.error
db = sqlite3.connect('file:/home/decomp/Decomp/.decomp/decomp.db?mode=ro', uri=True); db.row_factory = sqlite3.Row
cfg = json.loads(db.execute("select config from projects where slug='starfox64'").fetchone()[0])
link = cfg.get("link") or {}
url = link.get("url"); room = link.get("room")
print("stored room link:", url, "room=", room, "member=", link.get("member"))
if url:
    try:
        r = urllib.request.urlopen(f"{url}/collab/hello?invite=open&room={room}", timeout=15)
        print("room hello:", r.status, r.read()[:160].decode('utf-8','replace'))
    except urllib.error.HTTPError as e:
        print("room reachable, hello HTTP", e.code, e.read()[:120].decode('utf-8','replace'))
    except Exception as e:
        print("room NOT reachable:", type(e).__name__, str(e)[:100])
