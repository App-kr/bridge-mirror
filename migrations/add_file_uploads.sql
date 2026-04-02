-- Migration: Add file_uploads table and candidates photo columns
-- Run in Supabase SQL Editor

-- 1. file_uploads 테이블
CREATE TABLE IF NOT EXISTS file_uploads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('candidate','inquiry')),
    entity_id UUID NOT NULL,
    file_type TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookup by entity
CREATE INDEX IF NOT EXISTS idx_file_uploads_entity
    ON file_uploads(entity_type, entity_id)
    WHERE is_deleted = false;

-- 2. candidates 테이블에 사진 URL 컬럼 추가
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS photo_url TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS thumb_url TEXT;

-- 3. RLS (Row Level Security) — file_uploads
ALTER TABLE file_uploads ENABLE ROW LEVEL SECURITY;

-- service_role만 INSERT/SELECT 허용 (anon 차단)
CREATE POLICY "service_role_all" ON file_uploads
    FOR ALL USING (auth.role() = 'service_role');
