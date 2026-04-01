#!/bin/bash
# ~/bridge_claude.sh

SESSION="bridge"
PROJECT="/mnt/q/Claudework/bridge base"

tmux kill-session -t $SESSION 2>/dev/null
tmux new-session -d -s $SESSION

# Q드라이브 마운트 확인
if [ ! -d "/mnt/q" ]; then
    sudo mount -t drvfs Q: /mnt/q
fi

# 왼쪽 75%: Claude Code
tmux send-keys -t $SESSION:0.0 "cd '$PROJECT' && claude" Enter

# 오른쪽 25%: 상태 모니터
tmux split-window -t $SESSION -h -p 25
tmux send-keys -t $SESSION:0.1 "watch -n 5 '
  echo \"=== BRIDGE STATUS ===\"
  echo \"Time: \$(date +%H:%M:%S)\"
  echo \"\"
  echo \"--- Git ---\"
  git -C \"/mnt/q/Claudework/bridge base\" status --short 2>/dev/null | head -5
  echo \"\"
  echo \"--- Q Drive ---\"
  df -h /mnt/q 2>/dev/null | tail -1
  echo \"\"
  echo \"--- ccusage ---\"
  ccusage 2>/dev/null | head -10 || echo \"ccusage 미설치\"
'" Enter

tmux select-pane -t $SESSION:0.0
tmux attach -t $SESSION
