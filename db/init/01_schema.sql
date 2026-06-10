-- Voice-to-Order local schema. Ported from the production system (Supabase) to plain Postgres.
-- Embedding dimension: 256 (reduced-dimension text-embedding-3-small; Phase-4 contract).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Article catalog (anonymized ids; descriptions verbatim, Spanish)
CREATE TABLE catalogo (
    id_articulo        text PRIMARY KEY,
    articulo           text NOT NULL DEFAULT '',
    fecha_ultima_compra date,          -- reconstructed as the 1st of the anonymized month
    is_active          boolean NOT NULL DEFAULT TRUE
);

-- Catalog embeddings (filled in Phase 4)
CREATE TABLE embeddings (
    id_articulo text PRIMARY KEY REFERENCES catalogo(id_articulo) ON DELETE CASCADE,
    embedding   vector(256) NOT NULL
);

-- Learned memory: dictated phrase -> confirmed article (the system improves with use)
CREATE TABLE historico_pedidos (
    id                   serial PRIMARY KEY,
    user_text            text NOT NULL,
    catalog_description  text NOT NULL DEFAULT '',
    id_articulo_catalogo text REFERENCES catalogo(id_articulo),
    frequency            integer NOT NULL DEFAULT 1,
    last_used_month      text NOT NULL DEFAULT ''
);

-- History embeddings (filled in Phase 4)
CREATE TABLE historico_embeddings (
    historico_id integer PRIMARY KEY REFERENCES historico_pedidos(id) ON DELETE CASCADE,
    embedding    vector(256) NOT NULL
);

-- HNSW indexes: pgvector only plans an index scan for ORDER BY embedding <=> q LIMIT n
-- (the reason the CTE functions in 02_functions.sql exist).
CREATE INDEX embeddings_embedding_idx
    ON embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX historico_embeddings_embedding_idx
    ON historico_embeddings USING hnsw (embedding vector_cosine_ops);

-- Trigram index: demo-mode free-text fallback search (no API needed)
CREATE INDEX catalogo_articulo_trgm_idx
    ON catalogo USING gin (articulo gin_trgm_ops);
