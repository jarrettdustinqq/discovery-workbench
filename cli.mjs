#!/usr/bin/env node
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {parseCSV,discover,VERSION} from './engine.mjs';
const args=process.argv.slice(2);
if(args.length!==1||args[0]==='--help'){console.error('Usage: node cli.mjs observations.csv\nCSV: 1–4 inputs, final target; 30–2,000 rows. Output: reproducible JSON.');process.exitCode=args[0]==='--help'?0:2;}
else{
  try{const data=parseCSV(readFileSync(args[0],'utf8')),result=discover(data);const datasetSHA256=createHash('sha256').update(JSON.stringify({headers:data.headers,rows:data.rows})).digest('hex');console.log(JSON.stringify({schemaVersion:1,engineVersion:VERSION,datasetSHA256,data,result},null,2));}
  catch(error){console.error(`Error: ${error.message}`);process.exitCode=1;}
}
