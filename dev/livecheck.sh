echo "host py procs:"; pgrep -af live_host.py | head -2
echo "cloudflared procs:"; pgrep -af "cloudflared tunnel" | head -2
echo "retrying curl after propagation:"
L=$(/home/dev/fork-venv/bin/python -c 'import json;print(json.load(open("/home/dev/live-link.json"))["link"])')
base=${L%%/join*}
for i in 1 2 3; do sleep 8; curl -s -m 20 -o /dev/null -w "  try$i http=%{http_code}\n" "$base/collab/hello?invite=open&room=toy"; done
