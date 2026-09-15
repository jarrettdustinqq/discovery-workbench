"""Verify the public HTTPS runtime matches the checked-out revision."""
import hashlib,json,pathlib,time,urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
base='https://jarrettdustinqq.github.io/discovery-workbench/'
names=['index.html','styles.css','app.mjs','engine.mjs','worker.mjs']
for attempt in range(18):
    results=[]
    try:
        for name in names:
            with urllib.request.urlopen(base+name,timeout=15) as response:
                data=response.read()
                actual=hashlib.sha256(data).hexdigest()
                expected=hashlib.sha256((root/name).read_bytes()).hexdigest()
                results.append({'path':name,'status':response.status,'sha256':actual,'matches':actual==expected})
        if all(row['matches'] for row in results):
            (root/'evidence/public-assets.json').write_text(json.dumps(results,indent=2))
            print('PUBLIC_ASSETS_JSON '+json.dumps(results))
            break
    except Exception as error:
        print(type(error).__name__,str(error))
    if attempt==17: raise RuntimeError('Published runtime did not match this checked-out revision.')
    time.sleep(10)
