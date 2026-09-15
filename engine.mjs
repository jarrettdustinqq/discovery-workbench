/** Bounded symbolic model discovery. No eval, network, dependencies or hidden inference. */
export const VERSION = '0.1.0';
const MAX_BYTES = 1048576, MAX_ROWS = 2000, MAX_EVALUATIONS = 1500;
const NUMBER = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/;
const HEADER = /^[A-Za-z_][A-Za-z0-9_]{0,31}$/;
const mean = a => a.reduce((s,v)=>s+v,0)/a.length;
const dot = (a,b) => a.reduce((s,v,i)=>s+v*b[i],0);
const variance = a => { const m=mean(a); return mean(a.map(v=>(v-m)**2)); };
function random(seed) {let a=seed>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};}
function validate(data, full=true) {
  if(!data || !Array.isArray(data.headers) || !Array.isArray(data.rows)) throw Error('Expected headers and numeric rows.');
  const {headers,rows}=data;
  if(headers.length<2 || headers.length>5) throw Error('Use 1–4 input columns and one final target column.');
  if(headers.some(h=>typeof h!=='string'||!HEADER.test(h)) || new Set(headers).size!==headers.length) throw Error('Headers must be unique identifiers: letters, digits, underscore; start with a letter or underscore; max 32 characters.');
  if(rows.length>MAX_ROWS) throw Error('Maximum 2,000 data rows.');
  if(full && rows.length<30) throw Error('At least 30 rows and 30 distinct input groups are required.');
  for(let i=0;i<rows.length;i++) {
    if(!Array.isArray(rows[i]) || rows[i].length!==headers.length) throw Error(`Row ${i+2}: inconsistent column count.`);
    for(const v of rows[i]) {
      if(typeof v!=='number'||!Number.isFinite(v)) throw Error(`Row ${i+2}: every value must be a finite number.`);
      if(Math.abs(v)>1e6) throw Error(`Row ${i+2}: numeric magnitude exceeds the supported range (1e6).`);
    }
  }
}
export function parseCSV(text) {
  if(typeof text!=='string') throw Error('CSV must be text.');
  if(text.length>MAX_BYTES || new TextEncoder().encode(text).length>MAX_BYTES) throw Error('CSV exceeds the 1 MiB size limit.');
  text=text.replace(/^\uFEFF/,'');
  const records=[]; let row=[],field='',quoted=false,closed=false;
  const endField=()=>{row.push(field.trim());field='';closed=false;};
  const endRow=()=>{endField();if(row.length>1||row.some(v=>v!==''))records.push(row);row=[];};
  for(let i=0;i<text.length;i++) {
    const c=text[i];
    if(quoted) {if(c==='"'){if(text[i+1]==='"'){field+='"';i++;}else{quoted=false;closed=true;}}else field+=c;continue;}
    if(c==='"'){if(field.trim()!==''||closed)throw Error('Malformed CSV quote.');quoted=true;continue;}
    if(c===','){endField();continue;}
    if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;endRow();continue;}
    if(closed && !/\s/.test(c)) throw Error('Unexpected characters after closing CSV quote.');
    field+=c;
  }
  if(quoted)throw Error('Unclosed CSV quote.');
  if(field!==''||row.length)endRow();
  if(records.length<2)throw Error('CSV needs a header and numeric data rows.');
  const headers=records.shift();
  const rows=records.map((r,i)=>r.map(s=>{if(!NUMBER.test(s))throw Error(`Row ${i+2}: missing or invalid numeric value.`);const v=Number(s);if(!Number.isFinite(v))throw Error(`Row ${i+2}: number must be finite.`);return v;}));
  const data={headers,rows};validate(data,false);return data;
}
export function toCSV(data) {validate(data,false);return [data.headers.join(','),...data.rows.map(r=>r.join(','))].join('\n')+'\n';}
export function splitData(data,seed=42,mode='random') {
  validate(data);
  if(!Number.isInteger(seed)||seed<0||seed>4294967295)throw Error('Seed must be an integer from 0 to 4294967295.');
  if(!['random','ordered'].includes(mode))throw Error('Invalid split mode option.');
  const groups=new Map();
  data.rows.forEach((r,i)=>{const k=JSON.stringify(r.slice(0,-1));if(!groups.has(k))groups.set(k,[]);groups.get(k).push(i);});
  const entries=[...groups.values()];
  if(entries.length<30)throw Error('At least 30 distinct input groups are required for independent splits.');
  if(mode==='random'){const rng=random(seed);for(let i=entries.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[entries[i],entries[j]]=[entries[j],entries[i]];}}
  const a=Math.floor(entries.length*.6),b=Math.floor(entries.length*.8);
  return {train:entries.slice(0,a).flat(),validation:entries.slice(a,b).flat(),test:entries.slice(b).flat()};
}
function featureValue(f,x) {
  const a=x[f.a];
  switch(f.op){
    case 'raw':return a;case 'square':return a*a;case 'cube':return a*a*a;
    case 'sqrtabs':return Math.sqrt(Math.abs(a));case 'logabs':return Math.log1p(Math.abs(a));
    case 'sin':return Math.sin(a);case 'cos':return Math.cos(a);
    case 'reciprocal':return Math.abs(a)<1e-12?NaN:1/a;
    case 'product':return a*x[f.b];case 'ratio':return Math.abs(x[f.b])<1e-12?NaN:a/x[f.b];
    default:throw Error('Unknown feature operation.');
  }
}
function grammar(names,family) {
  const features=[];
  const add=(op,a,b,label,cost)=>features.push({op,a,...(b===null?{}:{b}),label,cost,id:features.length});
  names.forEach((n,a)=>{
    add('raw',a,null,n,1);add('square',a,null,`${n}^2`,2);add('cube',a,null,`${n}^3`,3);add('reciprocal',a,null,`1/${n}`,3);
    if(family==='expanded'){add('sqrtabs',a,null,`sqrt(abs(${n}))`,3);add('logabs',a,null,`log(1+abs(${n}))`,4);add('sin',a,null,`sin(${n})`,4);add('cos',a,null,`cos(${n})`,4);}
  });
  for(let a=0;a<names.length;a++)for(let b=a+1;b<names.length;b++)add('product',a,b,`${names[a]}*${names[b]}`,2);
  for(let a=0;a<names.length;a++)for(let b=0;b<names.length;b++)if(a!==b)add('ratio',a,b,`${names[a]}/${names[b]}`,3);
  return features;
}
/** Fit on training data only, using centered/scaled modified Gram–Schmidt QR. */
function fit(ids,features,columns,rows,train) {
  const y=train.map(i=>rows[i].at(-1)),ym=mean(y),target=y.map(v=>v-ym);
  const q=[],R=[],scales=[],means=[];
  for(let j=0;j<ids.length;j++) {
    const values=train.map(i=>columns[ids[j]][i]);if(values.some(v=>!Number.isFinite(v)))return null;
    const mu=mean(values),sd=Math.sqrt(variance(values));
    if(sd<1e-12*Math.max(1,Math.abs(mu)))return null;
    const v=values.map(n=>(n-mu)/sd);means.push(mu);scales.push(sd);
    R[j]=Array(ids.length).fill(0);
    for(let k=0;k<j;k++){R[k][j]=dot(q[k],v);for(let i=0;i<v.length;i++)v[i]-=R[k][j]*q[k][i];}
    // A second orthogonalization pass limits numerical loss for near-collinear terms.
    for(let k=0;k<j;k++){const correction=dot(q[k],v);R[k][j]+=correction;for(let i=0;i<v.length;i++)v[i]-=correction*q[k][i];}
    const norm=Math.sqrt(dot(v,v));if(norm<1e-7*Math.sqrt(v.length))return null;
    R[j][j]=norm;q.push(v.map(n=>n/norm));
  }
  const beta=q.map(v=>dot(v,target));
  for(let j=ids.length-1;j>=0;j--){for(let k=j+1;k<ids.length;k++)beta[j]-=R[j][k]*beta[k];beta[j]/=R[j][j];}
  const coefficients=beta.map((v,i)=>v/scales[i]),intercept=ym-dot(coefficients,means);
  if(!Number.isFinite(intercept)||coefficients.some(v=>!Number.isFinite(v)))return null;
  const terms=ids.map((id,i)=>({feature:features[id],coefficient:coefficients[i]}));
  const fmt=n=>Number(n.toPrecision(7)).toString();
  const expression=fmt(intercept)+terms.map(t=>` ${t.coefficient<0?'-':'+'} ${fmt(Math.abs(t.coefficient))} * ${t.feature.label}`).join('');
  return {inputCount:rows[0].length-1,intercept,terms,expression,complexity:1+terms.reduce((s,t)=>s+t.feature.cost,0)};
}
export function predict(model,inputs) {
  if(!model||!Array.isArray(model.terms)||!Array.isArray(inputs)||inputs.length!==model.inputCount||inputs.some(x=>!Number.isFinite(x)))throw Error('Invalid model or finite input vector.');
  return model.intercept+model.terms.reduce((s,t)=>s+t.coefficient*featureValue(t.feature,inputs),0);
}
function metrics(model,rows,indices) {
  const actual=indices.map(i=>rows[i].at(-1)),predicted=indices.map(i=>predict(model,rows[i].slice(0,-1)));
  if(predicted.some(v=>!Number.isFinite(v)))return {mse:null,rmse:null,r2:null,invalid:true,n:indices.length};
  const mse=mean(actual.map((v,i)=>(v-predicted[i])**2)),v=variance(actual);
  return {mse,rmse:Math.sqrt(mse),r2:v<1e-20?null:1-mse/v,invalid:false,n:indices.length};
}
function compare(a,b){return a.score-b.score||a.model.complexity-b.model.complexity||a.key.localeCompare(b.key);}
function experimentFor(models,rows,names,train,seed) {
  if(models.length<2)return null;
  // Only training inputs determine the candidate search domain. Final data never guide proposals.
  const observed=train.map(i=>rows[i].slice(0,-1)),rng=random(seed^0xA73F1942);
  const bounds=names.map((_,j)=>[Math.min(...observed.map(r=>r[j])),Math.max(...observed.map(r=>r[j]))]);
  const known=new Set(observed.map(x=>JSON.stringify(x))),points=[];
  for(let mask=0;mask<2**names.length;mask++)points.push(bounds.map(([lo,hi],j)=>((mask>>j)&1)?hi:lo));
  for(let i=0;i<384;i++)points.push(bounds.map(([lo,hi])=>lo+rng()*(hi-lo)));
  let best=null;
  for(const inputs of points){
    if(known.has(JSON.stringify(inputs)))continue;
    const predictions=models.map(m=>predict(m,inputs));if(predictions.some(v=>!Number.isFinite(v)))continue;
    const disagreement=Math.max(...predictions)-Math.min(...predictions);
    if(!best||disagreement>best.disagreement)best={inputs,predictions,disagreement};
  }
  if(!best||best.disagreement<1e-8*Math.max(1,...best.predictions.map(Math.abs)))return null;
  const nearestDistance=Math.min(...observed.map(r=>Math.sqrt(mean(r.map((v,j)=>((v-best.inputs[j])/(bounds[j][1]-bounds[j][0]||1))**2)))));
  return {...best,bounds,nearestDistance,offSupport:nearestDistance>.15,modelExpressions:models.map(m=>m.expression),note:'Proposed measurement only. Disagreement is not a confidence interval. Check physical feasibility and safety independently.'};
}
export function discover(data,options={},onProgress=()=>{}) {
  validate(data);
  const {seed=42,family='algebra',maxTerms=3,mode='random'}=options;
  if(!['algebra','expanded'].includes(family))throw Error('Invalid grammar family option.');
  if(!Number.isInteger(maxTerms)||maxTerms<1||maxTerms>3)throw Error('Maximum terms option must be 1, 2, or 3.');
  const split=splitData(data,seed,mode),{headers,rows}=data,names=headers.slice(0,-1);
  const features=grammar(names,family),columns=features.map(f=>rows.map(r=>featureValue(f,r)));
  const y=split.train.map(i=>rows[i].at(-1)),targetVariance=variance(y),scale=Math.max(targetVariance,1e-12);
  const warnings=['Association is not causation. No dimensional or physical constraints are enforced.','Final metrics are one held-out check, not independent replication. Adaptive reruns require fresh external validation.'];
  if(mode==='ordered')warnings.push('Ordered input groups are a stress test, not a guarantee of chronological or time-series validation.');
  const inputKeys=rows.map(r=>JSON.stringify(r.slice(0,-1)));
  if(new Set(inputKeys).size<rows.length)warnings.push('Repeated input groups are kept together; partition row percentages may differ from 60/20/20.');
  for(let a=0;a<names.length;a++)for(let b=a+1;b<names.length;b++){
    const av=split.train.map(i=>rows[i][a]),bv=split.train.map(i=>rows[i][b]),am=mean(av),bm=mean(bv),den=Math.sqrt(variance(av)*variance(bv));
    if(den>1e-20&&Math.abs(mean(av.map((v,i)=>(v-am)*(bv[i]-bm)))/den)>.98)warnings.push(`Inputs ${names[a]} and ${names[b]} are strongly correlated. The data may not identify which relationship is causal.`);
  }
  const baseline=fit([],features,columns,rows,split.train),candidates=[],seen=new Set();let evaluated=0;
  const consider=ids=>{
    const key=ids.join(',');if(seen.has(key)||evaluated>=MAX_EVALUATIONS)return null;seen.add(key);evaluated++;
    const model=fit(ids,features,columns,rows,split.train);if(!model)return null;
    const validation=metrics(model,rows,split.validation);if(validation.invalid)return null;
    const candidate={key,ids,model,validation,score:validation.mse/scale+.0005*model.complexity};candidates.push(candidate);return candidate;
  };
  let beam=[consider([])];
  for(let depth=1;depth<=maxTerms;depth++){
    const level=[];
    for(const parent of beam)for(const f of features){
      if(parent.ids.includes(f.id))continue;
      const c=consider([...parent.ids,f.id].sort((a,b)=>a-b));if(c)level.push(c);
    }
    level.sort(compare);beam=level.slice(0,8);onProgress({depth,evaluated});if(!beam.length)break;
  }
  candidates.sort(compare);const winner=candidates[0],champion=winner.model;
  const plausible=candidates.filter(c=>c.score<=winner.score+.02&&c.validation.mse<=winner.validation.mse+.03*scale).slice(0,8);
  const experiment=experimentFor(plausible.map(c=>c.model),rows,names,split.train,seed);
  // Final targets are consulted only after both champion and proposed experiment are frozen.
  const finalMetrics=metrics(champion,rows,split.test),baselineMetrics=metrics(baseline,rows,split.test);
  let status='not_supported';
  if(targetVariance<1e-20){status='constant_target';warnings.push('Training target is constant. There is no varying relationship to discover.');}
  else if(finalMetrics.invalid){status='invalid_on_holdout';warnings.push('The selected expression is undefined for at least one final test input. Do not use it.');}
  else if(baselineMetrics.mse>0&&finalMetrics.mse<.8*baselineMetrics.mse&&finalMetrics.r2!==null&&finalMetrics.r2>.5)status='supported_on_this_split';
  else warnings.push('The selected model did not clear the held-out utility threshold: R² > 0.5 and at least 20% less MSE than the training-mean baseline.');
  if(experiment?.offSupport)warnings.push('The proposed experiment is far from observed combinations, even though each coordinate is in range. Correlations or physical constraints may make it infeasible.');
  return {engineVersion:VERSION,options:{seed,family,maxTerms,mode},headers:[...headers],rowCount:rows.length,split,champion,validation:winner.validation,test:finalMetrics,baseline:baselineMetrics,status,warnings,experiment,alternatives:plausible.map(c=>({expression:c.model.expression,validationRMSE:c.validation.rmse,complexity:c.model.complexity,score:c.score})),search:{evaluated,limit:MAX_EVALUATIONS,featureCount:features.length,method:'Training-only QR; beam width 8; validation MSE / training variance + 0.0005 × complexity'},testPoints:split.test.map(i=>({row:i+2,actual:rows[i].at(-1),predicted:Number.isFinite(predict(champion,rows[i].slice(0,-1)))?predict(champion,rows[i].slice(0,-1)):null}))};
}
export function makeDemo(kind='polynomial') {
  const rng=random(1948);let headers,rows,truth;
  if(kind==='polynomial'){headers=['a','b','y'];rows=Array.from({length:160},()=>{const a=-2+4*rng(),b=-1+4*rng();return[a,b,1.7+2.4*a*a+.8*b];});truth='y = 1.7 + 2.4*a² + 0.8*b (noise-free, synthetic)';}
  else if(kind==='confounded'){headers=['sensor_a','sensor_b','y'];rows=Array.from({length:140},()=>{const a=4*rng();return[a,a,2+3*a];});truth='y = 2 + 3*sensor_a, but sensor_b equals sensor_a in every observed row. Observations alone cannot distinguish them.';}
  else if(kind==='noise'){headers=['x','y'];rows=Array.from({length:300},()=>[rng(),rng()]);truth='Independent pseudorandom x and y; no planted relationship.';}
  else if(kind==='nist'){headers=["nist_measurement", "customer_measurement"];rows=[[0.2,0.1],[337.4,338.8],[118.2,118.1],[884.6,888.0],[10.1,9.2],[226.5,228.1],[666.3,668.5],[996.3,998.5],[448.6,449.1],[777.0,778.9],[558.2,559.2],[0.4,0.3],[0.6,0.1],[775.5,778.1],[666.9,668.8],[338.0,339.3],[447.5,448.9],[11.6,10.8],[556.0,557.7],[228.1,228.3],[995.8,998.0],[887.6,888.8],[120.2,119.6],[0.3,0.3],[0.3,0.6],[556.8,557.6],[339.1,339.3],[887.2,888.0],[999.0,998.5],[779.0,778.9],[11.1,10.2],[118.3,117.6],[229.2,228.9],[669.1,668.4],[448.9,449.2],[0.5,0.2]];truth='NIST Norris: 36 published ozone-monitor calibration observations. This is reference validation, not a new discovery.';}
  else throw Error('Unknown demo scenario.');
  return {headers,rows,origin:kind==='nist'?'observed-reference':'synthetic',truth};
}
