"""Actual catalog HTTP handlers with an isolated SQL/session double; no DB/network/legacy setup.
Run from root: backend/.venv/Scripts/python.exe -B frontend/scripts/test-products-backend.py
This does NOT establish PostgreSQL/RLS/provider acceptance.
"""
import copy
import json
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v1 import catalog,catalog_templates
from pydantic import SecretStr
from app.api.auth import AccessError,access_error,AuthContext,get_auth_context
from app.core.config import Settings

class Result:
 def __init__(self,value=None):self.value=value
 def __iter__(self):return iter(self.value or [])
 def mappings(self):return self
 def all(self):return self.value or []
 def one(self):assert self.value is not None;return self.value
 def one_or_none(self):return self.value
 def scalar_one(self):return self.value
 def scalar_one_or_none(self):return self.value

class Session:
 def __init__(self):self.info={};self.tables={t:{} for t in ('products','product_categories','product_variants','product_images')};self.receipts={};self.sql=[]
 @contextmanager
 def begin_nested(self):
  before=copy.deepcopy((self.tables,self.receipts))
  try:yield
  except Exception:self.tables,self.receipts=before;raise
 def execute(self,statement,params=None):
  sql=' '.join(str(statement).split());p=params or {};self.sql.append(sql)
  assert not any(word in sql for word in ('public.tag_pairs','public.order_pair_units','public.qr_codes','allocation.finalize','sr_checkout','sr_typed_')),'Forbidden SQL reached'
  if 'to_regprocedure' in sql:return Result(False)
  if 'public.staff_roles' in sql:return Result(1)
  if 'pg_advisory_xact_lock' in sql:return Result()
  if 'SELECT * FROM public.idempotency_records' in sql:return Result(self.receipts.get((str(p['scope']),p['op'],p['key'])))
  if sql.startswith('INSERT INTO public.idempotency_records'):
   self.receipts[(str(p['scope']),p['op'],p['key'])]={'request_hash':p['hash'],'response_body_ciphertext':p['cipher'],'response_key_version':p['version']};return Result()
  if sql.startswith('INSERT INTO public.audit_events'):return Result()
  if sql.startswith('SELECT product_id FROM public.product_variants'):
   row=self.tables['product_variants'].get(str(p['id']));return Result(row['product_id'] if row else None)
  match=re.match(r'SELECT \* FROM public.(products|product_categories|product_variants|product_images)',sql)
  if match:
   table=self.tables[match[1]]
   if 'product_id=:id' in sql:return Result([copy.deepcopy(v) for v in table.values() if str(v.get('product_id'))==str(p['id'])])
   if 'id=:id' in sql:return Result(copy.deepcopy(table.get(str(p['id']))))
   rows=sorted((copy.deepcopy(v) for v in table.values()),key=lambda v:str(v['id']))
   if 'cursor' in p:rows=[v for v in rows if p['cursor'] is None or str(v['id'])>str(p['cursor'])]
   return Result(rows[:p.get('limit',100)])
  match=re.match(r'INSERT INTO public.(products|product_categories|product_variants|product_images)\(',sql)
  if match:
   kind=match[1];row={'id':str(uuid4()),'catalog_version':1,**copy.deepcopy(p)}
   if kind=='products':row={'allows_new_pair':False,'allows_existing_qr':False,**row}
   if kind=='product_variants':row={'currency_code':'PKR',**row}
   self.tables[kind][str(row['id'])]=row;return Result(copy.deepcopy(row))
  match=re.match(r'UPDATE public.(products|product_categories|product_variants|product_images) SET',sql)
  if match:
   kind=match[1];table=self.tables[kind]
   if 'is_primary=false' in sql:
    for v in table.values():
     if str(v['product_id'])==str(p.get('pid',p.get('id'))):v['is_primary']=False
    return Result()
   key=str(p.get('identifier',p.get('id')));row=table[key]
   row.update({k:copy.deepcopy(v) for k,v in p.items() if k not in ('identifier','id','pid')})
   if 'catalog_version=catalog_version+1' in sql:row['catalog_version']+=1
   return Result(copy.deepcopy(row))
  if sql.startswith('DELETE FROM public.product_images'):
   row=self.tables['product_images'].get(str(p['id']))
   if row and str(row['product_id'])==str(p['pid']):return Result(self.tables['product_images'].pop(str(p['id'])))
   return Result()
  raise AssertionError('Unexpected SQL shape: '+sql)

def main():
 db=Session();principal=SimpleNamespace(user_id=uuid4(),session_id=uuid4());context=AuthContext(db,principal,True,True)
 app=FastAPI();app.state.settings=Settings();app.add_exception_handler(AccessError,access_error);app.include_router(catalog.admin_router,prefix='/api/v1');app.include_router(catalog_templates.router,prefix='/api/v1');app.state.settings.catalog_approved_templates=['approved-template@1'];app.state.settings.cloudinary_cloud_name='synthetic';app.state.settings.cloudinary_api_key=SecretStr('123456');app.state.settings.cloudinary_api_secret=SecretStr('fixture-secret');app.state.settings.cloudinary_upload_preset='catalog';app.dependency_overrides[get_auth_context]=lambda:context
 # Encryption/provider substitution is test-local; backend source is unchanged.
 catalog.encrypt=lambda settings,actor,purpose,value:(value.encode(),1)
 catalog.decrypt=lambda settings,actor,purpose,value,version:value.decode()
 catalog.verified_asset=lambda settings,public_id:'https://res.cloudinary.com/synthetic/image/upload/v1/catalog/photo.png'
 checks=0
 with TestClient(app) as client:
  def req(method,path,body=None,version=None,key=None,expected=200):
   nonlocal checks
   assert path.startswith(('/api/v1/admin/products','/api/v1/admin/catalog/categories','/api/v1/admin/product-variants/','/api/v1/admin/catalog/approved-templates'))
   headers={'Idempotency-Key':key or str(uuid4())}
   if version is not None:headers['If-Match']='"'+str(version)+'"'
   r=client.request(method,path,json=body,headers=headers);assert r.status_code==expected,(r.status_code,r.text);checks+=1;return r.json()
  cats=req('POST','/api/v1/admin/catalog/categories',{'name':'Stickers','slug':'qr-stickers','is_active':True,'sort_order':0},expected=201)
  req('PATCH','/api/v1/admin/catalog/categories/'+cats['id'],{'name':'Updated category','slug':'qr-stickers','is_active':True,'sort_order':1},version=1)
  req('GET','/api/v1/admin/catalog/categories')
  choices=req('GET','/api/v1/admin/catalog/approved-templates');assert choices['items'][0]['template_key']=='approved-template'
  req('GET','/api/v1/admin/catalog/approved-templates?extra=1',expected=422)
  body={'name':'Product','slug':'real-product','description':'Original','category_id':cats['id'],'qr_type':'lost','price_per_copy':'12.50','max_order_copies':100,'lifecycle_status':'draft','is_featured':False,'featured_sort_order':0}
  product=req('POST','/api/v1/admin/products',body,key='one-intent-123',expected=201);pid=product['id']
  assert req('POST','/api/v1/admin/products',body,key='one-intent-123',expected=201)['id']==pid
  assert len(db.tables['products'])==1
  req('POST','/api/v1/admin/products',{**body,'name':'Different'},key='one-intent-123',expected=409)
  req('GET','/api/v1/admin/products');req('GET','/api/v1/admin/products/'+pid)
  req('PATCH','/api/v1/admin/products/'+pid,{**body,'name':'Edited'},version=1)
  req('PATCH','/api/v1/admin/products/'+pid,body,version=1,expected=412)
  req('GET','/api/v1/admin/products/'+str(uuid4()),expected=404)
  variant={'sku':'LARGE-1','name':'Large','size_mm':'40','material':'vinyl','color':'blue','fulfillment_method':'pdf_label','template_key':'approved','template_version':1,'is_active':True,'sort_order':0}
  v=req('POST','/api/v1/admin/products/'+pid+'/variants',variant,version=2,expected=201)
  assert v['unit_price']=='12.50'
  req('PATCH','/api/v1/admin/product-variants/'+v['id'],{**variant,'color':'green'},version=1)
  grant=req('POST','/api/v1/admin/products/'+pid+'/images?authorize_upload=true',{'cloudinary_public_id':'safereturn/catalog/pending','alt_text':'Artwork','sort_order':0,'is_primary':True},version=4,expected=201);assert grant['id']==pid and 'fixture-secret' not in str(grant)
  im=req('POST','/api/v1/admin/products/'+pid+'/images',{'cloudinary_public_id':'safereturn/catalog/test','alt_text':'Artwork','sort_order':0,'is_primary':True},version=4,expected=201)
  req('PATCH','/api/v1/admin/products/'+pid+'/images/'+im['id'],{'alt_text':'Updated alt','sort_order':2,'is_primary':True},version=5)
  req('DELETE','/api/v1/admin/products/'+pid+'/images/'+im['id'],version=6)
  req('POST','/api/v1/admin/products',{**body,'price_per_copy':-1},expected=422)
  req('POST','/api/v1/admin/products',{**body,'lifecycle_status':'published'},expected=422)
  # Mutable price never edits any historic table; the session double fails on every unknown statement.
  req('PATCH','/api/v1/admin/products/'+pid,{**body,'price_per_copy':'22.00'},version=7)
  assert all(not re.search(r'(INSERT|UPDATE|DELETE).*public.order_items',sql) for sql in db.sql)
 print(f'PASS {checks} actual FastAPI catalog handler HTTP checks with isolated session/provider doubles; no external network, DB, legacy fixture or excluded route.')
if __name__=='__main__':main()
