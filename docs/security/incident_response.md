# Incident Response Playbook — Bridge
> 최종 수정: 2026-03-31

---

## P0 — 크레덴셜 유출 즉시 대응 (30분 이내)

### 트리거
- git push 후 gitleaks 경고
- secret_scanner.py 차단 알림
- 외부 모니터링(GitGuardian 등) 탐지

### 즉시 조치
```bash
# 1. 해당 키 즉시 폐기 (Anthropic/Google/GitHub/AWS 각 콘솔)
# 2. Render 환경변수 새 키로 교체
#    → Render 대시보드 > Environment > 해당 변수 수정
# 3. git 히스토리 소각 (유출된 파일 특정 후)
git filter-repo --path <leaked_file> --invert-paths
git push --force-with-lease origin master
# 4. 모든 활성 세션 폐기
python tools/bridge_reset_password.py
# 5. 감사 로그 확인
cat logs/security_log.jsonl | tail -50
```

---

## P1 — npm 공급망 공격 의심

### 트리거
- security_audit.py critical/high 발견
- runtime_guard.py 차단 알림
- node_modules에 postinstall 이상 스크립트

### 조치
```bash
# 1. node_modules 격리
mv web_frontend/node_modules web_frontend/node_modules.quarantine
# 2. 의심 패키지 특정
npm audit --json | python tools/security_audit.py
# 3. package-lock.json 이전 커밋으로 복원
git checkout <safe_commit> -- web_frontend/package-lock.json
# 4. 클린 재설치
cd web_frontend && npm ci --ignore-scripts
# 5. 재감사
npm audit
```

---

## P2 — 백업 무결성 훼손

### 트리거
- weekly audit FAIL (BridgeSecurityAudit 태스크)
- 백업 파일 IsReadOnly=False 변경 감지

### 조치
```powershell
# 1. 백업 ACL 재적용
icacls "Q:\Claudework\_BACKUP" /inheritance:d /T /Q
icacls "Q:\Claudework\_BACKUP" /remove:g "NT AUTHORITY\Authenticated Users" /T /Q
icacls "Q:\Claudework\_BACKUP" /grant:r "NT AUTHORITY\Authenticated Users:(OI)(CI)RX" /T /Q
# 2. DB 읽기전용 재적용
Get-ChildItem "Q:\Claudework\_BACKUP" -Recurse -Filter "*.db" |
    ForEach-Object { Set-ItemProperty $_.FullName -Name IsReadOnly -Value $true }
# 3. 감사 로그 기록
```

---

## P3 — RPA 크롬 프로필 유출

### 트리거
- backup_daemon 실행 후 Login Data 감지
- 백업 내 .chrome_rpa_profile 재등장

### 조치
```powershell
# 1. 즉시 소각
Get-ChildItem "Q:\Claudework" -Recurse -Include "Login Data","Cookies" |
    Where-Object { $_.FullName -match "chrome_rpa_profile" -and $_.FullName -match "backup" } |
    Remove-Item -Force
# 2. Craigslist 계정 비밀번호 교체
# 3. rpa_credential_vault.py 재설정
python tools/rpa_credential_vault.py setup
```

---

## 연락처 / 에스컬레이션

| 항목 | 방법 |
|------|------|
| Render 환경변수 | Render 대시보드 직접 |
| GitHub token 폐기 | github.com/settings/tokens |
| Anthropic API key | console.anthropic.com |
| Google API key | console.cloud.google.com |

---

## 사후 처리 체크리스트

- [ ] 유출 경로 문서화
- [ ] 영향 받은 시스템 목록 작성
- [ ] 키 교체 완료 확인 (모든 환경)
- [ ] git history clean 확인 (`git log --all -S <secret>`)
- [ ] SECURITY_POLICY.md 업데이트
- [ ] security_audit.log 에 사건 기록
