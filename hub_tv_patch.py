#!/usr/bin/env python3
"""Installs the new God Remote design and the TV Home bridge on the home server hub.
Safe: backs up the old files, changes nothing if something looks unexpected.
Usage:  curl -sL https://raw.githubusercontent.com/MostGo1/tvhome-releases/main/hub_tv_patch.py | sudo python3 - <TV note key> [TV ip]"""
import os, shutil, subprocess, sys, time, urllib.request

KEY = sys.argv[1] if len(sys.argv) > 1 else ""
TV = sys.argv[2] if len(sys.argv) > 2 else "192.168.100.8"
if not KEY:
    sys.exit("Give the TV note key as the first argument.")

APP = "/opt/hub/app.py"
HTML = "/opt/hub/web/index.html"
URL = "https://raw.githubusercontent.com/MostGo1/tvhome-releases/main/hub_ui/index.html"

app = open(APP).read()
if "@require_token" not in app or '@app.route("/api/audit")' not in app:
    sys.exit("Unexpected hub files - nothing changed.")

new = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
if len(new) < 20000 or 'data-tab' not in new:
    sys.exit("The downloaded design looks wrong - nothing changed.")

stamp = time.strftime("%Y%m%d-%H%M%S")
shutil.copy(APP, APP + ".bak-" + stamp)
shutil.copy(HTML, HTML + ".bak-" + stamp)

if "def api_tv(" not in app:
    route = f'''
# ---- TV Home bridge (God Remote talks to the launcher on the TV, home network only) ----
@app.route("/api/tv/<sub>", methods=["GET", "POST"])
@require_token
def api_tv(sub):
    import json as _json, urllib.request as _u, urllib.error as _e
    paths = {{"status": "/status", "cmd": "/cmd", "photo": "/photo", "note": "/note"}}
    if sub not in paths:
        return jsonify({{"ok": False, "error": "unknown"}}), 404
    url = "http://{TV}:8766" + paths[sub] + "?k={KEY}"
    try:
        req = _u.Request(url, data=(request.get_data() if request.method == "POST" else None),
                         method=request.method)
        with _u.urlopen(req, timeout=25) as r:
            body = r.read()
            if sub in ("status", "cmd"):
                return app.response_class(body, mimetype="application/json")
            return jsonify({{"ok": r.status == 200}})
    except _e.HTTPError as e:
        return jsonify({{"ok": False, "error": "TV said " + str(e.code)}}), 502
    except Exception as e:
        return jsonify({{"ok": False, "error": "TV did not answer"}}), 502

'''
    app = app.replace('@app.route("/api/audit")', route + '@app.route("/api/audit")', 1)
    open(APP, "w").write(app)

open(HTML, "w").write(new)

subprocess.call("pkill -f app.py", shell=True)
time.sleep(1)
subprocess.Popen("cd /opt/hub && nohup venv/bin/python3 app.py > /tmp/hub.log 2>&1 &", shell=True)
print("Done. Backups end with .bak-" + stamp + ". Open the God Remote app and pull down to reload.")
