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

if "def api_screenrec(" not in app:
    rec = r'''
# ---- Screen recording on a TV through adb (saved only on the phone) ----
_REC = {}

def _rec_ip(raw):
    import ipaddress
    try:
        if ipaddress.ip_address(str(raw or "")).is_private:
            return str(raw)
    except Exception:
        pass
    return None

@app.route("/api/devices/<dev_id>/record", methods=["POST"])
@require_token
def api_screenrec(dev_id):
    import shutil, subprocess
    data = request.get_json(silent=True) or {}
    ip = _rec_ip(data.get("ip"))
    adb = shutil.which("adb")
    if not ip:
        return jsonify({"error": "bad device address"}), 400
    if not adb:
        return jsonify({"error": "adb is not installed on the hub"}), 501
    try:
        sec = max(5, min(120, int(data.get("seconds") or 15)))
    except Exception:
        sec = 15
    tgt = ip + ":5555"
    try:
        subprocess.run([adb, "connect", tgt], timeout=8, capture_output=True)
        old = _REC.pop(ip, None)
        if old and old.poll() is None:
            old.kill()
        _REC[ip] = subprocess.Popen([adb, "-s", tgt, "shell", "screenrecord",
            "--time-limit", str(sec), "--size", "1280x720", "--bit-rate", "3000000",
            "/sdcard/hubrec.mp4"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return jsonify({"error": "could not start: " + str(e)}), 502
    return jsonify({"ok": True})

@app.route("/api/devices/<dev_id>/record/file")
@require_token
def api_screenrec_file(dev_id):
    import os, shutil, subprocess, tempfile, time as _t
    ip = _rec_ip(request.args.get("ip"))
    adb = shutil.which("adb")
    if not ip or not adb:
        return jsonify({"error": "bad request"}), 400
    p = _REC.get(ip)
    if p:
        try:
            p.wait(timeout=45)
        except Exception:
            return jsonify({"error": "the TV is still recording, try again"}), 504
    _t.sleep(1)
    tgt = ip + ":5555"
    fd, local = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        r = subprocess.run([adb, "-s", tgt, "pull", "/sdcard/hubrec.mp4", local],
                           timeout=60, capture_output=True)
        if r.returncode != 0 or os.path.getsize(local) < 1000:
            return jsonify({"error": "The TV gave no video. Protected apps such as Netflix block recording."}), 502
        data = open(local, "rb").read()
        subprocess.run([adb, "-s", tgt, "shell", "rm", "/sdcard/hubrec.mp4"],
                       timeout=10, capture_output=True)
        return app.response_class(data, mimetype="video/mp4")
    except Exception as e:
        return jsonify({"error": "could not fetch: " + str(e)}), 502
    finally:
        try:
            os.remove(local)
        except Exception:
            pass

'''
    app = app.replace('@app.route("/api/audit")', rec + '@app.route("/api/audit")', 1)
    open(APP, "w").write(app)

open(HTML, "w").write(new)

subprocess.call(["pkill", "-f", "[v]env/bin/python3 app.py"])
time.sleep(1)
subprocess.Popen(["venv/bin/python3", "app.py"], cwd="/opt/hub", stdout=open("/opt/hub/hub.log", "ab"), stderr=subprocess.STDOUT, start_new_session=True)
print("Done. Backups end with .bak-" + stamp + ". Open the God Remote app and pull down to reload.")
