# 🔐 기기 등록 가이드 v2.0
## Device Registry 사용 방법

---

## 📋 빠른 시작 (5분)

### 현재 PC 자동 등록
```bash
python tools/device_registry.py register "내 PC" 192.168.1.100
```

✅ 결과:
```
✅ 기기 등록 완료
   기기명: 내 PC
   MAC: 40:B0:76:A1:EF:A0
   로컬 IP: 192.168.0.2
   공인 IP: 115.22.193.150
```

---

## 🎯 상황별 등록 방법

### 1️⃣ **현재 사용 중인 PC 등록** (자동 감지)

**명령어:**
```bash
python tools/device_registry.py register "PC 이름" [IP 주소]
```

**예제:**
```bash
# 자동 IP 감지
python tools/device_registry.py register "Scarlett_Main_PC"

# IP 명시
python tools/device_registry.py register "회사 PC" 192.168.1.105
```

**결과:**
- MAC주소: 자동으로 `getmac` 명령으로 감지
- 로컬 IP: 자동으로 감지 또는 명시
- 공인 IP: 자동으로 조회 (IPv4)

---

### 2️⃣ **향후 추가될 기기 미리 등록** (원격 등록)

**언제 사용?**
- 노트북, 패드, 폰을 **지금 등록하고 싶지만**
- **아직 물리적으로 켜져있지 않음**
- 미리 MAC주소만 입력해서 기기 화이트리스트에 추가

**명령어:**
```bash
python tools/device_registry.py register-remote "MAC주소" "기기명" [IP]
```

**예제:**
```bash
# 향후 구입할 노트북 (MAC 이미 알고 있음)
python tools/device_registry.py register-remote "AA:BB:CC:DD:EE:FF" "노트북" 192.168.1.101

# 향후 구입할 패드
python tools/device_registry.py register-remote "11:22:33:44:55:66" "iPad" 192.168.1.102

# 향후 구입할 폰
python tools/device_registry.py register-remote "DE:AD:BE:EF:00:01" "아이폰" 192.168.1.103
```

**MAC주소는 어디서?**
1. 새 기기 구입 시 박스 또는 설정 화면에서 확인
2. 또는 이전 기기에서 `getmac` 명령 실행 후 저장

---

### 3️⃣ **대화형 마법사** (권장: 초보자)

**명령어:**
```bash
python tools/device_registry.py register-interactive
```

**절차:**
```
🧙 기기 등록 마법사
============================================================

1. MAC 주소를 입력하세요 (예: AA:BB:CC:DD:EE:FF)
   현재 PC의 MAC: getmac 명령으로 확인 가능
MAC: AA:BB:CC:DD:EE:FF

2. 기기 이름을 입력하세요 (예: My Laptop)
기기명: 새 노트북

3. IP 주소를 입력하세요 (선택사항, Enter로 건너뛰기)
IP: 192.168.1.101

4. 3중 암호화로 저장할까요? (y/n, 기본값: n)
암호화: y

✅ 다음 정보로 등록하시겠습니까?
   MAC: AA:BB:CC:DD:EE:FF
   기기명: 새 노트북
   IP: 192.168.1.101
   암호화: YES 🔒

계속 진행? (y/n): y
✅ 기기 등록 완료
```

---

## 🔒 3중 암호화 저장

### 보안 레벨 비교

| 옵션 | 저장 방식 | 장점 | 단점 |
|------|---------|------|------|
| **일반 저장** | 평문 JSON | 빠름 | 파일 유출 시 노출 |
| **3중 암호화** | T3v1 포맷 | 세션마다 다른 암호문 | 약간 느림 |

### 암호화로 등록하기

```bash
# 옵션 1: 자동 감지 + 암호화
python tools/device_registry.py register "내 PC" 192.168.1.100 --encrypt

# 옵션 2: 원격 등록 + 암호화
python tools/device_registry.py register-remote "AA:BB:CC:DD:EE:FF" "노트북" 192.168.1.101 --encrypt

# 옵션 3: 마법사 + 암호화 (권장)
python tools/device_registry.py register-interactive
# → "3중 암호화로 저장할까요?" → y 입력
```

### 암호화 저장 시 발생하는 일

1. **마스터 키 자동 생성**
   ```
   🔑 새로운 마스터 키를 생성합니다...
   ✅ 마스터 키 저장: Q:\Claudework\bridge base\.device_key
   ```

2. **3중 암호화 (Layer 1/2/3)**
   - Layer 1: `AES-GCM(KDF(key+L1+field), nonce1)`
   - Layer 2: `AES-GCM(KDF(key+L2+nonce1), nonce2)`
   - Layer 3: `AES-GCM(KDF(key+L3+nonce2), nonce3)`

3. **포맷: T3v1**
   ```
   base64(T3v1 + salt1 + salt2 + salt3 + nonce1 + nonce2 + nonce3 + ciphertext)
   ```

4. **결과: ~120자 이상 암호문**
   ```json
   {
     "devices": {
       "40:B0:76:A1:EF:A0": {
         "name": "T3v1AgUCAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissPQ==",
         "encrypted": true
       }
     }
   }
   ```

---

## 👀 기기 목록 확인

### 평문으로 보기
```bash
python tools/device_registry.py list
```

**출력:**
```
📱 등록된 기기 목록:
────────────────────────────────────────────────────────────────────────────────
✅ 내 PC
   MAC: 40:B0:76:A1:EF:A0
   로컬 IP: 192.168.0.2 | 공인 IP: 115.22.193.150
   등록일: 2026-03-27

✅ 노트북
   MAC: AA:BB:CC:DD:EE:FF
   로컬 IP: 192.168.1.101 | 공인 IP: remote
   등록일: 2026-03-27
   🔒 3중 암호화 저장

✅ iPad
   MAC: 11:22:33:44:55:66
   로컬 IP: 192.168.1.102 | 공인 IP: unknown
   등록일: 2026-03-27
```

### 암호화된 값 복호화해서 보기
```bash
python tools/device_registry.py list --decrypt
```

**출력:**
```
✅ 노트북 🔓
   MAC: AA:BB:CC:DD:EE:FF
   로컬 IP: 192.168.1.101 | 공인 IP: remote
   등록일: 2026-03-27
   🔒 3중 암호화 저장
```

**주의:** 마스터 키(`.device_key`)가 필요합니다.

---

## ✅ 기기 검증

### 공유기 화이트리스트에서 확인
```bash
python tools/device_registry.py verify AA:BB:CC:DD:EE:FF
```

**허용된 기기:**
```
✅ 허용됨: 노트북
```

**차단된 기기:**
```
⛔ 비활성화된 기기: 구식 노트북
```

### IP 함께 검증
```bash
python tools/device_registry.py verify AA:BB:CC:DD:EE:FF 192.168.1.101
```

---

## ⛔ 기기 차단

**분실 또는 해킹 의심 시:**
```bash
python tools/device_registry.py revoke AA:BB:CC:DD:EE:FF
```

**결과:**
```
⛔ 기기 차단 완료: 노트북
```

**이 후:**
- 공유기 MAC 필터링 (화이트리스트)에서 자동 제외
- 수동 재연결 시도 차단됨
- `.device_registry.json`에 `status: revoked` 표시

---

## 🔧 네트워크 보안 점검

```bash
python tools/device_registry.py check-network
```

**출력:**
```
🔒 네트워크 보안 점검:
────────────────────────────────────────────────────────────────────────────────
✅ IPv6 비활성화
✅ 무선 암호화
⚠️ 공유기 기본 비밀번호
⚠️ 방화벽
✅ DNS 필터링

📋 권장사항:
1. 공유기 관리자 페이지 로그인 (192.168.1.1)
2. SSID 한글명 변경 (영문+숫자)
3. WiFi 암호화: WPA3 또는 WPA2/AES
4. 기본 비밀번호 변경
5. UPnP 비활성화
6. 포트 포워딩 점검 (필요한 것만 열기)
7. 펌웨어 최신 버전으로 업데이트
8. MAC 필터링 활성화 (이 도구로 등록된 기기만)
```

---

## 📝 실제 시나리오

### 시나리오 1: 노트북 구입 예정 (지금 등록)

**상황:**
- 온라인에서 노트북 구입 (배송 대기 중)
- MAC주소를 미리 알고 있음
- 지금 화이트리스트에 추가하고 싶음

**절차:**
```bash
# 1. 원격 등록
python tools/device_registry.py register-remote "AA:BB:CC:DD:EE:FF" "새 노트북" 192.168.1.101 --encrypt

# 2. 확인
python tools/device_registry.py list

# 3. 공유기에서 MAC 추가 (192.168.1.1)
# MAC 필터링 → 화이트리스트 → AA:BB:CC:DD:EE:FF 추가

# 4. 노트북 도착 후 전원 켜면 자동으로 WiFi 연결됨
```

### 시나리오 2: 회사 PC 추가 (사무실)

**상황:**
- 회사 PC는 다른 네트워크 대역대
- IP는 DHCP (자동 할당)
- 3중 암호화로 저장 원함

**절차:**
```bash
# 1. 회사 PC에서 MAC 확인
getmac

# 2. 원격 등록 + 암호화
python tools/device_registry.py register-remote "BB:CC:DD:EE:FF:00" "회사 PC" --encrypt

# 3. 회사 공유기에서도 MAC 필터링 추가
# 회사 공유기 관리자에게 MAC 전달: BB:CC:DD:EE:FF:00

# 4. Render ADMIN_ALLOWED_IPS에 회사 네트워크 IP 범위 추가
# ADMIN_ALLOWED_IPS=115.22.193.150/32,회사IP/32
```

### 시나리오 3: 패드/폰 추가 (향후)

**상황:**
- 기존 패드/폰 판매 중
- 새 기기 구입 예정 (3개월 후)
- 미리 목록만 관리하고 싶음

**절차:**
```bash
# 1. 대화형 마법사로 미리 등록
python tools/device_registry.py register-interactive

# 2. 3개월 후 기기 도착
# → 명령어 다시 실행하지 않음 (이미 등록됨)
# → 공유기 MAC 필터링에만 추가하면 끝

# 3. 리스트 확인
python tools/device_registry.py list
```

---

## 🔑 파일 구조

| 파일 | 용도 | 권한 |
|------|------|------|
| `.device_registry.json` | 기기 데이터 (평문/암호화) | 600 |
| `.device_key` | 마스터 키 (암호화용) | 600 |
| `.trusted_ips.json` | 신뢰 IP 목록 | 600 |

**모두 git에서 제외됨** (`.gitignore`)

---

## ❓ FAQ

### Q: MAC주소를 모르면?
**A:**
```bash
# Windows
getmac

# macOS
ifconfig | grep ether

# Linux
ip link show
```

### Q: 암호화한 기기를 복호화하려면?
**A:**
```bash
python tools/device_registry.py list --decrypt
```
마스터 키(`.device_key`)가 필요합니다.

### Q: 마스터 키를 잃어버렸으면?
**A:**
1. `.device_key` 파일 삭제
2. 암호화 데이터는 수동으로 삭제 또는 새 구조로 마이그레이션
3. 다시 새 마스터 키 생성

### Q: 공유기에 몇 개까지 등록?
**A:**
무제한 (공유기 사양에 따름, 보통 100+)

### Q: 원격 접속(VPN) 시에도 필요?
**A:**
예. VPN으로 접속하는 경우에도 MAC주소는 로컬 네트워크에서 유효합니다.
Render의 `ADMIN_ALLOWED_IPS`에는 공인 IP를 추가하세요.

---

## 📞 트러블슈팅

| 문제 | 원인 | 해결책 |
|------|------|-------|
| MAC주소 조회 실패 | 권한 부족 | 관리자 권한으로 실행 |
| 암호화 실패 | cryptography 미설치 | `pip install cryptography` |
| 기기 등록 안 됨 | 중복 등록 | `list`로 확인 후 `revoke` 후 재등록 |
| 공유기에 추가 안 됨 | 수동 추가 필요 | 192.168.1.1 접속해서 MAC 필터링에 추가 |

---

**버전:** 2.0
**최종 업데이트:** 2026-03-27
**다음 검토:** 2026-04-27
