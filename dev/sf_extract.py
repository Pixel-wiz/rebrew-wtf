import sqlite3, json
db = sqlite3.connect('file:/home/decomp/Decomp/.decomp/decomp.db?mode=ro', uri=True); db.row_factory = sqlite3.Row
# a small matched function with saved source + no relocs (self-contained, compiles+links cleanly)
r = db.execute("""select name, n_insns, length(matched_source) ml, matched_source from functions
                  where status='matched' and matched_source is not null and relocs='[]'
                  order by n_insns limit 1""").fetchone()
print("FUNC", r["name"], "insns", r["n_insns"], "srclen", r["ml"])
cfg = json.loads(db.execute("select config from projects where slug='starfox64'").fetchone()[0])
print("FLAGS", cfg["compiler"]["flags"])
open("/home/decomp/sf-func.json","w").write(json.dumps({"name": r["name"], "source": r["matched_source"],
                                                        "flags": cfg["compiler"]["flags"]}))
print("wrote /home/decomp/sf-func.json")
