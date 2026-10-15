import sys; sys.path.insert(0, "/mnt/c/debug/rebrew-wtf/dev")
from pathlib import Path
import rebrew_bridge as B
root = Path("/home/dev/proj-toy")
cfg = B.load_config(root)
print("config: target=", cfg.target_binary, "arch=", cfg.arch, "cflags=", repr(cfg.cflags))
funcs = B.load_functions(root)
print("functions parsed:", len(funcs))
# extract a known function's bytes and sanity-check length
for n in ("toy_clamp", "toy_adler32"):
    f = funcs.get(n)
    if not f: print(n, "MISSING from functions.toml"); continue
    b = B.extract_raw_bytes(cfg.target_binary, f["va"], f["size"])
    print(f"{n}: symbol={f['symbol']} va={f['va']:#x} size={f['size']} extracted={len(b)} bytes head={b[:8].hex()}")
# slicer check
src = B._slice(Path("/home/dev/targets/toy.c").read_text(), "toy_clamp")
print("sliced toy_clamp:\n", src)
