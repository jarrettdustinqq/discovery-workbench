"""Real Chromium smoke/regression tests. Uses an existing Playwright installation."""
import argparse, json, pathlib, subprocess, time, urllib.parse
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--url'); p.add_argument('--browser-engine', choices=['chromium','webkit'], default='chromium'); p.add_argument('--browser-executable'); p.add_argument('--output', default=str(ROOT/'evidence/browser-tests.json')); args=p.parse_args()
server=None
if not args.url:
    server=subprocess.Popen(['python3','-m','http.server','8765','--bind','127.0.0.1'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(.25)
url=args.url or 'http://127.0.0.1:8765/'
checks=[]; requests=[]; errors=[]
def check(name, value):
    assert value, name
    checks.append(name)
try:
  with sync_playwright() as pw:
    launch={'headless':True}
    if args.browser_executable: launch['executable_path']=args.browser_executable
    browser=getattr(pw,args.browser_engine).launch(**launch)
    page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
    page.goto(url,wait_until='networkidle')
    check('application title',page.title()=='Discovery Workbench')
    page.locator('#run').click();page.locator('#results:not([hidden])').wait_for(timeout=10000)
    check('polynomial demo supported',page.locator('#verdict').inner_text()=='Supported on this split')
    check('recovered square term visible','a^2' in page.locator('#equation').inner_text())
    with page.expect_download() as item: page.locator('#export').click()
    path=item.value.path();report=json.loads(pathlib.Path(path).read_text())
    check('report exports dataset SHA-256',len(report['datasetSHA256'])==64)
    check('report includes reproducible input',len(report['data']['rows'])==160)
    check('final error low',report['result']['test']['rmse']<1e-8)
    page.select_option('#scenario','confounded');page.locator('#load-demo').click();page.locator('#run').click()
    page.locator('#results:not([hidden])').wait_for(timeout=10000)
    check('confounding warning visible','correlated' in page.locator('#warnings').inner_text())
    check('next experiment visible',page.locator('#experiment-inputs').inner_text()!='')
    page.select_option('#scenario','noise');page.locator('#load-demo').click();page.locator('#run').click()
    page.locator('#results:not([hidden])').wait_for(timeout=10000)
    check('noise is not supported',page.locator('#verdict').inner_text()=='Not supported')
    page.locator('#csv').fill('x,y\n=alert(1),2');page.locator('#run').click()
    check('malformed data fails visibly','numeric' in page.locator('#status').inner_text())
    check('stale result hidden on input change',page.locator('#results').is_hidden())
    csv='x,y\n'+'\n'.join(f'{i/10},{2+3*i/10}' for i in range(80))
    page.locator('#csv-file').set_input_files({'name':'local.csv','mimeType':'text/csv','buffer':csv.encode()})
    page.wait_for_function("document.querySelector('#csv').value.includes('7.9,')")
    page.locator('#run').click();page.locator('#results:not([hidden])').wait_for(timeout=10000)
    check('local CSV executes',page.locator('#verdict').inner_text()=='Supported on this split')
    page.locator('#challenge-x').fill('1.25');page.locator('#challenge-y').fill('99');page.locator('#challenge').click()
    check('new contradictory measurement is shown','measurement' in page.locator('#challenge-result').inner_text().lower())
    page.locator('#append-observation').click()
    check('observation appended',page.locator('#csv').input_value().strip().endswith('1.25,99'))
    check('result invalidated after new evidence',page.locator('#results').is_hidden())
    # Set busy, then cancel in the same turn before a worker can finish.
    page.evaluate("document.querySelector('#run').click(); document.querySelector('#cancel').click()")
    check('cancellation returns to idle',page.locator('#run').is_enabled() and 'Cancelled' in page.locator('#status').inner_text())
    page.set_viewport_size({'width':390,'height':844})
    check('mobile viewport has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    page.select_option('#scenario','polynomial');page.locator('#load-demo').click();page.locator('#run').click();page.locator('#results:not([hidden])').wait_for(timeout=10000)
    check('mobile results have no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    page.screenshot(path=str(ROOT/'evidence/mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(ROOT/'evidence/desktop.png'),full_page=True)
    origin=urllib.parse.urlsplit(url).netloc
    check('no cross-origin requests',all(urllib.parse.urlsplit(r['url']).netloc==origin for r in requests))
    check('no upload or write requests',all(r['method']=='GET' for r in requests))
    check('no uncaught browser errors',not errors)
    output={'url':url,'checks':checks,'passed':len(checks),'errors':errors,'requests':requests,'browser':browser.version,'engine':args.browser_engine}
    pathlib.Path(args.output).write_text(json.dumps(output,indent=2)); print('BROWSER_REPORT_JSON '+json.dumps(output))
    browser.close()
finally:
  if server:server.terminate();server.wait(timeout=5)
