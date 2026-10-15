L=$(/home/dev/fork-venv/bin/python -c 'import json;print(json.load(open("/home/dev/live-link.json"))["link"])')
base=${L%%/join*}
echo "base=$base"
curl -s -m 20 -o /dev/null -w "hello http=%{http_code} time=%{time_total}s\n" "$base/collab/hello?invite=open&room=toy"
