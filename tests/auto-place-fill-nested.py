import importlib.util,json,time,subprocess,sys,math
from pathlib import Path
root=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('nav',root/'tests/navigator-nested.py');nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
nav.WINDOWS=[]
n=nav.Nested(sys.argv[1],root/'.build/shots-auto-fill',extra=',auto_fill=true,grid_size=80')
try:
 n.launch()
 n.dispatch('hl.dsp.exec_cmd('+json.dumps('env LD_PRELOAD=/usr/lib/libgtk4-layer-shell.so python '+str(root/'tests/tools/layer-bar.py')+' WAYLAND-1')+')');time.sleep(1)
 n.dispatch('hl.plugin.spatialoverview.overview("open all")');time.sleep(.6)
 n.dispatch('hl.dsp.exec_cmd("foot --app-id=auto-fill-test --title=auto-fill-test /usr/bin/cat")');time.sleep(1.5)
 c=next(c for c in n.clients() if c['class']=='auto-fill-test')
 m=json.loads(n.ctl('-j','monitors'))[0]
 print('client',c['at'],c['size'],'fullscreen',c['fullscreen'],'monitor',m['width'],m['height'],m['scale'],'reserved',m['reserved'],flush=True)
 expected=[round(m['width']/m['scale'])-36,round(m['height']/m['scale'])-sum(m['reserved'][1::2])-36]
 assert all(abs(a-b)<=1 for a,b in zip(c['size'],expected)),(c['size'],expected)
 expected=c['size']
 assert c['fullscreen']==0
 assert all(v % 80 == 0 for v in c['at']),c['at']
 positions={c['address']:c['at']}
 raw=subprocess.check_output(['grim','-t','ppm','-'],env=n.env());parts=raw.split(b'\n',3);w,h=map(int,parts[1].split());px=parts[3]
 hits=sum(px[(10*w+x)*3]>220 and px[(10*w+x)*3+1]<40 and px[(10*w+x)*3+2]>220 for x in range(0,w,8))
 assert hits>w//16,'bar not visible'
 for i in range(3):
  before=n.clients()
  view=json.loads(n.ctl('spatialoverview'))['screens'][0]['view']
  origin=[math.floor((view[k]+view[k+2]/2-expected[k]/2)/80+.5)*80 for k in (0,1)]
  n.dispatch('hl.dsp.exec_cmd('+json.dumps(f'foot --app-id=placed-{i} --title=placed-{i} /usr/bin/cat')+')');time.sleep(1)
  windows=[w for w in n.clients() if w['class'].startswith(('auto-fill-test','placed-'))]
  added=next(w for w in windows if w['class']==f'placed-{i}')
  distance=sum((added['at'][k]-origin[k])**2 for k in (0,1))
  radius=math.ceil(math.sqrt(distance)/80)
  for dx in range(-radius,radius+1):
   for dy in range(-radius,radius+1):
    if (dx*80)**2+(dy*80)**2>=distance: continue
    x,y=origin[0]+dx*80,origin[1]+dy*80
    assert any(x < w['at'][0]+w['size'][0]+40 and x+expected[0]>w['at'][0]-40 and
               y < w['at'][1]+w['size'][1]+40 and y+expected[1]>w['at'][1]-40 for w in before), 'closer free grid position was missed'

  for j,a in enumerate(windows):
   assert a['size']==expected
   assert all(v % 80 == 0 for v in a['at']),a['at']
   if a['address'] in positions: assert a['at']==positions[a['address']]
   positions[a['address']]=a['at']
   for b in windows[j+1:]:
    ax,ay=a['at'];aw,ah=a['size'];bx,by=b['at'];bw,bh=b['size']
    assert ax+aw<=bx or bx+bw<=ax or ay+ah<=by or by+bh<=ay, ('overlap',a['at'],b['at'])
 print('PASS: four filled windows occupy distinct grid positions without moving previous windows',flush=True)
 n.dispatch('hl.plugin.spatialoverview.canvas("fill")');time.sleep(.7)
 assert n.active()['size']!=expected
 print('PASS: fill toggle restores smaller size',flush=True)

finally:
 n.stop()
 assert n.proc.returncode==0,n.proc.returncode
