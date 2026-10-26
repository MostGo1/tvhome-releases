#!/usr/bin/env python3
"""Fixes the Note to TV screen in the God Remote app: solid background, room for the iPhone notch."""
import shutil, time, sys
HTML = "/opt/hub/web/index.html"
s = open(HTML).read()
old = "#tvnote{position:fixed;inset:0;z-index:60;background:rgba(10,12,20,.96);display:none;padding:16px;"
new = "#tvnote{position:fixed;inset:0;z-index:99999;background:#0b0e17;display:none;padding:calc(18px + env(safe-area-inset-top)) 16px calc(28px + env(safe-area-inset-bottom));"
if old not in s:
    sys.exit("Already fixed or not found - nothing changed.")
shutil.copy(HTML, HTML + ".bak" + time.strftime("%Y%m%d%H%M%S"))
open(HTML, "w").write(s.replace(old, new, 1))
print("Done. Close and reopen God Remote on the phone.")
