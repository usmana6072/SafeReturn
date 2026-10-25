// Webpack emits static/css; Turbopack emits CSS chunks. Use actual build styles
// in either mode; never silently test a layout without its utility stylesheet.
const fs=require('node:fs'),path=require('node:path');
module.exports=function compiledAdminCss(){const dirs=['.next/static/css','.next/static/chunks'];const files=dirs.flatMap(d=>fs.existsSync(d)?fs.readdirSync(d).filter(f=>f.endsWith('.css')).map(f=>path.join(d,f)):[]);if(!files.length)throw Error('Build CSS required for isolated Admin browser checks');return files.map(f=>fs.readFileSync(f,'utf8')).join('\n');};
