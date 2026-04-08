# PC + 공유기 보안 종합 점검 리포트
**작성일**: 2026-03-27 | **상태**: 🟡 부분 위험 / 요청 조치 필요

---

## 📊 현재 보안 상태 요약

| 영역 | 상태 | 평가 | 비고 |
|------|------|------|------|
| **Windows Defender** | ✅ 활성화 | 양호 | Real-time + Behavior monitoring 모두 ON |
| **방화벽** | ✅ 활성화 | 양호 | Domain/Private/Public 모두 ON |
| **로컬 계정** | ✅ 안전 | 양호 | Scarlett 계정만 활성화, 게스트 비활성 |
| **RDP (포트 3389)** | ⚠️ 리스닝 | **위험** | 외부 노출 가능 |
| **SMB (포트 139/445)** | ⚠️ 리스닝 | **위험** | 파일공유 활성화 |
| **WireGuard** | ✅ 비활성화 | 양호 | 세션 22에서 복구 완료 |
| **공유기 설정** | ❌ 미검증 | **높음** | 매뉴얼 확인 필수 |

---

## 🔴 즉시 조치 필요 사항 (HIGH)

### 1️⃣ RDP (Remote Desktop Protocol) 포트 3389 — 외부 노출 차단
**현재 상태**: 포트 3389 리스닝 중 (위험)
**문제**: 악의적 접근자가 RDP로 원격 접속 시도 가능

**조치 방법** (사용자 직접 실행):
```powershell
# 방화벽에서 RDP 인바운드 규칙 비활성화
netsh advfirewall firewall set rule name="Remote Desktop - User Mode (TCP-In)" new enable=no
netsh advfirewall firewall set rule name="Remote Desktop - User Mode (UDP-In)" new enable=no

# 또는 GUI: 설정 > 개인정보 및 보안 > 원격 데스크톱 > "원격 데스크톱 비활성화"
```

---

### 2️⃣ SMB (파일 공유) 포트 139/445 — 내부망만 허용
**현재 상태**: 포트 445 (SMB) 리스닝 중
**문제**: Ransomware/WannaCry 공격 벡터

**조치 방법** (사용자 직접 실행):
```powershell
# 방화벽: SMB 인바운드 로컬 네트워크(192.168.0.x)만 허용으로 제한
netsh advfirewall firewall set rule name="File and Printer Sharing (SMB-In)" new enable=yes
# GUI에서 "고급 보안이 있는 방화벽" → 인바운드 규칙 → "File and Printer Sharing" 수정

# 또는 공유기에서 포트 445 인바운드 차단 (외부에서 접근 불가)
```

---

### 3️⃣ 공유기 기본 설정 미흡 — MAC 필터링 + 암호화 미적용
**현재 상태**: 메모리에 기록된 권장사항 미완료
**문제**: 무단 접속/패킷 스니핑 위험

**조치 방법** (사용자가 공유기 설정 UI 직접 접근):
```
공유기 관리자 페이지: http://192.168.0.1 또는 http://192.168.1.1

1️⃣ 무선 보안 (WiFi)
   - 암호화: WPA3 (또는 WPA2/AES, WPA3 미지원 시)
   - 암호: 20자 이상 강력한 비밀번호 설정
   - 브로드캐스트: SSID 숨김 (선택)

2️⃣ MAC 필터링 — "화이트리스트" 활성화
   ✅ 현재 기기 MAC 추가:
   - Scarlett_Main_PC: 40:B0:76:A1:EF:A0
   - 미래 노트북: AA:BB:CC:DD:EE:01
   - 미래 iPad: BB:CC:DD:EE:FF:02
   - 미래 iPhone: CC:DD:EE:FF:00:03

3️⃣ 포트 전달 (Port Forwarding) — 불필요한 외부 포트 모두 닫기
   - SSH (22) — CLOSE
   - RDP (3389) — CLOSE
   - HTTP (80) → 필요시만 OPEN
   - HTTPS (443) → 필요시만 OPEN

4️⃣ 관리 인터페이스 보호
   - 공유기 관리자 비밀번호: 기본값 변경 (admin/admin → 강력한 비번)
   - Telnet/HTTP 관리: 비활성화 → HTTPS만 활성화

5️⃣ UPnP (Universal Plug and Play) — 비활성화
   - 악성 앱이 자동으로 포트를 개방하는 것을 방지

6️⃣ WPS (WiFi Protected Setup) — 비활성화
   - PIN 방식 접속 취약점 제거
```

**확인 체크리스트**:
- [ ] WiFi 암호화: WPA3 또는 WPA2/AES 확인
- [ ] SSID: 기본값 변경됨 확인
- [ ] MAC 필터링: "화이트리스트" 활성화 + 4개 MAC 추가
- [ ] 포트 22, 3389 외부 전달 비활성화 확인
- [ ] 관리자 비밀번호: 기본값 변경됨 확인
- [ ] UPnP: 비활성화 확인
- [ ] WPS: 비활성화 확인

---

## 🟡 중요 (MEDIUM) — 향후 개선 항목

### 1. RDP 요구사항 — 허가된 IP만 접속 가능
현재: 전체 접속 허용
권장: ADMIN_ALLOWED_IPS에 명시된 IP만 허용

```powershell
# 방화벽 고급 규칙에서 RDP 인바운드 필터
# 원본 IP: 115.22.193.150/32 (Render 배포 서버) 만 허용
netsh advfirewall firewall set rule name="Remote Desktop - User Mode (TCP-In)" new remoteip=115.22.193.150/32
```

---

### 2. DNS 설정 — Public DNS로 변경 권장
현재: ISP 기본 DNS (변수)
권장: Cloudflare (1.1.1.1) 또는 Google (8.8.8.8)

```powershell
# PowerShell (관리자 권한)
Set-DnsClientServerAddress -InterfaceIndex <인터페이스_번호> -ServerAddresses ("1.1.1.1", "1.0.0.1")
```

---

### 3. VPN/Proxy 모니터링 — 비정상 터널 감지
현재: WireGuard 비활성화 상태 (세션 22 복구 완료)
주의: `activate_wireguard.ps1` 자동 실행 금지 (CLAUDE.md IMMUTABLE CORE)

---

## ✅ 확인된 보안 조치 (양호)

### Backend Security (7계층)
1. ✅ HMAC 서명 (X-Bridge-Signature)
2. ✅ 세션 토큰 (/24 서브넷 바인딩)
3. ✅ IP 화이트리스트 (ADMIN_ALLOWED_IPS)
4. ✅ IP 블랙리스트 (누진차단 + 허니팟)
5. ✅ Rate Limiting (엔드포인트별 + 국가별)
6. ✅ 공격 탐지 (SQLi/XSS/SSRF/LLM)
7. ✅ CSRF Origin 검증

### Data Protection
- ✅ MasterVault v3.0 (Session-Ephemeral AES-256-GCM)
- ✅ 3중 AES-256-GCM 암호화 설계 (진행 중)
- ✅ Device Registry v2.0 (3중 암호화)
- ✅ RPA 자격증명 보관소 (3중 암호화)

### Network Security
- ✅ WireGuard 비활성화 (세션 22 복구)
- ✅ Device Registry (MAC 기반 관리)
- ✅ Render 환경변수 ADMIN_ALLOWED_IPS 설정 준비

---

## 📋 해킹 시도 이력 (세션 18 기록)

| 대상 | 시도 시간 | 상태 |
|------|---------|------|
| 네이버 계정 | 극심 | 🔒 강화된 비밀번호 필요 |
| 쿠팡 계정 | 극심 | 🔒 2FA 활성화 권장 |
| 페이스북 계정 | 극심 | 🔒 2FA + IP 제한 권장 |
| 인스타그램 계정 | 극심 | 🔒 2FA 활성화 권장 |

**조치**: 모든 계정에 2단계 인증(2FA) 활성화 + 비밀번호 변경 + 의심 세션 로그아웃

---

## 🔧 공유기 재설정 절차 (필요시)

```
1. 공유기 뒷면: "초기화" 버튼 3초 이상 눌러 초기화 (모든 설정 리셋)
2. 웹 UI: http://192.168.0.1 또는 192.168.1.1 접속
3. 기본 계정: admin / admin 로그인
4. 위의 "조치 방법" 섹션의 6가지 설정 수행
5. 저장 → 재부팅
```

---

## 📞 권장 다음 단계

| # | 작업 | 우선도 | 담당자 |
|----|------|--------|--------|
| 1 | RDP 3389 포트 방화벽 비활성화 | 🔴 HIGH | Scarlett |
| 2 | 공유기 MAC 필터링 + 암호화 설정 | 🔴 HIGH | Scarlett |
| 3 | 모든 온라인 계정 2FA 활성화 | 🟡 MEDIUM | Scarlett |
| 4 | DNS: Cloudflare 1.1.1.1 변경 | 🟡 MEDIUM | Scarlett |
| 5 | 월간 보안 감사 스케줄 | 🟢 LOW | 자동화 |

---

## 📝 다음 세션 작업 (연속성)

- [ ] 공유기 설정 완료 후 이 파일 업데이트 (`[DONE] 날짜`)
- [ ] 3중 AES-256-GCM 암호화 마이그레이션 완료 (work_state.md)
- [ ] master.db git 완전 소각 (work_state.md 1순위)
- [ ] 월간 보안 감사 자동화 스크립트 (향후)

---

**최종 평가**: 🟡 **부분 위험** — 공유기 설정 + RDP 차단 후 🟢 **양호**로 개선 가능

