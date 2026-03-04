/**
 * BRIDGE Team — 직원 영문 이름 (영국식)
 * 관리자 페이지 담당자 배정 등에 사용
 */

export interface TeamMember {
  name: string
  role: string
}

export const TEAM_MEMBERS: TeamMember[] = [
  { name: 'Scarlett',  role: '대표' },
  { name: 'Violet',    role: '운영부장' },
  { name: 'Charlotte', role: '채용담당' },
  { name: 'Eleanor',   role: '지원담당' },
  { name: 'Florence',  role: '마케팅' },
]

/** 담당자 배정 드롭다운용 이름 목록 */
export const STAFF_NAMES = TEAM_MEMBERS.map((m) => m.name)
