#!/usr/bin/env python3
"""Adds a "Note to TV" button to the God Remote hub app. Safe: makes backups, changes nothing if anything looks unexpected.
Usage (on the home server):  curl -sL <raw url> | sudo python3 - <TV note key> [TV ip]"""
import re, shutil, sys, time

KEY = sys.argv[1] if len(sys.argv) > 1 else ""
TV = sys.argv[2] if len(sys.argv) > 2 else "192.168.100.8"
if not KEY:
    sys.exit("Give the TV note key as the first argument.")

APP = "/opt/hub/app.py"
HTML = "/opt/hub/web/index.html"
app = open(APP).read()
html = open(HTML).read()

if "api_tv_note" in app or "tvnote-btn" in html:
    sys.exit("Already installed.")
if "@require_token" not in app or "</body>" not in html:
    sys.exit("Unexpected hub files - nothing changed.")
m = re.search(r"""["']X-Hub-Token["']\s*:\s*([^,}\n]+)""", html)
if not m:
    sys.exit("Could not find how the app sends its token - nothing changed.")
tok = m.group(1).strip()

route = f'''

# ---- Note to the TV (drawn on the phone, shown on the TV launcher) ----
@app.route("/api/tv-note", methods=["POST"])
@require_token
def api_tv_note():
    import urllib.request
    try:
        req = urllib.request.Request("http://{TV}:8766/note?k={KEY}", data=request.get_data(), method="POST")
        with urllib.request.urlopen(req, timeout=8) as r:
            return jsonify({{"ok": r.status == 200}})
    except Exception as e:
        return jsonify({{"ok": False, "error": str(e)}}), 502

'''
marker = '@app.route("/api/audit")'
if marker not in app:
    sys.exit("Could not find the place to add the route - nothing changed.")

ui = r'''
<style>
#tvnote-btn{position:fixed;right:16px;bottom:96px;z-index:50;border:0;border-radius:26px;padding:12px 18px;font-size:15px;font-weight:600;background:#fff;color:#111;box-shadow:0 4px 18px rgba(0,0,0,.4)}
#tvnote{position:fixed;inset:0;z-index:60;background:rgba(10,12,20,.96);display:none;padding:16px;color:#fff;font-family:-apple-system,system-ui,sans-serif;overflow:auto}
#tvnote canvas{width:100%;aspect-ratio:3/2;background:#1d2030;border-radius:18px;display:block;touch-action:none}
#tvnote .r{display:flex;gap:10px;margin:12px 0;align-items:center;flex-wrap:wrap}
#tvnote .c{width:30px;height:30px;border-radius:50%;border:3px solid transparent}#tvnote .c.on{border-color:#fff}
#tvnote button{border:0;border-radius:14px;padding:12px 16px;font-size:16px;background:#2a2f45;color:#fff}
#tvnote #tn-send{width:100%;background:#fff;color:#111;font-weight:600;padding:16px;font-size:18px}
#tvnote input{width:100%;box-sizing:border-box;border-radius:14px;border:0;padding:12px;font-size:16px;background:#1d2030;color:#fff}
</style>
<button id="tvnote-btn">Note to TV</button>
<div id="tvnote"><h2 style="margin:4px 0 12px;font-size:20px">Leave a note on the TV</h2>
<canvas id="tn-cv" width="900" height="600"></canvas><div class="r" id="tn-cols"></div>
<div class="r"><button id="tn-u">Undo</button><button id="tn-cl">Clear</button><button id="tn-1">Thin</button><button id="tn-2">Medium</button><button id="tn-3">Thick</button></div>
<input id="tn-tx" maxlength="120" placeholder="Or type a short message">
<p></p><button id="tn-send">Send to TV</button><p id="tn-st" style="text-align:center;min-height:24px"></p>
<button id="tn-x" style="width:100%">Close</button></div>
<script>
(function(){
var cv=document.getElementById('tn-cv'),x=cv.getContext('2d'),col='#fff',w=6,down=false,hist=[],drawn=false;
x.lineCap='round';x.lineJoin='round';
['#ffffff','#ffd24a','#ff8a3d','#ff4f9a','#a56bff','#4da3ff','#4ddb8a','#ff4d4d'].forEach(function(c,i){
 var d=document.createElement('div');d.className='c'+(i==0?' on':'');d.style.background=c;
 d.onclick=function(){col=c;[].forEach.call(document.querySelectorAll('#tvnote .c'),function(e){e.classList.remove('on')});d.classList.add('on')};
 document.getElementById('tn-cols').appendChild(d)});
function pos(e){var r=cv.getBoundingClientRect();return[(e.clientX-r.left)*cv.width/r.width,(e.clientY-r.top)*cv.height/r.height]}
cv.addEventListener('pointerdown',function(e){down=true;drawn=true;hist.push(x.getImageData(0,0,cv.width,cv.height));if(hist.length>20)hist.shift();
 var p=pos(e);x.strokeStyle=col;x.lineWidth=w;x.beginPath();x.moveTo(p[0],p[1]);x.lineTo(p[0]+0.1,p[1]);x.stroke();e.preventDefault()});
cv.addEventListener('pointermove',function(e){if(!down)return;var p=pos(e);x.lineTo(p[0],p[1]);x.stroke();e.preventDefault()});
window.addEventListener('pointerup',function(){down=false});
document.getElementById('tn-u').onclick=function(){var h=hist.pop();if(h)x.putImageData(h,0,0)};
document.getElementById('tn-cl').onclick=function(){x.clearRect(0,0,cv.width,cv.height);hist=[];drawn=false};
document.getElementById('tn-1').onclick=function(){w=3};document.getElementById('tn-2').onclick=function(){w=6};document.getElementById('tn-3').onclick=function(){w=12};
var box=document.getElementById('tvnote');
document.getElementById('tvnote-btn').onclick=function(){box.style.display='block'};
document.getElementById('tn-x').onclick=function(){box.style.display='none'};
document.getElementById('tn-send').onclick=function(){
 var st=document.getElementById('tn-st'),t=document.getElementById('tn-tx').value;
 if(!drawn&&!t){st.textContent='Draw or type something first';return}
 var bg=document.createElement('canvas');bg.width=cv.width;bg.height=cv.height;var b=bg.getContext('2d');b.fillStyle='#1d2030';b.fillRect(0,0,bg.width,bg.height);b.drawImage(cv,0,0);
 st.textContent='Sending...';
 fetch('/api/tv-note',{method:'POST',headers:{'X-Hub-Token':__TOK__,'Content-Type':'application/json'},body:JSON.stringify({img:drawn?bg.toDataURL('image/png'):'',text:t})})
 .then(function(r){return r.json()}).then(function(j){if(j.ok){st.textContent='Sent to the TV';x.clearRect(0,0,cv.width,cv.height);drawn=false;document.getElementById('tn-tx').value=''}else{st.textContent='Could not reach the TV'}})
 .catch(function(){st.textContent='Could not send'})};
})();
</script>
'''.replace("__TOK__", tok)

stamp = time.strftime("%Y%m%d%H%M%S")
shutil.copy(APP, APP + ".bak" + stamp)
shutil.copy(HTML, HTML + ".bak" + stamp)
open(APP, "w").write(app.replace(marker, route.lstrip("\n") + "\n" + marker, 1))
open(HTML, "w").write(html.replace("</body>", ui + "</body>", 1))
print("Done. Backups: *.bak" + stamp + ". Now restart the hub:")
print("  sudo pkill -f app.py; cd /opt/hub && nohup venv/bin/python3 app.py > /tmp/hub.log 2>&1 &")
