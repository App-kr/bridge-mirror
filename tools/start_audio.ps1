# AudioSwitcher 런처 — 로그온 시 자동 실행용
# Task Scheduler의 AudioSwitcher 작업이 이 스크립트를 호출

$scriptPath = 'Q:\Claudework\bridge base\tools\audio_switcher.py'
$arg        = '"' + $scriptPath + '"'

Start-Process -FilePath 'python' `
              -ArgumentList $arg `
              -WorkingDirectory 'Q:\Claudework\bridge base' `
              -WindowStyle Hidden
