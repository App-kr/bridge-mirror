import json
from pathlib import Path

VAULT = Path(r'Q:\Obsidian\Scarlett\BRIDGE\maps')
VAULT.mkdir(parents=True, exist_ok=True)

full = {'nodes':[
  {'id':'center','type':'text','text':'🌉 BRIDGE\nbridgejob.co.kr','x':-90,'y':-40,'width':180,'height':80,'color':'4'},
  {'id':'backend','type':'text','text':'⚙️ 백엔드\nFastAPI / Render','x':-420,'y':-180,'width':160,'height':70,'color':'6'},
  {'id':'frontend','type':'text','text':'🖥️ 프론트엔드\nNext.js / Vercel','x':240,'y':-180,'width':160,'height':70,'color':'6'},
  {'id':'db','type':'text','text':'🗄️ master.db','x':-420,'y':-60,'width':160,'height':70,'color':'2'},
  {'id':'candidates','type':'text','text':'👤 원어민 관리\n/admin/candidates','x':240,'y':-60,'width':160,'height':70,'color':'2'},
  {'id':'employers','type':'text','text':'🏢 업체 관리\n/admin/applications','x':240,'y':60,'width':160,'height':70,'color':'2'},
  {'id':'community','type':'text','text':'📋 커뮤니티\nFAQ / 비자 / Korea','x':-420,'y':60,'width':160,'height':70,'color':'2'},
  {'id':'automation','type':'text','text':'🤖 Craigslist RPA','x':-420,'y':180,'width':160,'height':70,'color':'3'},
  {'id':'backup','type':'text','text':'🛡️ 백업\nbridge_backup v3.0','x':-90,'y':180,'width':160,'height':70,'color':'3'},
  {'id':'infra','type':'text','text':'📡 모니터링\nRenderMonitor','x':240,'y':180,'width':160,'height':70,'color':'3'},
  {'id':'docs','type':'text','text':'📝 작업일지\nObsidian','x':-90,'y':-180,'width':160,'height':70,'color':'5'},
  {'id':'lock','type':'text','text':'🔒 CLAUDE.md\nIMMUTABLE','x':440,'y':-40,'width':160,'height':70,'color':'1'},
],'edges':[
  {'id':'e1','fromNode':'center','toNode':'backend','label':'API'},
  {'id':'e2','fromNode':'center','toNode':'frontend','label':'UI'},
  {'id':'e3','fromNode':'backend','toNode':'db'},
  {'id':'e4','fromNode':'frontend','toNode':'candidates'},
  {'id':'e5','fromNode':'frontend','toNode':'employers'},
  {'id':'e6','fromNode':'frontend','toNode':'community'},
  {'id':'e7','fromNode':'backend','toNode':'automation'},
  {'id':'e8','fromNode':'backend','toNode':'backup'},
  {'id':'e9','fromNode':'center','toNode':'infra'},
  {'id':'e10','fromNode':'center','toNode':'docs'},
  {'id':'e11','fromNode':'center','toNode':'lock'},
]}

backup = {'nodes':[
  {'id':'b0','type':'text','text':'🛡️ 백업 시스템','x':-90,'y':-40,'width':180,'height':60,'color':'3'},
  {'id':'b1','type':'text','text':'bridge_backup.py v3.0\n타임스탬프 스냅샷\nPreToolUse 훅\n30개 보관','x':-320,'y':80,'width':200,'height':100,'color':'6'},
  {'id':'b2','type':'text','text':'auto_backup.py\n5분 간격\n48h 전체\n이후 일별 1개','x':100,'y':80,'width':200,'height':100,'color':'6'},
  {'id':'b3','type':'text','text':'저장\nbridge base\\backups\\','x':-320,'y':220,'width':200,'height':70,'color':'2'},
  {'id':'b4','type':'text','text':'일지\nBRIDGE\\backup\\','x':100,'y':220,'width':200,'height':70,'color':'2'},
  {'id':'b5','type':'text','text':'Task Scheduler\nAutoBackup5min','x':-90,'y':220,'width':180,'height':70,'color':'5'},
],'edges':[
  {'id':'e1','fromNode':'b0','toNode':'b1'},
  {'id':'e2','fromNode':'b0','toNode':'b2'},
  {'id':'e3','fromNode':'b1','toNode':'b3'},
  {'id':'e4','fromNode':'b1','toNode':'b4'},
  {'id':'e5','fromNode':'b2','toNode':'b5'},
]}

admin = {'nodes':[
  {'id':'a0','type':'text','text':'📊 Admin Sheet','x':-90,'y':-40,'width':180,'height':60,'color':'4'},
  {'id':'a1','type':'text','text':'👤 원어민 관리\n가상스크롤\nPII 복호화\n51컬럼','x':-280,'y':80,'width':180,'height':100,'color':'2'},
  {'id':'a2','type':'text','text':'🏢 업체 관리\nEmployerMgmt','x':100,'y':80,'width':180,'height':100,'color':'2'},
  {'id':'a3','type':'text','text':'📧 메일 발송\n네이버 스타일\n9개 템플릿','x':-280,'y':220,'width':180,'height':90,'color':'6'},
  {'id':'a4','type':'text','text':'🔐 보안\nPII 마스킹\nADMIN_API_KEY FREEZE','x':100,'y':220,'width':180,'height':90,'color':'1'},
],'edges':[
  {'id':'e1','fromNode':'a0','toNode':'a1'},
  {'id':'e2','fromNode':'a0','toNode':'a2'},
  {'id':'e3','fromNode':'a1','toNode':'a3'},
  {'id':'e4','fromNode':'a1','toNode':'a4'},
]}

for fname, data in [
  ('BRIDGE_전체구조.canvas', full),
  ('BRIDGE_백업시스템.canvas', backup),
  ('BRIDGE_AdminSheet.canvas', admin),
]:
    out = VAULT / fname
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'OK: {out}')
