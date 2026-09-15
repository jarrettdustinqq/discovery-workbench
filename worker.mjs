import {discover} from './engine.mjs';
self.onmessage=({data})=>{
  try{const result=discover(data.dataset,data.options,progress=>self.postMessage({type:'progress',progress}));self.postMessage({type:'result',result});}
  catch(error){self.postMessage({type:'error',message:error instanceof Error?error.message:'Search failed.'});}
};
