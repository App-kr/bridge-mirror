-- ================================================================
-- BRIDGE Supabase 커뮤니티 DB 셋업
-- 실행: Supabase Dashboard → SQL Editor에 붙여넣고 Run
-- ================================================================

-- ── community_posts ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS community_posts (
  id           BIGSERIAL PRIMARY KEY,
  board        TEXT    NOT NULL,
  title        TEXT    NOT NULL DEFAULT '',
  body         TEXT    DEFAULT '',
  author_hash  TEXT    DEFAULT '',
  image_paths  TEXT    DEFAULT '[]',
  pinned       INTEGER DEFAULT 0,
  views        INTEGER DEFAULT 0,
  is_deleted   INTEGER DEFAULT 0,
  content_type TEXT    DEFAULT 'markdown',
  sort_order   INTEGER DEFAULT 0,
  category     TEXT    DEFAULT NULL,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE community_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_read" ON community_posts
  FOR SELECT USING (is_deleted = 0);

CREATE POLICY "service_full" ON community_posts
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_community_board
  ON community_posts (board, is_deleted, pinned DESC, sort_order DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_id
  ON community_posts (id, is_deleted);

-- ── boards ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS boards (
  id           TEXT PRIMARY KEY,
  label        TEXT NOT NULL,
  label_kr     TEXT,
  display_mode TEXT DEFAULT 'list',
  sort_order   INTEGER DEFAULT 0,
  is_hidden    INTEGER DEFAULT 0,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE boards ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_read" ON boards
  FOR SELECT USING (is_hidden = 0);

CREATE POLICY "service_full" ON boards
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_boards_sort ON boards (sort_order, id);

-- ── file_uploads (커뮤니티 이미지) ───────────────────────────────
CREATE TABLE IF NOT EXISTS file_uploads (
  id          BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id   TEXT NOT NULL,
  file_type   TEXT,
  file_url    TEXT,
  s3_key      TEXT,
  file_size   INTEGER DEFAULT 0,
  is_deleted  INTEGER DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE file_uploads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_full" ON file_uploads
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_uploads_entity
  ON file_uploads (entity_type, entity_id, is_deleted);

-- ── _seed_log (중복 시딩 방지) ────────────────────────────────────
-- migrate_community_to_supabase.py 실행 후 자동 기록됨.
-- 이미 실행된 시드 ID가 있으면 스크립트가 재실행을 거부함.
CREATE TABLE IF NOT EXISTS _seed_log (
  id         TEXT PRIMARY KEY,          -- 예: 'community_v1'
  seeded_at  TIMESTAMPTZ DEFAULT NOW(),
  note       TEXT
);
