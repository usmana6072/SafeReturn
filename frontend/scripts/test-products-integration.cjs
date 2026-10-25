const assert=require('node:assert/strict');
const {NextRequest}=require('next/server');
const {createHarness,id,cat}=require('../tests/products-fixture.cjs');
async function main(){const h=createHarness(),{state,relay}=h;const contract=h.load(require('node:path').resolve(__dirname,'../lib/admin-products-contract.ts'));
 const get=(path,extra={})=>h.dispatch('https://products.test/admin/catalog-api?'+new URLSearchParams({path,...extra}));
 const product={name:'New sticker',slug:'new-sticker',description:null,category_id:cat,qr_type:'lost',price_per_copy:'12.50',max_order_copies:100,lifecycle_status:'draft',is_featured:false,featured_sort_order:0};
 const send=(path,method,body,version,key='stable-intent-0001',upload=false)=>h.dispatch('https://products.test/admin/catalog-api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,method,body,version,key,...(upload?{authorize_upload:true}:{})})});
 let checks=0;const status=async(p,expected)=>{const r=await p;assert.equal(r.status,expected);checks++;return r;};
 state.authorized=false;await status(get('/admin/products'),401);assert.equal(state.calls.length,0);state.authorized=true;
 state.mfa=false;await status(get('/admin/products'),403);state.mfa=true;state.role='support';await status(get('/admin/products'),403);state.role='security_admin';await status(get('/admin/products'),200);state.role='operations';
 await status(get('/admin/products'),200);await status(get('/admin/products/'+id),200);await status(get('/admin/catalog/categories'),200);await status(get('/admin/catalog/approved-templates'),200);
 await status(get('/admin/products',{cursor:id,limit:'10'}),200);
 for(const path of ['/admin/qr-inventory/batches','/admin/orders/'+id+'/qr-allocation','/admin/support-cases/'+id+'/independent-qr','/admin/tag-pairs','/admin/orders','/admin/dashboard/summary']){const before=state.calls.length;await status(get(path),422);assert.equal(state.calls.length,before);}
 for(const extra of [{limit:'101'},{cursor:'../private'},{owner_id:id}])await status(get('/admin/products',extra),422);
 await status(get('/admin/products/'+id,{limit:'2'}),422);
 await status(relay.GET(new NextRequest('https://products.test/admin/catalog-api?path=/admin/products&path=/admin/products')),422);
 const created=await status(send('/admin/products','POST',product),201);assert.equal((await created.json()).name,'New sticker');
 const receipt=await status(send('/admin/products','POST',product),201);assert.equal((await receipt.json()).id,id);assert.equal(state.receipts.size,1);
 await status(send('/admin/products','POST',{...product,name:'Other'}),409);
 await status(send('/admin/products/'+id,'PATCH',{...product,name:'Edited'},1,'edit-intent'),200);assert.equal(state.calls.at(-1).options.headers['If-Match'],'"1"');
 state.conflict=true;await status(send('/admin/products/'+id,'PATCH',product,2,'stale-intent'),412);
 for(const change of [{price_per_copy:12},{price_per_copy:'0.001'},{max_order_copies:101},{private:'NO'}])await status(send('/admin/products','POST',{...product,...change},undefined,'invalid-intent'),422);
 await status(send('/admin/products','DELETE',undefined,1),422);await status(send('/admin/catalog/categories','PATCH',{},1),422);
 const category={name:'New category',slug:'new-category',is_active:true,sort_order:2};const cr=await status(send('/admin/catalog/categories','POST',category,undefined,'category-create'),201);const categoryId=(await cr.json()).id;await status(send('/admin/catalog/categories/'+categoryId,'PATCH',{...category,name:'Updated category'},1,'category-edit'),200);
 const variant={name:'Large',sku:'LARGE-1',size_mm:'40',material:'vinyl',color:'teal',fulfillment_method:'pdf_label',template_key:'approved-template',template_version:1,is_active:true,sort_order:2};const vr=await status(send('/admin/products/'+id+'/variants','POST',variant,3,'variant-create'),201);const v=await vr.json();assert.equal(v.unit_price,'12.50');await status(send('/admin/product-variants/'+v.id,'PATCH',{...variant,color:'blue'},v.catalog_version,'variant-edit'),200);
 const image={cloudinary_public_id:'safereturn/catalog/pending',alt_text:'Artwork',sort_order:0,is_primary:true};const ar=await status(send('/admin/products/'+id+'/images','POST',image,5,'upload-authorization',true),201);const grant=await ar.json();assert(!JSON.stringify(grant).includes('api_secret'));
 await status(send('/admin/products/'+id+'/images','POST',{...image,cloudinary_public_id:grant.public_id},5,'image-attach'),201);await status(send('/admin/products/'+id+'/images/'+h.img,'PATCH',{alt_text:'Edited alt',sort_order:2,is_primary:false},6,'image-edit'),200);await status(send('/admin/products/'+id+'/images/'+h.img,'DELETE',undefined,7,'image-unlink'),200);
 const before=state.calls.length;await status(relay.POST(new NextRequest('https://products.test/admin/catalog-api',{method:'POST',headers:{Origin:'https://attacker.invalid','Content-Type':'application/json'},body:JSON.stringify({path:'/admin/products',method:'POST',body:product,key:'safe-key-123'})})),403);assert.equal(state.calls.length,before);
 await status(relay.POST(new NextRequest('https://products.test/admin/catalog-api',{method:'POST',headers:{Origin:'https://products.test','Content-Type':'application/json'},body:JSON.stringify({padding:'X'.repeat(33000)})})),413);
 for(const code of [400,401,403,404,409,412,422,503]){state.status=code;const response=await status(get('/admin/products'),code);assert(!JSON.stringify(await response.json()).includes('DO_NOT_RENDER'));}state.status=0;
 state.malformed=true;await status(get('/admin/products'),503);state.malformed=false;
 for(const method of ['HEAD','OPTIONS','PUT','PATCH','DELETE'])await status(relay[method](),405);
 assert.throws(()=>contract.productBody({...product,lifecycle_status:'published'},true));assert.throws(()=>contract.variantBody({...variant,unit_price:'1.00'}));
 const partial=contract.parseProduct({...state.product,price_per_copy:null,variants:[{...v,unit_price:null}],images:[]});assert.equal(partial.price_per_copy,null);assert.equal(partial.variants[0].unit_price,null);
 for(const call of state.calls){if(call.path.startsWith('/api/v1/admin/print-templates')){assert.equal(call.method,'GET');h.load(require('node:path').resolve(__dirname,'../lib/admin-templates-contract.ts')).templateTarget(call.path.replace('/api/v1',''),call.method);}else contract.target(call.path.replace('/api/v1',''),call.method);assert.equal(call.options.cache,'no-store');assert.equal(call.options.redirect,'error');}
 console.log('PASS '+checks+' relay/contract checks; all 13 product routes, role/MFA/CSRF, sizes, replay/conflicts, media phases, bounds/redaction and default-deny. No network/DB requests.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
