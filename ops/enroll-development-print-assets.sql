-- Development project fhuxryfkfrvycsojkzvq only. One asset-set registration.
-- No role, schema, template revision, QA approval, binding or product publication.
BEGIN;
SET LOCAL statement_timeout = '5000ms';
SELECT pg_advisory_xact_lock(hashtextextended('dev-asset-set:0a7c508b-fc96-42d6-ba58-e367dbb8d08b',0));
INSERT INTO public.print_template_asset_sets
(asset_set_id,font_path,font_sha256,logo_path,logo_sha256,review_reference,reviewed_at)
VALUES ('0a7c508b-fc96-42d6-ba58-e367dbb8d08b','/app/print-assets/Amiri-Regular.ttf','ab391c4147d054c48976e98322ad0eefe1427aa0e0502a12a4c75d80a70cfcd7',
'/app/print-assets/logo.svg','6edd586082d2f2005252d4e745303cc1b2705cfad890d495575d51ed440beeea','owner-selected-development-assets-20261025',now())
ON CONFLICT (asset_set_id) DO NOTHING;
DO $$ BEGIN
IF NOT EXISTS (SELECT 1 FROM public.print_template_asset_sets WHERE asset_set_id='0a7c508b-fc96-42d6-ba58-e367dbb8d08b'
AND font_path='/app/print-assets/Amiri-Regular.ttf' AND font_sha256='ab391c4147d054c48976e98322ad0eefe1427aa0e0502a12a4c75d80a70cfcd7'
AND logo_path='/app/print-assets/logo.svg' AND logo_sha256='6edd586082d2f2005252d4e745303cc1b2705cfad890d495575d51ed440beeea' AND withdrawn_at IS NULL)
THEN RAISE EXCEPTION 'Asset enrollment mismatch; transaction rolled back'; END IF;
END $$;
COMMIT;
