# rebrew-wtf

Fork of decomp.wtf (MIT, i12bp8/decomp.wtf @ 8969c7a) that adds a Rebrew-backed project kind
(maci0/rebrew, MIT): function-by-function matching decompilation of PC programs (GCC/Clang/MinGW/MSVC)
with decomp.wtf's dashboard, MCP tools, agents and team rooms.

## Steps

| # | Step | Done when | Status |
|---|------|-----------|--------|
| 1 | Fork + baseline tests | suite runs unchanged | DONE 2026-10-15: 102 pass, 114 skip, 1 pre-existing fail |
| 2 | Known-answer target + `rebrew intake` | rebrew lists its functions | DONE: toy.c (13 fns) intake OK, pinned gcc-14.2.0 |
| 3 | Rebrew bridge (compile+compare as library) | known function scores 0 through bridge | DONE: 3/5 EXACT (toy_clamp/count_char/state score 0); 2 are real not-yet-matched |
| 4 | Rebrew project kind in engine + dashboard + agents | map lights up; 1 agent matches end to end | DONE: e2e gate PASS — import + attempt() scores 0 for 3 known-good, rejects wrong body |
| 4b | Disassembly at import (agents need function asm) | functions carry readable asm + n_insns | DONE: capstone listing + counts (6/17/29 insns shown) |
| 5 | Team rooms | 2nd instance joins, both claim + match | DONE: in-process host+guest gate PASS — normal room (guest imports, local match, host confirms) AND blind room (guest no binary, host judges, guest holds 1 fn / 0 target bytes) |
| 6 | Blind mode (option) | member sees only assigned function; never binary/names/strings/scope | DONE: PASS — member 0→1, no scope leak, no real-name leak; real names live ONLY in host's binary (opaque fcn_<va> in the shared DB). Key insight: matching slices target by ADDRESS not name, so renaming is free. |

## Verified gates (all green on the toy target, rebrew-dev)
- `dev/rebrew_bridge.py` — bridge: 3/5 EXACT (self-contained fns score 0).
- `dev/e2e_engine.py` — engine: import + attempt() → 3/3 known-good score 0, negative control held.
- `dev/blind_test.py` — blind mode: host sees all, member sees only claimed, no scope/name leak.
- `dev/room_test.py` — rooms: normal + blind host+guest in-process; both match, blind guest holds 0 target bytes.
- Full fork suite: 74 passed / 3 failed / 17 errors — IDENTICAL with and without my changes (failures are
  environmental: missing game toolchains + git identity in rebrew-dev), so zero regressions.

## Steps 1-6 all DONE + verified. Plus: real-HTTP-socket room, multi-binary (import_binaries), import route
## `/api/import?rebrew=1[&blind=1]` + GUI "Reverse a PC binary" button (route tested in suite). Remaining:
- Two-machine room test over a real trycloudflare tunnel (in-process is proven; this is the network-transport check).
- Import entry: expose `import_binary` via an MCP tool + the GUI "new project" flow (works as a library call now).
- Multi-binary project (exe + its DLLs) = several targets in one project (schema allows it; importer does one binary).
- Decide prod home: run rebrew projects in rebrew-dev (has Docker) or add Docker to the decomp-wtf distro.
- Upstream the rebrew ELF-dispatch fix (dev/patch_rebrew_elf.py) to maci0/rebrew.
- Room `state` sync for rebrew (blind members never sync scope; the live map on the host side may need a rebrew
  branch in apply_remote_layout if a non-blind member's GUI should mirror the host — not needed for matching).

## How to run the fork (rebrew-dev)

- Fork venv: `/home/dev/fork-venv` (Python 3.13, has decompnet + rebrew + the ELF patch).
- env: `REBREW_TOOLCHAINS_DIR=/home/dev/recompile-toolchains`, PATH includes `/home/dev/.local/bin`.
- Reproducible rebrew ELF-dispatch patch: `dev/patch_rebrew_elf.py <site-packages/rebrew>` (idempotent). MUST be
  re-applied after any `uv pip install rebrew` (upstream bug; `parse_obj_symbol_and_relocs` never routes ELF).
- Gates: `dev/rebrew_bridge.py` (bridge), `dev/e2e_engine.py` (engine) — both PASS on the toy target.

## Environment built overnight

- WSL distro `rebrew-dev` (Debian): user `dev`, systemd on, Docker working, gcc 14.2, uv, rebrew 4.1.0 installed.
  Kept alive by background `sleep infinity` (task b9tczvx2b). NOT the decomp-wtf distro — isolated so the SF64 room is untouched.
- `~/recompile-toolchains` cloned (rebrew's image build recipes); `REBREW_TOOLCHAINS_DIR` points at it.
- gcc-14.2.0 toolchain image building from source as systemd unit `rebrew-tc-gcc14b` (compiles GCC; ~30-45 min).
- Toy target: `dev/target/toy.c` -> `~/targets/toy` (gcc -O2), 13 named funcs, project at `~/proj-toy`.
- Bridge: `dev/rebrew_bridge.py` (judge via rebrew library: load_config + extract_raw_bytes + compile_and_compare).
  Self-test feeds each self-contained function's original source back; expects byte-match.

## Integration design (confirmed by reading rebrew + decomp.wtf source)

- A rebrew project = decomp.wtf project with `kind="rebrew"`. Reuse attempt()/claims/rooms/dashboard/MCP unchanged.
- Judge seam: target bytes come from the LINKED binary (needs rebrew's extract + reloc masking), candidate from
  compiling the .c. So keep compile+compare together = one `bridge.judge()` call per attempt. Do NOT split into
  decomp.wtf's `_compile`+`_evaluate(obj)` (that assumes a relocatable .o on both sides; the target is linked).
- Plan: `app/rebrewengine.py` attached like `self.forks`; `is_rebrew(proj)` branches in import + the attempt judge.
- Rebrew compilers run only in Docker; decomp.wtf's own WSL distro has no Docker. Either (a) run rebrew projects in
  rebrew-dev, or (b) add Docker to the decomp-wtf distro. Decide at step 4. rebrew-dev is the clean room for now.

## Blind mode (step 6) design

- Host holds the binary + full function list + symbol/string/data. Members get ONLY: one assigned function's
  disassembly (needed to decompile it) + the shared type header. Never the binary, file set, names, or scope.
- Mechanism: in a room, `claim` hands out the asm of the claimed function only; `compile_and_diff` sends C to the
  host, host runs bridge.judge, returns score + masked diff rows. Members never run the judge => never need bytes.
  This matches collab.py's existing host-judges-attempts path; blind mode just also withholds the function list
  (list_functions returns only what the member has claimed) and strips symbol names from asm (rename to fcn_VA).

## Decisions

- Reuse decomp.wtf engine/GUI/MCP/agents/collab; new code is one project kind (template: `app/forkengine.py`).
- A project can hold several binaries (exe + its dlls); functions from all of them are handed out.
- Blind mode => host holds the binary and judges every attempt; members send C, get diffs back.
  Members are handed individual functions (like decomp.wtf claims), never the binary or file set.
  Members never receive the binary, symbol names, strings/data contents, or the function list.
  Limit: the assembly of the assigned function itself is disclosed (needed to decompile it).

## Known

- Pre-existing failure on unmodified fork: `tests/test_app_server.py::test_the_api_agent_stays_within_a_small_local_context`.
- Dev tests: `wsl -d decomp-wtf -u decomp -- bash -l /mnt/c/debug/rebrew-wtf/.devtest.sh` (venv `~/rebrew-wtf-venv`).
- Rebrew compilers run in Docker images; Docker not available in WSL yet (step 2 blocker).

## Next action

Get Docker reachable from WSL, install rebrew, build a small GCC 14 test program, run `rebrew intake`.
