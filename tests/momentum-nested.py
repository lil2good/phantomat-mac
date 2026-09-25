#!/usr/bin/env python3
"""Compare unmodified Chromium touchpad momentum in native and canvas sessions."""
import importlib.util, json, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('nav',ROOT/'tests/navigator-nested.py')
nav=importlib.util.module_from_spec(spec); spec.loader.exec_module(nav)
results=[]
for canvas in (False, True):
    n=nav.Nested(sys.argv[1],ROOT/'.build/momentum-shots',extra_lua='hl.config({input={touchpad={scroll_factor=0.4}}})')
    pointer=None
    try:
        n.launch(); n.ctl('plugin','load',str(ROOT/'.build/swipe-probe.so'))
        page=Path(n.tmp.name)/'scroll.html'
        page.write_text('<title>Momentum:0</title><body style="height:30000px;background:linear-gradient(#234,#abc)"><script>onscroll=()=>document.title="Momentum:"+Math.round(scrollY)</script>')
        trace=ROOT/f'.build/momentum-{canvas}.trace'
        cmd=f'WAYLAND_DEBUG=client chromium --ozone-platform=wayland --user-data-dir={n.tmp.name}/chrome --no-first-run --no-default-browser-check --password-store=basic file://{page} 2>{trace}'
        n.dispatch('hl.dsp.exec_cmd('+json.dumps(cmd)+')')
        def browser():
            return next((c for c in n.clients() if c['class'].lower().startswith('chromium')),None)
        for _ in range(100):
            if browser() and browser()['title'].startswith('Momentum:'): break
            time.sleep(.1)
        if canvas: n.dispatch('hl.plugin.spatialoverview.overview("toggle all")')
        c=browser(); sel='address:'+c['address']
        if not c['floating']: n.dispatch(f'hl.dsp.window.float({{action="toggle",window="{sel}"}})')
        n.dispatch(f'hl.dsp.window.resize({{x=900,y=560,window="{sel}"}})')
        n.dispatch(f'hl.dsp.window.move({{x=190,y=80,window="{sel}"}})')
        time.sleep(1)
        if canvas:
            n.dispatch('hl.plugin.spatialoverview.canvas("search Momentum")'); n.keys('-k','Return'); time.sleep(1)
        pointer=subprocess.Popen([str(ROOT/'.build/vpointer'),'1280','720','abs','640','360','sleep','200','rel','1','1','sleep','60000'],env=n.env())
        time.sleep(.5)
        n.shot('momentum-'+str(canvas))
        print('geometry',browser()['at'],browser()['size'],'pointer',n.ctl('cursorpos'),flush=True)
        for _ in range(5):
            n.ctl('swipeprobe','scroll','10'); time.sleep(.04)
        n.ctl('swipeprobe','scroll','0')
        time.sleep(3)
        distance=int(browser()['title'].split(':')[-1].split()[0])
        print('canvas' if canvas else 'native',distance,flush=True)
        assert distance>0, 'page did not scroll'
        results.append(distance)
        pointer_lines=[line for line in trace.read_text().splitlines() if 'wl_pointer#' in line and any(x in line for x in ['.axis(','.axis_stop(','.motion(','.frame('])]
        (ROOT/f'.build/momentum-{canvas}-pointer.log').write_text('\n'.join(pointer_lines))
        first_axis=next(i for i,line in enumerate(pointer_lines) if '.axis(' in line)
        last_stop=max(i for i,line in enumerate(pointer_lines) if '.axis_stop(' in line)
        assert not any('.motion(' in line for line in pointer_lines[first_axis:last_stop]), 'stationary scrolling injects mouse motion'
    finally:
        if pointer: pointer.terminate(); pointer.wait()
        n.stop()
    assert n.proc.returncode==0
ratio=results[1]/results[0]
print('canvas/native distance ratio',round(ratio,3),flush=True)
assert .8<ratio<1.2, 'Phantomat changes browser momentum'
print('ALL PASSED',flush=True)
