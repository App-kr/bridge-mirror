-- ================================================================
-- Supabase Admin Tables 생성 (7개 테이블)
-- 실행: Supabase Dashboard → SQL Editor에 전체 붙여넣고 Run
-- 순서: 이 파일 1개로 모두 처리됨
-- ================================================================

-- ──────────────────────────────────────────────────────────────
-- 1. email_templates
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_templates (
  id           BIGSERIAL PRIMARY KEY,
  template_key TEXT    NOT NULL UNIQUE,
  subject      TEXT    NOT NULL DEFAULT '',
  body_html    TEXT    NOT NULL DEFAULT '',
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "et_service_full" ON email_templates
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ──────────────────────────────────────────────────────────────
-- 2. guide_links
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS guide_links (
  id         BIGSERIAL PRIMARY KEY,
  link_key   TEXT NOT NULL UNIQUE,
  url        TEXT NOT NULL DEFAULT '',
  label      TEXT DEFAULT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE guide_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "gl_public_read" ON guide_links
  FOR SELECT USING (true);

CREATE POLICY "gl_service_full" ON guide_links
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ──────────────────────────────────────────────────────────────
-- 3. boards
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS boards (
  id         BIGSERIAL PRIMARY KEY,
  slug       TEXT    NOT NULL UNIQUE,
  label      TEXT    NOT NULL DEFAULT '',
  is_visible INTEGER DEFAULT 1,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE boards ENABLE ROW LEVEL SECURITY;

CREATE POLICY "boards_public_read" ON boards
  FOR SELECT USING (is_visible = 1);

CREATE POLICY "boards_service_full" ON boards
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_boards_sort ON boards (sort_order, id);

-- ──────────────────────────────────────────────────────────────
-- 4. banners
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS banners (
  id         BIGSERIAL PRIMARY KEY,
  title      TEXT    NOT NULL DEFAULT '',
  body       TEXT    DEFAULT '',
  link_url   TEXT    DEFAULT NULL,
  is_active  INTEGER DEFAULT 1,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE banners ENABLE ROW LEVEL SECURITY;

CREATE POLICY "banners_public_read" ON banners
  FOR SELECT USING (is_active = 1);

CREATE POLICY "banners_service_full" ON banners
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_banners_sort ON banners (sort_order, id);

-- ──────────────────────────────────────────────────────────────
-- 5. site_partners
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS site_partners (
  id         BIGSERIAL PRIMARY KEY,
  name       TEXT    NOT NULL DEFAULT '',
  category   TEXT    DEFAULT NULL,
  logo_url   TEXT    DEFAULT NULL,
  website    TEXT    DEFAULT NULL,
  is_active  INTEGER DEFAULT 1,
  is_deleted INTEGER DEFAULT 0,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE site_partners ENABLE ROW LEVEL SECURITY;

CREATE POLICY "partners_public_read" ON site_partners
  FOR SELECT USING (is_active = 1 AND is_deleted = 0);

CREATE POLICY "partners_service_full" ON site_partners
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_partners_sort ON site_partners (sort_order, name);

-- ──────────────────────────────────────────────────────────────
-- 6. site_settings
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS site_settings (
  id         BIGSERIAL PRIMARY KEY,
  key        TEXT    NOT NULL UNIQUE,
  value      TEXT    DEFAULT '',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE site_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "settings_public_read" ON site_settings
  FOR SELECT USING (true);

CREATE POLICY "settings_service_full" ON site_settings
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ──────────────────────────────────────────────────────────────
-- 7. testimonials
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS testimonials (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT    NOT NULL DEFAULT '',
  country     TEXT    DEFAULT NULL,
  photo_url   TEXT    DEFAULT NULL,
  rating      INTEGER DEFAULT 5,
  review_text TEXT    DEFAULT '',
  is_visible  INTEGER DEFAULT 1,
  is_deleted  INTEGER DEFAULT 0,
  sort_order  INTEGER DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE testimonials ENABLE ROW LEVEL SECURITY;

CREATE POLICY "testimonials_public_read" ON testimonials
  FOR SELECT USING (is_visible = 1 AND is_deleted = 0);

CREATE POLICY "testimonials_service_full" ON testimonials
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_testimonials_sort ON testimonials (sort_order DESC, id DESC);
