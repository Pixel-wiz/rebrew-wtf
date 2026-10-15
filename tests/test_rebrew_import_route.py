"""The /api/import?rebrew=1 route imports a PC binary as a rebrew project (gated on the rebrew toolchain)."""
import time
from pathlib import Path

import pytest

from .test_app_server import app  # noqa: F401  (reuse the authenticated TestClient fixture)

TOY = Path("/home/dev/targets/toy")
pytestmark = pytest.mark.skipif(not TOY.exists(), reason="needs the rebrew-dev toy binary")


def test_import_a_binary_as_a_rebrew_project(app):  # noqa: F811
    client, net, _ = app
    h = {"X-Decomp": "1"}
    job = client.post(f"/api/import?confirmed=1&rebrew=1&path={TOY}", content=b"", headers=h).json()["job"]
    for _ in range(600):
        j = client.get(f"/api/job?id={job}").json()
        if j["state"] != "running":
            break
        time.sleep(0.1)
    assert j["state"] == "done", j
    slug = j["result"]["slug"]
    proj = net.store.one("SELECT * FROM projects WHERE slug=?", slug)
    import json as _j
    assert _j.loads(proj["config"])["kind"] == "rebrew"
    assert net.store.one("SELECT COUNT(*) c FROM functions WHERE project_id=?", proj["id"])["c"] > 0
