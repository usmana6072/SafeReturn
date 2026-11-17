"""Synthetic fixtures for the disposable local cluster; no provider claims."""
import json
from uuid import uuid4
from sqlalchemy import text
from test_print_templates import content
from app.core.inventory_secrets import new_public_token


def actor(c, uid):
    c.execute(text("SELECT set_config('safereturn.actor_id',:id,true),set_config('safereturn.mfa_verified','true',true)"), {"id":str(uid)})


def seed(pg, assets=None, *, origin="https://synthetic.invalid"):
    staff, customer, sid, category, asset, policy = (uuid4() for _ in range(6))
    catalog = {}
    with pg.connect() as c:
        for uid in (staff, customer):
            c.execute(
                text(
                    "INSERT INTO auth.users(id,email_confirmed_at) VALUES(:id,now())"
                ),
                {"id": uid},
            )
        c.execute(
            text(
                "INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES(:id,:uid,'aal2',now()+interval '1 hour')"
            ),
            {"id": sid, "uid": staff},
        )
        for role in ("finance", "operations"):
            c.execute(
                text(
                    "INSERT INTO public.staff_roles(user_id,role) VALUES(:id,:role)"
                ),
                {"id": staff, "role": role},
            )
        # This release row exists only inside this test's isolated namespace.
        c.execute(text("UPDATE public.single_checkout_release SET enabled=true"))
        actor(c, staff)
        c.execute(
            text(
                "INSERT INTO public.product_categories(id,slug,name) VALUES(:id,'qr-stickers','Synthetic QR stickers')"
            ),
            {"id": category},
        )
        c.execute(
            text(
                "INSERT INTO public.print_template_asset_sets(asset_set_id,font_path,font_sha256,logo_path,logo_sha256,review_reference,reviewed_at) VALUES(:id,:font_path,:font_sha,:logo_path,:logo_sha,'SYNTHETIC fixture',now())"
            ),
            {"id": asset, **(assets or {"font_path": "synthetic/font.ttf", "font_sha": "a" * 64, "logo_path": "synthetic/logo.svg", "logo_sha": "a" * 64})},
        )
        c.execute(
            text(
                "INSERT INTO public.template_production_policies(policy_id,version,sha256,body,reviewed_by,archive_reference) VALUES(:id,1,:hash,CAST(:body AS jsonb),:staff,'SYNTHETIC-fixture')"
            ),
            {
                "id": policy,
                "hash": "b" * 64,
                "body": json.dumps(
                    {"canonical_origin": origin}
                ),
                "staff": staff,
            },
        )
        for kind in ("lost", "ice"):
            pid, vid, tid, rid, approval = (uuid4() for _ in range(5))
            key = "synthetic-" + uuid4().hex
            body = {**content(), "asset_set_id": str(asset)}
            c.execute(
                text(
                    "INSERT INTO public.print_templates(template_id,key,name,purpose,created_by) VALUES(:id,:key,'Synthetic',:kind,:staff)"
                ),
                {"id": tid, "key": key, "kind": kind, "staff": staff},
            )
            c.execute(
                text(
                    "INSERT INTO public.print_template_revisions(revision_id,template_id,version,content,version_note,created_by,updated_by) VALUES(:id,:tid,1,CAST(:content AS jsonb),'SYNTHETIC fixture',:staff,:staff)"
                ),
                {
                    "id": rid,
                    "tid": tid,
                    "content": json.dumps(body),
                    "staff": staff,
                },
            )
            c.execute(
                text("""INSERT INTO public.template_qa_approvals(approval_id,evidence_id,revision_id,revision_row_version,revision_fingerprint_sha256,evidence_sha256,policy_id,policy_version,summary,ciphertext,key_version,importer_human,expires_at,consumed_at,consumed_by)
             VALUES(:id,:evidence,:rid,1,:hash,:hash,:policy,1,'{"attestations":[],"archive_references":[]}'::jsonb,:cipher,1,:staff,now()+interval '1 day',now(),:staff)"""),
                {
                    "id": approval,
                    "evidence": uuid4(),
                    "rid": rid,
                    "hash": "c" * 64,
                    "policy": policy,
                    "cipher": b"s" * 40,
                    "staff": staff,
                },
            )
            c.execute(
                text(
                    "UPDATE public.print_template_revisions SET status='published',fingerprint_sha256=:hash,published_at=now(),approval_id=:approval WHERE revision_id=:rid"
                ),
                {"hash": "c" * 64, "approval": approval, "rid": rid},
            )
            c.execute(
                text(
                    "INSERT INTO public.products(id,category_id,slug,name,price_per_copy,max_order_copies,commerce_model,qr_type,allows_new_pair) VALUES(:id,:cat,:slug,:name,1.00,100,'single_qr',:kind,false)"
                ),
                {
                    "id": pid,
                    "cat": category,
                    "slug": "synthetic-" + uuid4().hex,
                    "name": "Synthetic " + kind,
                    "kind": kind,
                },
            )
            c.execute(
                text(
                    "INSERT INTO public.product_variants(id,product_id,sku,name,size_mm,material,unit_price,fulfillment_method,template_key,template_version) VALUES(:id,:pid,:sku,'35 mm',35,'synthetic-paper',1,'pdf_label',:key,1)"
                ),
                {
                    "id": vid,
                    "pid": pid,
                    "sku": "SYNTHETIC-" + uuid4().hex,
                    "key": key,
                },
            )
            c.execute(
                text(
                    "INSERT INTO public.template_registry_sources(variant_id) VALUES(:id)"
                ),
                {"id": vid},
            )
            c.execute(
                text(
                    "INSERT INTO public.print_template_variant_bindings(variant_id,tag_type,revision_id) VALUES(:vid,:kind,:rid)"
                ),
                {"vid": vid, "kind": kind, "rid": rid},
            )
            c.execute(
                text(
                    "INSERT INTO public.product_images(product_id,cloudinary_public_id,alt_text,is_primary,verified_public_url) VALUES(:id,:public_id,'Synthetic fixture',true,'https://res.cloudinary.com/synthetic/image/upload/v1/fixture.png')"
                ),
                {"id": pid, "public_id": "synthetic/" + uuid4().hex},
            )
            c.execute(
                text(
                    "UPDATE public.products SET lifecycle_status='published' WHERE id=:id"
                ),
                {"id": pid},
            )
            catalog[kind] = (pid, vid)
        c.commit()
    return pg, staff, customer, sid, catalog

def make_order(case, kinds=("lost",), copies=3, *, submit_payment=True):
    pg, _staff, customer, _, catalog = case
    oid, address = uuid4(), uuid4()
    with pg.connect() as c:
        actor(c, customer)
        c.execute(
            text(
                "INSERT INTO public.orders(id,order_number,customer_user_id,commerce_model,payment_instructions_snapshot,subtotal_pkr,total_pkr) VALUES(:id,:ref,:uid,'single_qr',jsonb_build_object('version','SYNTHETIC'),:total,:total)"
            ),
            {
                "id": oid,
                "ref": "SYN-" + uuid4().hex,
                "uid": customer,
                "total": len(kinds) * copies,
            },
        )
        c.execute(
            text(
                "INSERT INTO public.shipping_addresses(id,customer_user_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,key_version) VALUES(:id,:uid,:cipher,:cipher,:cipher,'Synthetic',1)"
            ),
            {"id": address, "uid": customer, "cipher": b"synthetic-ciphertext"},
        )
        c.execute(
            text(
                "INSERT INTO public.order_shipping_snapshots(order_id,source_address_id,recipient_name_ciphertext,phone_ciphertext,address_ciphertext,city,key_version) VALUES(:id,:address,:cipher,:cipher,:cipher,'Synthetic',1)"
            ),
            {"id": oid, "address": address, "cipher": b"synthetic-ciphertext"},
        )
        for index, kind in enumerate(kinds):
            pid, vid = catalog[kind]
            iid = c.execute(
                text(
                    "INSERT INTO public.order_logical_items(order_id,product_id,identity_group,product_name_snapshot,qr_type_snapshot,quantity,unit_price_snapshot,line_total,max_copies_snapshot,product_version_snapshot) SELECT :oid,p.id,:group,p.name,p.qr_type,:copies,p.price_per_copy,:copies*p.price_per_copy,p.max_order_copies,p.catalog_version FROM public.products p WHERE p.id=:pid RETURNING id"
                ),
                {
                    "oid": oid,
                    "group": "distinct-" + str(index),
                    "copies": copies,
                    "pid": pid,
                },
            ).scalar_one()
            c.execute(
                text(
                    "INSERT INTO public.order_item_sizes(logical_item_id,variant_id,variant_name_snapshot,sku_snapshot,size_mm_snapshot,material_snapshot,copies,variant_version_snapshot,print_spec_snapshot) SELECT :iid,v.id,v.name,v.sku,v.size_mm,v.material,:copies,v.catalog_version,public.sr_template_resolve(v.id,jsonb_build_array(jsonb_build_object('tag_type',CAST(:kind AS text))))->0 FROM public.product_variants v WHERE id=:vid"
                ),
                {"iid": iid, "copies": copies, "kind": kind, "vid": vid},
            )
        c.execute(
            text(
                "UPDATE public.orders SET order_status='placed',placed_at=clock_timestamp() WHERE id=:id"
            ),
            {"id": oid},
        )
        aid = c.execute(
            text(
                "INSERT INTO public.payment_attempts(order_id,provider_key,idempotency_key,amount,state) VALUES(:id,'manual_bank',:key,:amount,'submitted') RETURNING id"
            ),
            {"id": oid, "key": uuid4().hex, "amount": len(kinds) * copies},
        ).scalar_one() if submit_payment else None
        c.commit()
    return oid, aid, len(kinds) * copies


def stock(case, kind="lost", quantity=1):
    pg, staff, _, sid, _ = case
    with pg.connect() as c:
        actor(c, staff)
        c.execute(
            text(
                "SELECT public.sr_typed_inventory_generate(:sid,:label,:kind,:quantity,'Q',:key,CAST(:tokens AS jsonb))"
            ),
            {
                "sid": sid,
                "label": "STOCK-" + uuid4().hex[:20],
                "kind": kind,
                "quantity": quantity,
                "key": uuid4().hex,
                "tokens": json.dumps([new_public_token() for _ in range(quantity)]),
            },
        )
        c.commit()


def claims(case, oid):
    with case[0].connect() as c:
        return c.execute(
            text(
                "SELECT logical_item_id,qr_id FROM public.order_item_qr_allocations WHERE order_id=:id ORDER BY logical_item_id"
            ),
            {"id": oid},
        ).all()

