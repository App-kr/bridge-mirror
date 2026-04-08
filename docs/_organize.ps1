$d = 'Q:\Claudework\bridge base\docs'
$arch = "$d\architecture"
$sec  = "$d\security"
$api  = "$d\api"
$hand = "$d\handoff"
$scr  = "$d\scripts"

$moves = @(
  @{ src="$d\BRIDGE_MASTER_PLAN.md";                dst=$arch },
  @{ src="$d\BRIDGE_Master_Deployment.md";           dst=$arch },
  @{ src="$d\DEPLOY.md";                             dst=$arch },
  @{ src="$d\FULL_STABILIZATION.md";                 dst=$arch },
  @{ src="$d\bridge-architecture.excalidraw";        dst=$arch },
  @{ src="$d\bridge-architecture.png";               dst=$arch },
  @{ src="$d\CREDENTIALS_REFERENCE.md";              dst=$sec  },
  @{ src="$d\SECURITY_AUDIT_2026-03-27.md";          dst=$sec  },
  @{ src="$d\FIREWALL_LOCK_2026-03-27.md";           dst=$sec  },
  @{ src="$d\RDP_SECURE_CONFIG_2026-03-27.md";       dst=$sec  },
  @{ src="$d\RDP_TODO_2026-03-27.md";                dst=$sec  },
  @{ src="$d\PRIVATE_NETWORK_SETUP_2026-03-27.md";   dst=$sec  },
  @{ src="$d\FINAL_SETUP_STATUS_2026-03-27.md";      dst=$sec  },
  @{ src="$d\DEVICE_REGISTRATION.md";                dst=$sec  },
  @{ src="$d\NETWORK_SECURITY.md";                   dst=$sec  },
  @{ src="$d\WIREGUARD_PC_SETUP.md";                 dst=$sec  },
  @{ src="$d\incident_response.md";                  dst=$sec  },
  @{ src="$d\API_TEST_REPORT.md";                    dst=$api  },
  @{ src="$d\API_TEST_SUMMARY.txt";                  dst=$api  },
  @{ src="$d\API_SECURITY_INDEX.md";                 dst=$api  },
  @{ src="$d\AI_SECURITY_DESIGN.md";                 dst=$api  },
  @{ src="$d\AI_CONTEXT.md";                         dst=$hand },
  @{ src="$d\AI_MASTER_HANDOFF.md";                  dst=$hand },
  @{ src="$d\claude_web_handoff.md";                 dst=$hand },
  @{ src="$d\SESSION_24_COMPLETE_2026-03-27.md";     dst=$hand },
  @{ src="$d\AUTOMATION_GUIDE.md";                   dst=$hand }
)

foreach ($m in $moves) {
  if (Test-Path $m.src) {
    Move-Item -Force $m.src $m.dst
    Write-Host "OK: $(Split-Path $m.src -Leaf)"
  } else {
    Write-Host "SKIP: $(Split-Path $m.src -Leaf)"
  }
}

# 한글 파일명 별도 처리
Get-ChildItem "$d\*.js" | ForEach-Object {
  Move-Item -Force $_.FullName $scr
  Write-Host "OK: $($_.Name)"
}

Write-Host "`n완료!"
