"""One-shot, frozen-protocol external-site test. No application code is changed."""
from __future__ import annotations
import base64, datetime, gzip, hashlib, io, itertools, json, os, pickle
import platform, subprocess, sys, time, urllib.request, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import scipy, sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from core import FEATURES, HEADERS, prepare, select_development, metrics, clip_predictions, bootstrap_ratio, advantage_gate

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'.utility_output'
SOURCE='https://archive.ics.uci.edu/static/public/501/beijing%2Bmulti%2Bsite%2Bair%2Bquality%2Bdata.zip'
BASE='191245df224bdbdb585848997eee0ba7a50ae121'
PROTOCOL_COMMIT='c2238efdfe1f7964307ea219e1206df2bb373cd4'
ENGINE_HASH='58cf24333025f2ce7a138390aca557a802dc62746a81a735d34466d7b54fe3f7'

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(name,obj):
    raw=encoded(obj);(OUT/name).write_bytes(raw);return sha(raw)
def emit(kind,obj):print(kind+' '+json.dumps(obj,separators=(',',':'),allow_nan=False),flush=True)
def download(url):
    req=urllib.request.Request(url,headers={'User-Agent':'DiscoveryWorkbench-ReproducibleEvaluation/1.0'})
    with urllib.request.urlopen(req,timeout=60) as response:
        data=response.read(32*1024*1024+1)
        if response.status!=200 or len(data)>32*1024*1024:raise RuntimeError('Download status or size invalid')
        return data

def bridge(mode,obj):
    result=subprocess.run(['node',str(HERE/'workbench.mjs'),mode],input=json.dumps(obj),
                          text=True,capture_output=True,check=True,timeout=90)
    return json.loads(result.stdout)

def independent_predict(model,x):
    result=np.full(len(x),model['intercept'],dtype=float)
    for term in model['terms']:
        f=term['feature'];a=x[:,f['a']];op=f['op']
        with np.errstate(divide='ignore',invalid='ignore'):
            if op=='raw':v=a
            elif op=='square':v=a*a
            elif op=='cube':v=a*a*a
            elif op=='reciprocal':v=np.where(np.abs(a)<1e-12,np.nan,1/a)
            elif op=='product':v=a*x[:,f['b']]
            elif op=='ratio':
                b=x[:,f['b']];v=np.where(np.abs(b)<1e-12,np.nan,a/b)
            else:raise ValueError('Unexpected feature outside frozen algebra grammar')
        result+=term['coefficient']*v
    return result

def run():
    OUT.mkdir(exist_ok=False)
    if sha((ROOT/'engine.mjs').read_bytes())!=ENGINE_HASH:raise RuntimeError('Engine differs from frozen release')
    release=json.loads((ROOT/'evidence/release.json').read_text())
    assets=[]
    for name,expected in release['runtime_file_sha256'].items():
        local=sha((ROOT/name).read_bytes());live=sha(download('https://jarrettdustinqq.github.io/discovery-workbench/'+name))
        if local!=expected or live!=expected:raise RuntimeError('Live/source runtime mismatch: '+name)
        assets.append({'file':name,'sha256':expected,'https_matches':True})
    engine_check=subprocess.run(['node','--test','--test-reporter=tap','tests/engine.test.mjs'],cwd=ROOT,capture_output=True,text=True,check=True,timeout=45)
    (OUT/'engine-tests.txt').write_text(engine_check.stdout+engine_check.stderr)
    if '# tests 35' not in engine_check.stdout or '# fail 0' not in engine_check.stdout:raise RuntimeError('Unexpected release test count')
    raw=download(SOURCE);(OUT/'source.zip').write_bytes(raw)
    outer=zipfile.ZipFile(io.BytesIO(raw))
    nested_names=[n for n in outer.namelist() if Path(n).name=='PRSA2017_Data_20130301-20170228.zip']
    if len(nested_names)!=1:raise RuntimeError('Unexpected UCI archive structure')
    nested_raw=outer.read(nested_names[0]);archive=zipfile.ZipFile(io.BytesIO(nested_raw))
    extraction_log=[];frozen=False
    def station_data(station):
        if station!='Aotizhongxin' and not frozen:raise RuntimeError('Attempted test access before model freeze')
        suffix=f'PRSA_Data_{station}_20130301-20170228.csv'
        names=[n for n in archive.namelist() if Path(n).name==suffix]
        if len(names)!=1:raise RuntimeError('Station source absent or ambiguous: '+station)
        extraction_log.append({'station':station,'time':now(),'phase':'test' if frozen else 'development'})
        content=archive.read(names[0])
        return pd.read_csv(io.BytesIO(content)),sha(content)
    development_raw,development_source_hash=station_data('Aotizhongxin')
    development,development_meta=prepare(development_raw,'Aotizhongxin','2013-03-01','2014-12-31T18:00:00')
    sample=select_development(development)
    data={'headers':HEADERS,'rows':sample[HEADERS].to_numpy().tolist()}
    (OUT/'development.csv').write_text(sample[HEADERS].to_csv(index=False))
    start=time.perf_counter();workbench=bridge('train',data);tool_seconds=time.perf_counter()-start
    split=workbench['split']
    if {k:len(v) for k,v in split.items()}!={'train':1200,'validation':400,'test':400}:raise RuntimeError('Unexpected group partition')
    indices=[i for group in split.values() for i in group]
    if sorted(indices)!=list(range(2000)):raise RuntimeError('Split overlap or incomplete coverage')
    train=sample.iloc[split['train']];validation=sample.iloc[split['validation']];audit=sample.iloc[split['test']]
    if not (train.index.max()+pd.Timedelta(hours=1)<validation.index.min()-pd.Timedelta(hours=1) and
            validation.index.max()+pd.Timedelta(hours=1)<audit.index.min()-pd.Timedelta(hours=1)):
        raise RuntimeError('Chronological or measurement-window separation failure')
    full=development.loc[(development.index<=train.index.max()) &
                         (development.index+pd.Timedelta(hours=1)<validation.index.min()-pd.Timedelta(hours=1))]
    split_manifest={k:{'indices':v,'origins':[t.isoformat() for t in sample.index[v]]} for k,v in split.items()}
    split_hash=save('split_manifest.json',split_manifest)
    xv=validation[FEATURES].to_numpy();yv=validation.target.to_numpy()
    ytrain=train.target.to_numpy();median=float(np.median(ytrain))
    models={'persistence':None,'median':median};selected={};scores={};grid_scores=[];fit_seconds={}
    def base_predict(name,model,x):
        if name=='persistence':return x[:,0]
        if name=='median':return np.full(len(x),model)
        return model.predict(x)
    for name,model in models.items():scores[name]=metrics(yv,clip_predictions(base_predict(name,model,xv))[0])
    for label,pool in [('equal',train),('full',full)]:
        x=pool[FEATURES].to_numpy();y=pool.target.to_numpy()
        for family in ['ridge','hgb']:
            best=None;start=time.perf_counter()
            if family=='ridge':grid=[{'alpha':a} for a in [0.,.1,1.,10.,100.]]
            else:grid=[{'loss':loss,'max_leaf_nodes':leaves,'l2_regularization':reg}
                       for loss,leaves,reg in itertools.product(['squared_error','absolute_error'],[7,15,31],[0.,1.])]
            for config in grid:
                if family=='ridge':estimator=make_pipeline(StandardScaler(),Ridge(**config))
                else:estimator=HistGradientBoostingRegressor(**config,max_iter=200,learning_rate=.05,
                      min_samples_leaf=20,early_stopping=False,random_state=42)
                estimator.fit(x,y)
                pred,negative=clip_predictions(estimator.predict(xv));score=metrics(yv,pred)
                key=json.dumps(config,sort_keys=True,separators=(',',':'))
                grid_scores.append({'family':family,'pool':label,'config':config,'rmse':score['rmse'],'mae':score['mae'],'negative_predictions':negative})
                candidate=(score['rmse'],key)
                if best is None or candidate<best[0]:best=(candidate,estimator,config,score)
            name=family+'_'+label;models[name]=best[1];scores[name]=best[3]
            selected[name]={'config':best[2],'training_rows':len(pool),'validation':best[3]}
            fit_seconds[name]=time.perf_counter()-start
    champion=min(scores,key=lambda name:(scores[name]['rmse'],name))
    tool_val_raw=np.asarray(bridge('predict',{'model':workbench['champion'],'inputs':xv.tolist()}))
    np.testing.assert_allclose(tool_val_raw,independent_predict(workbench['champion'],xv),rtol=1e-10,atol=1e-7)
    tool_val,tool_val_negative=clip_predictions(tool_val_raw)
    model_hashes={}
    for name,model in models.items():
        blob=pickle.dumps(model,protocol=5);(OUT/(name+'.pkl')).write_bytes(blob);model_hashes[name]=sha(blob)
    save('workbench_model.json',workbench['champion'])
    freeze={'frozen_at':now(),'evaluation_commit':os.environ.get('GITHUB_SHA','local'),
      'protocol_commit':PROTOCOL_COMMIT,'release_commit':BASE,'engine_sha256':ENGINE_HASH,
      'protocol_sha256':sha((HERE/'PROTOCOL.md').read_bytes()),
      'code_sha256':{name:sha((HERE/name).read_bytes()) for name in ['core.py','run_eval.py','workbench.mjs','test_core.py']},
      'source_archive_sha256':sha(raw),'nested_archive_sha256':sha(nested_raw),'development_station_sha256':development_source_hash,
      'development_csv_sha256':sha((OUT/'development.csv').read_bytes()),'development':development_meta,
      'sample_rows':len(sample),'split_manifest_sha256':split_hash,
      'partitions':{k:{'n':len(v),'first':sample.index[v].min().isoformat(),'last':sample.index[v].max().isoformat()} for k,v in split.items()},
      'full_training_rows':len(full),'model_file_sha256':model_hashes,'workbench_model':workbench['champion'],
      'workbench_internal_status':workbench['status'],'workbench_internal_test':workbench['test'],
      'workbench_validation_clipped':metrics(yv,tool_val),'workbench_validation_negatives':tool_val_negative,
      'workbench_search':workbench['search'],'selected_baselines':selected,'baseline_validation':scores,
      'primary_baseline':champion,'all_validation_grid_results':grid_scores,
      'training_target_q90':float(np.quantile(ytrain,.9)),
      'compute_seconds':{'workbench':tool_seconds,**fit_seconds},
      'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,
                     'node':subprocess.check_output(['node','--version'],text=True).strip()},
      'live_assets':assets,'external_station_extractions_before_freeze':0}
    freeze_hash=save('freeze.json',freeze)
    emit('FREEZE_JSON',freeze)
    # Every fitted model and selection is fixed above. Test files are first opened below.
    frozen=True;site_results={};bootstrap_cohorts=[];comparisons=[];prediction_frames=[]
    lo=train[FEATURES].min().to_numpy();hi=train[FEATURES].max().to_numpy()
    for station in ['Dongsi','Dingling']:
        test_raw,station_hash=station_data(station)
        frame,meta=prepare(test_raw,station,'2016-01-01','2016-12-31T18:00:00')
        if len(frame)<1000:raise RuntimeError('Insufficient test coverage at '+station)
        x=frame[FEATURES].to_numpy();actual=frame.target.to_numpy();predictions={};negative={}
        raw_tool=np.asarray(bridge('predict',{'model':workbench['champion'],'inputs':x.tolist()}))
        np.testing.assert_allclose(raw_tool,independent_predict(workbench['champion'],x),rtol=1e-10,atol=1e-7)
        predictions['workbench'],negative['workbench']=clip_predictions(raw_tool)
        for name,model in models.items():predictions[name],negative[name]=clip_predictions(base_predict(name,model,x))
        score={name:metrics(actual,pred) for name,pred in predictions.items()}
        tail=actual>=freeze['training_target_q90']
        tail_scores={name:metrics(actual[tail],pred[tail]) for name,pred in predictions.items()} if tail.any() else {}
        out=frame.copy();out.insert(0,'station',station)
        for name,pred in predictions.items():out['prediction_'+name]=pred
        prediction_frames.append(out)
        monthly={str(month):{name:metrics(actual[frame.index.month==month],pred[frame.index.month==month])
                            for name,pred in predictions.items()} for month in sorted(set(frame.index.month))}
        site_results[station]={'coverage':meta,'source_station_sha256':station_hash,'metrics':score,'tail_metrics':tail_scores,
            'out_of_training_range_rows':int(((x<lo)|(x>hi)).any(axis=1).sum()),'unclipped_negative_counts':negative,
            'nonfinite_prediction_count':0,'first_origin':frame.index.min().isoformat(),'last_origin':frame.index.max().isoformat()}
        save(station+'_monthly.json',monthly)
        bootstrap_cohorts.append({'times':frame.index,'actual':actual,'tool':predictions['workbench'],'baseline':predictions[champion]})
        w,b,p=score['workbench'],score[champion],score['persistence']
        comparisons.append({'site':station,'tool_rmse':w['rmse'],'baseline_rmse':b['rmse'],'persistence_rmse':p['rmse'],
                            'tool_mae':w['mae'],'baseline_mae':b['mae'],'persistence_mae':p['mae']})
    uncertainty=bootstrap_ratio(bootstrap_cohorts)
    predictions=pd.concat(prediction_frames)
    predictions.index.name='forecast_origin'
    predictions.to_csv(OUT/'predictions.csv',float_format='%.12g')
    # Re-read the retained forecasts and independently recompute metrics from the CSV.
    reread=pd.read_csv(OUT/'predictions.csv')
    for station,record in site_results.items():
        part=reread[reread.station==station]
        for name,s in record['metrics'].items():
            rmse=float(np.sqrt(np.mean((part['prediction_'+name]-part.target)**2)))
            if not np.isclose(rmse,s['rmse'],rtol=1e-9,atol=1e-8):raise RuntimeError('CSV metric readback discrepancy')
    pooled={name:{'rmse':float(np.sqrt(np.mean([v['metrics'][name]['mse'] for v in site_results.values()]))),
                  'mae':float(np.mean([v['metrics'][name]['mae'] for v in site_results.values()]))}
            for name in ['workbench',*models]}
    passed=advantage_gate(comparisons,uncertainty['ci95'][1])
    result={'evaluation':'pm25-utility-v1','completed_at':now(),'evaluation_commit':os.environ.get('GITHUB_SHA','local'),
      'protocol_commit':PROTOCOL_COMMIT,'freeze_sha256':freeze_hash,'release_commit':BASE,'engine_sha256':ENGINE_HASH,
      'primary_baseline':champion,'sites':site_results,'site_balanced_metrics':pooled,
      'bootstrap_workbench_over_baseline':uncertainty,'gate_comparisons':comparisons,'useful_advantage':passed,
      'decision':'prospective pilot decision warranted; no automatic deployment' if passed else 'no demonstrated useful advantage; stop tool expansion',
      'predictions_csv_sha256':sha((OUT/'predictions.csv').read_bytes()),'prediction_rows':len(predictions),
      'extraction_log':extraction_log,'independent_python_prediction_check':'passed','csv_metric_readback':'passed',
      'protocol_deviations':[],'source_url':SOURCE,'data_license':'CC BY 4.0; Song Chen (2017), DOI 10.24432/C5RK5G',
      'limits':['Retrospective data, not a prospective intervention or new scientific discovery.',
                'Separate later sites within one network; shared weather and residual temporal dependence remain.',
                'Complete-case evaluation excludes missing readings; source publication latency was not measured.',
                'One-hour-ahead predictions made at six-hourly origins, not an all-hours evaluation.',
                'Predictive equation utility only: the proposed-experiment component was not field-tested.',
                'No runtime changes, main updates, deployment, outreach, paid APIs, artifact/cache uploads or schedules.']}
    save('result.json',result);emit('RESULT_JSON',result)
    # Small durable receipt; no hosted artifact/cache storage is consumed.
    receipt={'freeze':freeze,'result':result,'split_manifest':split_manifest}
    packed=base64.b64encode(gzip.compress(encoded(receipt),mtime=0)).decode()
    for i in range(0,len(packed),6000):print(f'AUDIT_B64_PART_{i//6000} '+packed[i:i+6000],flush=True)
    print('AUDIT_B64_SHA256 '+sha(packed.encode()),flush=True)
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:Path(summary).write_text('# First utility test\n\n'+result['decision']+'\n\n'+json.dumps(pooled,indent=2))

if __name__=='__main__':
    try:run()
    except Exception as exc:
        failure={'failed_at':now(),'type':type(exc).__name__,'message':str(exc),'outcome':'no claimed advantage; preserve attempt'}
        if OUT.exists():save('failure.json',failure)
        emit('FAILURE_JSON',failure)
        raise
