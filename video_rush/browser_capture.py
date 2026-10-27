"""Truthful screenshots of an exact committed web tool via its real DOM controls."""
from __future__ import annotations
import functools
import hashlib
import http.server
import shutil
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse
from .common import ROOT,digest,read,write,sha,run
from .snapshot import snapshot


def capture(repo, asset, destination):
    from playwright.sync_api import sync_playwright
    repo,destination=Path(repo),Path(destination)
    commit=run(['git','-C',repo,'rev-parse',asset['commit']+'^{commit}']).strip()
    browser=next((shutil.which(x) for x in ['chromium','google-chrome','google-chrome-stable','chromium-browser'] if shutil.which(x)),None)
    if not browser:raise RuntimeError('Browser capture requires Chromium or Google Chrome')
    version=run([browser,'--version']).strip()
    paths=asset['snapshot_paths']
    for path in [*paths,asset.get('entry','index.html')]:
        p=Path(path)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Browser snapshot paths must be repository-relative')
    key=digest({'asset':asset,'commit':commit,'browser':version,'code':sha(Path(__file__))})
    receipt_path=destination.with_suffix('.capture.json')
    if destination.exists() and receipt_path.exists():
        receipt=read(receipt_path)
        if receipt.get('key')==key and receipt['screenshot_sha256']==sha(destination):return receipt
    root=ROOT/'build/browser-snapshots'/digest({'commit':commit,'paths':paths})[:20]
    result=snapshot(repo,commit,paths,root)
    tree=run(['git','-C',repo,'ls-tree','-r',commit,'--',*paths])
    for line in tree.splitlines():
        meta,name=line.split('\t',1);mode,kind,oid=meta.split()
        if kind!='blob' or mode not in ('100644','100755'):raise ValueError('Only ordinary web files supported')
        data=(root/name).read_bytes()
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=oid:raise ValueError('Snapshot bytes do not match Git blob')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    errors=[];blocked=[]
    try:
        with sync_playwright() as pw:
            instance=pw.chromium.launch(executable_path=browser,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            try:
                page=instance.new_page(viewport=asset.get('viewport',{'width':1920,'height':1080}),device_scale_factor=1)
                page.set_default_timeout(15000)
                def route(request):
                    if urlparse(request.request.url).hostname=='127.0.0.1':request.continue_()
                    else:blocked.append(request.request.url);request.abort()
                page.route('**/*',route);page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/'+asset.get('entry','index.html'),wait_until='networkidle',timeout=30000)
                for step in asset.get('steps',[]):
                    op=step['operation'];target=page.locator(step['selector'])
                    if step.get('first'):target=target.first
                    if op=='click':target.click()
                    elif op=='fill':target.fill(step['value'])
                    elif op=='select':target.select_option(step['value'])
                    elif op=='wait':target.wait_for(state=step.get('state','visible'))
                    else:raise ValueError('Unsupported browser action: '+op)
                page.wait_for_timeout(250)
                if errors:raise RuntimeError('Captured application has runtime errors: '+str(errors))
                destination.parent.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(destination),animations='disabled')
                observed=page.locator('body').inner_text()[:2500]
            finally:instance.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    receipt={'key':key,'source_commit':commit,'source_tree_sha256':hashlib.sha256(tree.encode()).hexdigest(),
             'snapshot':result,'all_snapshot_git_blobs_verified':True,'browser':version,'steps':asset.get('steps',[]),
             'viewport':asset.get('viewport',{'width':1920,'height':1080}),'screenshot_sha256':sha(destination),
             'observed_page_text':observed,'page_errors':errors,'blocked_external_requests':blocked,
             'truth':'New screenshot of immutable historical web app; real DOM controls, not original historical recording or game physics proof'}
    write(receipt_path,receipt);return receipt
