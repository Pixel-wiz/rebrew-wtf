#!/usr/bin/env python3
"""Apply the ELF .o dispatch fix to an installed rebrew (bug: parse_obj_symbol_and_relocs
never routes ELF objects to _parse_elf_symbol_bytes, so gcc/clang projects fail EXTRACT_ERROR).
Idempotent. Usage: python patch_rebrew_elf.py <path-to-site-packages-rebrew>"""
import sys
from pathlib import Path

p = Path(sys.argv[1]) / "matcher" / "parsers.py"
t = p.read_text()
marker = "rebrew-wtf patch: ELF .o objects"
if marker in t:
    print("already patched:", p); sys.exit(0)
anchor = "            return _parse_coff(obj_path, coff_path, symbol)\n\n    return _parse_coff(obj_path, None, symbol)"
patch = (
    "            return _parse_coff(obj_path, coff_path, symbol)\n\n"
    "    # rebrew-wtf patch: ELF .o objects (gcc/clang posix profiles) have a working\n"
    "    # extractor (_parse_elf_symbol_bytes) but were never dispatched here.\n"
    "    if _detect_obj_format_data(magic) == \"elf\":\n"
    "        code, reloc_dict = _parse_elf_symbol_bytes(str(obj_path), symbol)\n"
    "        return code, reloc_dict, []\n\n"
    "    return _parse_coff(obj_path, None, symbol)"
)
if anchor not in t:
    print("ANCHOR NOT FOUND — rebrew layout changed; patch manually:", p); sys.exit(1)
p.write_text(t.replace(anchor, patch, 1))
print("patched:", p)
