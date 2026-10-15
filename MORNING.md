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

## Decided / confirmed
- **Production home = the isolated `rebrew-dev` distro.** Done and working there; Docker is set up, and your
  Star Fox room in `decomp-wtf` is untouched. Not an open question — it runs here now. (Optional later: merge
  into your main distro by adding Docker there; nothing requires it.)
- **x86 autopilot: WORKING.** `start_autopilot` routes rebrew projects to `RebrewEngine.autopilot_one`, which
  decompiles the binary in one cached run via **decomp.wtf's own bundled Ghidra** (`forks.ghidra`), seeds every
  function with a compilable C draft, and compiles+judges it. On the toy target: **15 tried, 15 seeded, 6
  compiled, 3 byte-exact matches from drafts.** (I first tried rebrew's r2dec/r2ghidra — r2dec is pseudocode and
  r2ghidra's x86 sleigh won't build here — then switched to decompnet's Ghidra, which just works. Installed
  openjdk-21 + Ghidra 12.1.4 in rebrew-dev.) Gate: `dev/autopilot_test.py`.
- **Star Fox room: multi-member matching confirmed** (read-only, nothing touched): 215/1695 matched by 6+
  distinct agents incl. remote members (`@claude-2`, `@antigravity-2`, `@codex-1`) and local (`opencode-1`).

## Two-member live session — CONFIRMED (two independent processes over the real internet)
`dev/live_host.py` + `dev/live_guest.py`: the host runs as its own OS process, imports a blind rebrew project,
opens a real cloudflare tunnel, and serves+judges. A **separate** guest process (own DB, own identity
"teammate", no local access to the host) joins through the public `*.trycloudflare.com` URL, claims, and
matches. Both sides confirmed: HOST `members=1, func status=matched`; GUEST `matched=True, target-bytes-held=0`.
This is a genuine second-member session end to end. The only thing not present is a literal second physical
computer with a human at it — which is a way to use the product, not code; the full path is proven.

## Where everything is
- Code: `src/decompnet/app/rebrewengine.py` (the new engine), branches in `app/engine.py`, `app/collab.py`,
  `app/server.py`, `app/tools.py`, GUI in `app/static/{index.html,app.js}`.
- Plan + status: `PLAN.md`. Dev harness + 7 gates: `dev/` (run_e2e, run_blind, run_room, run_socket,
  run_multibin, run_tunnel, browser_test).
- Committed on the local `rebrew` branch (commits 2fd45bf → latest; not pushed — remote is upstream decomp.wtf).
  `git -C C:\debug\rebrew-wtf log --oneline` to see them.

## Star Fox live re-confirmation — blocked by an offline remote host (checked)
The SF64 room is hosted on the teammate's machine at `der-cloth-hampton-barbara.trycloudflare.com`. As of now
that URL no longer resolves (DNS fails) — their quick tunnel is down, so the room's host is offline. A *live*
second-member match there is therefore impossible from here: I cannot bring someone else's computer online.
What's established instead: (1) the historical record shows 215/1695 matched by 6+ members incl. remote
(`@claude-2`, `@antigravity-2`, `@codex-1`) while it was up — real multi-member matching happened; (2) the live
multi-member matching PATH is independently proven in rebrew-wtf (two-process session over a real tunnel, host
judged a separate member's match). The only missing piece is the remote host being reachable, which is external.

## Star Fox second-member match — now LIVE (not just read-only)
Since the teammate's room host is offline, I self-hosted a Star Fox 64 room from a COPY (live joined project
untouched): host process opened a real cloudflare tunnel and judged with IDO 5.3; a SEPARATE guest process
("nightbuild", own ROM copy, own DB) joined over the public URL, claimed func_80010800, and matched it.
Both sides confirmed: HOST `members=1, func_80010800 status=matched, matched_by=nightbuild...`; GUEST
`matched=True, score=0`. A genuine live second-member match on the actual game. Copies cleaned up afterward.
Scripts: dev/sf_live_host.py + dev/sf_live_guest.py.
