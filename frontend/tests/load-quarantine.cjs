// Run the real protected policy with a synthetic transport; never bypass its rules.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
module.exports=function loadQuarantine(fetch){
 function load(name){const box={exports:{},Request,fetch,require:()=>load('quarantine-operations')};vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../lib/api',name+'.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,box);return box.exports;}
 return load('quarantine');
};
