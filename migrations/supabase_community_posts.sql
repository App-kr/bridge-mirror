-- ================================================================
-- Supabase community_posts 테이블 생성
-- 실행: Supabase Dashboard → SQL Editor에 붙여넣고 Run
-- ================================================================

CREATE TABLE IF NOT EXISTS community_posts (
  id           BIGSERIAL PRIMARY KEY,
  board        TEXT    NOT NULL,
  title        TEXT    NOT NULL DEFAULT '',
  body         TEXT    DEFAULT '',
  author_hash  TEXT    DEFAULT '',
  pinned       INTEGER DEFAULT 0,
  views        INTEGER DEFAULT 0,
  is_deleted   INTEGER DEFAULT 0,
  content_type TEXT    DEFAULT 'markdown',
  sort_order   INTEGER DEFAULT 0,
  category     TEXT    DEFAULT NULL,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security 활성화
ALTER TABLE community_posts ENABLE ROW LEVEL SECURITY;

-- 퍼블릭: 삭제되지 않은 게시물만 읽기 가능
CREATE POLICY "public_read" ON community_posts
  FOR SELECT USING (is_deleted = 0);

-- service_role: 전체 접근 (백엔드 API 전용)
CREATE POLICY "service_full" ON community_posts
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 인덱스 (성능)
CREATE INDEX IF NOT EXISTS idx_community_board ON community_posts (board, is_deleted, pinned DESC, sort_order DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_id ON community_posts (id, is_deleted);
