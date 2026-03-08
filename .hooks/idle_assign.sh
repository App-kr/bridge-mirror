#!/bin/bash
# idle_assign.sh — TeammateIdle hook
# 유휴 에이전트 → QA 작업 자동 배정
# Bridge CLAUDE.md v4.0 FINAL

set -euo pipefail

WORK_ROOT="Q:/Claudework/bridge base"
LOG_DIR="$WORK_ROOT/.logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
IDLE_AGENT="${IDLE_AGENT:-unknown}"

echo "[$TIMESTAMP] TeammateIdle: $IDLE_AGENT → QA 배정" >> "$LOG_DIR/idle_assign.log"

# QA 작업 큐 확인
QA_QUEUE="$WORK_ROOT/tasks/qa_queue.txt"
if [ -f "$QA_QUEUE" ] && [ -s "$QA_QUEUE" ]; then
    NEXT_TASK=$(head -1 "$QA_QUEUE")
    echo "[$TIMESTAMP] QA 배정: $NEXT_TASK → $IDLE_AGENT" >> "$LOG_DIR/idle_assign.log"
    # 큐에서 제거
    tail -n +2 "$QA_QUEUE" > "${QA_QUEUE}.tmp" && mv "${QA_QUEUE}.tmp" "$QA_QUEUE"
    echo "ASSIGNED: $NEXT_TASK"
else
    echo "[$TIMESTAMP] QA 큐 비어있음" >> "$LOG_DIR/idle_assign.log"
    echo "IDLE_OK: no pending QA tasks"
fi

exit 0
