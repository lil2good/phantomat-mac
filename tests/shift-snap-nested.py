#!/usr/bin/env python3
"""Exercise free dragging, held Shift snapping and releasing Shift before drop."""
import importlib.util, json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('nav', ROOT/'tests/navigator-nested.py')
nav=importlib.util.module_from_spec(spec); spec.loader.exec_module(nav)
overview=bool(os.environ.get('SNAP_OVERVIEW'))
n=nav.Nested(sys.argv[1],ROOT/'.build/shift-snap-shots',extra=',grid_size=80,initial_zoom=0.5',
             extra_lua='hl.config({plugin={spatialoverview={distortion={enabled=false}}}})' if overview else '')
processes=[]
def keyboard(*args):
    p=subprocess.Popen(['wtype',*args],env=n.env()); processes.append(p); return p

def frame(name):
    n.shot(name)
    data=subprocess.check_output(['grim','-t','ppm','-'],env=n.env())
    _,dims,_,pixels=data.split(b'\n',3)
    return pixels

try:
    n.launch()
    n.dispatch('hl.plugin.spatialoverview.overview("toggle all")')
    client=next(c for c in n.clients() if c['title']=='btop')
    sel='address:'+client['address']
    for mode in ['free','shift','release']:
        n.dispatch(f'hl.dsp.window.resize({{x=400,y=280,window="{sel}"}})')
        n.dispatch(f'hl.dsp.window.move({{x=213,y=117,window="{sel}"}})')
        time.sleep(.8)
        n.dispatch('hl.plugin.spatialoverview.canvas("search btop")')
        if not overview: n.keys('-k','Return')
        time.sleep(.7)
        current=next(c for c in n.clients() if c['address']==client['address'])
        before=current['at']
        camera=json.loads(n.ctl('spatialoverview'))['screens'][0]
        zoom=camera['zoom']
        cx=round((before[0]+current['size'][0]/2-camera['view'][0])*zoom)
        cy=round((before[1]+current['size'][1]/2-camera['view'][1])*zoom)
        alt=keyboard('-M','alt','-s','7000','-m','alt'); time.sleep(.15)
        mouse=subprocess.Popen([str(ROOT/'.build/vpointer'),'1280','720','abs',str(cx),str(cy),'sleep','200','down','sleep','200','rel','137','73','sleep','4000','up','sleep','200'],env=n.env())
        processes.append(mouse); time.sleep(.8)
        free=frame(mode+'-free')
        if mode!='free':
            shift=keyboard('-M','shift','-s','1300' if mode=='release' else '5000','-m','shift')
            time.sleep(.35)
            snapped=frame(mode+'-preview')
            changed=sum(a!=b for a,b in zip(free,snapped))
            assert changed>1000, 'Shift did not reveal the drop zone without moving the pointer'
            print('PASS Shift reveals drop zone while pointer is stationary',flush=True)
            if mode=='release':
                shift.wait(); time.sleep(.35)
                released=frame('release-cleared')
                difference=sum(abs(a-b) for a,b in zip(free,released))/len(free)
                assert difference<1.0, f'preview remains after releasing Shift: difference={difference}'
                print('PASS releasing Shift clears the drop zone',flush=True)
        mouse.wait(); time.sleep(.4)
        after=next(c for c in n.clients() if c['address']==client['address'])['at']
        raw=[before[0]+137/zoom,before[1]+73/zoom]
        expected=[round(v/80)*80 for v in raw] if mode=='shift' else raw
        print(mode,'before',before,'after',after,'expected',expected,flush=True)
        assert all(abs(a-b)<=1 for a,b in zip(after,expected)), f'{mode} drop position wrong'
        print('PASS',mode,'drop',flush=True)
        alt.wait()
        if mode=='shift': shift.wait()
    assert not n.ctl('configerrors')
finally:
    for p in processes:
        if p.poll() is None: p.terminate()
        p.wait()
    n.stop()
assert n.proc.returncode==0
print('ALL PASSED',flush=True)
