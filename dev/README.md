# rebrew-wtf dev harness

Isolated dev environment + verification gates for the rebrew project kind. All run inside the
`rebrew-dev` WSL distro as user `dev` (see setup-rebrew-dev.sh). Fork venv: /home/dev/fork-venv.

- `setup-rebrew-dev.sh`  — provision the distro (docker, gcc, uv).
- `patch_rebrew_elf.py`  — apply the rebrew ELF .o dispatch fix (idempotent; re-run after any rebrew reinstall).
- Gates (all green): `run_e2e.sh` (engine import+match), `run_blind.sh` (blind scope hiding),
  `run_room.sh` (in-process rooms), `run_socket.sh` (room over a real HTTP socket), `run_multibin.sh`
  (exe+DLL in one project). Each wraps the matching *_test.py / *.py.
- `target/` — toy.c + lib.c, the known-answer binaries.
