-- Ukiyora Character Catalogue v1 — SQLite / Cloudflare D1 compatible
-- This database is a character discovery index, not a verified power-scale dataset.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS series (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  japanese_title TEXT,
  source_kind TEXT NOT NULL DEFAULT 'ukiyora_seed',
  source_url TEXT
);

CREATE TABLE IF NOT EXISTS characters (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  japanese_name TEXT,
  aliases_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(aliases_json)),
  biography TEXT,
  profile_status TEXT NOT NULL DEFAULT 'unverified'
    CHECK (profile_status IN ('unverified','researching','verified','disputed')),
  portrait_url TEXT,
  portrait_source_url TEXT,
  portrait_license TEXT,
  portrait_credit TEXT,
  portrait_status TEXT NOT NULL DEFAULT 'missing'
    CHECK (portrait_status IN ('missing','pending_review','approved','rejected')),
  source_kind TEXT NOT NULL,
  source_ref TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appearances (
  character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  series_id TEXT NOT NULL REFERENCES series(id) ON DELETE CASCADE,
  role TEXT,
  source_ref TEXT,
  PRIMARY KEY (character_id, series_id)
);
CREATE INDEX IF NOT EXISTS idx_appearances_series ON appearances(series_id);

CREATE TABLE IF NOT EXISTS external_identifiers (
  character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  external_ref TEXT NOT NULL,
  source_url TEXT,
  PRIMARY KEY (provider, external_ref)
);

CREATE TABLE IF NOT EXISTS character_forms (
  id TEXT PRIMARY KEY,
  character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'state'
    CHECK (kind IN ('baseline','transformation','state','ability_note','continuity_note','other')),
  continuity TEXT NOT NULL DEFAULT 'unspecified',
  arc TEXT,
  description TEXT,
  verification_status TEXT NOT NULL DEFAULT 'research_candidate'
    CHECK (verification_status IN ('research_candidate','under_review','verified','rejected','disputed')),
  evidence_ref TEXT,
  source_ref TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_forms_character ON character_forms(character_id, sort_order);

CREATE TABLE IF NOT EXISTS feats_ledger (
  id TEXT PRIMARY KEY,
  form_id TEXT NOT NULL REFERENCES character_forms(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  primary_source_ref TEXT,
  episode_or_chapter TEXT,
  continuity TEXT NOT NULL,
  verification_status TEXT NOT NULL DEFAULT 'unverified'
    CHECK (verification_status IN ('unverified','under_review','verified','rejected','disputed')),
  reviewed_by TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feats_form ON feats_ledger(form_id, verification_status);

CREATE TABLE IF NOT EXISTS source_attributions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT,
  license TEXT,
  license_url TEXT,
  remarks TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS character_search_fts USING fts5(
  character_id UNINDEXED,
  name,
  series_title,
  aliases,
  tokenize = 'unicode61 remove_diacritics 2'
);
