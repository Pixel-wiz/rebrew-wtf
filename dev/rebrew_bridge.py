"""Bridge: drive rebrew's compile-and-compare judge as a library, the way decomp.wtf's
engine will. Given a rebrew project root, a function (symbol + VA + size) and candidate C,
return a uniform verdict: matched / score / message. No rebrew CLI per attempt.

Run as a script for the known-answer self-test (needs the gcc-14.2.0 image built):
    python rebrew_bridge.py <project-root> <original-source.c>
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import tomllib

from rebrew.config import load_config
from rebrew.formats.binary_loader import extract_raw_bytes
from rebrew.compiler.compile import compile_and_compare


@dataclass
class Verdict:
    matched: bool
    status: str          # EXACT | RELOC | NEAR_MATCHING | SIZE_MISMATCH | COMPILE_ERROR | ...
    match_count: int | None
    total: int | None
    message: str

    @property
    def score(self) -> int | None:
        """0 == byte-identical; else bytes that differ; None == didn't compile."""
        if self.matched:
            return 0
        if self.match_count is None or self.total is None:
            return None
        return self.total - self.match_count


def load_functions(root: Path) -> dict[str, dict]:
    """name -> {symbol, va, size, status, file} from rebrew-functions.toml."""
    data = tomllib.loads((root / "rebrew-functions.toml").read_text())
    out = {}
    for key, v in data.items():
        if key == "format":
            continue
        va = int(key.split(".0x")[-1], 16) if ".0x" in key else int(v.get("va", "0x0"), 16)
        out[v["name"]] = {"symbol": v["symbol"], "va": va, "size": v.get("size"),
                          "status": v.get("status"), "file": v.get("file")}
    return out


# Minimal type context so a function lifted out of its translation unit still compiles
# (size_t, fixed-width ints, NULL). The real engine stores this per-project as the shared header.
DEFAULT_HEADER = "#include <stddef.h>\n#include <stdint.h>\n#include <string.h>\n#include <stdlib.h>\n"


def judge(root: Path, symbol: str, va: int, size: int, source: Path | str, header: str = DEFAULT_HEADER) -> Verdict:
    """Compile `source` (prefixed with `header`) and compare the one function's bytes against the target."""
    cfg = load_config(root)
    target = extract_raw_bytes(cfg.target_binary, va, size)
    src_path = Path(source)
    if header:
        body = src_path.read_text()
        if header not in body:
            src_path.write_text(header + body)
    cmp = compile_and_compare(cfg, src_path, symbol, target,
                              cfg.cflags, section_va=va, use_cache=False)
    return Verdict(bool(cmp.matched), cmp.status, cmp.match_count,
                   getattr(cmp, "total", None) or (len(target) if target else None),
                   cmp.message or "")


# ---- known-answer self-test ------------------------------------------------

def elf_functions(binary: Path) -> dict[str, tuple[int, int]]:
    """name -> (va, size) from an ELF symbol table (authoritative; intake renames by address)."""
    import subprocess

    out = subprocess.run(["readelf", "-sW", str(binary)], capture_output=True, text=True).stdout
    funcs = {}
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 8 and p[3] == "FUNC" and p[6] != "UND":
            try:
                funcs[p[7]] = (int(p[1], 16), int(p[2]))
            except ValueError:
                pass
    return funcs


def _selftest(root: Path, original: Path) -> int:
    """Feed each self-contained function's ORIGINAL source back in; it must byte-match.
    Proves the judge is wired correctly end to end. Self-contained = no calls/globals, so
    it links in isolation without reloc fixups (toy_push etc. need those; skipped here)."""
    text = original.read_text()
    cfg = load_config(root)
    elf = elf_functions(cfg.target_binary)
    names = ["toy_clamp", "toy_adler32", "toy_parse_hex", "toy_count_char", "toy_state"]
    ok = tried = 0
    for name in names:
        src = _slice(text, name)
        if src is None or name not in elf:
            print(f"SKIP {name}: source or symbol not found")
            continue
        va, size = elf[name]
        tmp = root / f"_selftest_{name}.c"
        tmp.write_text(src + "\n")
        try:
            v = judge(root, name, va, size, tmp)
        finally:
            tmp.unlink(missing_ok=True)
        tried += 1
        ok += v.matched
        print(f"{'OK ' if v.matched else 'BAD'} {name:16} status={v.status:14} score={v.score} :: {v.message[:60]}")
    print(f"\n{ok}/{tried} known-answer functions byte-matched")
    # dump the raw CompareResult shape once, so the engine can be wired against confirmed fields
    try:
        name = "toy_clamp"
        va, size = elf[name]
        tmp = root / "_shape.c"
        tmp.write_text(_slice(text, name) + "\n")
        cmp = compile_and_compare(cfg, tmp, name, extract_raw_bytes(cfg.target_binary, va, size),
                                  cfg.cflags, section_va=va, use_cache=False)
        tmp.unlink(missing_ok=True)
        print("\nCompareResult fields:", {k: (v if not isinstance(v, (bytes, bytearray)) else f"<{len(v)} bytes>")
                                           for k, v in vars(cmp).items()})
    except Exception as e:
        print("shape dump failed:", e)
    return 0 if tried and ok == tried else 1


def _slice(text: str, name: str) -> str | None:
    """Extract a single top-level C function definition by name (brace-balanced)."""
    import re

    m = re.search(rf"(^|\n)([A-Za-z_][\w \*]*\b{name}\s*\([^;]*?\)\s*\{{)", text)
    if not m:
        return None
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
    return None


if __name__ == "__main__":
    sys.exit(_selftest(Path(sys.argv[1]), Path(sys.argv[2])))
