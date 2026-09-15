import {parseCSV,toCSV,makeDemo,predict,VERSION} from './engine.mjs';
const $=id=>document.getElementById(id);
let worker=null,timer=null,result=null,dataset=null,report=null,observation=null,runId=0;
const text=(id,value)=>{$(id).textContent=value;};
const fmt=v=>v===null||!Number.isFinite(v)?'Undefined':v===0?'0':Math.abs(v)<.001||Math.abs(v)>=10000?v.toExponential(2):Number(v.toPrecision(5)).toString();
function status(message,error=false){text('status',message);$('status').classList.toggle('error',error);}
function idle(){if(worker)worker.terminate();worker=null;if(timer)clearTimeout(timer);timer=null;$('run').disabled=false;$('cancel').hidden=true;}
function invalidate(){runId++;idle();result=null;report=null;observation=null;$('results').hidden=true;$('empty').hidden=false;$('append-observation').hidden=true;}
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function loadDemo(){invalidate();const d=makeDemo($('scenario').value);$('csv').value=toCSV(d);text('demo-note',`${d.origin==='synthetic'?'SYNTHETIC':'OBSERVED REFERENCE'} · ${d.truth}`);status('Ready. The demo’s answer is not supplied to the search.');}
async function hashData(data){const bytes=new TextEncoder().encode(JSON.stringify({headers:data.headers,rows:data.rows}));const buffer=await crypto.subtle.digest('SHA-256',bytes);return [...new Uint8Array(buffer)].map(x=>x.toString(16).padStart(2,'0')).join('');}
function plot(points){
  const canvas=$('plot'),ratio=window.devicePixelRatio||1,w=canvas.clientWidth,h=220;canvas.width=w*ratio;canvas.height=h*ratio;const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);ctx.clearRect(0,0,w,h);
  const valid=points.filter(p=>Number.isFinite(p.actual)&&Number.isFinite(p.predicted));if(!valid.length)return;
  let lo=Math.min(...valid.flatMap(p=>[p.actual,p.predicted])),hi=Math.max(...valid.flatMap(p=>[p.actual,p.predicted]));if(lo===hi){lo-=1;hi+=1;}const pad=(hi-lo)*.07;lo-=pad;hi+=pad;
  const left=48,top=12,right=w-15,bottom=h-37,X=x=>left+(x-lo)/(hi-lo)*(right-left),Y=y=>bottom-(y-lo)/(hi-lo)*(bottom-top);
  ctx.font='10px system-ui';ctx.lineWidth=1;
  for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4;ctx.strokeStyle='#e1e7df';ctx.beginPath();ctx.moveTo(X(v),top);ctx.lineTo(X(v),bottom);ctx.moveTo(left,Y(v));ctx.lineTo(right,Y(v));ctx.stroke();ctx.fillStyle='#596d68';ctx.textAlign='center';ctx.fillText(fmt(v),X(v),bottom+15);ctx.textAlign='right';ctx.fillText(fmt(v),left-7,Y(v)+3);}
  ctx.setLineDash([4,4]);ctx.strokeStyle='#82968f';ctx.beginPath();ctx.moveTo(X(lo),Y(lo));ctx.lineTo(X(hi),Y(hi));ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#176452bb';
  for(const p of valid){ctx.beginPath();ctx.arc(X(p.actual),Y(p.predicted),3.3,0,Math.PI*2);ctx.fill();}
  ctx.fillStyle='#596d68';ctx.textAlign='center';ctx.fillText('Actual target',(left+right)/2,h-3);ctx.save();ctx.translate(11,(top+bottom)/2);ctx.rotate(-Math.PI/2);ctx.fillText('Predicted target',0,0);ctx.restore();
}
function render(r){
  result=r;$('results').hidden=false;$('empty').hidden=true;
  const verdicts={supported_on_this_split:'Supported on this split',not_supported:'Not supported',constant_target:'Constant target',invalid_on_holdout:'Invalid on final test'};
  text('verdict',verdicts[r.status]);$('verdict').closest('section').dataset.status=r.status;
  text('equation',`${r.headers.at(-1)} = ${r.champion.expression}`);text('metric-r2',fmt(r.test.r2));text('metric-rmse',fmt(r.test.rmse));text('metric-baseline',fmt(r.baseline.rmse));
  text('split-note',`${r.split.train.length} training / ${r.split.validation.length} selection / ${r.split.test.length} final rows · ${r.search.evaluated} evaluated candidates · seed ${r.options.seed}`);
  $('warnings').replaceChildren(...r.warnings.map(w=>{const li=document.createElement('li');li.textContent=w;return li;}));
  $('alternatives').replaceChildren(...r.alternatives.map(a=>{const tr=document.createElement('tr');for(const v of [a.expression,fmt(a.validationRMSE)]){const td=document.createElement('td');td.textContent=v;tr.append(td);}return tr;}));
  $('experiment-inputs').replaceChildren();
  if(r.experiment){const e=r.experiment;text('experiment-summary',`At this proposed input, ${e.modelExpressions.length} comparably fitting explanations differ by ${fmt(e.disagreement)} target units. Measuring here could distinguish them.`);e.inputs.forEach((x,i)=>{const chip=document.createElement('span');chip.textContent=`${r.headers[i]} = ${fmt(x)}`;$('experiment-inputs').append(chip);});text('experiment-warning',`${e.offSupport?'OFF-SUPPORT: this input combination is far from observed data. ':''}Training-coordinate bounds are not a physical safety check. This is a proposal, not a performed experiment or a calibrated confidence interval.`);$('challenge-x').value=e.inputs.map(x=>Number(x.toPrecision(10))).join(', ');}
  else{text('experiment-summary','No materially disagreeing near-best models were found within the training-coordinate ranges. This is not proof that the selected explanation is true.');text('experiment-warning','A larger grammar or an independently chosen challenge may reveal failure.');$('challenge-x').value=dataset.rows[r.split.test[0]].slice(0,-1).join(', ');}
  text('challenge-label',`Inputs in order: ${r.headers.slice(0,-1).join(', ')}`);$('challenge-y').value='';text('challenge-result','');$('append-observation').hidden=true;plot(r.testPoints);
}
$('run').addEventListener('click',async()=>{
  invalidate();const id=runId;
  try{
    dataset=parseCSV($('csv').value);
    const options={seed:Number($('seed').value),family:$('family').value,maxTerms:Number($('terms').value),mode:$('mode').value};
    if($('seed').value.trim()==='')throw Error('Enter a numeric seed.');
    if(!window.Worker)throw Error('This browser does not support Web Workers. Use the Node CLI instead.');
    if(!crypto.subtle)throw Error('A secure HTTPS origin is required for reproducible dataset hashing.');
    $('run').disabled=true;$('cancel').hidden=false;status('Searching candidate representations; final test answers remain isolated.');
    const w=new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});worker=w;
    timer=setTimeout(()=>{if(id!==runId)return;invalidate();status('Search stopped after the 15-second runtime budget. Try fewer terms or a smaller dataset.',true);},15000);
    w.onerror=()=>{if(id!==runId)return;invalidate();status('Worker failed to start or execute. Check browser support; no result was retained.',true);};
    w.onmessage=async({data})=>{
      if(id!==runId)return;
      if(data.type==='progress'){status(`Testing ${data.progress.depth}-term explanations · ${data.progress.evaluated} candidates evaluated.`);return;}
      if(data.type==='error'){invalidate();status(data.message,true);return;}
      if(data.type==='result'){
        try{const sha=await hashData(dataset);if(id!==runId)return;idle();report={schemaVersion:1,engineVersion:VERSION,generatedAt:new Date().toISOString(),datasetSHA256:sha,data:{headers:dataset.headers,rows:dataset.rows},result:data.result,provenance:'Executed locally; generated timestamp and digest are not independent attestations.'};render(data.result);status(`Finished. ${data.result.search.evaluated} candidates evaluated. Export preserves full-precision evidence.`);}
        catch(error){invalidate();status(`Evidence export preparation failed: ${error.message}`,true);}
      }
    };
    w.postMessage({dataset,options});
  }catch(error){invalidate();status(error.message,true);}
});
$('cancel').addEventListener('click',()=>{invalidate();status('Cancelled. The worker was terminated; no partial result was promoted.');});
$('load-demo').addEventListener('click',loadDemo);
$('csv').addEventListener('input',()=>{invalidate();text('demo-note','CUSTOM INPUT · Imported or edited observations have not been independently verified.');status('Input changed. Run a fresh search.');});
for(const id of ['family','mode','seed','terms'])$(id).addEventListener('change',()=>{invalidate();status('Settings changed. Run a fresh search.');});
$('csv-file').addEventListener('change',async event=>{
  invalidate();const id=runId,file=event.target.files[0];if(!file)return;
  try{if(file.size>1048576)throw Error('CSV exceeds the 1 MiB size limit.');const value=await file.text();if(id!==runId)return;parseCSV(value);$('csv').value=value;text('demo-note','CUSTOM INPUT · Local file; not uploaded.');status('Local CSV loaded. Ready to search.');}
  catch(error){status(error.message,true);}
});
$('download-data').addEventListener('click',()=>{try{download('observations.csv',toCSV(parseCSV($('csv').value)),'text/csv');}catch(error){status(error.message,true);}});
$('export').addEventListener('click',()=>{if(report)download(`discovery-evidence-${report.datasetSHA256.slice(0,12)}.json`,JSON.stringify(report,null,2),'application/json');});
$('challenge').addEventListener('click',()=>{
  if(!result)return;observation=null;$('append-observation').hidden=true;
  try{const fields=$('challenge-x').value.split(',').map(v=>v.trim()),target=$('challenge-y').value.trim();if(fields.length!==dataset.headers.length-1||fields.some(v=>v==='')||target==='')throw Error('Enter every input and a measured target.');const d=parseCSV(dataset.headers.join(',')+'\n'+[...fields,target].join(','));const row=d.rows[0],prediction=predict(result.champion,row.slice(0,-1));if(!Number.isFinite(prediction))throw Error('The model is undefined at this input; this is a demonstrated domain failure.');const residual=row.at(-1)-prediction;observation=row;text('challenge-result',`New measurement ${fmt(row.at(-1))}; frozen-model prediction ${fmt(prediction)}; residual ${fmt(residual)}. Compare this error with instrument noise and final-test RMSE ${fmt(result.test.rmse)}. A single deviation is not automatically a causal refutation.`);$('append-observation').hidden=false;}
  catch(error){text('challenge-result',error.message);}
});
for(const id of ['challenge-x','challenge-y'])$(id).addEventListener('input',()=>{observation=null;$('append-observation').hidden=true;text('challenge-result','Measurement edited. Check it again before adding it.');});
$('append-observation').addEventListener('click',()=>{if(!observation)return;const next={headers:dataset.headers,rows:[...dataset.rows,observation]};const csv=toCSV(next);invalidate();$('csv').value=csv;text('demo-note','CUSTOM INPUT · A new measurement was added. Prior test results must not be treated as fresh independent evidence.');status('Observation added. Old result invalidated; rerun to update the model.');});
window.addEventListener('resize',()=>{if(result)plot(result.testPoints);});
loadDemo();
