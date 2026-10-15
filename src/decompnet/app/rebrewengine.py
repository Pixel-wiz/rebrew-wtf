"""Rebrew-backed projects: byte-matching decompilation of PC programs (PE/ELF/Mach-O),
function by function, judged by rebrew's compiler-in-the-loop compare. The rest of decomp.wtf
— dashboard, MCP tools, agents, team rooms — is reused unchanged: a rebrew project is an
ordinary project with kind="rebrew", and only the compile+judge seam is replaced.

rebrew (maci0/rebrew, MIT) must be importable and Docker must be reachable (its compiler
toolchains run in images). See dev/PLAN.md for how the environment is set up.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from ..compiler import CompileResult
from ..elfobj import FunctionObj, extract_function
from ..network import NetworkError

# Binary format -> decomp.wtf arch label for the disassembler/scoring display.
_ARCH = {"x86_64": "x86_64", "x86_32": "x86", "arm64": "arm", "arm32": "arm"}


def available() -> tuple[bool, str]:
    """(usable, why-not): rebrew importable and Docker reachable."""
    try:
        import rebrew  # noqa: F401
    except ImportError as e:
        return False, f"rebrew not installed: {e}"
    import shutil
    import subprocess

    if not shutil.which("docker"):
        return False, "docker CLI not on PATH (rebrew toolchains run in images)"
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=15, check=True)
    except Exception as e:  # noqa: BLE001
        return False, f"docker not reachable: {e}"
    return True, ""


class RebrewEngine:
    """Attached to the network as `self.rebrew`, mirroring `self.forks`. Holds the compile+judge
    seam and the importer; claims/records/rooms/dashboard stay in the Network base class."""

    def __init__(self, net):
        self.net = net

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def is_rebrew(proj) -> bool:
        return json.loads(proj["config"]).get("kind") == "rebrew"

    def _cfg(self, proj):
        """rebrew ProjectConfig for this project (its intake tree lives at config.rebrew.root)."""
        from rebrew.config import load_config

        root = Path(json.loads(proj["config"])["rebrew"]["root"])
        return load_config(root)

    def _arch(self, proj) -> str:
        return _ARCH.get(json.loads(proj["config"]).get("arch", "x86_64"), "x86_64")

    # ------------------------------------------------------------------ import

    @staticmethod
    def is_member_shell(proj) -> bool:
        """A blind-room member's local project: the room's compiler but NO binary and NO functions until the
        host hands one out on claim. Claims, asm and verdicts all proxy to the host over the link."""
        c = json.loads(proj["config"])
        return c.get("kind") == "rebrew" and bool(c.get("member_shell"))

    def create_member_shell(self, hello: dict, link_info: dict, log=print) -> str:
        """Local project for joining a blind room: holds the compiler, no binary, no functions."""
        base = _slug(f"room-{hello.get('room', 'binary')}")
        slug, n = base, 2
        while self.net.store.one("SELECT 1 FROM projects WHERE slug=?", slug):
            slug, n = f"{base}-{n}", n + 1
        config = {
            "kind": "rebrew", "blind": True, "member_shell": True,
            "arch": hello.get("arch") or "x86_64", "format": hello.get("format") or "pe",
            "compiler": hello.get("compiler") or {"toolchain": "gcc-14.2.0", "flags": [], "timeout": 60},
            "context": {"file": None}, "link": link_info,
        }
        import time as _t
        with self.net.store.tx() as db:
            pid = db.execute(
                "INSERT INTO projects(slug,name,description,arch,big_endian,root,config) VALUES(?,?,?,?,?,?,?)",
                (slug, hello.get("title") or "a private binary", "blind room (member)",
                 _ARCH.get(hello.get("arch") or "x86_64", "x86_64"), 0, str(self.net.workspace / slug),
                 json.dumps(config))).lastrowid
            db.execute("INSERT INTO context_versions(project_id,version,header,agent_id,message,created_at,unit) "
                       "VALUES(?,?,?,?,?,?,?)", (pid, 1, _BASE_HEADER, None, "basic types", _t.time(), ""))
        return slug

    def record_claimed(self, proj, name: str, vram: int, asm: str) -> None:
        """Member shell: store the single function the host just handed out, so the member's agents can read its
        asm and the local claim/list reflect it. Target bytes are NEVER stored here — the host judges."""
        if self.net.store.one("SELECT 1 FROM functions WHERE project_id=? AND name=?", proj["id"], name):
            return
        with self.net.store.tx() as db:
            db.execute(
                "INSERT INTO functions(project_id,name,size,n_insns,target,relocs,asm,seed,unit,vram,rom_offset,status) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (proj["id"], name, 0, asm.count("\n/") if asm else 0, b"", json.dumps({"symbol": name}),
                 asm or "", None, "", int(vram or 0), int(vram or 0), "open"))

    @staticmethod
    def is_blind(proj) -> bool:
        """Blind project: room members are handed one claimed function's asm at a time and never the
        binary, the function list, real symbol names, or the project's scope. The host sees everything."""
        return bool(json.loads(proj["config"]).get("blind"))

    def import_binary(self, path: Path, *, toolchain: str, confirmed: bool, name: str = "",
                      blind: bool = False, log=print) -> str:
        """Onboard a program the user owns: rebrew intake, then one function row per symbol.
        Target bytes are sliced from the binary and stored like a ROM project's targets.
        `blind`: hide scope from room members (see is_blind)."""
        from rebrew.config import load_config
        from rebrew.formats.binary_loader import extract_raw_bytes

        if not confirmed:
            raise NetworkError("confirm you have the right to reverse this binary")
        path = Path(path)
        base = _slug(name or path.stem)
        slug, n = base, 2
        while self.net.store.one("SELECT 1 FROM projects WHERE slug=?", slug) or (self.net.workspace / slug).exists():
            slug, n = f"{base}-{n}", n + 1
        workdir = self.net.workspace / slug
        workdir.mkdir(parents=True)

        # rebrew intake: scaffold + detect + per-function stubs, pinned to the chosen toolchain.
        self._intake(workdir, path, toolchain, log)
        cfg = load_config(workdir)
        funcs = self._functions(cfg)   # name -> (symbol, va, size)
        if not funcs:
            raise NetworkError("no functions found in the binary's symbol table")
        arch = _ARCH.get(cfg.arch, "x86_64")

        import hashlib
        program_sha1 = hashlib.sha1(Path(cfg.target_binary).read_bytes()).hexdigest()
        config = {
            "kind": "rebrew", "arch": cfg.arch, "format": cfg.binary_format, "blind": bool(blind),
            # program_sha1 lets non-blind room members verify they have the same binary. Omitted (None at
            # read time) for blind rooms, where members never have the binary to check.
            "program_sha1": None if blind else program_sha1,
            "rebrew": {"root": str(workdir), "toolchain": toolchain},
            "compiler": {"toolchain": toolchain, "flags": _split(cfg.cflags), "timeout": 60},
            "context": {"file": None},
            "legal": {"basis": "owner-authorized", "statement": "imported by someone authorized to reverse it",
                      "confirmed_at": time.time()},
        }
        now = time.time()
        with self.net.store.tx() as db:
            pid = db.execute(
                "INSERT INTO projects(slug,name,description,arch,big_endian,root,config) VALUES(?,?,?,?,?,?,?)",
                (slug, name or path.stem, f"{cfg.binary_format.upper()} {cfg.arch} · {len(funcs)} functions",
                 arch, 0, str(workdir), json.dumps(config))).lastrowid
            n = self._insert_functions(db, pid, cfg.target_binary, funcs, arch, blind, unit="", tag="")
            db.execute("INSERT INTO context_versions(project_id,version,header,agent_id,message,created_at,unit) "
                       "VALUES(?,?,?,?,?,?,?)", (pid, 1, _BASE_HEADER, None, "basic types", now, ""))
            self.net._event(db, pid, None, "import", f"{n} functions from {name or path.stem}")
        log(f"ready: {n} functions to rebuild")
        return slug

    def import_binaries(self, paths: list[Path], *, toolchain: str, confirmed: bool, name: str = "",
                        blind: bool = False, log=print) -> str:
        """One project spanning several binaries (an exe and its DLLs). The first binary creates the project and
        fixes the toolchain; every binary's functions are added, namespaced by a per-binary unit so an exe and a
        DLL that share an address or a symbol name never collide. Functions are judged by their stored bytes, so
        no re-intake is needed per binary."""
        from rebrew.config import load_config

        paths = [Path(p) for p in paths]
        if not paths:
            raise NetworkError("give at least one binary")
        if len(paths) == 1:
            return self.import_binary(paths[0], toolchain=toolchain, confirmed=confirmed, name=name,
                                      blind=blind, log=log)
        if not confirmed:
            raise NetworkError("confirm you have the right to reverse these binaries")
        base = _slug(name or paths[0].stem)
        slug, k = base, 2
        while self.net.store.one("SELECT 1 FROM projects WHERE slug=?", slug) or (self.net.workspace / slug).exists():
            slug, k = f"{base}-{k}", k + 1
        workdir = self.net.workspace / slug
        workdir.mkdir(parents=True)
        self._intake(workdir, paths[0], toolchain, log)   # first binary scaffolds the project + toolchain
        cfg = load_config(workdir)
        arch = _ARCH.get(cfg.arch, "x86_64")
        config = {
            "kind": "rebrew", "arch": cfg.arch, "format": cfg.binary_format, "blind": bool(blind),
            "program_sha1": None,  # multi-binary: members verify per-binary on claim, not one project hash
            "rebrew": {"root": str(workdir), "toolchain": toolchain},
            "binaries": [p.name for p in paths],
            "compiler": {"toolchain": toolchain, "flags": _split(cfg.cflags), "timeout": 60},
            "context": {"file": None},
            "legal": {"basis": "owner-authorized", "statement": "imported by someone authorized to reverse it",
                      "confirmed_at": time.time()},
        }
        now = time.time()
        total = 0
        with self.net.store.tx() as db:
            pid = db.execute(
                "INSERT INTO projects(slug,name,description,arch,big_endian,root,config) VALUES(?,?,?,?,?,?,?)",
                (slug, name or paths[0].stem, f"{cfg.binary_format.upper()} {cfg.arch} · {len(paths)} binaries",
                 arch, 0, str(workdir), json.dumps(config))).lastrowid
            for i, p in enumerate(paths):
                funcs = _symbols_via_lief(p)
                # unit = the binary's name (host-visible); tag namespaces claim handles. Blind uses an opaque
                # unit id (u0, u1, …) so the filename is never revealed to members.
                tag = f"u{i}" if blind else p.stem
                total += self._insert_functions(db, pid, str(p), funcs, arch, blind, unit=p.name, tag=tag)
            db.execute("INSERT INTO context_versions(project_id,version,header,agent_id,message,created_at,unit) "
                       "VALUES(?,?,?,?,?,?,?)", (pid, 1, _BASE_HEADER, None, "basic types", now, ""))
            self.net._event(db, pid, None, "import", f"{total} functions from {len(paths)} binaries")
        log(f"ready: {total} functions across {len(paths)} binaries")
        return slug

    def _insert_functions(self, db, pid: int, binary: str, funcs: dict, arch: str, blind: bool,
                          unit: str, tag: str) -> int:
        """Insert one binary's functions. `tag` namespaces the claim-handle/extract-symbol so multiple binaries
        never collide; empty for a single-binary project (keeps the plain names)."""
        from rebrew.formats.binary_loader import extract_raw_bytes

        pre = f"{tag}_" if tag else ""
        n = 0
        for fname, (symbol, va, size) in sorted(funcs.items(), key=lambda kv: kv[1][1]):
            target = extract_raw_bytes(binary, va, size)
            if not target:
                continue
            # Matching slices the target by ADDRESS not name, so the claim handle = extract symbol can be anything
            # the member will define. Blind → opaque fcn_<va>; multi-binary → prefixed so an exe+DLL never clash.
            disp = f"{pre}fcn_{va:08x}" if blind else (f"{pre}{fname}" if pre else fname)
            esym = disp if (blind or pre) else symbol
            asm, n_insns = self._disasm(disp, target, arch, va)
            db.execute(
                "INSERT INTO functions(project_id,name,size,n_insns,target,relocs,asm,seed,unit,vram,rom_offset) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (pid, disp, size, n_insns, target, json.dumps({"symbol": esym}), asm, None, unit, va, va))
            db.execute("INSERT INTO symbols(project_id,name,address,size,kind,preview) VALUES(?,?,?,?,?,?)",
                       (pid, disp, va, size, "func", None))
            n += 1
        return n

    @staticmethod
    def _disasm(name: str, code: bytes, arch: str, va: int) -> tuple[str, int]:
        """Readable disassembly listing + instruction count for a function's bytes.
        Feeds the agent's view and, in blind mode, the only thing a member is handed."""
        if arch not in ("x86", "x86_64"):
            return "", 0
        from .. import scoring

        try:
            insns = scoring.disassemble(FunctionObj(name, arch, False, code, []))
        except Exception:  # noqa: BLE001
            return "", 0
        lines = [f"glabel {name}"]
        for ins in insns:
            lines.append(f"/* {va + ins.offset:X} */  {ins.text}")
        lines.append(f"endlabel {name}")
        return "\n".join(lines), len(insns)

    def _intake(self, workdir: Path, binary: Path, toolchain: str, log) -> None:
        import subprocess

        env = {"REBREW_TOOLCHAINS_DIR": str(_toolchains_dir())}
        r = subprocess.run(["rebrew", "intake", str(binary), "--toolchain", toolchain, "--json"],
                           cwd=workdir, capture_output=True, text=True, env={**_osenv(), **env}, timeout=600)
        if r.returncode != 0:
            raise NetworkError(f"rebrew intake failed: {(r.stderr or r.stdout).strip()[-400:]}")

    @staticmethod
    def _functions(cfg) -> dict[str, tuple[str, int, int]]:
        """name -> (symbol, va, size) from the binary's own symbol table (authoritative)."""
        return _symbols_via_lief(cfg.target_binary)

    # ------------------------------------------------- compile + judge seam

    def compile(self, proj, header: str, source: str) -> CompileResult:
        """Compile candidate C (header + source) to a .o/.obj via rebrew's toolchain image.
        Returns the object bytes in CompileResult.obj for evaluate() to extract + compare."""
        from rebrew.compiler.compile import compile_to_obj

        cfg = self._cfg(proj)
        with tempfile.TemporaryDirectory(prefix="rebrew-wtf-") as tmp:
            src = Path(tmp) / "func.c"
            src.write_text((header or "") + "\n" + source + "\n")
            obj_path, err = compile_to_obj(cfg, src, cfg.cflags, tmp, use_cache=False)
            if obj_path is None:
                return CompileResult(False, None, err or "compile failed")
            return CompileResult(True, Path(obj_path).read_bytes(), "")

    def evaluate(self, fn, proj, obj: bytes):
        """(candidate FunctionObj | None, verdict bool, problems): verdict from rebrew's byte compare;
        candidate FunctionObj is for decomp.wtf's displayed diff only."""
        from rebrew.compiler.compile import _extract_and_compare

        symbol = json.loads(fn["relocs"])["symbol"]
        arch = self._arch(proj)
        cand = extract_function(obj, symbol) if arch in ("x86", "x86_64") else None
        with tempfile.TemporaryDirectory(prefix="rebrew-wtf-") as tmp:
            op = Path(tmp) / "cand.o"
            op.write_bytes(obj)
            cmp = _extract_and_compare(str(op), symbol, bytes(fn["target"]), section_va=fn["vram"])
        problems = [] if cmp.matched else [cmp.message]
        if cand is None:   # arch decomp.wtf can't disassemble: synthesize from compiled bytes for display
            cand = FunctionObj(fn["name"], arch, False, cmp.obj_bytes or b"", [])
        return cand, bool(cmp.matched), problems

    # ------------------------------------------------- autopilot (x86 drafts)

    def autopilot_prepare(self, slug: str) -> list[int]:
        """Open functions, smallest first, for autopilot to try a decompiler draft on. Needs a rebrew decompiler
        backend (r2dec/r2ghidra/ghidra); raises a clear message if none is available, like the m2c path does."""
        proj = self.net._project(slug)
        if self._decompiler(proj) is None:
            raise NetworkError("x86 autopilot needs a decompiler backend (radare2 + r2dec, or ghidra) reachable "
                               "by rebrew; agents still work without it")
        return [r["id"] for r in self.net.store.all(
            "SELECT id FROM functions WHERE project_id=? AND status='open' ORDER BY n_insns, vram", proj["id"])]

    def _decompiler(self, proj) -> str | None:
        """First rebrew decompiler backend that actually answers for this project, or None."""
        import subprocess

        root = json.loads(proj["config"])["rebrew"]["root"]
        fn = self.net.store.one("SELECT vram FROM functions WHERE project_id=? AND status='open' ORDER BY n_insns LIMIT 1",
                                proj["id"])
        if not fn:
            return None
        for backend in ("r2dec", "r2ghidra", "ghidra"):
            try:
                r = subprocess.run(["rebrew", "decompile", hex(fn["vram"]), "--decompiler", backend, "--json"],
                                   cwd=root, capture_output=True, text=True, env=_osenv(), timeout=120)
                if r.returncode == 0 and '"error"' not in r.stdout:
                    return backend
            except Exception:  # noqa: BLE001
                continue
        return None

    def autopilot_one(self, agent, proj, fid: int) -> str:
        """Decompile one function with rebrew, compile+judge the draft, seed it as the best attempt. Mirrors the
        ROM autopilot's claim bookkeeping. match | near | far | fail | skip."""
        import subprocess

        now = time.time()
        root = json.loads(proj["config"])["rebrew"]["root"]
        backend = getattr(self, "_ap_backend", None) or self._decompiler(proj)
        self._ap_backend = backend
        with self.net.store.tx() as db:
            self.net._expire_claims(db)
            fn = db.execute("SELECT * FROM functions WHERE id=?", (fid,)).fetchone()
            if fn is None or fn["status"] != "open" or db.execute("SELECT 1 FROM claims WHERE function_id=?", (fid,)).fetchone():
                return "skip"
            db.execute("INSERT INTO claims VALUES(?,?,?,?)", (fid, agent.id, now, now + 300))
        try:
            ctx = self.net._context(proj["id"], fn["unit"])
            try:
                r = subprocess.run(["rebrew", "decompile", hex(fn["vram"]), "--decompiler", backend, "--json"],
                                   cwd=root, capture_output=True, text=True, env=_osenv(), timeout=120)
                draft = (json.loads(r.stdout).get("code") or "") if r.returncode == 0 else ""
            except Exception:  # noqa: BLE001
                draft = ""
            if not draft.strip() or not backend:
                return "fail"
            source = f"/* draft via rebrew {backend}, tried by autopilot */\n{draft}\n"
            result = self.compile(proj, ctx["header"], source)
            if not result.ok:
                return "fail"
            cand, verdict, _ = self.evaluate(fn, proj, result.obj)
            if cand is None:
                return "fail"
            from .. import scoring
            d = scoring.diff(self.target_obj(fn, proj), cand)
            score = 0 if verdict else max(1, d.score)
            self.net._record(fn, agent, score, source, ctx["version"], matched=bool(verdict))
            return "match" if verdict else "near" if d.percent >= 90 else "far"
        finally:
            with self.net.store.tx() as db:
                db.execute("DELETE FROM claims WHERE function_id=? AND agent_id=?", (fid, agent.id))

    def overview(self, slug: str, proj, agg) -> dict:
        """Dashboard/room overview for a rebrew project (its toolchain lives in rebrew, not decompnet)."""
        cfg = json.loads(proj["config"])
        comp = cfg.get("compiler", {})
        return {
            "slug": proj["slug"], "title": proj["name"], "description": proj["description"],
            "platform": "pc", "platform_name": (cfg.get("format") or "pe").upper() + " " + (cfg.get("arch") or ""),
            "compilers": [], "kind": "rebrew", "blind": bool(cfg.get("blind")),
            "compiler": {"toolchain": comp.get("toolchain"), "name": comp.get("toolchain"),
                         "flags": comp.get("flags", []), "installed": True, "proprietary": False,
                         "supported": True, "wsl": False},
            "functions": agg["total"] or 0, "matched": agg["matched"] or 0, "bytes": agg["bytes"] or 0,
            "matched_bytes": agg["matched_bytes"] or 0, "attempts": agg["attempts"] or 0,
            "context_version": self.net._context(proj["id"])["version"], "folder": proj["root"],
            "export": None, "exportable": False, "room": self.net._room_info(proj["slug"]),
        }

    def target_obj(self, fn, proj) -> FunctionObj:
        """Target as a FunctionObj for the displayed diff. Relocs empty (the match verdict is rebrew's,
        not this diff's): for non-matches the call-site rows may look noisier than they are."""
        return FunctionObj(fn["name"], self._arch(proj), False, bytes(fn["target"]), [])


# --------------------------------------------------------------------- utils

def _symbols_via_lief(binary: Path) -> dict[str, tuple[str, int, int]]:
    """name -> (symbol, va, size) from a linked ELF/PE via LIEF (fallback enumerator)."""
    import lief

    out: dict[str, tuple[str, int, int]] = {}
    b = lief.parse(str(binary))
    if b is None:
        return out
    for sym in getattr(b, "symbols", []):
        name = getattr(sym, "name", "") or ""
        is_func = getattr(getattr(sym, "type", None), "name", "") == "FUNC" or getattr(sym, "is_function", False)
        va = int(getattr(sym, "value", 0) or 0)
        size = int(getattr(sym, "size", 0) or 0)
        if name and is_func and va and size:
            out[name] = (name, va, size)
    return out


def _slug(s: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out or "binary"


def _split(cflags) -> list[str]:
    import shlex

    return cflags if isinstance(cflags, list) else shlex.split(cflags or "")


def _toolchains_dir() -> Path:
    import os

    return Path(os.environ.get("REBREW_TOOLCHAINS_DIR", Path.home() / "recompile-toolchains"))


def _osenv() -> dict:
    import os

    return dict(os.environ)


_BASE_HEADER = (
    "#include <stddef.h>\n#include <stdint.h>\n#include <string.h>\n#include <stdlib.h>\n"
    "typedef signed char s8;\ntypedef unsigned char u8;\ntypedef signed short s16;\n"
    "typedef unsigned short u16;\ntypedef signed int s32;\ntypedef unsigned int u32;\n"
)
