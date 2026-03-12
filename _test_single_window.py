"""
테스트 2: 단일 창 설계
- python.exe (not pythonw.exe) 로 실행 → CMD 창 1개만 표시
- Tkinter overlay 없음
- console print로 상태 표시
- Chrome은 headless=True 옵션 사용
- 창 닫으면 RPA 중단 (의도적 종료 = OK)
"""
import time, sys, os

def print_status(step, total, msg, success=0, fail=0):
    bar_len = 30
    filled  = int(bar_len * step / max(total, 1))
    bar     = "#" * filled + "-" * (bar_len - filled)
    sys.stdout.write(
        f"\r  [{bar}] {step}/{total}  OK={success} NG={fail}  {msg[:35]:<35}"
    )
    sys.stdout.flush()

print("=" * 60)
print("  BRIDGE RPA — Single Window Mode")
print("  python.exe 직접 실행 / Tkinter 없음 / Chrome headless")
print("  이 창을 닫으면 RPA가 종료됩니다.")
print("=" * 60)
print()

# 실제 RPA 루프 시뮬레이션 (5개 항목)
TOTAL = 5
success = 0
fail    = 0

for i in range(1, TOTAL + 1):
    print_status(i, TOTAL, f"처리중: 항목{i}", success, fail)
    time.sleep(1)
    # 성공/실패 시뮬레이션
    if i % 4 == 0:
        fail += 1
    else:
        success += 1

print()
print()
print(f"  완료: 성공={success}, 실패={fail}, 합계={TOTAL}")
print("=" * 60)
input("\n  Enter 키를 누르면 창이 닫힙니다...")
