# 🔒 BRIDGE 네트워크 보안 가이드 v1.0
**목표**: 원격 작업 지원 + 등록된 기기만 접속 허용

---

## 1️⃣ 기기 등록 (첫 사용 시 한 번만)

### PC에서 실행:
```bash
python "Q:\Claudework\bridge base\tools\device_registry.py" register "내 PC" 192.168.1.100
```

### 결과:
```
✅ 기기 등록 완료
   기기명: 내 PC
   MAC: AA:BB:CC:DD:EE:FF
   로컬 IP: 192.168.1.100
   공인 IP: 1.2.3.4
```

### 각 사용 기기별로 반복 (노트북, 태블릿 등):
```bash
python tools/device_registry.py register "내 노트북" 192.168.1.101
python tools/device_registry.py register "회사 PC" 1.2.3.50
```

### 등록된 기기 확인:
```bash
python tools/device_registry.py list
```

---

## 2️⃣ 공유기 설정 (관리자 페이지)

### 🔓 공유기 접속
1. 브라우저: **`http://192.168.0.1`** ✅ (자동 감지됨)
   - 대체: `http://192.168.1.1` 또는 `http://10.0.0.1` (모델별로 다를 수 있음)
   - 확인: `python tools/network_diagnostic.py` 실행 후 "공유기 IP" 확인
2. 로그인 (기본: admin/admin 등 — **반드시 변경**)

### ✅ 체크리스트

#### A. 기본 보안
- [ ] **관리자 비밀번호 변경** (12자 이상, 특수문자 포함)
- [ ] SSID 한글명 → 영문+숫자로 변경 (예: BRIDGE-WIFI-2024)
- [ ] WiFi 비밀번호 변경 (16자 이상, 특수문자)
- [ ] WiFi 암호화: **WPA3** 또는 **WPA2/AES** (WEP/TKIP 금지)

#### B. 고급 보안
- [ ] **MAC 필터링 활성화** (아래 참조)
- [ ] UPnP 비활성화 (Security > UPnP)
- [ ] 포트 포워딩 확인 (Port Forwarding)
  - [ ] 22(SSH) — 폐쇄 또는 비표준 포트로 변경
  - [ ] 3389(RDP) — 폐쇄
  - [ ] 필요한 포트만 개방 (예: 443=HTTPS)
- [ ] DDNS 설정 (선택) — 공인IP 변경 시 자동 추적

#### C. 펌웨어 및 로그
- [ ] 펌웨어 자동 업데이트 활성화
- [ ] 보안 로그 활성화 (System > Log)
- [ ] 월 1회 펌웨어 수동 업데이트 확인

---

## 3️⃣ MAC 필터링 설정

### 단계:

**1. 공유기 관리자 페이지 → WiFi > MAC 필터링**

**2. 필터 모드: "화이트리스트" (등록된 기기만 접속)**

**3. 허용 MAC 주소 추가:**

아래 명령어로 등록 기기 MAC 확인:
```bash
python tools/device_registry.py list
```

출력 예:
```
📱 등록된 기기 목록:
✅ 내 PC
   MAC: AA:BB:CC:DD:EE:FF
   로컬 IP: 192.168.1.100

✅ 내 노트북
   MAC: 11:22:33:44:55:66
   로컬 IP: 192.168.1.101
```

**4. 공유기에서 각 MAC 추가:**
- AA:BB:CC:DD:EE:FF
- 11:22:33:44:55:66
- (기타 새 기기 추가할 때마다 등록)

---

## 4️⃣ Render 원격 접속 보안

### Render 대시보드: https://dashboard.render.com

#### 환경변수 설정 (Settings > Environment)

**추가 필요:**
```
ADMIN_ALLOWED_IPS=1.2.3.4/32,5.6.7.8/32
BRIDGE_FIELD_KEY=(이미 설정됨)
JWT_SECRET=(이미 설정됨)
```

- `1.2.3.4` = 내 공인IP (전 설정)
- `5.6.7.8` = 회사/다른 장소 공인IP (필요시 추가)

#### 공인IP 확인:
```bash
curl https://api.ipify.org
```

---

## 5️⃣ 방화벽 설정 (Windows)

### 인바운드 규칙 (필요시만)

```powershell
# 관리자 권한 필요
netsh advfirewall firewall show allprofiles

# 특정 IP에서만 SSH 허용 (선택)
netsh advfirewall firewall add rule name="SSH_WhiteList" dir=in action=allow protocol=tcp localport=22 remoteip=1.2.3.4
```

---

## 6️⃣ VPN/원격 접속 (원격 작업용)

### 옵션 A: WireGuard (추천)
- 설치: https://www.wireguard.com/install/
- 공유기가 WireGuard 지원하면 VPN 서버 구성 가능

### 옵션 B: 공유기 내장 VPN
- 공유기 모델에 따라 PPTP/L2TP 지원 확인
- 관리자 페이지 > VPN 메뉴

### 옵션 C: Tailscale (가장 간단)
```bash
# PC 설치
https://tailscale.com/download/

# 다른 기기에서도 설치 후 같은 Tailscale 계정으로 연결
# 자동으로 암호화된 VPN 터널 생성
```

---

## 7️⃣ 모니터링 및 로그

### 주간 점검:
```bash
python tools/device_registry.py check-network
```

### 공유기 로그 확인:
1. 관리자 페이지 > System > Log
2. 비정상적인 접속 시도 확인
3. 알 수 없는 MAC주소 차단 기록 확인

### 실시간 감시:
```bash
# Bridge API 감사 로그 확인
tail -f Q:\Claudework\bridge\ base\security_log.jsonl | grep "unauthorized\|attack"
```

---

## 8️⃣ 긴급 차단 절차

**기기 분실 또는 해킹 의심 시:**

```bash
# 즉시 기기 차단
python tools/device_registry.py revoke AA:BB:CC:DD:EE:FF
```

**공유기 응답:**
- 해당 MAC주소 자동 연결 불가
- 수동 재연결 시도 차단됨

---

## 9️⃣ 트러블슈팅

### Q: WiFi 연결 안 됨
A:
1. 공유기 재부팅 (전원 끄고 30초 후 켜기)
2. 기기 MAC주소 공유기 화이트리스트에 있는지 확인
3. `python tools/device_registry.py list` 로 MAC 재확인

### Q: 원격에서 Render 접속 안 됨
A:
1. 공인IP 확인: `curl https://api.ipify.org`
2. Render ADMIN_ALLOWED_IPS에 현재 공인IP 추가
3. 예: `ADMIN_ALLOWED_IPS=1.2.3.4/32`

### Q: 불명의 기기가 연결된 것 같음
A:
1. `python tools/device_registry.py list` 로 MAC 확인
2. 모르는 MAC이 있으면 차단:
   ```bash
   python tools/device_registry.py revoke XX:XX:XX:XX:XX:XX
   ```
3. 공유기 로그에서 접속 기록 확인

---

## 🔟 정기점검 일정

| 항목 | 주기 | 확인 방법 |
|------|------|---------|
| 펌웨어 업데이트 | 월 1회 | 공유기 관리자 페이지 |
| 보안 로그 | 주 1회 | 공유기 System > Log |
| 기기 목록 | 주 1회 | `python tools/device_registry.py list` |
| 비정상 접속 | 실시간 | Render 감사 로그 |

---

## 🔑 참고 파일

- `.device_registry.json` — 등록 기기 데이터 (권한: 600)
- `.trusted_ips.json` — 신뢰 IP 목록
- `security_log.jsonl` — API 감사 로그

**모두 암호화되어 저장됨 — git에서 제외**

---

**작성**: 2026-03-27
**버전**: 1.0
**다음 검토**: 2026-04-27
