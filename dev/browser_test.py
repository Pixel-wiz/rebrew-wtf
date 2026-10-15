"""Headless-browser click-test of the GUI: load the real index.html+app.js against a running server, click
the "Reverse a PC binary" button, fill the dialog, submit, and confirm a rebrew project is created. Verifies
the JS wiring (button -> dialog -> /api/import?rebrew=1), not just the route."""
import sys
import threading
import time
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

sys.path.insert(0, "/mnt/c/debug/rebrew-wtf/tests")
from test_app_server import build  # noqa: E402

TOY = "/home/dev/targets/toy"
PORT, SECRET = 6811, "s3cret-for-tests"


def main():
    import shutil
    home = Path("/home/dev/browser-home"); shutil.rmtree(home, ignore_errors=True)
    (home / ".decomp").mkdir(parents=True)
    from decompnet.app.engine import RomNetwork
    net = RomNetwork(home / ".decomp" / "decomp.db", home)
    mcp, manager, security = build(net, home / ".decomp", PORT, SECRET)
    app = mcp.streamable_http_app(transport_security=security, host="127.0.0.1")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)

    ok = False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            ctx = browser.new_context(base_url=f"http://127.0.0.1:{PORT}")
            ctx.add_cookies([{"name": "decomp_live", "value": SECRET, "domain": "127.0.0.1", "path": "/"}])
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
            page.wait_for_selector("#binPick", timeout=10000)
            page.click("#binPick")
            page.wait_for_selector("#bpPath", timeout=5000)
            page.fill("#bpPath", TOY)
            page.check("#bpOwn")
            page.click("#bpGo")
            # the import runs as a job; poll the server state for a rebrew project
            for _ in range(600):
                projs = net.store.all("SELECT config FROM projects")
                import json
                if any(json.loads(p["config"]).get("kind") == "rebrew" for p in projs):
                    ok = True
                    break
                time.sleep(0.1)
            browser.close()
    finally:
        server.should_exit = True

    n = net.store.one("SELECT COUNT(*) c FROM functions") or {"c": 0}
    print(f"rebrew project created via GUI click: {ok}; functions stored: {n['c']}")
    print(f"\nBROWSER CLICK {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
