// Isolated browser harness: actual QA components, synthetic role context, no auth bypass route.
const fs = require('fs');
const path = require('path');
const ts = require('typescript');
module.exports = function bundleQA(options = {}) {
  const modules = [], ids = new Map();
  function add(file) {
    if (ids.has(file)) return ids.get(file);
    const id = modules.length; ids.set(file, id); modules.push('');
    let source = fs.readFileSync(file, 'utf8');
    if (/\.tsx?$/.test(file)) source = ts.transpileModule(source, { fileName:file, compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 } }).outputText;
    source = source.replace(/require\(["']([^"']+)["']\)/g, (_, request) => {
      if (request.endsWith('.module.css')) {
        const css = fs.readFileSync(path.resolve(path.dirname(file),request),'utf8');
        const names = Array.from(css.matchAll(/\.([a-zA-Z][\w-]*)/g), match => match[1]);
        const classes = Object.fromEntries(names.map(name => [name,name === 'screen' ? (options.cssClass || 'qa-screen') : name]));
        return '({__esModule:true,default:'+JSON.stringify(classes)+'})';
      }
      if (request === './admin-shell' && !options.wrapperPath) return '({useAdminRole:()=>window.qaRole})';
      if (options.wrapperPath && request === 'next/navigation') return '({usePathname:()=>location.pathname,useRouter:()=>({push:(href)=>location.assign(href),replace:(href)=>location.replace(href),refresh:()=>location.reload()})})';
      if (options.wrapperPath && (request.endsWith('/app/admin/actions') || request.endsWith('/app/auth/actions'))) return '({adminLanguage:async()=>{},logout:async()=>{}})';
      if (request === 'next/link') return '({__esModule:true,default:({children,href,prefetch,...props})=>requireReact.createElement("a",{href,...props},children)})';
      const resolved = require.resolve(request, { paths: [path.dirname(file)] });
      return '__require(' + add(resolved) + ')';
    });
    modules[id] = 'function(module,exports,__require){' + source + '\n}';
    return id;
  }
  const react = add(require.resolve('react'));
  const dom = add(require.resolve('react-dom/client'));
  const qa = add(path.resolve(__dirname, options.componentPath || '../components/admin-qa.tsx'));
  const toast = add(path.resolve(__dirname, '../components/admin-toast.tsx'));
  const wrapper = options.wrapperPath ? add(path.resolve(__dirname, options.wrapperPath)) : undefined;
  const screen = 'requireReact.createElement(__require('+qa+')["'+(options.exportName || 'AdminQA')+'"], window.qaProps || {})';
  const content = wrapper === undefined ? screen : 'requireReact.createElement(__require('+wrapper+').AdminShell,{security:window.qaSecurity,ur:window.qaUr||false},'+screen+')';
  const tree = 'requireReact.createElement(__require('+toast+').AdminToastProvider,null,'+content+')';
  const server = options.hydrate ? add(require.resolve('react-dom/server.browser')) : undefined;
  const mount = server === undefined ? '__require('+dom+').createRoot(document.getElementById("root")).render('+tree+')' : '(function(){const root=document.getElementById("root"),tree='+tree+';window.qaHydrationErrors=[];root.innerHTML=__require('+server+').renderToString(tree);__require('+dom+').hydrateRoot(root,tree,{onRecoverableError:(error)=>window.qaHydrationErrors.push(error.message)});})()';
  return '(function(){const process={env:{NODE_ENV:"development"}}, modules=['+modules.join(',')+'],cache={}; function __require(id){if(cache[id])return cache[id].exports;const m=cache[id]={exports:{}};modules[id](m,m.exports,__require);return m.exports;} const requireReact=__require('+react+'); window.mountQA=()=>'+mount+'; window.mountQA();})();';
};
