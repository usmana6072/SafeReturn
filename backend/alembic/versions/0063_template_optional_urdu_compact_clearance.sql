CREATE OR REPLACE FUNCTION public.sr_template_content_valid(c jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE field text; n numeric; item jsonb; expected text[]:=ARRAY[
 'schema_version','renderer','preset','symbol_mm','width_mm','height_mm','qr_x_mm','qr_y_mm',
 'logo_mm','min_pitch_mm','font_pt','header','english_lines','urdu_lines','asset_set_id','material_codes'];
BEGIN
 IF c IS NULL OR jsonb_typeof(c)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(c))<>cardinality(expected)
 OR EXISTS(SELECT 1 FROM jsonb_object_keys(c) k WHERE NOT k=ANY(expected))
 OR c->'schema_version' IS DISTINCT FROM '1'::jsonb OR c->>'renderer' IS DISTINCT FROM 'safereturn-vector-v1'
 OR c->>'preset' IS NULL OR c->>'preset' NOT IN ('fixed-footer-v1','fixed-footer-v2') THEN RETURN false; END IF;
 FOREACH field IN ARRAY ARRAY['symbol_mm','width_mm','height_mm','qr_x_mm','qr_y_mm','logo_mm','min_pitch_mm','font_pt'] LOOP
  IF jsonb_typeof(c->field)<>'string' OR (c->>field)!~'^[0-9]{1,3}\.[0-9]{2}$' THEN RETURN false; END IF;
  n:=(c->>field)::numeric; IF n<=0 OR n>270 THEN RETURN false; END IF;
 END LOOP;
 IF (c->>'symbol_mm')::numeric NOT BETWEEN 20 AND 100 OR (c->>'width_mm')::numeric NOT BETWEEN 30 AND 190
 OR (c->>'height_mm')::numeric NOT BETWEEN 50 AND 270 OR (c->>'qr_x_mm')::numeric<4 OR (c->>'qr_y_mm')::numeric<13
 OR (c->>'logo_mm')::numeric>6 OR (c->>'logo_mm')::numeric>(c->>'symbol_mm')::numeric*0.15
 OR (c->>'min_pitch_mm')::numeric<0.3 OR (c->>'font_pt')::numeric NOT BETWEEN 8 AND 14
 OR (c->>'qr_x_mm')::numeric+(c->>'symbol_mm')::numeric>(c->>'width_mm')::numeric-4
 OR (c->>'qr_y_mm')::numeric+(c->>'symbol_mm')::numeric>(c->>'height_mm')::numeric-
    (CASE c->>'preset' WHEN 'fixed-footer-v2' THEN 8 ELSE 12 END) THEN RETURN false; END IF;
 IF jsonb_typeof(c->'header')<>'string' OR char_length(c->>'header') NOT BETWEEN 1 AND 50 THEN RETURN false; END IF;
 FOREACH field IN ARRAY ARRAY['english_lines','urdu_lines','material_codes'] LOOP
  IF jsonb_typeof(c->field)<>'array' OR jsonb_array_length(c->field) NOT BETWEEN
     (CASE WHEN field='urdu_lines' THEN 0 ELSE 1 END) AND (CASE WHEN field='material_codes' THEN 10 ELSE 4 END) THEN RETURN false; END IF;
  FOR item IN SELECT value FROM jsonb_array_elements(c->field) LOOP
   IF jsonb_typeof(item)<>'string' OR char_length(item#>>'{}') NOT BETWEEN 1 AND 120 THEN RETURN false; END IF;
   IF field='material_codes' AND (item#>>'{}')!~'^[a-z0-9_-]{1,40}$' THEN RETURN false; END IF;
   IF field='urdu_lines' AND (item#>>'{}')~'[A-Za-z0-9]' THEN RETURN false; END IF;
  END LOOP;
 END LOOP;
 IF (c->>'qr_y_mm')::numeric-4-(c->>'font_pt')::numeric*1.5/2.8346456693*
    (jsonb_array_length(c->'english_lines')+jsonb_array_length(c->'urdu_lines')-1)<4 THEN RETURN false; END IF;
 IF c->'material_codes'<>(SELECT jsonb_agg(v ORDER BY v) FROM (SELECT DISTINCT value v FROM jsonb_array_elements(c->'material_codes')) x) THEN RETURN false; END IF;
 IF jsonb_typeof(c->'asset_set_id')<>'string' OR c->>'asset_set_id' IS NULL THEN RETURN false; END IF;
 PERFORM (c->>'asset_set_id')::uuid;
 IF (c->>'header') ~ '[<>\\{}[:cntrl:]]' OR (c->>'header') ~* '[a-z][a-z0-9+.-]*[[:space:]]*:'
 OR EXISTS(SELECT 1 FROM jsonb_array_elements_text((c->'english_lines')||(c->'urdu_lines')) v WHERE v ~ '[<>\\{}[:cntrl:]]' OR v ~* '[a-z][a-z0-9+.-]*[[:space:]]*:') THEN RETURN false; END IF;
 RETURN true;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;
