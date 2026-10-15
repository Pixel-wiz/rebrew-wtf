"""Ghidra drafts: decompiled C for platforms m2c doesn't read (x86, AArch64, Xbox 360 PowerPC, SuperH...).

Optional: Ghidra is large (540 MB) and needs Java 21+. Headless Ghidra analyses a unit's target object once
and decompiles all its functions; the result is cached next to the project, so the cost (tens of seconds,
mostly starting the JVM) is paid once per source file.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from importlib import resources
from pathlib import Path

from .. import toolchains
from ..limits import capped


def available() -> bool:
    return toolchains.installed("ghidra") is not None and toolchains.java_version() >= 21


def _headless() -> Path:
    base = toolchains.path("ghidra") / "support"
    return base / ("analyzeHeadless.bat" if os.name == "nt" else "analyzeHeadless")


def functions(obj: Path, cache_dir: Path, timeout: float = 900) -> dict[str, tuple[int, int]]:
    """name -> (entry VA, body size) for every function Ghidra finds, WITHOUT decompiling (fast).
    This is how STRIPPED binaries (no symbol table) are onboarded: Ghidra's auto-analysis recovers
    function boundaries where the symbol enumerator finds nothing. Cached by the object's content."""
    data = obj.read_bytes()
    key = hashlib.sha1(data).hexdigest()[:16]
    cache = cache_dir / f"{obj.stem}-{key}-funcs.json"
    if cache.exists():
        return {k: (v[0], v[1]) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
    if not available():
        return {}
    rows = _run_script(obj, "DecompWtfFunctions.java", timeout)
    result = {r["name"]: (int(r["va"]), int(r["size"])) for r in rows if int(r.get("size", 0)) > 0}
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({k: list(v) for k, v in result.items()}), encoding="utf-8")
    return result


def _run_script(obj: Path, script: str, timeout: float) -> list[dict]:
    """Headless-analyse `obj` and run `script` (writes JSONL to its first arg); return the parsed rows."""
    with tempfile.TemporaryDirectory(prefix="decompwtf-ghidra-") as tmp:
        scripts = Path(tmp) / "scripts"
        scripts.mkdir()
        src = resources.files("decompnet.forks").joinpath("ghidra_scripts", script)
        (scripts / script).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        out = Path(tmp) / "out.jsonl"
        target = Path(tmp) / obj.name
        shutil.copyfile(obj, target)
        argv = [str(_headless()), tmp, "decompwtf", "-import", str(target), "-scriptPath", str(scripts),
                "-postScript", script, str(out), "-deleteProject"]
        try:
            subprocess.run(capped(argv), capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            return []
        rows = []
        if out.exists():
            for line in out.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
        return rows


def decompile_object(obj: Path, cache_dir: Path, timeout: float = 900) -> dict[str, str]:
    """name -> decompiled C for every function in an object file (cached by the object's content)."""
    data = obj.read_bytes()
    key = hashlib.sha1(data).hexdigest()[:16]
    cache = cache_dir / f"{obj.stem}-{key}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if not available():
        return {}
    with tempfile.TemporaryDirectory(prefix="decompwtf-ghidra-") as tmp:
        scripts = Path(tmp) / "scripts"
        scripts.mkdir()
        src = resources.files("decompnet.forks").joinpath("ghidra_scripts", "DecompWtfExport.java")
        (scripts / "DecompWtfExport.java").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        out = Path(tmp) / "out.jsonl"
        target = Path(tmp) / obj.name
        shutil.copyfile(obj, target)
        argv = [str(_headless()), tmp, "decompwtf", "-import", str(target), "-scriptPath", str(scripts),
                "-postScript", "DecompWtfExport.java", str(out), "-deleteProject"]
        try:
            subprocess.run(capped(argv), capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            return {}
        result = {}
        if out.exists():
            for line in out.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                result[row["name"]] = row["c"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result), encoding="utf-8")
    return result
