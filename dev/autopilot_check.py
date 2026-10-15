import shutil
from pathlib import Path
from decompnet.app.engine import RomNetwork
from decompnet.network import NetworkError
ws = Path("/home/dev/ap-ws"); shutil.rmtree(ws, ignore_errors=True); ws.mkdir()
net = RomNetwork(ws/"d.db", ws)
slug = net.rebrew.import_binary(Path("/home/dev/targets/toy"), toolchain="gcc-14.2.0", confirmed=True, name="toy", log=lambda *a:None)
try:
    net.start_autopilot(slug)
    print("autopilot started (unexpected without a decompiler)")
except NetworkError as e:
    print("autopilot safely declined with a clear message:", str(e)[:90])
except Exception as e:
    print("CRASH:", type(e).__name__, str(e)[:90])
