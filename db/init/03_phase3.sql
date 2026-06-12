-- Phase 3 additions. Idempotent: safe to apply to a live database.

-- Precomputed demo query embeddings (filled by Phase 4). Demo-mode vector search looks
-- queries up here; absent queries fall back to pg_trgm.
CREATE TABLE IF NOT EXISTS query_embeddings (
    query_text text PRIMARY KEY,
    embedding  vector(256) NOT NULL
);

-- The ported upsert needs this natural key (original schema had it implicitly).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'historico_pedidos_user_text_desc_key'
    ) THEN
        ALTER TABLE historico_pedidos
            ADD CONSTRAINT historico_pedidos_user_text_desc_key
            UNIQUE (user_text, catalog_description);
    END IF;
END $$;

-- Demo trigram fallback also reaches the memory (new rows have no embedding in demo).
CREATE INDEX IF NOT EXISTS historico_pedidos_user_text_trgm_idx
    ON historico_pedidos USING gin (user_text gin_trgm_ops);

-- Learning-loop upsert, ported from the original's upsert_historico_with_status and
-- adapted to the replica schema (last_used_month text instead of timestamptz; columns
-- order_number/confidence_score/user_id were dropped from the public dataset).
CREATE OR REPLACE FUNCTION public.upsert_historico_with_status(
    p_user_text text,
    p_catalog_description text,
    p_id_articulo_catalogo text,
    p_last_used_month text
)
 RETURNS TABLE(historico_id integer, is_new boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
  result RECORD;
BEGIN
  INSERT INTO public.historico_pedidos (
      user_text, catalog_description, id_articulo_catalogo, frequency, last_used_month
  )
  VALUES (
      p_user_text, p_catalog_description, p_id_articulo_catalogo, 1, p_last_used_month
  )
  ON CONFLICT (user_text, catalog_description)
  DO UPDATE SET
    frequency = historico_pedidos.frequency + 1,
    last_used_month = EXCLUDED.last_used_month,
    id_articulo_catalogo = EXCLUDED.id_articulo_catalogo
  RETURNING id AS historico_id, (xmax = 0) AS is_new
  INTO result;
  RETURN QUERY SELECT result.historico_id, result.is_new;
END;
$function$;
