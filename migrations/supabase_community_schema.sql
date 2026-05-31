-- ============================================================
-- BRIDGE 커뮤니티 게시판 — Supabase 영구 저장 스키마
-- 사용법: Supabase 대시보드 → SQL Editor → 아래 전체 복붙 → Run
-- 안전: IF NOT EXISTS 멱등 — 여러 번 실행해도 데이터 보존
-- ============================================================

-- 1) boards (게시판 메타)
CREATE TABLE IF NOT EXISTS public.boards (
    id           TEXT PRIMARY KEY,
    label        TEXT NOT NULL,
    label_kr     TEXT,
    display_mode TEXT    DEFAULT 'list',
    sort_order   INTEGER DEFAULT 0,
    is_hidden    INTEGER DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- 2) community_posts (게시물 본문)
CREATE TABLE IF NOT EXISTS public.community_posts (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    board        TEXT    NOT NULL DEFAULT 'support',
    title        TEXT    NOT NULL,
    body         TEXT    NOT NULL,
    author_hash  TEXT,
    image_paths  TEXT    DEFAULT '[]',
    pinned       INTEGER DEFAULT 0,
    views        INTEGER DEFAULT 0,
    is_deleted   INTEGER DEFAULT 0,
    category     TEXT,
    content_type TEXT    DEFAULT 'markdown',
    sort_order   INTEGER DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- 3) 조회 성능 인덱스 (보드별 + 삭제여부)
CREATE INDEX IF NOT EXISTS idx_cp_board_del
    ON public.community_posts (board, is_deleted);
CREATE INDEX IF NOT EXISTS idx_cp_sort
    ON public.community_posts (pinned DESC, sort_order DESC, created_at DESC);

-- ============================================================
-- 보안: RLS(Row Level Security) 활성화 — 외부 직접 접근 차단.
-- 서버는 service_role 키로 접속하므로 RLS를 우회함(정상).
-- anon/public 키로는 읽기/쓰기 모두 막힘 → 안전.
-- ============================================================
ALTER TABLE public.community_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.boards          ENABLE ROW LEVEL SECURITY;

-- (정책 미생성 = 기본 deny. service_role은 RLS 무시하므로 서버는 정상 동작)
