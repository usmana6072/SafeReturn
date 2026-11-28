-- Add a versioned development asset set for the new SafeReturn QR-center logo.
-- Historical asset set 0a7c508b-fc96-42d6-ba58-e367dbb8d08b remains immutable.
-- This does not create a template revision, QA approval, binding, or publication.
BEGIN;
SET LOCAL statement_timeout = '5000ms';
SELECT pg_advisory_xact_lock(hashtextextended('dev-asset-set:70af0cb0-0cef-4d3a-a24a-f3cb0c81d5e4',0));
INSERT INTO public.print_template_asset_sets
(asset_set_id,font_path,font_sha256,logo_path,logo_sha256,review_reference,reviewed_at)
VALUES ('70af0cb0-0cef-4d3a-a24a-f3cb0c81d5e4','/app/print-assets/Amiri-Regular.ttf','ab391c4147d054c48976e98322ad0eefe1427aa0e0502a12a4c75d80a70cfcd7',
'/app/print-assets/logo-icon-192.svg','652c5cbae3a5f67a8007c37831abf18cea427174018941bf439437dbc76e8d97','owner-selected-development-logo-icon-192-20261128',now())
ON CONFLICT (asset_set_id) DO NOTHING;
DO $$ BEGIN
IF NOT EXISTS (SELECT 1 FROM public.print_template_asset_sets WHERE asset_set_id='70af0cb0-0cef-4d3a-a24a-f3cb0c81d5e4'
AND font_path='/app/print-assets/Amiri-Regular.ttf' AND font_sha256='ab391c4147d054c48976e98322ad0eefe1427aa0e0502a12a4c75d80a70cfcd7'
AND logo_path='/app/print-assets/logo-icon-192.svg' AND logo_sha256='652c5cbae3a5f67a8007c37831abf18cea427174018941bf439437dbc76e8d97' AND withdrawn_at IS NULL)
THEN RAISE EXCEPTION 'New asset enrollment mismatch; transaction rolled back'; END IF;
END $$;
COMMIT;
