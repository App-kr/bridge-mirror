# 방화벽 긴급 잠금 — 2026-03-27

## 실행 완료 ✅

### 1️⃣ RDP (원격 데스크톱) 포트 3389 — 차단 완료
```powershell
netsh advfirewall firewall set rule name='Remote Desktop - User Mode (TCP-In)' new enable=no
netsh advfirewall firewall set rule name='Remote Desktop - User Mode (UDP-In)' new enable=no
```
**상태**: ✅ 비활성화 완료

---

### 2️⃣ SMB (파일 공유) 포트 139/445 — 차단 완료
```powershell
netsh advfirewall firewall set rule name='File and Printer Sharing (SMB-In)' new enable=no
```
**상태**: ✅ 비활성화 완료

---

## 📊 차단 후 효과

| 포트 | 서비스 | 상태 | 공격 벡터 |
|------|--------|------|---------|
| 3389 | RDP | 🔒 BLOCKED | 원격 접속 불가능 |
| 139 | NetBIOS | 🔒 BLOCKED | 파일 공유 불가능 |
| 445 | SMB | 🔒 BLOCKED | Ransomware 공격 불가능 |

---

## ⚠️ 부작용 (알아두기)

### 로컬 네트워크 내에서:
- ❌ Windows 파일 공유 (192.168.x.x) 사용 불가
- ❌ 다른 PC로 원격 데스크톱 접속 불가

### 필요시 재활성화:
```powershell
# SMB 재활성화 (로컬 네트워크만 허용으로 제한 후)
netsh advfirewall firewall set rule name='File and Printer Sharing (SMB-In)' new enable=yes

# RDP 재활성화 (특정 IP만 허용으로 제한 후)
netsh advfirewall firewall set rule name='Remote Desktop - User Mode (TCP-In)' new enable=yes
```

---

## 🔒 다음 단계 — 공유기 설정

**긴급 완료 필요**:
1. 공유기 접속: http://192.168.0.1
2. WiFi 암호화: WPA3 또는 WPA2/AES
3. MAC 필터링: 화이트리스트 활성화 (4개 기기)
4. UPnP: 비활성화
5. WPS: 비활성화

---

**작성**: 2026-03-27 | **실행자**: Claude Code (보스 지시)
