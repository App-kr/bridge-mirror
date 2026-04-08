# PC WireGuard 클라이언트 설정 가이드

## 📋 준비물
- wireguard-installer.exe (바탕화면에 있음)
- PC 설정 파일: `Q:\Claudework\bridge base\security_config\wireguard\pc\pc.conf`
- 공유기 관리자 접근

---

## 1단계: WireGuard 설치

1. **바탕화면에서 `wireguard-installer.exe` 실행**
2. **"Install"** 클릭
3. **Windows 11 보안 경고**가 나타나면 **"자세한 정보" → "실행"** 클릭
4. **완료되면** WireGuard 앱이 자동으로 열림

---

## 2단계: PC WireGuard 키 생성

### 방법 A: WireGuard UI에서 생성 (권장)

1. WireGuard 앱 → **오른쪽 하단 "+"** 클릭
2. **"Add Empty Tunnel..."** 선택
3. 이름: `Scarlett_Main_PC` 입력
4. **"Create"** 클릭
5. **생성된 설정 파일 열기** (자동으로 메모장에서 오픈)
6. `[Interface]` 섹션에서 `PrivateKey =` 값 **복사** (나중에 필요)
7. **닫기**

### 방법 B: 명령줄에서 생성

```bash
wg genkey | tee pc_private.key | wg pubkey > pc_public.key
```

---

## 3단계: PC 설정 파일 채우기

1. **메모장에서** `Q:\Claudework\bridge base\security_config\wireguard\pc\pc.conf` 열기

2. 다음과 같이 수정:

```ini
[Interface]
PrivateKey = [Step 2에서 복사한 개인키]
Address = 10.0.0.2/32
DNS = 8.8.8.8, 8.8.4.4
SaveMconfig = false

[Peer]
PublicKey = SERVER_PUBLIC_KEY_HERE  # ← 공유기에서 복사해서 입력
Endpoint = bridgejob.co.kr:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

3. **저장**

---

## 4단계: 공유기에서 PC 공개키 등록

### PC 공개키 생성

**Step 2에서 개인키를 얻었다면**, 공개키도 생성됨.

**또는 수동:**
```bash
# PowerShell에서 (Windows)
$key = "개인키"  # Step 2에서 복사
wg pubkey ($key | Out-String) > pc_public.txt
```

### 공유기에 등록

1. **192.168.0.1 접속** (관리자/admin)
2. **고급설정 → 보안 → WireGuard**
3. **"Peer 추가"** 또는 **"클라이언트 추가"**
4. 다음 입력:
   - **이름**: `Scarlett_Main_PC`
   - **공개키**: [Step 2에서 생성된 PC 공개키]
   - **IP**: `10.0.0.2` (또는 자동 할당)
5. **저장** → 서버 재시작

### 서버 공개키 확인

공유기 WireGuard 설정 페이지에서:
1. **"서버 설정"** 또는 **"인터페이스"** 찾기
2. **"공개키"** 값 **복사**
3. pc.conf의 `PublicKey = SERVER_PUBLIC_KEY_HERE` 에 **붙여넣기**

---

## 5단계: WireGuard 클라이언트에서 설정 임포트

1. **WireGuard 앱 실행**
2. **오른쪽 하단 "+"** 클릭
3. **"Import tunnel(s) from file..."** 선택
4. `Q:\Claudework\bridge base\security_config\wireguard\pc\pc.conf` **선택**
5. **확인**

---

## 6단계: VPN 연결

1. WireGuard 앱에서 **Scarlett_Main_PC** 찾기
2. **토글 스위치 ON**
3. **상태**:
   - 🟢 "Active" → 연결 성공
   - 🔴 "Inactive" → 오류 (공유기 설정 확인)

---

## 🐛 트러블슈팅

### "Handshake did not complete"
- ✅ 공유기 WireGuard 서버 활성화 확인
- ✅ 포트 51820 열려있는지 확인 (`netstat -an | findstr 51820`)
- ✅ 공개키가 정확히 입력되었는지 확인

### "Connection timeout"
- ✅ PC 프라이빗 키 확인
- ✅ 공유기 NAT 설정 확인
- ✅ Endpoint `bridgejob.co.kr:51820` 핑 가능한지 확인

### "No internet after connecting"
- ✅ AllowedIPs 설정 확인 (현재: `10.0.0.0/24`)
- ✅ DNS 설정 확인 (현재: `8.8.8.8, 8.8.4.4`)

---

## ✅ 연결 확인

```bash
# 터미널에서 (관리자 권한 필수)
ping 10.0.0.1   # VPN 게이트웨이
ping 10.0.0.3   # iPhone
ping 10.0.0.4   # iPad
```

모두 응답하면 ✅ 완료!

---

## 📍 설정 파일 위치

| 기기 | 설정 파일 |
|------|---------|
| PC | `Q:\Claudework\bridge base\security_config\wireguard\pc\pc.conf` |
| iPhone | `Q:\Claudework\bridge base\security_config\wireguard\phone\phone.conf` |
| iPad | `Q:\Claudework\bridge base\security_config\wireguard\pad\pad.conf` |

---

생성: 2026-03-27
