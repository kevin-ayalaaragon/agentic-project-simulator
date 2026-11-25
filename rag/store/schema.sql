-- Retrieval store: one table serves both search arms.
-- Keyword arm: generated tsvector + GIN. Dense arm: pgvector, cosine distance.
-- No ANN index: at about a thousand chunks an exact scan is fast, and exact
-- results are the ground truth any later HNSW index is measured against.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    text PRIMARY KEY,          -- control ID, plus #n when a long control is split
    control_id  text NOT NULL,             -- OSCAL form, e.g. ac-2.1
    family      text NOT NULL,             -- e.g. ac
    title       text NOT NULL,
    body        text NOT NULL,
    tsv         tsvector GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', title), 'A') ||
                    setweight(to_tsvector('english', body), 'B')
                ) STORED,
    embedding   vector(384) NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_control_idx ON chunks (control_id);

CREATE TABLE IF NOT EXISTS store_meta (
    key   text PRIMARY KEY,
    value text NOT NULL
);
