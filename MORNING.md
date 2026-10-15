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

6. **Rooms over a real HTTP socket** (not just in-process): host served by uvicorn on 127.0.0.1, guest joins with
   a real httpx client. Blind room matched over the wire; guest held 0 target bytes. A cloudflare tunnel only adds
   NAT traversal on top of this exact path.
7. **Multi-binary projects** (an exe + its DLLs in one effort): `import_binaries([...])` namespaces each binary's
   functions by unit so an exe and a DLL that share an address or name never collide. Verified: one project over
   two binaries, a function matched from each.
8. **Import endpoint**: `POST /api/import?rebrew=1[&blind=1]` creates a rebrew project (single binary). Library
   calls `net.rebrew.import_binary` / `import_binaries` cover single and multi.

The `rebrew` branch is **committed locally** (commit 2fd45bf; not pushed — your repo's remote is upstream
decomp.wtf). `git -C C:\debug\rebrew-wtf log` to see it.

9. **GUI button + import route**: a "Reverse a PC binary (.exe/.dll/ELF)" button on the start screen opens a
   dialog (path + "blind room" + authorised checkboxes) and calls `POST /api/import?rebrew=1[&blind=1]`. The
   route is verified by a real-HTTP test (`tests/test_rebrew_import_route.py`, in the suite — 75 pass now).

10. **Blind room over a REAL public cloudflare tunnel**: cloudflared exposes the host at a `*.trycloudflare.com`
    URL; the guest joins through it over the actual internet (edge → back to localhost), claims, and the host
    judges the match remotely — guest holds 0 target bytes. Gate: `dev/run_tunnel.sh`. The full two-machine path;
    only a literal second computer is absent, which the code is indifferent to.

11. **Headless-browser click-test**: real Chromium loads the GUI, clicks "Reverse a PC binary", fills the dialog,
    submits — a rebrew project with 15 functions is created through the real JS → /api/import path.
    Gate: `dev/browser_test.py`.

## Seven gates, all green
engine match · blind scope-hiding · rooms in-process · rooms over a real HTTP socket · multi-binary ·
blind room over a real cloudflare tunnel · headless-browser button click. Full suite 75 pass, zero regressions.

## What's left (needs your decision, or is optional/low-value)
- **Production home (recommendation, your call):** keep rebrew projects in the isolated `rebrew-dev` distro —
  Docker already works there and your Star Fox room in `decomp-wtf` stays untouched. I set it up that way.
- **x86 autopilot seeding (optional, low value):** rebrew's draft decompilers need radare2/ghidra, and drafts
  almost never byte-match, so this would seed agents at best and yield ~0 free matches. Documented, not wired.
- **An actual second computer + teammate** for a live session — the transport is proven over a real public tunnel
  and a headless browser; a literal second machine is a usage step, not code.

## Where everything is
- Code: `src/decompnet/app/rebrewengine.py` (the new engine), branches in `app/engine.py`, `app/collab.py`,
  `app/server.py`, `app/tools.py`, GUI in `app/static/{index.html,app.js}`.
- Plan + status: `PLAN.md`. Dev harness + 7 gates: `dev/` (run_e2e, run_blind, run_room, run_socket,
  run_multibin, run_tunnel, browser_test).
- Committed on the local `rebrew` branch (commits 2fd45bf → latest; not pushed — remote is upstream decomp.wtf).
  `git -C C:\debug\rebrew-wtf log --oneline` to see them.
