# 구 홈페이지 작업 로그 — 2026-03-13

## 작업 대상
- 사이트: http://bridgejob.co.kr/ (구 홈페이지, 그누보드5 + 카페24)
- 로컬 파일: `Q:\Bridge web_old\www\`
- 배포 방법: 파일질라(FileZilla) FTP → 서버 `/www/` 덮어쓰기
- **⚠️ Q:\Claudework\bridge base (새 홈페이지)는 절대 건드리지 않음**

## 사이트 구조
- 그누보드5 기반
- 테마: `cookie` (`/www/theme/cookie/`)
- FTP 접속: `ftp.bridgejob.co.kr` / 카페24 계정 / 포트 21
- 주요 파일:
  - `/www/theme/cookie/head.php` — 공통 헤더 + 네비게이션
  - `/www/theme/cookie/mobile/tail.php` — 공통 푸터 (PC + 모바일 통합)
  - `/www/theme/cookie/tail.php` — PC 푸터
  - `/www/theme/cookie/css/custom.css` — 커스텀 CSS
  - `/www/apply_confirm.php` — 지원 자격 확인 페이지
  - `/www/form.php` — 지원 폼 (action="form_send.php")
  - `/www/apply.php` — 지원 페이지 (form.php 포함)
  - `/recruiting` — 그누보드 게시판 (bo_table=recruiting)

## 완료된 작업
### ✅ 우측 바로가기 버튼 제거 (2026-03-13)
- 파일: `/www/theme/cookie/mobile/tail.php`
- 제거 항목: 메일(bridgejobkr@gmail.com), 스카이프, 카카오톡 우측 고정 버튼 (.rbtnbox)
- PC버전(.rbtnbox.pcview) + 모바일버전(.rbtnbox.mobileview) 둘 다 제거

## 내일 이어서 할 작업
### ⏳ 구글폼 팝업 추가
- 대상 페이지: `/apply_confirm.php`, `/recruiting` 게시판
- 방법: `head.sub.php` (`/www/theme/cookie/head.sub.php`)에 팝업 코드 추가
  - URL에 `apply_confirm` 또는 `recruiting` 포함 시 자동 표시
- **필요한 정보**: 구글폼 URL (아직 미수령)

### ⏳ 메인 홈페이지 개편 알림 배너
- 대상: 메인 페이지
- **필요한 정보**: 새 홈페이지 URL + 알림 문구 (아직 미수령)

## CSS 참고
- `.rbtnbox` — 우측 고정 버튼 컨테이너 (position: fixed; top: 50%; right: 25px)
- `.rbicon1` — 메일 아이콘 (mailico.png)
- `.rbicon2` — 스카이프 아이콘 (skpicon.png)
- `.rbicon3` — 카카오 아이콘 (kkoicon.png)
