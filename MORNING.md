# rebrew-wtf — morning summary

A working fork of decomp.wtf that does **byte-matching decompilation of PC programs**
(PE/ELF, GCC/Clang/MinGW/MSVC) one function at a time, reusing decomp.wtf's dashboard,
MCP tools, agents, and team rooms. Built and verified overnight.

## What works (verified, not just written)

1. **Fork** at `C:\debug\rebrew-wtf` (branch `rebrew`). Base suite: zero regressions from my changes
   (identical pass/fail with and without — proven by stash-and-compare).
2. **Import a binary** → rebrew intake + per-function rows with target bytes, disassembly, instruction counts.
3. **Judge**: an agent's C is compiled with the real toolchain and compared byte-for-byte to the target.
   Proven: `toy_clamp`/`toy_count_char`/`toy_state` score **0 (byte-identical)** through `attempt()` — the
   same path agents/MCP/rooms use — and a wrong body is correctly rejected.
4. **Blind mode** (your security requirement): a member sees only the one function they've claimed — never the
   binary, the function list, the scope, or the real symbol names. Real names live only in your binary; the
   shared DB carries opaque `fcn_<addr>`. Verified: host sees all 15 toy functions, a member sees 0 then 1
   after claiming, no leak via `status=all`, no `toy_*` name ever reaches the member.

## Found and fixed a real rebrew bug

rebrew 4.1.0 never routes ELF `.o` files to its own ELF extractor (they fall through to the COFF parser and
fail). Patched reproducibly (`dev/patch_rebrew_elf.py`); worth upstreaming to maci0/rebrew.

5. **Team rooms — both kinds work**, verified in-process (host + guest, the pattern decomp.wtf's own tests use):
   - **Normal room**: the guest joins with their own copy of the binary, works locally, and the host confirms
     the match. Verified: guest claims `toy_clamp`, matches, host records it matched.
   - **Blind room (your case)**: the guest joins with **no binary at all**. The host hands out one function's
     disassembly (opaque `fcn_<addr>`) on claim and judges every attempt remotely. Verified: the guest matched
     the function while holding **1 function and 0 bytes of the binary** — nothing about your binary leaves the host.

## What's designed but not finished (all smaller than what's done)

- **Two-machine room over a real tunnel**: rooms are proven in-process; this is just the network-transport check.
- **Import UI/MCP**: `import_binary` works as a library call; it still needs a GUI "new project" button and/or
  an MCP tool. Multi-binary projects (an exe + its DLLs) are allowed by the schema but the importer does one binary.
- **Production home**: rebrew's compilers need Docker. I built an isolated WSL distro `rebrew-dev` for this so
  your Star Fox room (in `decomp-wtf`) is untouched. Decide whether prod runs there or Docker gets added to
  the main distro.

## Where everything is
- Code: `src/decompnet/app/rebrewengine.py` (the new engine), small branches in `app/engine.py`, `app/tools.py`.
- Plan + status: `PLAN.md`. Dev harness + gates: `dev/` (`rebrew_bridge.py`, `e2e_engine.py`, `blind_test.py`).
- Run gates (inside `wsl -d rebrew-dev -u dev`): `bash dev/run_e2e.sh`, `bash dev/run_blind.sh`,
  `bash dev/run_room.sh` — all green.
- Nothing is committed to git (per your repo's "commit only when asked"). Say the word and I'll commit the branch.
