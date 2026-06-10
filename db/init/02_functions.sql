-- Search functions ported VERBATIM from the production system (only comments translated).
-- They encode the fix for a real production incident: pgvector only uses the HNSW index when the
-- query follows the ORDER BY embedding <=> query LIMIT n pattern; filtering on a computed
-- similarity forced a sequential scan and the role's statement_timeout killed it. The CTE isolates
-- the index-friendly part; SET statement_timeout scopes headroom to these two functions only.
-- See the portfolio's case study 06 ("the bug I fixed") for the full story.

CREATE OR REPLACE FUNCTION public.buscar_articulos(query_embedding vector, match_threshold double precision, match_count integer)
 RETURNS TABLE(id_articulo text, articulo text, fecha_ultima_compra date, similarity double precision)
 LANGUAGE sql
 STABLE
 SET statement_timeout = '30s'
AS $function$
  -- CTE that forces the HNSW/IVFFlat index via the ORDER BY <=> LIMIT pattern
  WITH vector_matches AS (
    SELECT
      e.id_articulo,
      1 - (e.embedding <=> query_embedding) AS similarity
    FROM
      embeddings AS e
    ORDER BY
      e.embedding <=> query_embedding
    LIMIT
      match_count * 3  -- extra candidates to compensate for is_active/threshold filtering
  )
  SELECT
    c.id_articulo,
    c.articulo,
    c.fecha_ultima_compra,
    vm.similarity
  FROM
    vector_matches vm
  JOIN
    catalogo AS c ON vm.id_articulo = c.id_articulo
  WHERE
    c.is_active = TRUE
    AND vm.similarity > match_threshold
  ORDER BY
    vm.similarity DESC
  LIMIT
    match_count;
$function$;

CREATE OR REPLACE FUNCTION public.buscar_historicos(query_embedding vector, match_threshold double precision, match_count integer)
 RETURNS TABLE(id integer, user_text text, catalog_description text, similarity double precision, id_articulo_catalogo text)
 LANGUAGE sql
 STABLE
 SET statement_timeout = '30s'
AS $function$
  -- CTE that forces the HNSW/IVFFlat index via the ORDER BY <=> LIMIT pattern
  WITH vector_matches AS (
    SELECT
      e.historico_id,
      1 - (e.embedding <=> query_embedding) AS similarity
    FROM
      historico_embeddings AS e
    ORDER BY
      e.embedding <=> query_embedding
    LIMIT
      match_count * 3
  )
  SELECT
    h.id,
    h.user_text,
    h.catalog_description,
    vm.similarity,
    h.id_articulo_catalogo
  FROM
    vector_matches vm
  JOIN
    historico_pedidos AS h ON vm.historico_id = h.id
  WHERE
    vm.similarity > match_threshold
  ORDER BY
    vm.similarity DESC
  LIMIT
    match_count;
$function$;
