#!/usr/bin/env python3
"""Compare real Chromium scrolling outside and inside the canvas; check swipe lag."""
import importlib.util, json, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('nav', ROOT / 'tests/navigator-nested.py')
nav = importlib.util.module_from_spec(spec); spec.loader.exec_module(nav)
n = nav.Nested(sys.argv[1], ROOT / '.build/scroll-shots', extra_lua='hl.config({input={touchpad={scroll_factor=0.4}}})')

def browser():
    return next((c for c in n.clients() if c['class'].lower().startswith('chromium')), None)

pointers = []
def mouse(x,y):
    pointers.append(subprocess.Popen([str(ROOT/'.build/vpointer'), '1280', '720', 'abs', str(x),str(y),'sleep','60000'], env=n.env()))
    time.sleep(.3)

def scroll():
    before = int(browser()['title'].split(':')[-1].split()[0])
    for _ in range(5):
        n.ctl('swipeprobe','scroll','10')
        time.sleep(.04)
    n.ctl('swipeprobe','scroll','0')
    time.sleep(.5)
    after = int(browser()['title'].split(':')[-1].split()[0])
    return after - before

try:
    n.launch()
    n.ctl('plugin','load',str(ROOT/'.build/swipe-probe.so'))
    page = Path(n.tmp.name)/'scroll.html'
    page.write_text('<title>Scroll probe:0</title><body style="height:30000px;background:linear-gradient(#234,#abc)"><h1>Scroll test</h1><script>let total=0;addEventListener("wheel",e=>{e.preventDefault();scrollBy(0,e.deltaY);total+=e.deltaY;document.title="Scroll probe:"+Math.round(total)},{passive:false})</script>')
    cmd=f'chromium --ozone-platform=wayland --user-data-dir={n.tmp.name}/chrome --no-first-run --no-default-browser-check --password-store=basic --window-size=900,560 file://{page}'
    n.dispatch('hl.dsp.exec_cmd('+json.dumps(cmd)+')')
    for _ in range(100):
        if browser() and browser()['title'].startswith('Scroll probe:'): break
        time.sleep(.1)
    time.sleep(1)
    c=browser()
    selector='address:'+c['address']
    n.dispatch(f'hl.dsp.window.float({{action="toggle",window="{selector}"}})')
    n.dispatch(f'hl.dsp.window.resize({{x=900,y=560,window="{selector}"}})')
    n.dispatch(f'hl.dsp.window.move({{x=190,y=80,window="{selector}"}})')
    time.sleep(1)
    c=browser(); mouse(c['at'][0]+c['size'][0]//2,c['at'][1]+c['size'][1]//2)
    n.shot('native-before')
    print('native browser',c['at'],c['size'],n.ctl('cursorpos'),flush=True)
    native=scroll()
    assert native > 0, 'native app did not scroll'
    n.dispatch('hl.plugin.spatialoverview.overview("toggle all")')
    n.dispatch(f'hl.dsp.window.resize({{x=900,y=560,window="{selector}"}})')
    time.sleep(1)
    n.dispatch('hl.plugin.spatialoverview.canvas("search Scroll probe")')
    n.keys('-k','Return'); time.sleep(1)
    mouse(640,360)
    n.shot('canvas-before')
    print('canvas state',n.ctl('spatialoverview'),'active',n.active()['title'],flush=True)
    canvas=scroll()
    n.shot('canvas-after')
    print('native scroll',native,'canvas scroll',canvas,flush=True)
    assert abs(native-canvas)<=2, 'canvas bypasses native touchpad speed'
    print('PASS app scroll matches native speed and keeps receiving events',flush=True)
    n.ctl('repl','hl.config({input={touchpad={scroll_factor=0.2}}})')
    slower=scroll()
    assert abs(slower-native/2)<=2, 'runtime touchpad speed change ignored'
    print('PASS runtime scroll-speed changes are respected',flush=True)
    before=json.loads(n.ctl('spatialoverview'))['screens'][0]['view'][0]
    n.ctl('swipeprobe','begin')
    n.ctl('swipeprobe','update','-100')
    immediate=json.loads(n.ctl('spatialoverview'))['screens'][0]['view'][0]
    n.ctl('swipeprobe','end')
    time.sleep(.6)
    settled=json.loads(n.ctl('spatialoverview'))['screens'][0]['view'][0]
    print('pan',before,immediate,settled,flush=True)
    assert abs(immediate-before-100)<=2, 'swipe trails behind fingers'
    assert abs(settled-immediate)<=2, 'canvas keeps moving after fingers lift'
    print('PASS three-finger pan follows input immediately without trailing animation',flush=True)
    assert not n.ctl('configerrors')
finally:
    for pointer in pointers:
        pointer.terminate()
        pointer.wait()
    n.stop()
assert n.proc.returncode == 0
print('ALL PASSED',flush=True)
