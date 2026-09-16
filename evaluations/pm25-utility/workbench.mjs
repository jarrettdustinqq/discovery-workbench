/** Evaluation adapter only: imports the unchanged shipped numerical engine. */
import {readFileSync} from 'node:fs';
import {discover, predict} from '../../engine.mjs';
const payload=JSON.parse(readFileSync(0,'utf8'));
if(process.argv[2]==='train') {
  console.log(JSON.stringify(discover(payload,{seed:42,family:'algebra',maxTerms:3,mode:'ordered'})));
} else if(process.argv[2]==='predict') {
  const values=payload.inputs.map(x=>predict(payload.model,x));
  if(values.some(x=>!Number.isFinite(x))) throw Error('Nonfinite external prediction');
  console.log(JSON.stringify(values));
} else {
  throw Error('Expected train or predict');
}
