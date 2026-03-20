import { useState, useMemo, useCallback, useEffect, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

let _nxt=1101;
function nextId(){const n=_nxt;_nxt+=2;return`N${n}`;}
function uniq(a,k){return[...new Set(a.map(d=>d[k]).filter(Boolean))].sort();}

// ─── 양식 ───────────────────────────────────────────────
// teachingAge 한글 번역
const AGE_MAP={
  "Pre-K":"유아(Pre-K)","Kindy":"유치","Kinder":"유치","Kindergarten":"유치",
  "Elem":"초등","Elementary":"초등","Preschool":"미취학",
  "Middle":"중등","Middle School":"중등","Jr.High":"중등",
  "High":"고등","High School":"고등","Adult":"성인","All ages":"전연령",
  "초중":"초중","유치":"유치","초등":"초등","중고":"중고","유초":"유초",
  "유중":"유중","성인":"성인","고등":"고등","초고":"초고","전연령":"전연령",
};
const translateAge=(raw)=>{
  if(!raw)return"";
  return raw.split(/[,\/\-~]+/).map(p=>{
    const t=p.trim();
    for(const [en,ko] of Object.entries(AGE_MAP)){if(t.toLowerCase()===en.toLowerCase())return ko;}
    return t;
  }).join(" · ");
};

const TEMPLATES=[
  {id:"intro",name:"📢 소개발송",subject:"📢 BRIDGE 원어민 강사 소식 — 국내/해외 프로필 확인하세요",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>BRIDGE 원어민 강사 프로필을 공유드립니다.<br/>Start date and preferences noted. Reference provided for review only.</p><hr style="border:none;border-top:1px solid #ddd;margin:16px 0;"/><p><em>아래 프로필을 확인해 주시고, 관심 있으신 경우 회신 부탁드립니다.</em></p><p>&nbsp;</p><p style="font-size:12px;color:#888;">💡 If you are not the intended recipient or no longer in this role, please notify us and delete this email.</p>`},
  {id:"basic",name:"기본안내",subject:"[BRIDGE] 안내드립니다",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>BRIDGE 리크루팅입니다.</p><p>&nbsp;</p><p>감사합니다.<br/>BRIDGE Recruitment Team</p>`},
  {id:"fee",name:"요금안내",subject:"[BRIDGE] 서비스 요금 안내",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>요청하신 서비스 요금을 안내드립니다.</p><p>&nbsp;</p><p>감사합니다.<br/>BRIDGE</p>`},
  {id:"contract",name:"체결안내",subject:"[BRIDGE] 계약 체결 안내",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>계약 체결 관련 안내드립니다.</p><p>&nbsp;</p>`},
  {id:"confirm",name:"확정안내",subject:"[BRIDGE] 채용 확정 안내",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>채용이 확정되었음을 안내드립니다.</p><p>&nbsp;</p>`},
  {id:"entry",name:"입국안내",subject:"[BRIDGE] 입국 관련 안내",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>입국 일정 관련 안내드립니다.</p><p>&nbsp;</p>`},
  {id:"visa",name:"출입국업무",subject:"[BRIDGE] 출입국 업무 안내",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>출입국 업무 관련 안내드립니다.</p><p>&nbsp;</p>`},
  {id:"receive",name:"채용정보접수",subject:"[BRIDGE] 채용 정보 접수 확인",html:`<p>안녕하세요, <strong>{{name}}</strong> 담당자님.</p><p>채용 정보를 접수하였습니다.</p><p>&nbsp;</p>`},
  {id:"custom",name:"직접작성",subject:"",html:"<p></p>"},
];
const SENDERS=["bridgejobkr@naver.com","bridgejobkr@gmail.com"];

// ─── 인라인 편집 ────────────────────────────────────────
const EditCell=({value,onChange,style:st,multiline})=>{
  const[ed,setEd]=useState(false);
  const[tmp,setTmp]=useState(value||"");
  const ref=useRef(null);
  useEffect(()=>{if(ed&&ref.current)ref.current.focus();},[ed]);
  const save=()=>{onChange(tmp);setEd(false);};
  if(ed){
    if(multiline)return <textarea ref={ref} value={tmp} onChange={e=>setTmp(e.target.value)} onBlur={save} rows={3} style={{width:"100%",padding:"4px 6px",border:"1px solid #2563eb",borderRadius:4,fontSize:"inherit",fontFamily:"inherit",resize:"vertical",...st}}/>;
    return <input ref={ref} value={tmp} onChange={e=>setTmp(e.target.value)} onBlur={save} onKeyDown={e=>{if(e.key==="Enter")save();if(e.key==="Escape"){setTmp(value||"");setEd(false);}}} style={{width:"100%",padding:"3px 6px",border:"1px solid #2563eb",borderRadius:4,fontSize:"inherit",...st}}/>;
  }
  return <span onDoubleClick={()=>{setTmp(value||"");setEd(true);}} style={{cursor:"text",minHeight:18,display:"inline-block",...st}} title="더블클릭 편집">{value||"—"}</span>;
};

// ─── 드롭다운 필터 (상단 공통 필터바용) ─────────────────
const DropFilter=({label,optKey,data,filters,setFilters})=>{
  const[open,setOpen]=useState(false);
  const[q,setQ]=useState("");
  const ref=useRef(null);
  useEffect(()=>{
    const h=e=>{if(ref.current&&!ref.current.contains(e.target))setOpen(false);};
    document.addEventListener("mousedown",h);
    return()=>document.removeEventListener("mousedown",h);
  },[]);
  const opts=uniq(data,optKey);
  const sel=filters[optKey]||[];
  const active=sel.length>0;
  return(
    <div ref={ref} style={{position:"relative",display:"inline-block"}}>
      <button onClick={()=>setOpen(!open)} style={{padding:"5px 12px",border:`1px solid ${active?"#2563eb":"#ccc"}`,borderRadius:6,background:active?"#eff6ff":"#fff",color:active?"#2563eb":"#555",fontSize:"0.82rem",fontWeight:active?700:400,cursor:"pointer",display:"flex",alignItems:"center",gap:4,whiteSpace:"nowrap"}}>
        {label}{active&&<span style={{background:"#2563eb",color:"#fff",borderRadius:10,padding:"0 5px",fontSize:"0.65rem",fontWeight:800}}>{sel.length}</span>}<span style={{fontSize:"0.65rem"}}>{open?"▲":"▼"}</span>
      </button>
      {open&&<div onClick={e=>e.stopPropagation()} style={{position:"absolute",top:"calc(100% + 4px)",left:0,zIndex:400,background:"#fff",border:"1px solid #ddd",borderRadius:8,boxShadow:"0 6px 20px rgba(0,0,0,0.12)",minWidth:160,maxHeight:260,display:"flex",flexDirection:"column"}}>
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="검색..." autoFocus style={{padding:"7px 10px",border:"none",borderBottom:"1px solid #eee",fontSize:"0.82rem",outline:"none",borderRadius:"8px 8px 0 0"}}/>
        <div style={{overflowY:"auto",flex:1}}>
          <label style={{display:"flex",alignItems:"center",gap:7,padding:"6px 10px",cursor:"pointer",fontSize:"0.82rem",fontWeight:600,borderBottom:"1px solid #f0f0f0",background:"#fafafa"}}>
            <input type="checkbox" checked={sel.length===0} onChange={()=>setFilters(p=>({...p,[optKey]:[]}))} style={{accentColor:"#2563eb"}}/>(전체)
          </label>
          {opts.filter(o=>o.toLowerCase().includes(q.toLowerCase())).map(o=>(
            <label key={o} style={{display:"flex",alignItems:"center",gap:7,padding:"5px 10px",cursor:"pointer",fontSize:"0.82rem",background:sel.includes(o)?"#eff6ff":"transparent"}}>
              <input type="checkbox" checked={sel.includes(o)} onChange={()=>setFilters(p=>{const c=p[optKey]||[];return{...p,[optKey]:c.includes(o)?c.filter(x=>x!==o):[...c,o]};})} style={{accentColor:"#2563eb"}}/>{o}
            </label>
          ))}
        </div>
      </div>}
    </div>
  );
};

// ─── 열 헤더 필터 (엑셀뷰 각 열) ────────────────────────
const ColFilter=({col,data,filters,setFilters})=>{
  const[open,setOpen]=useState(false);
  const ref=useRef(null);
  const[q,setQ]=useState("");
  useEffect(()=>{const h=e=>{if(ref.current&&!ref.current.contains(e.target))setOpen(false)};document.addEventListener("mousedown",h);return()=>document.removeEventListener("mousedown",h)},[]);
  const opts=uniq(data,col.key);
  const sel=filters[col.key]||[];
  const all=sel.length===0;
  return(
    <div ref={ref} style={{display:"inline-block",position:"relative"}}>
      <button onClick={e=>{e.stopPropagation();setOpen(!open);}} style={{background:"none",border:"none",cursor:"pointer",fontSize:"0.6rem",color:sel.length?"#2563eb":"#aaa",marginLeft:2,verticalAlign:"middle"}}>{sel.length?`▼(${sel.length})`:"▼"}</button>
      {open&&<div style={{position:"absolute",top:"100%",left:0,zIndex:300,background:"#fff",border:"1px solid #ccc",borderRadius:6,boxShadow:"0 4px 16px rgba(0,0,0,0.15)",minWidth:150,maxHeight:250,display:"flex",flexDirection:"column"}} onClick={e=>e.stopPropagation()}>
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="검색..." style={{padding:"6px 8px",border:"none",borderBottom:"1px solid #eee",fontSize:"0.82rem",outline:"none"}}/>
        <div style={{overflowY:"auto",flex:1}}>
          <label style={{display:"flex",alignItems:"center",gap:6,padding:"5px 8px",cursor:"pointer",fontSize:"0.8rem",fontWeight:600,borderBottom:"1px solid #f0f0f0"}}>
            <input type="checkbox" checked={all} onChange={()=>setFilters(p=>({...p,[col.key]:[]}))}/>전체
          </label>
          {opts.filter(o=>o.toLowerCase().includes(q.toLowerCase())).map(o=>(
            <label key={o} style={{display:"flex",alignItems:"center",gap:6,padding:"4px 8px",cursor:"pointer",fontSize:"0.8rem"}}>
              <input type="checkbox" checked={all||sel.includes(o)} onChange={()=>setFilters(p=>{const c=p[col.key]||[];return{...p,[col.key]:c.includes(o)?c.filter(x=>x!==o):[...c,o]};})}/>
              {o}
            </label>
          ))}
        </div>
      </div>}
    </div>
  );
};

// ─── 색상 팔레트 ─────────────────────────────────────────
const ColorPalette=({onSelect,onClose,colors})=>(
  <div style={{position:"absolute",top:"100%",left:0,zIndex:100,background:"#fff",border:"1px solid #ddd",borderRadius:6,padding:6,boxShadow:"0 4px 12px rgba(0,0,0,0.12)",display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:3}}>
    {colors.map(c=><button key={c} onClick={()=>{onSelect(c);onClose();}} style={{width:24,height:24,border:c==="#ffffff"?"1px solid #ddd":"1px solid transparent",borderRadius:3,background:c,cursor:"pointer"}}/>)}
  </div>
);

// ─── 메일 팝업 ───────────────────────────────────────────
const MailComposer=({recipients:initRecipients,onClose})=>{
  const[tplId,setTplId]=useState("intro");
  const[sender,setSender]=useState(SENDERS[0]);
  const[subject,setSubject]=useState(TEMPLATES[0].subject);
  const[attachments,setAttachments]=useState([]);
  const[sending,setSending]=useState(false);
  const[sent,setSent]=useState(false);
  const[previewHtml,setPreviewHtml]=useState("");
  const[showFg,setShowFg]=useState(false);
  const[showBg,setShowBg]=useState(false);
  const[showRecipients,setShowRecipients]=useState(true);
  const[extraEmails,setExtraEmails]=useState([]);
  const[editingEmail,setEditingEmail]=useState(null); // {src:"init"|"extra", ri:number, ei:number}
  const[editEmailVal,setEditEmailVal]=useState("");
  // 수신자 이메일 로컬 편집본 (initRecipients 기반)
  const[localRecipients,setLocalRecipients]=useState(()=>initRecipients.map(r=>({...r,emails:[...(r.emails||[r.email])]})));
  const[newEmail,setNewEmail]=useState("");
  const[editorH,setEditorH]=useState(280);
  const[editorH2,setEditorH2]=useState(280);
  const[activeEditor,setActiveEditor]=useState(1);
  const editorRef=useRef(null);
  const editorRef2=useRef(null);
  const[pos,setPos]=useState({x:window.innerWidth/2-625,y:window.innerHeight/2-490});
  const[dragging,setDragging]=useState(false);
  const dragStart=useRef(null);
  const[sendResult,setSendResult]=useState(null); // {ok,fail}
  const startDrag=useCallback(e=>{
    if(e.button!==0)return;
    dragStart.current={mx:e.clientX,my:e.clientY,px:pos.x,py:pos.y};
    setDragging(true);
    const onMove=ev=>{if(!dragStart.current)return;setPos({x:dragStart.current.px+(ev.clientX-dragStart.current.mx),y:dragStart.current.py+(ev.clientY-dragStart.current.my)});};
    const onUp=()=>{setDragging(false);dragStart.current=null;document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);};
    document.addEventListener("mousemove",onMove);
    document.addEventListener("mouseup",onUp);
  },[pos]);
  const fileInputRef=useRef(null);
  const FG=["#000000","#333333","#555555","#888888","#dc2626","#ea580c","#f59e0b","#16a34a","#0891b2","#2563eb","#7c3aed","#be185d"];
  const BG=["#ffffff","#f8f8f8","#fff3cd","#d1ecf1","#d4edda","#f8d7da","#e2e3e5","#cce5ff","#fef3c7","#dbeafe","#ede9fe","#fce7f3"];

  const allRecipientEmails=useMemo(()=>{
    const fromList=localRecipients.flatMap(r=>r.emails.filter(e=>e.trim()).map(em=>({name:r.name,email:em})));
    const extras=extraEmails.filter(e=>e.trim()).map(e=>({name:e.split("@")[0],email:e}));
    return [...fromList,...extras];
  },[localRecipients,extraEmails]);
  const totalEmails=allRecipientEmails.length;

  const exec=(cmd,val=null)=>{document.execCommand(cmd,false,val);(activeEditor===1?editorRef:editorRef2).current?.focus();};
  const selectTpl=useCallback(id=>{setTplId(id);const t=TEMPLATES.find(x=>x.id===id);if(t){setSubject(t.subject);const ref=activeEditor===1?editorRef:editorRef2;if(ref.current)ref.current.innerHTML=t.html;}},[activeEditor]);
  useEffect(()=>{if(editorRef.current)editorRef.current.innerHTML=TEMPLATES[0].html;if(editorRef2.current)editorRef2.current.innerHTML="";},[]);
  const updatePreview=useCallback(()=>{const ref=activeEditor===1?editorRef:editorRef2;const raw=ref.current?.innerHTML||"";if(!initRecipients.length){setPreviewHtml(raw);return;}const r=initRecipients[0];setPreviewHtml(raw.replace(/\{\{name\}\}/g,r.name).replace(/\{\{region\}\}/g,r.region).replace(/\{\{city\}\}/g,r.city).replace(/\{\{teachingAge\}\}/g,r.teachingAge));},[initRecipients,activeEditor]);
  useEffect(()=>{const t=setInterval(updatePreview,500);return()=>clearInterval(t);},[updatePreview]);

  const parseEmails=(raw)=>raw.split(/[,;\s\n]+/).map(e=>e.trim()).filter(e=>e.includes("@")&&e.length>3);
  const addEmail=()=>{
    const parsed=parseEmails(newEmail);
    if(parsed.length>0){setExtraEmails(p=>[...p,...parsed]);setNewEmail("");}
  };
  const removeExtra=idx=>setExtraEmails(p=>p.filter((_,i)=>i!==idx));
  const handleFiles=files=>{setAttachments(p=>[...p,...[...files].map(f=>({name:f.name,size:f.size<1024*1024?`${(f.size/1024).toFixed(0)}KB`:`${(f.size/1024/1024).toFixed(1)}MB`,big:f.size>10*1024*1024}))]);};
  const startEdResize=useCallback(e=>{e.preventDefault();const startY=e.clientY;const startH=editorH;const onMove=ev=>setEditorH(Math.max(150,startH+(ev.clientY-startY)));const onUp=()=>{document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);};document.addEventListener("mousemove",onMove);document.addEventListener("mouseup",onUp);},[editorH]);
  const startEdResize2=useCallback(e=>{e.preventDefault();const startY=e.clientY;const startH=editorH2;const onMove=ev=>setEditorH2(Math.max(150,startH+(ev.clientY-startY)));const onUp=()=>{document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);};document.addEventListener("mousemove",onMove);document.addEventListener("mouseup",onUp);},[editorH2]);

  // 실제 발송
  const doSend=async()=>{
    if(!subject.trim())return;
    setSending(true);setSendResult(null);
    const activeRef=activeEditor===1?editorRef:editorRef2;
    const html=activeRef.current?.innerHTML||"";
    let ok=0,fail=0;
    for(const r of allRecipientEmails.slice(0,99)){
      try{
        const body=html.replace(/\{\{name\}\}/g,r.name||"").replace(/\{\{region\}\}/g,"").replace(/\{\{city\}\}/g,"").replace(/\{\{teachingAge\}\}/g,"");
        const res=await fetch(`${API_BASE}/api/send-mail`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({from:sender,to:r.email,subject,html:body})});
        res.ok?ok++:fail++;
      }catch{fail++;}
    }
    setSending(false);setSendResult({ok,fail});
    if(fail===0)setTimeout(onClose,2000);
  };

  if(sent)return(
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000}}>
      <div style={{background:"#fff",borderRadius:16,padding:"50px 40px",textAlign:"center"}}>
        <div style={{fontSize:"3rem",marginBottom:12}}>✓</div>
        <h2 style={{fontSize:"1.3rem",fontWeight:800,color:"#16a34a"}}>발송 완료</h2>
        <p style={{fontSize:"0.95rem",color:"#111",fontWeight:700,marginTop:8}}>{totalEmails}건 개별 발송 · 타인 정보 미노출</p>
      </div>
    </div>
  );

  return(
    <div style={{position:"fixed",inset:0,zIndex:1000,pointerEvents:"none"}}>
      <div style={{position:"absolute",left:Math.max(0,pos.x),top:Math.max(0,pos.y),width:"min(1250px,96vw)",height:"min(96vh,980px)",background:"#fff",borderRadius:10,boxShadow:"0 16px 48px rgba(0,0,0,0.3)",display:"flex",flexDirection:"column",resize:"both",overflow:"hidden",minWidth:600,minHeight:400,pointerEvents:"auto",cursor:dragging?"grabbing":"auto"}} onClick={e=>e.stopPropagation()}>
        <div onMouseDown={startDrag} style={{padding:"10px 20px",borderBottom:"1px solid #e5e5e5",display:"flex",justifyContent:"space-between",alignItems:"center",background:"#fafafa",flexShrink:0,cursor:"grab",userSelect:"none"}}>
          <div style={{display:"flex",alignItems:"center",gap:12}}>
            <span style={{fontSize:"1.05rem",fontWeight:800}}>✉ 메일쓰기</span>
            <span style={{fontSize:"0.8rem",color:"#888"}}>{totalEmails}건 개별발송</span>
          </div>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            <div style={{display:"flex",flexDirection:"column",alignItems:"flex-end",gap:3}}>
              <button onClick={doSend} disabled={sending||totalEmails===0} style={{padding:"7px 24px",borderRadius:6,border:"none",background:sending?"#94a3b8":totalEmails===0?"#e5e5e5":"#03c75a",color:"#fff",fontSize:"0.9rem",fontWeight:700,cursor:sending||totalEmails===0?"not-allowed":"pointer"}}>{sending?"발송중...":"보내기"}</button>
              {sendResult&&<span style={{fontSize:"0.72rem",fontWeight:700,color:sendResult.fail>0?"#dc2626":"#16a34a"}}>✓ {sendResult.ok}건 성공{sendResult.fail>0?` / ✗ ${sendResult.fail}건 실패`:""}</span>}
            </div>
            <button onClick={onClose} style={{width:30,height:30,borderRadius:"50%",background:"#eee",border:"none",cursor:"pointer",fontSize:"0.9rem",color:"#888"}}>✕</button>
          </div>
        </div>
        <div style={{display:"flex",flex:1,overflow:"hidden"}}>
          <div style={{flex:1,display:"flex",flexDirection:"column",borderRight:"1px solid #e5e5e5",overflow:"hidden"}}>
            <div style={{padding:"12px 20px",overflowY:"auto",flex:1}}>
              <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8,paddingBottom:8,borderBottom:"1px solid #f0f0f0"}}>
                <span style={{fontSize:"0.82rem",color:"#111",fontWeight:700,minWidth:65}}>보내는사람</span>
                <select value={sender} onChange={e=>setSender(e.target.value)} style={{padding:"4px 8px",border:"1px solid #ddd",borderRadius:4,fontSize:"0.85rem",flex:1}}>
                  {SENDERS.map(s=><option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div style={{marginBottom:8,paddingBottom:8,borderBottom:"1px solid #f0f0f0"}}>
                <div style={{display:"flex",alignItems:"center",gap:8}}>
                  <span style={{fontSize:"0.82rem",color:"#111",fontWeight:700,minWidth:65}}>받는사람</span>
                  <span style={{fontSize:"0.82rem",color:"#111",fontWeight:600}}>{totalEmails}개 이메일 (개별발송)</span>
                  <button onClick={()=>setShowRecipients(!showRecipients)} style={{background:"none",border:"none",color:"#2563eb",fontSize:"0.75rem",cursor:"pointer"}}>{showRecipients?"접기":"펼치기"}</button>
                </div>
                {showRecipients&&<div style={{marginTop:6,maxHeight:200,overflowY:"auto"}}>
                  {localRecipients.map((r,ri)=><div key={ri} style={{padding:"4px 0",borderBottom:"1px solid #f5f5f5",display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
                    <span style={{fontSize:"0.8rem",fontWeight:600,minWidth:90}}>{r.name}</span>
                    <div style={{display:"flex",gap:3,flexWrap:"wrap"}}>
                      {r.emails.map((em,ei)=>{
                        const isEditing=editingEmail?.src==="init"&&editingEmail.ri===ri&&editingEmail.ei===ei;
                        return isEditing
                          ?<input key={ei} value={editEmailVal} autoFocus
                              onChange={e=>setEditEmailVal(e.target.value)}
                              onKeyDown={e=>{
                                if(e.key==="Enter"){
                                  setLocalRecipients(p=>p.map((rr,rri)=>rri===ri?{...rr,emails:rr.emails.map((ee,eei)=>eei===ei?editEmailVal:ee)}:rr));
                                  setEditingEmail(null);
                                }
                                if(e.key==="Escape")setEditingEmail(null);
                              }}
                              onBlur={()=>{
                                setLocalRecipients(p=>p.map((rr,rri)=>rri===ri?{...rr,emails:rr.emails.map((ee,eei)=>eei===ei?editEmailVal:ee)}:rr));
                                setEditingEmail(null);
                              }}
                              style={{padding:"2px 7px",border:"2px solid #2563eb",borderRadius:4,fontSize:"0.75rem",outline:"none",width:180}}/>
                          :<span key={ei} onClick={()=>{setEditingEmail({src:"init",ri,ei});setEditEmailVal(em);}} title="클릭하여 수정"
                              style={{background:"#f0f4ff",padding:"2px 7px",borderRadius:4,fontSize:"0.75rem",cursor:"pointer",border:"1px solid transparent",display:"inline-flex",alignItems:"center",gap:3}}>
                              {em}<span style={{fontSize:"0.6rem",color:"#93c5fd"}}>✎</span>
                            </span>;
                      })}
                      <button onClick={()=>{setLocalRecipients(p=>p.map((rr,rri)=>rri===ri?{...rr,emails:[...rr.emails,""]}:rr));setEditingEmail({src:"init",ri,ei:r.emails.length});setEditEmailVal("");}} style={{background:"none",border:"1px dashed #93c5fd",color:"#2563eb",fontSize:"0.68rem",cursor:"pointer",borderRadius:4,padding:"1px 6px"}}>+</button>
                    </div>
                  </div>)}
                  {extraEmails.map((em,i)=>{
                    const isEditing=editingEmail?.src==="extra"&&editingEmail.ei===i;
                    return <div key={`ex-${i}`} style={{padding:"4px 0",borderBottom:"1px solid #f5f5f5",display:"flex",alignItems:"center",gap:8}}>
                      <span style={{fontSize:"0.8rem",color:"#2563eb",fontWeight:600,minWidth:90}}>추가</span>
                      {isEditing
                        ?<input value={editEmailVal} autoFocus onChange={e=>setEditEmailVal(e.target.value)}
                            onKeyDown={e=>{if(e.key==="Enter"){setExtraEmails(p=>p.map((ee,ii)=>ii===i?editEmailVal:ee));setEditingEmail(null);}if(e.key==="Escape")setEditingEmail(null);}}
                            onBlur={()=>{setExtraEmails(p=>p.map((ee,ii)=>ii===i?editEmailVal:ee));setEditingEmail(null);}}
                            style={{padding:"2px 7px",border:"2px solid #2563eb",borderRadius:4,fontSize:"0.75rem",outline:"none",width:180}}/>
                        :<span onClick={()=>{setEditingEmail({src:"extra",ei:i});setEditEmailVal(em);}} style={{background:"#dbeafe",padding:"2px 7px",borderRadius:4,fontSize:"0.75rem",cursor:"pointer",display:"inline-flex",alignItems:"center",gap:3}}>{em}<span style={{fontSize:"0.6rem",color:"#93c5fd"}}>✎</span></span>
                      }
                      <button onClick={()=>removeExtra(i)} style={{background:"none",border:"none",color:"#999",cursor:"pointer",fontSize:"0.7rem"}}>✕</button>
                    </div>;
                  })}
                </div>}
                <div style={{display:"flex",gap:4,marginTop:6}}>
                  <input value={newEmail}
  onChange={e=>{
    const v=e.target.value;
    // 콤마·세미콜론 입력 시 즉시 분리
    if(v.includes(",")&&v.includes("@")){
      const parsed=parseEmails(v);
      if(parsed.length>0){setExtraEmails(p=>[...p,...parsed]);setNewEmail("");return;}
    }
    setNewEmail(v);
  }}
  onKeyDown={e=>{if(e.key==="Enter")addEmail();}}
  onPaste={e=>{
    e.preventDefault();
    const pasted=e.clipboardData.getData("text");
    const parsed=parseEmails(pasted);
    if(parsed.length>0){setExtraEmails(p=>[...p,...parsed]);setNewEmail("");}
    else setNewEmail(pasted.trim());
  }}
  placeholder="이메일 추가 · 콤마/붙여넣기 지원"
  style={{flex:1,padding:"4px 8px",border:"1px solid #ddd",borderRadius:4,fontSize:"0.8rem",outline:"none"}}/>
                  <button onClick={addEmail} style={{padding:"4px 12px",border:"1px solid #03c75a",borderRadius:4,background:"#fff",color:"#03c75a",fontSize:"0.78rem",fontWeight:600,cursor:"pointer"}}>추가</button>
                </div>
                <p style={{fontSize:"0.75rem",fontWeight:700,color:"#111",marginTop:4}}>각 이메일로 1:1 개별 발송 · 타인 정보 절대 미노출 · <span style={{color:"#2563eb"}}>1회 최대 99건</span></p>
              </div>
              <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8,paddingBottom:8,borderBottom:"1px solid #f0f0f0"}}>
                <span style={{fontSize:"0.82rem",color:"#111",fontWeight:700,minWidth:65}}>제목</span>
                <input value={subject} onChange={e=>setSubject(e.target.value)} style={{flex:1,padding:"6px 10px",border:"1px solid #ddd",borderRadius:4,fontSize:"0.9rem",outline:"none"}}/>
              </div>
              <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8,paddingBottom:8,borderBottom:"1px solid #f0f0f0"}}>
                <span style={{fontSize:"0.82rem",color:"#111",fontWeight:700,minWidth:65}}>파일첨부</span>
                <button onClick={()=>fileInputRef.current?.click()} style={{padding:"3px 10px",border:"1px solid #ddd",borderRadius:4,background:"#fff",fontSize:"0.78rem",cursor:"pointer"}}>내 PC</button>
                <input ref={fileInputRef} type="file" multiple style={{display:"none"}} onChange={e=>{if(e.target.files)handleFiles(e.target.files);e.target.value="";}}/>
                <div onDrop={e=>{e.preventDefault();handleFiles(e.dataTransfer.files);}} onDragOver={e=>e.preventDefault()} onClick={()=>fileInputRef.current?.click()} style={{flex:1,border:"1px dashed #93c5fd",borderRadius:4,padding:"6px 10px",fontSize:"0.78rem",color:"#aaa",minHeight:28,display:"flex",alignItems:"center",flexWrap:"wrap",gap:4,cursor:"pointer"}}>
                  {attachments.length===0&&<span style={{display:"flex",alignItems:"center",gap:5,color:"#bbb"}}><span style={{fontSize:"1rem"}}>📎</span><span>파일 첨부 (클릭 또는 드래그)</span></span>}
                  {attachments.map((a,i)=><span key={i} style={{background:a.big?"#fef3c7":"#f0f4ff",padding:"2px 8px",borderRadius:4,fontSize:"0.75rem",color:a.big?"#92400e":"#2563eb",display:"inline-flex",alignItems:"center",gap:3}}>{a.big&&<span style={{fontSize:"0.65rem",background:"#f59e0b",color:"#fff",padding:"0 4px",borderRadius:2}}>대용량</span>}{a.name} ({a.size})<button onClick={()=>setAttachments(p=>p.filter((_,idx)=>idx!==i))} style={{background:"none",border:"none",color:"#999",cursor:"pointer",padding:0,fontSize:"0.7rem"}}>✕</button></span>)}
                </div>
              </div>
              {/* 템플릿 버튼 */}
              <div style={{display:"flex",gap:3,marginBottom:8,flexWrap:"wrap"}}>
                {TEMPLATES.map(t=><button key={t.id} onClick={()=>selectTpl(t.id)} style={{padding:"3px 9px",borderRadius:4,border:tplId===t.id?"1px solid #03c75a":"1px solid #eee",background:tplId===t.id?"#e8faf0":"#fff",color:tplId===t.id?"#03c75a":"#777",fontSize:"0.72rem",fontWeight:tplId===t.id?700:400,cursor:"pointer"}}>{t.name}</button>)}
              </div>
              {/* 에디터 탭 */}
              {[1,2].map(n=>(
                <div key={n} style={{border:"1px solid #ddd",borderRadius:6,overflow:"hidden",display:"flex",flexDirection:"column",marginBottom:8}}>
                  {/* 탭 헤더 */}
                  <div style={{display:"flex",alignItems:"center",borderBottom:"1px solid #eee",background:"#f5f5f5"}}>
                    <button onClick={()=>setActiveEditor(n)} style={{padding:"5px 16px",border:"none",borderRight:"1px solid #eee",background:activeEditor===n?"#fff":"#f5f5f5",fontWeight:activeEditor===n?700:400,fontSize:"0.82rem",color:activeEditor===n?"#2563eb":"#888",cursor:"pointer",borderBottom:activeEditor===n?"2px solid #2563eb":"none"}}>에디터 {n}</button>
                    <div style={{flex:1,display:"flex",alignItems:"center",gap:2,padding:"3px 6px",flexWrap:"wrap",opacity:activeEditor===n?1:0.4,pointerEvents:activeEditor===n?"auto":"none"}}>
                      <select onChange={e=>{exec("fontName",e.target.value);e.target.value="";}} defaultValue="" style={{padding:"2px",border:"1px solid #ddd",borderRadius:3,fontSize:"0.75rem"}}><option value="" disabled>나눔고딕</option>{["나눔고딕","맑은 고딕","Arial","Georgia"].map(f=><option key={f} value={f}>{f}</option>)}</select>
                      <select onChange={e=>{exec("fontSize",e.target.value);e.target.value="";}} defaultValue="" style={{padding:"2px",border:"1px solid #ddd",borderRadius:3,fontSize:"0.75rem",width:44}}><option value="" disabled>14</option>{["1","2","3","4","5","6"].map(s=><option key={s} value={s}>{parseInt(s)*4+8}</option>)}</select>
                      <div style={{width:1,height:18,background:"#ddd",margin:"0 1px"}}/>
                      {[{c:"bold",i:"B",s:{fontWeight:800}},{c:"italic",i:"I",s:{fontStyle:"italic"}},{c:"underline",i:"U",s:{textDecoration:"underline"}},{c:"strikeThrough",i:"S",s:{textDecoration:"line-through"}}].map(b=><button key={b.c} onClick={()=>exec(b.c)} style={{width:22,height:22,border:"1px solid #ddd",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.78rem",display:"flex",alignItems:"center",justifyContent:"center",...b.s}}>{b.i}</button>)}
                      <div style={{width:1,height:18,background:"#ddd",margin:"0 1px"}}/>
                      <div style={{position:"relative"}}><button onClick={()=>{setShowFg(!showFg);setShowBg(false);}} style={{width:22,height:22,border:"1px solid #ddd",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.7rem",position:"relative"}}>A<div style={{position:"absolute",bottom:1,left:2,right:2,height:3,background:"#dc2626",borderRadius:1}}/></button>{showFg&&activeEditor===n&&<ColorPalette colors={FG} onSelect={col=>exec("foreColor",col)} onClose={()=>setShowFg(false)}/>}</div>
                      <div style={{position:"relative"}}><button onClick={()=>{setShowBg(!showBg);setShowFg(false);}} style={{width:22,height:22,border:"1px solid #ddd",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.7rem",position:"relative"}}>A<div style={{position:"absolute",bottom:1,left:2,right:2,height:3,background:"#f59e0b",borderRadius:1}}/></button>{showBg&&activeEditor===n&&<ColorPalette colors={BG} onSelect={col=>exec("hiliteColor",col)} onClose={()=>setShowBg(false)}/>}</div>
                      <div style={{width:1,height:18,background:"#ddd",margin:"0 1px"}}/>
                      <button onClick={()=>exec("insertUnorderedList")} style={{width:22,height:22,border:"1px solid #ddd",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.7rem"}}>•</button>
                      <button onClick={()=>{const u=prompt("URL:","https://");if(u)exec("createLink",u);}} style={{width:22,height:22,border:"1px solid #ddd",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.68rem"}}>🔗</button>
                    </div>
                  </div>
                  {/* 에디터 본문 */}
                  <div ref={n===1?editorRef:editorRef2} contentEditable onFocus={()=>setActiveEditor(n)} onInput={()=>{if(activeEditor===n)updatePreview();}} style={{height:n===1?editorH:editorH2,overflowY:"auto",padding:"14px 18px",fontSize:"0.9rem",lineHeight:1.8,outline:"none",fontFamily:"'Malgun Gothic',sans-serif",background:activeEditor===n?"#fff":"#fafafa"}}/>
                  <div onMouseDown={n===1?startEdResize:startEdResize2} style={{height:6,cursor:"ns-resize",background:"#f0f0f0",borderTop:"1px solid #eee",display:"flex",alignItems:"center",justifyContent:"center"}}><div style={{width:30,height:2,background:"#ccc",borderRadius:1}}/></div>
                </div>
              ))}
            </div>
          </div>
          <div style={{width:400,display:"flex",flexDirection:"column",background:"#f8f8f8",flexShrink:0}}>
            <div style={{padding:"10px 16px",borderBottom:"1px solid #e5e5e5",background:"#f0f0f0",flexShrink:0}}><span style={{fontSize:"0.88rem",fontWeight:700}}>미리보기</span>{initRecipients.length>0&&<span style={{fontSize:"0.78rem",color:"#888",marginLeft:6}}>— {initRecipients[0].name}</span>}</div>
            <div style={{flex:1,overflowY:"auto",padding:"14px"}}>
              <div style={{background:"#fff",borderRadius:6,boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                <div style={{padding:"10px 14px",borderBottom:"1px solid #eee",fontSize:"0.8rem",color:"#666"}}>
                  <p>From: {sender}</p><p>To: {allRecipientEmails[0]?.email||"—"} <span style={{color:"#16a34a",fontSize:"0.7rem"}}>(개별)</span></p>
                  <p style={{marginTop:6,fontWeight:700,color:"#111",fontSize:"0.9rem"}}>{subject.replace(/\{\{name\}\}/g,initRecipients[0]?.name||"")}</p>
                </div>
                <div style={{padding:"14px",fontSize:"0.88rem",lineHeight:1.7}} dangerouslySetInnerHTML={{__html:previewHtml}}/>
                {attachments.length>0&&<div style={{padding:"8px 14px",borderTop:"1px solid #eee",fontSize:"0.75rem",color:"#888"}}>첨부: {attachments.map(a=>a.name).join(", ")}</div>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── 워드 블록 ──────────────────────────────────────────
// rawText 붙여넣기 정규화: 백틱 제거, 줄 앞 공백/특수문자 정리, 원문 줄바꿈 유지
function normalizeRawText(text){
  // 1단계: 줄 앞 백틱·공백 제거
  const lines=text.split("\n").map(line=>line.replace(/^[\s`]+/,"").trimEnd());
  // 2단계: "Key :\n값" 패턴 → "Key : 값" 으로 병합
  const merged=[];
  let skip=false;
  for(let i=0;i<lines.length;i++){
    if(skip){skip=false;continue;}
    const cur=lines[i];
    const next=lines[i+1]??null;
    // 현재 줄이 "Something :" 으로 끝나고 (값 없음), 다음 줄이 비어있지 않으면 병합
    if(/^.+?\s*:\s*$/.test(cur)&&next!==null&&next.trim()!==""){
      merged.push(cur.trimEnd()+" "+next.trim());
      skip=true;
    } else {
      merged.push(cur);
    }
  }
  return merged.join("\n");
}

const SmallBtn=({onClick,color,children})=>(
  <button onClick={onClick} style={{padding:"2px 9px",borderRadius:4,border:`1px solid ${color||"#ccc"}`,background:"#fff",fontSize:"0.72rem",cursor:"pointer",color:color||"#555",fontWeight:600,whiteSpace:"nowrap"}}>{children}</button>
);

const DocBlock=({item,onConfirm,onUpdate,onMove,searchQ,fontInfo,fontMemo,fontBody,onMailTo})=>{
  const[editRaw,setEditRaw]=useState(false);
  const[tmpRaw,setTmpRaw]=useState(item.rawText);
  const[editMemo,setEditMemo]=useState(false);
  const[tmpMemo,setTmpMemo]=useState(item.memo||"");
  const[editInfo,setEditInfo]=useState(false);
  const[tmpInfo,setTmpInfo]=useState({name:item.name,contact:item.contact||"",email:item.email,phone:item.phone});
  const[editTags,setEditTags]=useState(true);
  const[editHeader,setEditHeader]=useState(false);
  const[tmpJNumber,setTmpJNumber]=useState(item.jNumber);
  const[tmpName,setTmpName]=useState(item.name);

  const[newTag,setNewTag]=useState("");
  const PRESET_TAGS=["방학","짧은","급여","분위기","비추천"];
  const tags=item.tags||[];
  const[collapsed,setCollapsed]=useState(false);
  const btn={padding:"4px 10px",borderRadius:5,border:"1px solid #ccc",background:"#fff",fontSize:"0.78rem",cursor:"pointer",color:"#555"};
  const isHighlighted=searchQ&&(
    item.rawText.toLowerCase().includes(searchQ.toLowerCase())||
    (item.memo||"").toLowerCase().includes(searchQ.toLowerCase())||
    item.name.toLowerCase().includes(searchQ.toLowerCase())||
    item.jNumber.toLowerCase().includes(searchQ.toLowerCase())
  );
  const isNewBlink=item.isNew&&!item.confirmed;

  // rawText: 백틱 줄 제거 후 파싱
  const lines=normalizeRawText(item.rawText).split("\n");

  return(
    <div style={{marginBottom:0,padding:"20px 24px 22px",background:isHighlighted?"#fffde7":"#fff",borderRadius:0,boxShadow:"none",borderBottom:"none",boxShadow:"none",position:"relative",borderLeft:item.blacklist?"4px solid #dc2626":isNewBlink?"4px solid #fecaca":"4px solid #e5e5e5",outline:isHighlighted?"2px solid #fbbf24":"none",outlineOffset:0,animation:isNewBlink?"newBarBlink 1s ease-in-out infinite":undefined}}>
      {item.blacklist&&<div style={{position:"absolute",inset:0,background:"rgba(220,38,38,0.05)",pointerEvents:"none"}}/>}
      {isNewBlink&&<button onClick={()=>onConfirm(item.jNumber)} style={{position:"absolute",top:10,right:10,background:"#fee2e2",color:"#dc2626",border:"1px solid #fca5a5",borderRadius:6,padding:"6px 16px",fontSize:"0.82rem",fontWeight:700,cursor:"pointer",animation:"blink 1s step-end infinite",zIndex:2}}>★ NEW — 확인</button>}

      {/* 헤더: 번호 + 지역 + 이름 + 컨트롤 버튼 */}
      <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:6}}>
        {editHeader
          ?<>
            <span style={{fontSize:"0.72rem",color:"#aaa",fontFamily:"monospace",cursor:"pointer"}} onClick={()=>setEditHeader(false)} title="번호 편집 (클릭 취소)">#{tmpJNumber}</span>
            <span style={{fontSize:"1rem",color:"#555",fontWeight:400}}>{item.region} {item.city}</span>
            <input value={tmpName} onChange={e=>setTmpName(e.target.value)} style={{fontSize:"1rem",fontWeight:600,padding:"3px 8px",border:"2px solid #2563eb",borderRadius:6,outline:"none",minWidth:160}} autoFocus onKeyDown={e=>{if(e.key==="Enter"){onUpdate(item.jNumber,{jNumber:tmpJNumber,name:tmpName,rawText:item.rawText.replace(/Job\.\s*\S+/,`Job. ${tmpJNumber}`)});setEditHeader(false);}if(e.key==="Escape")setEditHeader(false);}}/>
            <button onClick={()=>{onUpdate(item.jNumber,{jNumber:tmpJNumber,name:tmpName,rawText:item.rawText.replace(/Job\.\s*\S+/,`Job. ${tmpJNumber}`)});setEditHeader(false);}} style={{padding:"3px 10px",borderRadius:4,border:"none",background:"#2563eb",color:"#fff",fontSize:"0.78rem",fontWeight:700,cursor:"pointer"}}>저장</button>
            <button onClick={()=>setEditHeader(false)} style={{padding:"3px 8px",borderRadius:4,border:"1px solid #ccc",background:"#fff",fontSize:"0.78rem",color:"#888",cursor:"pointer"}}>취소</button>
          </>
          :<>
            <span style={{fontSize:"0.72rem",color:"#bbb",fontFamily:"monospace",userSelect:"none"}}>{item.jNumber}</span>
            <span style={{fontSize:"1rem",color:"#555",fontWeight:400}}>{item.region} {item.city}</span>
            <span onDoubleClick={()=>{setTmpJNumber(item.jNumber);setTmpName(item.name);setEditHeader(true);}} title="더블클릭으로 업체명 편집" style={{fontSize:"1rem",color:"#111",fontWeight:500,cursor:"text"}}>{item.name}</span>
          </>
        }
        {tags.map((tag,ti)=>{
          const bg=tag==="비추천"?"#fee2e2":tag==="분위기"?"#d1fae5":tag==="급여"?"#fef3c7":tag==="짧은"?"#ede9fe":"#dbeafe";
          const col=tag==="비추천"?"#dc2626":tag==="분위기"?"#16a34a":tag==="급여"?"#92400e":tag==="짧은"?"#7c3aed":"#2563eb";
          const bdr=tag==="비추천"?"#fca5a5":tag==="분위기"?"#6ee7b7":tag==="급여"?"#fcd34d":tag==="짧은"?"#c4b5fd":"#93c5fd";
          return <span key={ti} style={{display:"inline-flex",alignItems:"center",gap:2,padding:"2px 9px",borderRadius:10,fontSize:"0.7rem",fontWeight:700,background:bg,color:col,border:`1px solid ${bdr}`}}>{tag}<button onClick={()=>onUpdate(item.jNumber,{tags:tags.filter((_,i)=>i!==ti)})} style={{background:"none",border:"none",cursor:"pointer",color:col,fontSize:"0.58rem",padding:0,lineHeight:1,marginLeft:2,opacity:0.5}}>✕</button></span>;
        })}
        {item.blacklist&&<span style={{fontSize:"0.72rem",background:"#dc2626",color:"#fff",padding:"2px 10px",borderRadius:999,fontWeight:700}}>BLACKLIST</span>}
      </div>

      {/* 액션 버튼 줄 */}
      {!item.blacklist&&<div style={{display:"flex",gap:4,alignItems:"center",marginBottom:12,flexWrap:"wrap"}}>
        <button onClick={()=>onUpdate(item.jNumber,{status:"active"})} style={{...btn,border:item.status==="active"?"2px solid #16a34a":"1px solid #ccc",color:item.status==="active"?"#16a34a":"#999",fontWeight:item.status==="active"?700:400}}>● 활성</button>
        <button onClick={()=>onUpdate(item.jNumber,{status:"paused"})} style={{...btn,border:item.status==="paused"?"2px solid #f59e0b":"1px solid #ccc",color:item.status==="paused"?"#b45309":"#999",fontWeight:item.status==="paused"?700:400}}>○ 비활성</button>
        <div style={{width:1,height:18,background:"#ddd"}}/>
        <button onClick={()=>onMove(item.jNumber,"top")} style={{...btn,fontWeight:600}}>⤒ 맨위로</button>
        <button onClick={()=>onMove(item.jNumber,"up")} style={btn}>↑</button>
        <button onClick={()=>onMove(item.jNumber,"down")} style={btn}>↓</button>
        <div style={{width:1,height:18,background:"#ddd"}}/>
        <button onClick={()=>setCollapsed(!collapsed)} style={{...btn,color:"#666"}}>{collapsed?"▼ 펼치기":"▲ 접기"}</button>
        <div style={{width:1,height:18,background:"#ddd"}}/>

        {editTags
          ?<>{PRESET_TAGS.filter(p=>!tags.includes(p)).map(p=>(
              <button key={p} onClick={()=>onUpdate(item.jNumber,{tags:[...tags,p]})} style={{padding:"2px 8px",borderRadius:12,fontSize:"0.72rem",fontWeight:600,background:p==="비추천"?"#fee2e2":"#f5f5f5",border:p==="비추천"?"1px dashed #fca5a5":"1px dashed #ccc",cursor:"pointer",color:p==="비추천"?"#dc2626":"#777"}}>+{p}</button>
            ))}
            <input value={newTag} onChange={e=>setNewTag(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&newTag.trim()){onUpdate(item.jNumber,{tags:[...tags,newTag.trim()]});setNewTag("");}}} placeholder="직접입력" style={{padding:"2px 6px",border:"1px solid #93c5fd",borderRadius:8,fontSize:"0.72rem",outline:"none",width:56}}/>
            <button onClick={()=>setEditTags(false)} style={{...btn,fontSize:"0.68rem",color:"#bbb",padding:"2px 6px"}}>접기</button>
          </>
          :<button onClick={()=>setEditTags(true)} style={{padding:"2px 8px",borderRadius:12,fontSize:"0.72rem",fontWeight:600,background:"#f8f8f8",border:"1px dashed #bbb",cursor:"pointer",color:"#999"}}>＋태그</button>
        }
        {/* 비추천 태그 있으면 블랙리스트 이동 버튼 노출 */}
        {tags.includes("비추천")&&<button onClick={()=>onUpdate(item.jNumber,{blacklist:true,active:false,status:"blacklist"})} style={{marginLeft:"auto",padding:"3px 12px",borderRadius:5,border:"1px solid #dc2626",background:"#fee2e2",color:"#dc2626",fontSize:"0.75rem",fontWeight:700,cursor:"pointer"}}>🚫 블랙리스트 이동</button>}
      </div>}

      {!collapsed&&<>
        {/* ① INFO 박스 — MEMO 위 */}
        <div style={{background:"#f8faff",border:"1px solid #dce8ff",borderRadius:6,padding:"10px 14px",marginBottom:10,position:"relative"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}>
            <span style={{fontSize:"0.72rem",fontWeight:700,color:"#2563eb",letterSpacing:"0.08em"}}>INFO</span>
            {!editInfo
              ?<SmallBtn onClick={()=>{setTmpInfo({name:item.name,contact:item.contact||"",email:item.email,phone:item.phone});setEditInfo(true);}} color="#2563eb">✏ 수정</SmallBtn>
              :<div style={{display:"flex",gap:4}}>
                <SmallBtn onClick={()=>{onUpdate(item.jNumber,{name:tmpInfo.name,contact:tmpInfo.contact,email:tmpInfo.email,phone:tmpInfo.phone,emails:[tmpInfo.email]});setTmpName(tmpInfo.name);setEditInfo(false);}} color="#16a34a">저장</SmallBtn>
                <SmallBtn onClick={()=>setEditInfo(false)}>취소</SmallBtn>
              </div>
            }
          </div>
          {editInfo
            ?<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"6px 16px"}}>
              {[["업체명","name"],["담당자","contact"],["이메일","email"],["전화","phone"]].map(([lbl,k])=>(
                <div key={k} style={{display:"flex",gap:6,alignItems:"center"}}>
                  <span style={{color:"#555",fontWeight:600,minWidth:46,fontSize:"0.8rem"}}>{lbl}</span>
                  <input value={tmpInfo[k]} onChange={e=>setTmpInfo(p=>({...p,[k]:e.target.value}))} style={{flex:1,padding:"3px 6px",border:"1px solid #93c5fd",borderRadius:4,fontSize:"0.82rem",outline:"none"}}/>
                </div>
              ))}
            </div>
            :<div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"3px 24px"}}>
              {item.name&&<div style={{display:"flex",gap:8}}><span style={{color:"#555",fontWeight:600,minWidth:46,fontSize:`${fontInfo}px`}}>업체명</span><span style={{fontSize:`${fontInfo}px`}}>{item.name}</span></div>}
              {item.email&&<div style={{display:"flex",gap:8}}><span style={{color:"#555",fontWeight:600,minWidth:46,fontSize:`${fontInfo}px`}}>이메일</span><span onClick={()=>onMailTo&&onMailTo(item)} style={{fontSize:`${fontInfo}px`,color:"#2563eb",cursor:"pointer",textDecoration:"underline",textUnderlineOffset:2}}>{item.email}</span></div>}
              {item.contact&&<div style={{display:"flex",gap:8}}><span style={{color:"#555",fontWeight:600,minWidth:46,fontSize:`${fontInfo}px`}}>담당자</span><span style={{fontSize:`${fontInfo}px`}}>{item.contact}</span></div>}
              {item.phone&&<div style={{display:"flex",gap:8}}><span style={{color:"#555",fontWeight:600,minWidth:46,fontSize:`${fontInfo}px`}}>전화</span><span style={{fontSize:`${fontInfo}px`}}>{item.phone}</span></div>}
            </div>
          }
        </div>

        {/* ② MEMO 박스 */}
        <div style={{background:"#fffde7",border:"1px solid #f0e68c",borderRadius:5,padding:"10px 14px",marginBottom:12,position:"relative"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:editMemo?6:item.memo?4:0}}>
            <span style={{fontWeight:700,color:"#b8860b",fontSize:"0.72rem",letterSpacing:"0.06em"}}>MEMO</span>
            {!editMemo
              ?<SmallBtn onClick={()=>{setTmpMemo(item.memo||"");setEditMemo(true);}} color="#b45309">✏ 수정</SmallBtn>
              :<div style={{display:"flex",gap:4}}>
                <SmallBtn onClick={()=>{onUpdate(item.jNumber,{memo:tmpMemo});setEditMemo(false);}} color="#f59e0b">저장</SmallBtn>
                <SmallBtn onClick={()=>setEditMemo(false)}>취소</SmallBtn>
              </div>
            }
          </div>
          {editMemo
            ?<textarea value={tmpMemo} onChange={e=>setTmpMemo(e.target.value)} rows={3} style={{width:"100%",padding:"6px 8px",borderRadius:4,border:"1px solid #f59e0b",fontSize:"0.88rem",lineHeight:1.6,background:"#fffef5",resize:"vertical",fontFamily:"inherit",outline:"none"}}/>
            :<span style={{fontSize:`${fontMemo}px`,lineHeight:1.6,color:"#111"}}>{item.memo||<span style={{color:"#ccc",fontStyle:"italic"}}>없음</span>}</span>
          }
        </div>

        {/* ③ 본문 (rawText) — 우측 상단에 수정 버튼 */}
        <div style={{borderTop:"2px solid #e0e0e0",paddingTop:14,position:"relative"}}>
          <div style={{position:"absolute",top:14,right:0,display:"flex",gap:6,alignItems:"center"}}>

            {!editRaw
              ?<SmallBtn onClick={()=>{setTmpRaw(item.rawText);setEditRaw(true);}} color="#2563eb">✏ 본문수정</SmallBtn>
              :<>
                <SmallBtn onClick={()=>{onUpdate(item.jNumber,{rawText:normalizeRawText(tmpRaw)});setEditRaw(false);}} color="#16a34a">저장</SmallBtn>
                <SmallBtn onClick={()=>setEditRaw(false)}>취소</SmallBtn>
              </>
            }
          </div>
          {editRaw
            ?<textarea
                value={tmpRaw}
                onChange={e=>setTmpRaw(e.target.value)}
                onPaste={e=>{
                  e.preventDefault();
                  const pasted=e.clipboardData.getData("text");
                  const normalized=normalizeRawText(pasted);
                  const ta=e.target;
                  const start=ta.selectionStart;
                  const end=ta.selectionEnd;
                  const newVal=tmpRaw.slice(0,start)+normalized+tmpRaw.slice(end);
                  setTmpRaw(newVal);
                }}
                rows={Math.max(8,tmpRaw.split("\n").length+2)}
                style={{width:"100%",padding:"10px 12px",borderRadius:5,border:"2px solid #2563eb",fontSize:"0.88rem",lineHeight:1.7,fontFamily:"'Consolas',monospace",resize:"vertical",outline:"none",marginTop:4}}
              />
            :<div style={{fontSize:`${fontBody}px`,lineHeight:1.9,color:"#111",paddingRight:130}}>
              {(()=>{
                const merged=[];
                let skip=false;
                for(let i=0;i<lines.length;i++){
                  if(skip){skip=false;continue;}
                  const t=lines[i].trim();
                  if(!t){merged.push({type:"empty",key:i});continue;}
                  const kvFull=t.match(/^(.+?)\s*:\s*(.+)$/);
                  if(kvFull){merged.push({type:"kv",key:i,k:kvFull[1],v:kvFull[2]});continue;}
                  const kvEmpty=t.match(/^(.+?)\s*:\s*$/);
                  if(kvEmpty&&i+1<lines.length){
                    const nextT=lines[i+1].trim();
                    if(nextT){merged.push({type:"kv",key:i,k:kvEmpty[1],v:nextT});skip=true;continue;}
                  }
                  merged.push({type:"text",key:i,v:t});
                }
                return merged.map(row=>{
                  if(row.type==="empty")return <div key={row.key} style={{height:4}}/>;
                  if(row.type==="kv")return(
                    <div key={row.key} style={{display:"flex",gap:6,marginBottom:2}}>
                      <span style={{color:"#444",fontWeight:700,minWidth:280,flexShrink:0,fontSize:`${fontBody}px`}}>{row.k} :</span>
                      <span style={{fontWeight:400,color:"#111",fontSize:`${fontBody}px`}}>{row.v}</span>
                    </div>
                  );
                  return <div key={row.key} style={{color:"#111",fontSize:`${fontBody}px`,marginBottom:2,paddingLeft:2}}>{row.v}</div>;
                });
              })()}
            </div>
          }
        </div>
      </>}
    </div>
  );
};

// ─── 열관리 팝업 ────────────────────────────────────────

// ─── 엑셀뷰 ─────────────────────────────────────────────
const EXCEL_COLS_DEF=[
  {key:"rowNum",label:"",w:44,fixed:true},
  {key:"sel",label:"",w:32,fixed:true},
  {key:"jNumber",label:"번호",w:64},
  {key:"region",label:"지역",w:72},
  {key:"city",label:"도시",w:84},
  {key:"name",label:"업체명",w:150},
  {key:"teachingAge",label:"연령대",w:124},
  {key:"email",label:"이메일",w:210},
  {key:"phone",label:"연락처",w:134},
  {key:"salary",label:"급여",w:114},
  {key:"status",label:"상태",w:84},
  {key:"memo",label:"메모",w:270},
];
const COL_LETTERS="ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const getColLetter=(ci)=>ci<26?COL_LETTERS[ci]:COL_LETTERS[Math.floor(ci/26)-1]+COL_LETTERS[ci%26];

const XCell=({value,onChange,multiline,style:st,selected,onSelect})=>{
  const[edit,setEdit]=useState(false);
  const[v,setV]=useState(value);
  const ref=useRef(null);
  useEffect(()=>setV(value),[value]);
  useEffect(()=>{if(edit&&ref.current){ref.current.focus();if(ref.current.select)ref.current.select();}},[edit]);
  if(edit){
    const commit=()=>{onChange(v);setEdit(false);};
    if(multiline)return <textarea ref={ref} value={v} onChange={e=>setV(e.target.value)} onBlur={commit} onKeyDown={e=>{if(e.key==="Escape"){setV(value);setEdit(false);}}} rows={3} style={{width:"100%",padding:"3px 5px",border:"2px solid #2563eb",borderRadius:0,fontSize:"0.8rem",outline:"none",resize:"vertical",fontFamily:"inherit",lineHeight:1.5,...st}}/>;
    return <input ref={ref} value={v} onChange={e=>setV(e.target.value)} onBlur={commit} onKeyDown={e=>{if(e.key==="Enter")commit();if(e.key==="Escape"){setV(value);setEdit(false);}}} style={{width:"100%",padding:"3px 5px",border:"2px solid #2563eb",borderRadius:0,fontSize:"0.8rem",outline:"none",...st}}/>;
  }
  return(
    <div
      onClick={onSelect}
      onDoubleClick={()=>{onSelect&&onSelect();setEdit(true);}}
      style={{minHeight:22,padding:"3px 5px",cursor:"default",lineHeight:1.5,
        overflow:"hidden",whiteSpace:"nowrap",textOverflow:"ellipsis",
        outline:selected?"2px solid #2563eb":"none",outlineOffset:-2,
        background:selected?"#e8f0fe":"transparent",...st}}>
      {value||""}
    </div>
  );
};

const ExcelView=({data,onUpdate,onAddRow,onDelRows,onMoveRow,checked,setChecked,searchQ,filtered,confirm:confirmNew,onMailTo,exFl,setExFl})=>{
  const[cols,setCols]=useState(EXCEL_COLS_DEF.map(c=>({...c})));
  const[sortKey,setSortKey]=useState(null);
  const[sortDir,setSortDir]=useState("asc");
  const[showColMgr,setShowColMgr]=useState(false);
  const[resizing,setResizing]=useState(null);
  const[rowHeights,setRowHeights]=useState({}); // key:ri → height px
  const[resizingRow,setResizingRow]=useState(null);
  const savedColWidths=useRef({});
  const savedRowHeights=useRef({});
  const[selCell,setSelCell]=useState(null); // {ri,ci}
  const[selCol,setSelCol]=useState(null);   // ci (열 전체 선택)
  const[selRow,setSelRow]=useState(null);   // ri (행 전체 선택)
  const[zoom,setZoom]=useState(100);
  const[fontSize,setFontSize]=useState(13);
  const[bold,setBold]=useState(false);
  const[fontColor,setFontColor]=useState("#111111");
  const[bgColor,setBgColor]=useState("#ffffff");
  const[cellStyles,setCellStyles]=useState({}); // key:"ri-ci" → {bold,color,bg,fontSize}
  const[history,setHistory]=useState([]);
  const[future,setFuture]=useState([]);
  const[showFgPicker,setShowFgPicker]=useState(false);
  const[showBgPicker,setShowBgPicker]=useState(false);
  const tbodyRef=useRef(null);
  const allChecked=filtered.length>0&&filtered.every(d=>checked.has(d.jNumber));

  const FG_COLORS=["#111111","#555555","#888888","#dc2626","#ea580c","#f59e0b","#16a34a","#2563eb","#7c3aed","#db2777","#ffffff","#cccccc"];
  const BG_COLORS=["#ffffff","#fef9c3","#dbeafe","#dcfce7","#fce7f3","#ede9fe","#fee2e2","#fff7ed","#f0fdf4","#e0f2fe","#f5f5f5","#111111"];

  const pushHistory=useCallback((snap)=>{setHistory(h=>[...h.slice(-49),snap]);setFuture([]);},[]);
  const undo=()=>{if(!history.length)return;const prev=history[history.length-1];setFuture(f=>[...f,{/*current*/}]);setHistory(h=>h.slice(0,-1));};
  const redo=()=>{if(!future.length)return;};

  const toggleSort=key=>{if(sortKey===key)setSortDir(d=>d==="asc"?"desc":"asc");else{setSortKey(key);setSortDir("asc");}};

  const startResize=useCallback((ci,e)=>{
    e.preventDefault();e.stopPropagation();
    const sx=e.clientX,sw=cols[ci].w;
    const onMove=ev=>setCols(p=>{const n=[...p];n[ci]={...n[ci],w:Math.max(32,sw+(ev.clientX-sx))};return n;});
    const onUp=()=>{
      document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);
      setResizing(null);
      setCols(p=>{p.forEach(col=>savedColWidths.current[col.key]=col.w);return p;});
    };
    document.addEventListener("mousemove",onMove);document.addEventListener("mouseup",onUp);setResizing(ci);
  },[cols]);

  // 행 높이 드래그
  const startRowResize=useCallback((ri,e)=>{
    e.preventDefault();e.stopPropagation();
    const sy=e.clientY,sh=rowHeights[ri]||32;
    const onMove=ev=>{const nh=Math.max(22,sh+(ev.clientY-sy));setRowHeights(p=>({...p,[ri]:nh}));};
    const onUp=()=>{
      document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);
      setResizingRow(null);
      setRowHeights(p=>{savedRowHeights.current={...p};return p;});
    };
    document.addEventListener("mousemove",onMove);document.addEventListener("mouseup",onUp);setResizingRow(ri);
  },[rowHeights]);

  const visRows=useMemo(()=>{
    let r=[...filtered];
    // exFl 필터 적용
    ["region","city","teachingAge","status"].forEach(key=>{
      if(exFl[key]?.length>0)r=r.filter(d=>exFl[key].includes(d[key]));
    });
    if(sortKey){r.sort((a,b)=>{const av=a[sortKey]||"",bv=b[sortKey]||"";return sortDir==="asc"?av.localeCompare(bv,undefined,{numeric:true}):bv.localeCompare(av,undefined,{numeric:true});});}
    return r;
  },[filtered,sortKey,sortDir,exFl]);

  const totalW=cols.reduce((a,c)=>a+c.w,0)+44; // +44 for row number col

  const STATUS_OPTS=["active","paused","new","blacklist"];
  const STATUS_LABEL={"active":"Active","paused":"Paused","new":"New","blacklist":"BLOCK"};
  const STATUS_COLOR={"active":"#16a34a","paused":"#f59e0b","new":"#2563eb","blacklist":"#dc2626"};

  const getCellStyle=(ri,ci)=>cellStyles[`${ri}-${ci}`]||{};
  const setCellStyle=(ri,ci,patch)=>{
    const key=`${ri}-${ci}`;
    setCellStyles(p=>({...p,[key]:{...p[key],...patch}}));
  };

  const applyStyleToSel=(patch)=>{
    if(selCell)setCellStyle(selCell.ri,selCell.ci,patch);
    else if(selRow!==null){cols.forEach((_,ci)=>setCellStyle(selRow,ci,patch));}
    else if(selCol!==null){visRows.forEach((_,ri)=>setCellStyle(ri,selCol,patch));}
  };

  // 데이터 열 (rowNum, sel 제외)
  const dataCols=cols.filter(c=>c.key!=="rowNum"&&c.key!=="sel");
  const dataColStartIdx=2; // rowNum=0, sel=1, data starts at 2

  const TB={padding:"3px 7px",border:"1px solid #ddd",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.78rem",height:26,display:"flex",alignItems:"center",justifyContent:"center"};
  const TBS={...TB,minWidth:26};

  return(
    <div style={{display:"flex",flexDirection:"column",height:"100%",userSelect:resizing!==null?"none":"auto",fontSize:`${fontSize}px`}}>

      {/* ── 툴바 ── */}
      <div style={{background:"#f8f8f8",borderBottom:"1px solid #ddd",flexShrink:0}}>
        {/* 1행: 실행 도구 */}
        <div style={{display:"flex",gap:4,alignItems:"center",padding:"4px 8px",borderBottom:"1px solid #eee",flexWrap:"wrap"}}>
          {/* 되돌리기/다시실행 */}
          <button onClick={undo} title="되돌리기 (Ctrl+Z)" style={{...TBS,color:history.length?"#111":"#ccc"}}>↩</button>
          <button onClick={redo} title="다시실행 (Ctrl+Y)" style={{...TBS,color:future.length?"#111":"#ccc"}}>↪</button>
          <div style={{width:1,height:20,background:"#ddd",margin:"0 2px"}}/>

          {/* 확대/축소 */}
          <button onClick={()=>setZoom(z=>Math.max(50,z-10))} style={TBS}>−</button>
          <span style={{fontSize:"0.75rem",minWidth:36,textAlign:"center",color:"#555"}}>{zoom}%</span>
          <button onClick={()=>setZoom(z=>Math.min(200,z+10))} style={TBS}>+</button>
          <button onClick={()=>setZoom(100)} style={{...TB,fontSize:"0.7rem",padding:"2px 6px",color:"#888"}}>초기화</button>
          <div style={{width:1,height:20,background:"#ddd",margin:"0 2px"}}/>

          {/* 행/열 추가삭제 */}
          <button onClick={onAddRow} style={{...TB,border:"1px solid #2563eb",color:"#2563eb",background:"#eff6ff",padding:"3px 10px"}}>+ 행 추가</button>
          <button onClick={()=>{if(checked.size===0)return;if(window.confirm(`${checked.size}건 삭제?`))onDelRows([...checked]);}} disabled={checked.size===0} style={{...TB,border:"1px solid #dc2626",color:checked.size>0?"#dc2626":"#ccc",background:checked.size>0?"#fef2f2":"#fff",padding:"3px 10px"}}>🗑 {checked.size>0&&`(${checked.size})`}</button>
          <div style={{width:1,height:20,background:"#ddd",margin:"0 2px"}}/>

          {/* 이동 */}
          <button onClick={()=>{const s=[...checked];if(s.length===1)onMoveRow(s[0],"top");}} disabled={checked.size!==1} title="맨위로" style={{...TBS,color:checked.size===1?"#444":"#ccc"}}>⤒</button>
          <button onClick={()=>{const s=[...checked];if(s.length===1)onMoveRow(s[0],"up");}} disabled={checked.size!==1} title="위로" style={{...TBS,color:checked.size===1?"#444":"#ccc"}}>↑</button>
          <button onClick={()=>{const s=[...checked];if(s.length===1)onMoveRow(s[0],"down");}} disabled={checked.size!==1} title="아래로" style={{...TBS,color:checked.size===1?"#444":"#ccc"}}>↓</button>
          <div style={{width:1,height:20,background:"#ddd",margin:"0 2px"}}/>

          <button onClick={()=>setShowColMgr(true)} style={{...TB,padding:"3px 10px"}}>열 관리</button>
          <span style={{marginLeft:"auto",fontSize:"0.72rem",color:"#888"}}>{filtered.length}행{checked.size>0&&<span style={{color:"#2563eb",fontWeight:700}}> · {checked.size}선택</span>}</span>
        </div>

        {/* 2행: 서식 도구 */}
        <div style={{display:"flex",gap:3,alignItems:"center",padding:"3px 8px",flexWrap:"wrap"}}>
          {/* 글꼴 */}
          <select onChange={e=>applyStyleToSel({fontFamily:e.target.value})} defaultValue="default" style={{...TB,width:110,fontSize:"0.75rem"}}>
            <option value="default">기본 글꼴</option>
            {["나눔고딕","맑은 고딕","Arial","Georgia","Courier New","Times New Roman"].map(f=><option key={f} value={f}>{f}</option>)}
          </select>

          {/* 글자 크기 */}
          <select value={fontSize} onChange={e=>setFontSize(Number(e.target.value))} style={{...TB,width:52,fontSize:"0.75rem"}}>
            {[9,10,11,12,13,14,16,18,20,24,28,32].map(n=><option key={n} value={n}>{n}</option>)}
          </select>

          <div style={{width:1,height:20,background:"#ddd",margin:"0 1px"}}/>

          {/* 굵게/기울임/밑줄/취소선 */}
          {[
            {label:"B",title:"굵게",style:{fontWeight:800},action:()=>applyStyleToSel({bold:!bold})},
            {label:"I",title:"기울임",style:{fontStyle:"italic"},action:()=>applyStyleToSel({italic:true})},
            {label:"U",title:"밑줄",style:{textDecoration:"underline"},action:()=>applyStyleToSel({underline:true})},
            {label:"S",title:"취소선",style:{textDecoration:"line-through"},action:()=>applyStyleToSel({strike:true})},
          ].map(b=>(
            <button key={b.label} onClick={b.action} title={b.title} style={{...TBS,...b.style}}>{b.label}</button>
          ))}

          <div style={{width:1,height:20,background:"#ddd",margin:"0 1px"}}/>

          {/* 글자색 */}
          <div style={{position:"relative"}}>
            <button onClick={()=>{setShowFgPicker(v=>!v);setShowBgPicker(false);}} title="글자색" style={{...TBS,position:"relative",overflow:"hidden"}}>
              <span style={{fontWeight:800,color:fontColor}}>A</span>
              <div style={{position:"absolute",bottom:2,left:4,right:4,height:3,background:fontColor,borderRadius:1}}/>
            </button>
            {showFgPicker&&(
              <div style={{position:"absolute",top:"calc(100% + 4px)",left:0,zIndex:300,background:"#fff",border:"1px solid #ddd",borderRadius:6,padding:6,boxShadow:"0 4px 16px rgba(0,0,0,0.15)",display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:3,width:132}}>
                {FG_COLORS.map(col=>(
                  <div key={col} onClick={()=>{setFontColor(col);applyStyleToSel({color:col});setShowFgPicker(false);}}
                    style={{width:18,height:18,background:col,borderRadius:3,cursor:"pointer",border:col==="#ffffff"?"1px solid #ddd":"none"}}/>
                ))}
                <input type="color" value={fontColor} onChange={e=>{setFontColor(e.target.value);applyStyleToSel({color:e.target.value});}} style={{width:18,height:18,border:"none",padding:0,cursor:"pointer",borderRadius:3}}/>
              </div>
            )}
          </div>

          {/* 배경색 */}
          <div style={{position:"relative"}}>
            <button onClick={()=>{setShowBgPicker(v=>!v);setShowFgPicker(false);}} title="배경색" style={{...TBS,position:"relative",overflow:"hidden"}}>
              <span style={{fontSize:"0.72rem"}}>A</span>
              <div style={{position:"absolute",bottom:2,left:4,right:4,height:3,background:bgColor==="#ffffff"?"#f59e0b":bgColor,borderRadius:1}}/>
            </button>
            {showBgPicker&&(
              <div style={{position:"absolute",top:"calc(100% + 4px)",left:0,zIndex:300,background:"#fff",border:"1px solid #ddd",borderRadius:6,padding:6,boxShadow:"0 4px 16px rgba(0,0,0,0.15)",display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:3,width:132}}>
                {BG_COLORS.map(col=>(
                  <div key={col} onClick={()=>{setBgColor(col);applyStyleToSel({bg:col});setShowBgPicker(false);}}
                    style={{width:18,height:18,background:col,borderRadius:3,cursor:"pointer",border:"1px solid #ddd"}}/>
                ))}
                <input type="color" value={bgColor} onChange={e=>{setBgColor(e.target.value);applyStyleToSel({bg:e.target.value});}} style={{width:18,height:18,border:"none",padding:0,cursor:"pointer",borderRadius:3}}/>
              </div>
            )}
          </div>

          <div style={{width:1,height:20,background:"#ddd",margin:"0 1px"}}/>

          {/* 정렬 */}
          {[{t:"◀",v:"left"},{t:"■",v:"center"},{t:"▶",v:"right"}].map(a=>(
            <button key={a.v} onClick={()=>applyStyleToSel({align:a.v})} title={a.v} style={{...TBS,fontSize:"0.6rem"}}>{a.t}</button>
          ))}

          <div style={{width:1,height:20,background:"#ddd",margin:"0 1px"}}/>

          {/* 서식 지우기 */}
          <button onClick={()=>{if(selCell)setCellStyles(p=>{const n={...p};delete n[`${selCell.ri}-${selCell.ci}`];return n;});}} title="서식 지우기" style={{...TB,padding:"3px 8px",fontSize:"0.7rem",color:"#888"}}>↺ 서식초기화</button>
        </div>
      </div>

      {/* ── 테이블 ── */}
      <div style={{flex:1,overflow:"auto",position:"relative",transform:`scale(${zoom/100})`,transformOrigin:"top left",width:`${10000/zoom}%`,height:`${10000/zoom}%`}}>
        <table style={{borderCollapse:"collapse",tableLayout:"fixed",width:totalW+44,minWidth:"100%",fontSize:`${fontSize}px`}}>
          <thead>
            {/* 알파벳 열 헤더 */}
            <tr style={{background:"#f0f0f0",position:"sticky",top:0,zIndex:30}}>
              {/* 행번호 고정셀 */}
              <th style={{width:44,minWidth:44,background:"#e8e8e8",border:"1px solid #c8c8c8",position:"sticky",top:0,left:0,zIndex:40}}/>
              {/* 체크박스 열 */}
              <th style={{width:32,minWidth:32,background:"#e8e8e8",border:"1px solid #c8c8c8",padding:"4px",position:"sticky",top:0,zIndex:30,textAlign:"center"}}>
                <input type="checkbox" checked={allChecked} onChange={e=>{if(e.target.checked)setChecked(new Set(filtered.map(d=>d.jNumber)));else setChecked(new Set());}} style={{accentColor:"#2563eb",cursor:"pointer"}}/>
              </th>
              {/* 데이터 열 — A B C ... */}
              {dataCols.map((col,dci)=>{
                const ci=dci+dataColStartIdx;
                const isSelCol=selCol===ci;
                return(
                  <th key={col.key}
                    onClick={()=>{setSelCol(isSelCol?null:ci);setSelRow(null);setSelCell(null);}}
                    style={{width:col.w,minWidth:col.w,padding:"4px 5px",textAlign:"center",fontWeight:700,
                      fontSize:"0.72rem",border:"1px solid #c8c8c8",whiteSpace:"nowrap",
                      position:"sticky",top:0,background:isSelCol?"#c8d8ff":"#e8e8e8",zIndex:20,
                      overflow:"hidden",userSelect:"none",cursor:"pointer",
                      color:isSelCol?"#2563eb":"#555"}}>
                    {getColLetter(dci)}
                    {sortKey===col.key&&<span style={{marginLeft:2,fontSize:"0.55rem"}}>{sortDir==="asc"?"▲":"▼"}</span>}
                    <div onMouseDown={e=>startResize(ci,e)} style={{position:"absolute",right:0,top:0,bottom:0,width:4,cursor:"col-resize",background:resizing===ci?"#2563eb":"transparent"}}/>
                  </th>
                );
              })}
            </tr>
            {/* 실제 컬럼명 행 */}
            <tr style={{background:"#f5f5f5",position:"sticky",top:28,zIndex:20}}>
              <th style={{width:44,background:"#f0f0f0",border:"1px solid #ddd",fontSize:"0.65rem",color:"#aaa",textAlign:"center",position:"sticky",left:0,zIndex:25}}>행</th>
              <th style={{width:32,background:"#f0f0f0",border:"1px solid #ddd"}}/>
              {dataCols.map((col,dci)=>{
                const ci=dci+dataColStartIdx;
                return(
                  <th key={col.key}
                    onClick={()=>toggleSort(col.key)}
                    style={{width:col.w,padding:"4px 6px",textAlign:"left",fontWeight:700,
                      fontSize:"0.73rem",border:"1px solid #ddd",whiteSpace:"nowrap",
                      background:"#f5f5f5",color:"#333",cursor:"pointer",userSelect:"none"}}>
                    {col.label}
                    {sortKey===col.key&&<span style={{marginLeft:2,fontSize:"0.6rem"}}>{sortDir==="asc"?"▲":"▼"}</span>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody ref={tbodyRef}>
            {visRows.map((item,ri)=>{
              const isNew=item.isNew&&!item.confirmed;
              const isBL=item.blacklist;
              const isChk=checked.has(item.jNumber);
              const isHl=searchQ&&(item.rawText?.toLowerCase().includes(searchQ.toLowerCase())||item.name?.toLowerCase().includes(searchQ.toLowerCase())||item.jNumber?.toLowerCase().includes(searchQ.toLowerCase()));
              const isSelRow=selRow===ri;
              const rowBg=isBL?"rgba(220,38,38,0.05)":isSelRow?"#dbeafe":isChk?"#fef9c3":isHl?"#fffde7":"#fff";
              return(
                <tr key={item.jNumber} style={{background:rowBg,height:rowHeights[ri]||32,maxHeight:rowHeights[ri]||32,overflow:"hidden"}}>
                  {/* 행 번호 + 높이 조절 핸들 */}
                  <td onClick={()=>{setSelRow(isSelRow?null:ri);setSelCol(null);setSelCell(null);}}
                    style={{width:44,padding:"2px 4px",textAlign:"center",fontWeight:600,fontSize:"0.72rem",
                      color:isSelRow?"#2563eb":"#999",background:isSelRow?"#bfdbfe":"#f5f5f5",
                      border:"1px solid #ddd",cursor:"pointer",userSelect:"none",position:"sticky",left:0,zIndex:5,
                      overflow:"hidden",height:rowHeights[ri]||32,maxHeight:rowHeights[ri]||32,position:"relative"}}>
                    {item.jNumber||ri+1}
                    <div onMouseDown={e=>startRowResize(ri,e)}
                      style={{position:"absolute",bottom:0,left:0,right:0,height:4,cursor:"row-resize",
                        background:resizingRow===ri?"#2563eb":"transparent",zIndex:10}}/>
                  </td>
                  {/* 체크박스 */}
                  <td style={{width:32,padding:"3px 4px",textAlign:"center",border:"1px solid #e8e8e8",background:rowBg}}>
                    <input type="checkbox" checked={isChk} onChange={e=>{const s=new Set(checked);e.target.checked?s.add(item.jNumber):s.delete(item.jNumber);setChecked(s);}} style={{accentColor:"#2563eb",cursor:"pointer"}}/>
                  </td>
                  {/* 데이터 셀 */}
                  {dataCols.map((col,dci)=>{
                    const ci=dci+dataColStartIdx;
                    const isSel=selCell?.ri===ri&&selCell?.ci===ci;
                    const isColSel=selCol===ci;
                    const cs=getCellStyle(ri,ci);
                    const cellBg=cs.bg&&cs.bg!=="#ffffff"?cs.bg:isColSel?"#e8f0fe":rowBg;

                    if(col.key==="jNumber")return(
                      <td key="jNumber" style={{padding:0,border:"1px solid #e8e8e8",background:cellBg}}>
                        <XCell value={item.jNumber} onChange={v=>onUpdate(item.jNumber,{jNumber:v,rawText:(item.rawText||"").replace(/Job\.\s*\S+/,`Job. ${v}`)})}
                          selected={isSel} onSelect={()=>{setSelCell({ri,ci});setSelRow(null);setSelCol(null);}}
                          style={{fontFamily:"monospace",fontWeight:"600",color:cs.color||"#888",fontSize:`${Math.max(10,fontSize-2)}px`,textAlign:"center"}}/>
                      </td>
                    );
                    if(col.key==="email")return(
                      <td key="email" style={{padding:"2px 4px",border:"1px solid #e8e8e8",background:cellBg}}>
                        <div style={{display:"flex",flexDirection:"column",gap:1}}>
                          {(item.emails||[item.email]).map((em,j)=>(
                            <div key={j} style={{display:"flex",alignItems:"center",gap:2}}>
                              <XCell value={em} onChange={v=>{const ne=[...(item.emails||[item.email])];ne[j]=v;onUpdate(item.jNumber,{emails:ne,email:ne[0]});}}
                                selected={isSel} onSelect={()=>{setSelCell({ri,ci});setSelRow(null);setSelCol(null);}}
                                style={{fontSize:`${Math.max(10,fontSize-1)}px`,color:cs.color||"#2563eb",flex:1}}/>
                              <button onClick={()=>onMailTo&&onMailTo(item)} title="메일 보내기" style={{padding:"1px 5px",border:"1px solid #93c5fd",borderRadius:3,background:"#eff6ff",cursor:"pointer",fontSize:"0.65rem",color:"#2563eb",whiteSpace:"nowrap"}}>✉</button>
                            </div>
                          ))}
                          <button onClick={()=>{const ne=[...(item.emails||[item.email]),""];onUpdate(item.jNumber,{emails:ne});}} style={{background:"none",border:"1px dashed #93c5fd",borderRadius:3,color:"#2563eb",fontSize:"0.65rem",cursor:"pointer",padding:"1px 5px",marginTop:1}}>+ 메일추가</button>
                        </div>
                      </td>
                    );
                    if(col.key==="memo")return(
                      <td key="memo" style={{padding:0,border:"1px solid #e8e8e8",background:cs.bg||"#fffde7"}}>
                        <XCell value={item.memo||""} onChange={v=>onUpdate(item.jNumber,{memo:v})} multiline
                          selected={isSel} onSelect={()=>{setSelCell({ri,ci});setSelRow(null);setSelCol(null);}}
                          style={{fontSize:`${fontSize}px`,color:cs.color||"#5d4e0f",textAlign:cs.align||"left"}}/>
                      </td>
                    );
                    if(col.key==="status")return(
                      <td key="status" style={{padding:"3px 4px",border:"1px solid #e8e8e8",background:cellBg}}>
                        {isNew
                          ?<button onClick={()=>confirmNew(item.jNumber)} style={{background:"#dc2626",color:"#fff",border:"none",borderRadius:4,padding:"2px 8px",fontSize:"0.72rem",fontWeight:700,cursor:"pointer",animation:"blink 1s step-end infinite"}}>New✓</button>
                          :<select value={item.status||"active"} onChange={e=>onUpdate(item.jNumber,{status:e.target.value,blacklist:e.target.value==="blacklist",active:e.target.value!=="blacklist"})}
                              style={{padding:"2px 4px",border:"1px solid #ddd",borderRadius:4,fontSize:"0.75rem",color:STATUS_COLOR[item.status]||"#111",fontWeight:600,background:"#fff",cursor:"pointer",width:"100%"}}>
                              {STATUS_OPTS.map(s=><option key={s} value={s} style={{color:STATUS_COLOR[s]}}>{STATUS_LABEL[s]}</option>)}
                            </select>
                        }
                      </td>
                    );
                    const displayVal=col.key==="teachingAge"?translateAge(item[col.key]||""):item[col.key]||"";
                    return(
                      <td key={col.key} style={{padding:0,border:"1px solid #e8e8e8",background:cellBg,overflow:"hidden",maxWidth:col.w}}>
                        <XCell value={col.key==="teachingAge"?displayVal:(item[col.key]||"")} onChange={v=>onUpdate(item.jNumber,{[col.key]:v})}
                          selected={isSel} onSelect={()=>{setSelCell({ri,ci});setSelRow(null);setSelCol(null);}}
                          style={{fontWeight:cs.bold?"800":(col.key==="name"?"600":"400"),
                            color:cs.color||(col.key==="name"?"#111":"#333"),
                            fontSize:`${fontSize}px`,
                            fontStyle:cs.italic?"italic":"normal",
                            textDecoration:cs.underline?"underline":cs.strike?"line-through":"none",
                            textAlign:cs.align||"left",
                            fontFamily:cs.fontFamily||"inherit"}}/>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            <tr style={{background:"#fafafa",cursor:"pointer"}} onClick={onAddRow}>
              <td colSpan={dataCols.length+2} style={{padding:"8px 12px",color:"#bbb",fontSize:"0.73rem",textAlign:"center"}}>+ 행 추가 (클릭)</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* 열 관리 팝업 */}
      {showColMgr&&(
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.3)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:500}} onClick={()=>setShowColMgr(false)}>
          <div onClick={e=>e.stopPropagation()} style={{background:"#fff",borderRadius:10,padding:"24px",width:300,maxHeight:"80vh",overflowY:"auto"}}>
            <h3 style={{fontSize:"1rem",fontWeight:800,marginBottom:12}}>열 관리</h3>
            {EXCEL_COLS_DEF.filter(c=>c.key!=="rowNum"&&c.key!=="sel").map(def=>{
              const on=cols.some(c=>c.key===def.key);
              const idx=cols.findIndex(c=>c.key===def.key);
              return(
                <div key={def.key} style={{display:"flex",alignItems:"center",gap:6,padding:"5px 0",borderBottom:"1px solid #f5f5f5"}}>
                  <input type="checkbox" checked={on} onChange={()=>{if(on)setCols(p=>p.filter(c=>c.key!==def.key));else setCols(p=>[...p,{...def}]);}} style={{accentColor:"#2563eb"}}/>
                  <span style={{flex:1,fontSize:"0.85rem",color:on?"#111":"#bbb"}}>{def.label||def.key}</span>
                  {on&&<>
                    <button onClick={()=>{if(idx>1)setCols(p=>{const n=[...p];[n[idx-1],n[idx]]=[n[idx],n[idx-1]];return n;});}} style={{border:"none",background:"none",cursor:"pointer",fontSize:"0.75rem"}}>▲</button>
                    <button onClick={()=>{setCols(p=>{if(idx<p.length-1){const n=[...p];[n[idx],n[idx+1]]=[n[idx+1],n[idx]];return n;}return p;});}} style={{border:"none",background:"none",cursor:"pointer",fontSize:"0.75rem"}}>▼</button>
                  </>}
                </div>
              );
            })}
            <button onClick={()=>setShowColMgr(false)} style={{marginTop:14,width:"100%",padding:"8px",borderRadius:6,border:"none",background:"#111",color:"#fff",fontWeight:700,cursor:"pointer"}}>완료</button>
          </div>
        </div>
      )}
    </div>
  );
};


const ALL_COLS=[{key:"jNumber",label:"NO.",w:80},{key:"region",label:"지역",w:70},{key:"city",label:"도시",w:80},{key:"name",label:"업체명",w:140},{key:"email",label:"이메일",w:200},{key:"phone",label:"연락처",w:130},{key:"teachingAge",label:"연령",w:120},{key:"salary",label:"급여",w:110},{key:"memo",label:"메모",w:260},{key:"status",label:"상태",w:80}];
const ColMgr=({cols,setCols,onClose})=>{
  const ak=ALL_COLS.map(c=>c.key);
  const ck=cols.map(c=>c.key);
  return(
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.3)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:500}} onClick={onClose}>
      <div onClick={e=>e.stopPropagation()} style={{background:"#fff",borderRadius:10,padding:"24px",width:340}}>
        <h3 style={{fontSize:"1rem",fontWeight:800,marginBottom:12}}>열 관리</h3>
        {ak.map(k=>{const on=ck.includes(k);const idx=cols.findIndex(c=>c.key===k);return(
          <div key={k} style={{display:"flex",alignItems:"center",gap:6,padding:"4px 0",borderBottom:"1px solid #f5f5f5"}}>
            <input type="checkbox" checked={on} onChange={()=>{if(on)setCols(p=>p.filter(c=>c.key!==k));else setCols(p=>[...p,{...ALL_COLS.find(c=>c.key===k)}]);}} style={{accentColor:"#2563eb"}}/>
            <span style={{flex:1,fontSize:"0.85rem",color:on?"#111":"#bbb"}}>{ALL_COLS.find(c=>c.key===k)?.label}</span>
            {on&&<><button onClick={()=>{if(idx>0)setCols(p=>{const n=[...p];[n[idx-1],n[idx]]=[n[idx],n[idx-1]];return n;});}} style={{border:"none",background:"none",cursor:"pointer",fontSize:"0.75rem"}}>▲</button><button onClick={()=>{setCols(p=>{if(idx<p.length-1){const n=[...p];[n[idx],n[idx+1]]=[n[idx+1],n[idx]];return n;}return p;});}} style={{border:"none",background:"none",cursor:"pointer",fontSize:"0.75rem"}}>▼</button></>}
          </div>
        );})}
        <button onClick={onClose} style={{marginTop:12,width:"100%",padding:"8px",borderRadius:6,border:"none",background:"#111",color:"#fff",fontWeight:700,cursor:"pointer"}}>완료</button>
      </div>
    </div>
  );
};

// ─── 메인 ───────────────────────────────────────────────
export default function EmployerManagement(){
  const[data,setData]=useState([]);
  const[loading,setLoading]=useState(true);

  useEffect(()=>{
    const adminKey=localStorage.getItem("bridge_admin_key")||"";
    const hdrs={"Content-Type":"application/json"};
    if(adminKey)hdrs["x-admin-key"]=adminKey;
    (async()=>{
      try{
        let all=[];let page=1;let more=true;
        while(more){
          const res=await fetch(`${API_BASE}/api/admin/applications?type=employer&page=${page}&limit=500`,{headers:hdrs});
          if(!res.ok)break;
          const json=await res.json();
          const items=(json.data||[]).map(it=>({
            _apiId:it.id,
            jNumber:it.job_code||it.id||"",
            region:it.location||"",city:it.city||"",
            name:it.school_name||it.name||"",
            email:it.email||"",emails:[it.email].filter(Boolean),
            phone:it.phone||"",contact:it.contact_name||"",
            teachingAge:it.teaching_age||"",salary:it.salary_raw||"",
            status:it.status||"open",blacklist:false,
            active:it.status!=="closed",
            isNew:it.created_at?(Date.now()-new Date(it.created_at).getTime())<7*86400000:false,
            confirmed:false,tags:[],
            memo:it.memo||"",
            rawText:it.raw_text||[it.location,it.city,it.job_code&&`Job. ${it.job_code}`,it.start_date&&`Starting Date : ${it.start_date}`,it.teaching_age&&`Teaching Age : ${it.teaching_age}`,it.class_size&&`Class size : ${it.class_size}`,it.working_hours&&`Working Hours : ${it.working_hours}`,it.salary_raw&&`Monthly Salary : ${it.salary_raw}`,it.teach_hrs_week&&`Average Teaching Hours per Week : ${it.teach_hrs_week}`,it.vacation&&`Vacation : ${it.vacation}`,it.native_count&&`Native Teacher (Numbers can change) : ${it.native_count}`,it.housing&&`Housing : ${it.housing}`,it.benefits&&`Employee Benefits : ${it.benefits}`].filter(Boolean).join("\n"),
          }));
          all=[...all,...items];
          more=json.has_more||false;page++;
        }
        setData(all);
      }catch(e){console.error("Load failed:",e);}
      finally{setLoading(false);}
    })();
  },[]);
  const[tab,setTab]=useState("active");
  const[mode,setMode]=useState("doc");
  const[fl,setFl]=useState({});
  const[cols,setCols]=useState(ALL_COLS.map(c=>({...c})));
  const[showColMgr,setShowColMgr]=useState(false);
  const[mailPopup,setMailPopup]=useState(false);
  const[mailTarget,setMailTarget]=useState(null);
  const[exFl,setExFl]=useState({});
  const[checked,setChecked]=useState(new Set());
  const[sortKey,setSortKey]=useState("");
  const[sortDir,setSortDir]=useState("asc");
  const[boardTitle,setBoardTitle]=useState("BRIDGE — 구인자 채용공고");
  const[editTitle,setEditTitle]=useState(false);
  const[searchQ,setSearchQ]=useState("");
  const[showSearch,setShowSearch]=useState(false);
  const searchRef=useRef(null);
  const cRef=useRef(null);

  // Ctrl+F 커스텀 검색
  useEffect(()=>{
    const h=e=>{
      if((e.ctrlKey||e.metaKey)&&e.key==="f"){
        e.preventDefault();
        setShowSearch(s=>!s);
        setTimeout(()=>searchRef.current?.focus(),50);
      }
      if(e.key==="Escape")setShowSearch(false);
    };
    window.addEventListener("keydown",h);
    return()=>window.removeEventListener("keydown",h);
  },[]);

  const filtered=useMemo(()=>{
    let r=[...data];
    if(tab==="active")r=r.filter(d=>d.active&&!d.blacklist);
    else if(tab==="blacklist")r=r.filter(d=>d.blacklist);
    // 상단 필터 적용
    Object.entries(fl).forEach(([k,v])=>{if(v&&v.length)r=r.filter(d=>{const val=(d[k]||"").toString();return v.includes(val);});});
    // Ctrl+F 검색 필터
    if(searchQ.trim()){
      const q=searchQ.toLowerCase();
      r=r.filter(d=>(d.rawText||"").toLowerCase().includes(q)||(d.memo||"").toLowerCase().includes(q)||d.name.toLowerCase().includes(q)||d.jNumber.toLowerCase().includes(q));
    }
    if(sortKey)r.sort((a,b)=>{const av=(a[sortKey]||"").toString().toLowerCase();const bv=(b[sortKey]||"").toString().toLowerCase();return sortDir==="asc"?(av<bv?-1:av>bv?1:0):(av>bv?-1:av<bv?1:0);});
    return r;
  },[data,tab,fl,sortKey,sortDir,searchQ]);

  const newCount=data.filter(d=>d.isNew&&!d.confirmed&&d.active&&!d.blacklist).length;
  const confirm=useCallback(jn=>setData(p=>p.map(d=>d.jNumber===jn?{...d,confirmed:true,isNew:false}:d)),[]);
  const confirmAll=useCallback(()=>setData(p=>p.map(d=>d.isNew&&!d.confirmed?{...d,confirmed:true}:d)),[]);
  const delRows=useCallback((jns)=>{setData(p=>p.filter(d=>!jns.includes(d.jNumber)));setChecked(new Set());},[]);

  const saveData=useCallback(()=>{
    // 1. localStorage 저장
    try{localStorage.setItem("bridge_employers_backup",JSON.stringify({savedAt:new Date().toISOString(),data}));}catch(e){}
    // 2. JSON 파일 다운로드
    const blob=new Blob([JSON.stringify({savedAt:new Date().toISOString(),count:data.length,data},null,2)],{type:"application/json"});
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url;
    a.download=`BRIDGE_구인자_${new Date().toISOString().slice(0,10).replace(/-/g,"")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  },[data]);
  const addNew=useCallback(()=>{
    const id=nextId();
    setData(p=>[{jNumber:id,region:"서울",city:"강남",name:"NEW 어학원",email:"new@test.com",emails:["new@test.com"],phone:"010-0000-0000",contact:"",teachingAge:"Elementary",salary:"2,500,000",status:"new",blacklist:false,active:true,isNew:true,confirmed:false,tags:[],memo:`(서울 강남 NEW어학원 신규접수)`,rawText:`Seoul Gangnam\nJob. ${id}\nStarting Date : September\nTeaching Age : Elementary`},...p]);
    if(cRef.current)cRef.current.scrollTop=0;
  },[]);
  const updateItem=useCallback((jn,u)=>setData(p=>p.map(d=>{
    if(d.jNumber!==jn)return d;
    const next={...d,...u};
    // jNumber 변경 시 새 값으로 교체
    if(u.jNumber&&u.jNumber!==jn)next.jNumber=u.jNumber;
    return next;
  })),[]);

  // 신규 접수 자동 감지 — 60초 간격
  const seenIds=useRef(new Set());
  useEffect(()=>{seenIds.current=new Set(data.map(d=>d._apiId||d.jNumber));},[data]);
  const moveItem=useCallback((jn,dir)=>{setData(p=>{const idx=p.findIndex(d=>d.jNumber===jn);if(idx<0)return p;const n=[...p];if(dir==="top"){const it=n.splice(idx,1)[0];n.unshift(it);}else if(dir==="up"&&idx>0)[n[idx-1],n[idx]]=[n[idx],n[idx-1]];else if(dir==="down"&&idx<n.length-1)[n[idx],n[idx+1]]=[n[idx+1],n[idx]];return n;});},[]);
  const toggleCheck=useCallback(jn=>setChecked(p=>{const n=new Set(p);n.has(jn)?n.delete(jn):n.add(jn);return n;}),[]);
  const checkAll=useCallback(()=>setChecked(new Set(filtered.map(d=>d.jNumber))),[filtered]);
  const uncheckAll=useCallback(()=>setChecked(new Set()),[]);
  const checkedRecipients=useMemo(()=>filtered.filter(d=>checked.has(d.jNumber)),[filtered,checked]);
  const toggleSort=useCallback(k=>{if(sortKey===k)setSortDir(d=>d==="asc"?"desc":"asc");else{setSortKey(k);setSortDir("asc");}},[sortKey]);
  const startResize=useCallback((idx,e)=>{e.preventDefault();e.stopPropagation();const sx=e.clientX;const sw=cols[idx].w;const onMove=ev=>{setCols(prev=>{const n=[...prev];n[idx]={...n[idx],w:Math.max(40,sw+(ev.clientX-sx))};return n;});};const onUp=()=>{document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);};document.addEventListener("mousemove",onMove);document.addEventListener("mouseup",onUp);},[cols]);
  const[fontInfo,setFontInfo]=useState(18);
  const[fontMemo,setFontMemo]=useState(13);
  const[fontBody,setFontBody]=useState(15);
  const hasF=Object.values(fl).some(v=>v&&v.length>0);

  // 탭 정의 — 메일링 제거, 3개만
  const TABS=[
    {id:"active",l:"활발한 채용보기",c:data.filter(d=>d.active&&!d.blacklist).length,co:"#2563eb"},
    {id:"all",l:"전체보기",c:data.length,co:"#111"},
    {id:"blacklist",l:"블랙리스트",c:data.filter(d=>d.blacklist).length,co:"#dc2626"},
  ];

  if(loading)return <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"60vh",color:"#888",fontSize:"1rem"}}>
    <div style={{textAlign:"center"}}><div style={{fontSize:"2rem",marginBottom:8,animation:"spin 1s linear infinite"}}>&#8635;</div>데이터 로딩 중...</div>
    <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
  </div>;

  return(
    <div style={{display:"flex",flexDirection:"column",height:"100%",fontFamily:"'Malgun Gothic',-apple-system,sans-serif",background:"#f0f0f0"}}>
      <style>{`
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
        @keyframes newCardBlink{0%,100%{box-shadow:0 0 0 0 rgba(37,99,235,0.4)}50%{box-shadow:0 0 0 6px rgba(37,99,235,0.1)}}
        @keyframes newBarBlink{0%,100%{border-left-color:#fecaca}50%{border-left-color:#fff1f2}}
        *{box-sizing:border-box;margin:0}
        ::-webkit-scrollbar{width:7px}
        ::-webkit-scrollbar-thumb{background:#bbb;border-radius:4px}
        .rh{position:absolute;right:0;top:0;bottom:0;width:4px;cursor:col-resize;background:transparent}
        .rh:hover{background:#2563eb}
      `}</style>
        {/* 헤더 */}
        <div style={{background:"#fff",borderBottom:"1px solid #ddd",padding:"12px 20px"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
            <div>
              <h2 style={{fontSize:"1.3rem",fontWeight:800}}>구인자관리</h2>
              <span style={{fontSize:"0.85rem",color:"#111",fontWeight:700}}>{filtered.length}건</span>
            </div>
            <div style={{display:"flex",gap:8,alignItems:"center"}}>
              {/* 전역 폰트 슬라이더 */}
              <div style={{display:"flex",gap:8,alignItems:"center",paddingRight:10,borderRight:"1px solid #eee"}}>
                {[["INFO",fontInfo,setFontInfo,"#2563eb"],["MEMO",fontMemo,setFontMemo,"#b45309"],["본문",fontBody,setFontBody,"#555"]].map(([lbl,val,setter,col])=>(
                  <div key={lbl} style={{display:"flex",alignItems:"center",gap:2}}>
                    <span style={{fontSize:"0.58rem",color:col,fontWeight:700}}>{lbl}</span>
                    <span style={{fontSize:"0.58rem",color:"#ccc"}}>가</span>
                    <input type="range" min={11} max={20} value={val} onChange={e=>setter(Number(e.target.value))} style={{width:40,accentColor:col,cursor:"pointer"}}/>
                    <span style={{fontSize:"0.65rem",color:"#ccc"}}>가</span>
                    <span style={{fontSize:"0.58rem",color:"#aaa",minWidth:12}}>{val}</span>
                  </div>
                ))}
              </div>
              <div style={{display:"flex",border:"1px solid #111",overflow:"hidden",borderRadius:5}}>
                {[{id:"doc",l:"워드뷰"},{id:"table",l:"엑셀뷰"}].map(v=>(
                  <button key={v.id} onClick={()=>setMode(v.id)} style={{padding:"5px 14px",border:"none",background:mode===v.id?"#111":"#fff",color:mode===v.id?"#fff":"#111",fontSize:"0.82rem",fontWeight:600,cursor:"pointer"}}>{v.l}</button>
                ))}
              </div>
              {mode==="table"&&<button onClick={()=>setShowColMgr(true)} style={{padding:"5px 12px",borderRadius:5,border:"1px solid #aaa",background:"#fff",fontSize:"0.78rem",cursor:"pointer"}}>열관리</button>}

              <button onClick={()=>{setMailTarget(null);setMailPopup(true);}} style={{padding:"5px 16px",borderRadius:5,border:"none",background:checked.size>0?"#03c75a":"#a3e6bc",color:"#fff",fontSize:"0.82rem",fontWeight:700,cursor:"pointer"}}>✉ 메일발송{checked.size>0?` (${checked.size})`:""}</button>
              <button onClick={()=>window.location.reload()} title="새로고침" style={{padding:"6px 14px",borderRadius:5,border:"1px solid #ccc",background:"#fff",fontSize:"1rem",cursor:"pointer",display:"flex",alignItems:"center",gap:4,fontWeight:700}}>⟳</button>
              <button onClick={saveData} style={{padding:"5px 16px",borderRadius:5,border:"none",background:"#7c3aed",color:"#fff",fontSize:"0.82rem",fontWeight:700,cursor:"pointer"}}>💾 저장</button>
              <button onClick={addNew} style={{padding:"5px 16px",borderRadius:5,border:"none",background:"#2563eb",color:"#fff",fontSize:"0.82rem",fontWeight:700,cursor:"pointer"}}>+ 새접수</button>
            </div>
          </div>

          {/* 탭 3개 */}
          <div style={{display:"flex",borderBottom:"2px solid #eee",marginBottom:8}}>
            {TABS.map(t=>{const nc=t.id==="active"?newCount:0;return(
              <button key={t.id} onClick={()=>{setTab(t.id);setChecked(new Set());setFl({});}} style={{padding:"7px 16px",border:"none",background:"transparent",borderBottom:tab===t.id?`4px solid ${t.co}`:"4px solid transparent",color:tab===t.id?t.co:"#444",fontSize:"0.88rem",fontWeight:tab===t.id?800:500,cursor:"pointer",marginBottom:-2,position:"relative"}}>
                {nc>0&&<span style={{position:"absolute",top:-5,left:"50%",transform:"translateX(-50%)",background:"#dc2626",color:"#fff",fontSize:"0.62rem",fontWeight:800,padding:"1px 7px",borderRadius:8,animation:"blink 1s step-end infinite"}}>NEW {nc}</span>}
                {t.l}
                <span style={{marginLeft:4,fontSize:"0.68rem",fontWeight:600,background:tab===t.id?(t.id==="blacklist"?"#fecaca":t.id==="all"?"#e5e7eb":"#dbeafe"):"#e8e8e8",color:tab===t.id?t.co:"#444",padding:"2px 8px",borderRadius:10,fontWeight:tab===t.id?700:600}}>{t.c}</span>
              </button>
            );})}

          </div>

          {/* 공통 필터바 — 워드뷰에서만 표시 */}
          <div style={{display:mode==="table"?"none":"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
            <DropFilter label="전체 지역" optKey="region" data={data} filters={fl} setFilters={setFl}/>
            <DropFilter label="전체 도시" optKey="city" data={data} filters={fl} setFilters={setFl}/>
            <DropFilter label="전체 대상" optKey="teachingAge" data={data} filters={fl} setFilters={setFl}/>
            <DropFilter label="상태" optKey="status" data={data} filters={fl} setFilters={setFl}/>
            {/* Ctrl+F 검색 인라인 */}
            <div style={{position:"relative",marginLeft:"auto",display:"flex",alignItems:"center",gap:4}}>
              <input
                ref={searchRef}
                value={searchQ}
                onChange={e=>setSearchQ(e.target.value)}
                placeholder="Ctrl+F 검색..."
                style={{padding:"5px 10px",border:"1px solid",borderColor:searchQ?"#2563eb":"#ccc",borderRadius:6,fontSize:"0.82rem",outline:"none",width:searchQ||showSearch?180:120,transition:"width 0.2s",background:searchQ?"#eff6ff":"#fff"}}
                onFocus={()=>setShowSearch(true)}
              />
              {searchQ&&<button onClick={()=>setSearchQ("")} style={{position:"absolute",right:6,top:"50%",transform:"translateY(-50%)",background:"none",border:"none",cursor:"pointer",color:"#999",fontSize:"0.8rem"}}>✕</button>}
            </div>
            {hasF&&<button onClick={()=>setFl({})} style={{padding:"4px 10px",border:"1px solid #ccc",background:"#fff",fontSize:"0.72rem",color:"#888",cursor:"pointer",borderRadius:5}}>필터 초기화</button>}
          </div>
        </div>

        {/* 컨텐츠 */}
        <div ref={cRef} style={{flex:1,overflow:"auto",padding:mode==="doc"?"14px 20px":0}}>
          {mode==="doc"&&(
            <div style={{maxWidth:860,margin:"0 auto"}}>
              <div style={{background:"#fff",padding:"24px 0",boxShadow:"0 1px 4px rgba(0,0,0,0.06)"}}>

                {filtered.map((item,i)=>(
                  <div key={i} style={{padding:"0 24px"}}>
                    <DocBlock item={item} onConfirm={confirm} onUpdate={updateItem} onMove={moveItem} searchQ={searchQ} fontInfo={fontInfo} fontMemo={fontMemo} fontBody={fontBody} onMailTo={it=>{setMailTarget(it);setMailPopup(true);}}/>
                    {i<filtered.length-1&&(
                      <div style={{margin:"0 -24px",height:8,background:"linear-gradient(to bottom,#6b7280,#d1d5db)",boxShadow:"0 2px 4px rgba(0,0,0,0.10)"}}/>
                    )}
                  </div>
                ))}
                {!filtered.length&&<div style={{textAlign:"center",padding:50,color:"#bbb"}}>검색 결과 없음</div>}
              </div>
            </div>
          )}
          {mode==="table"&&(
            <ExcelView
              data={data}
              filtered={filtered}
              onUpdate={updateItem}
              onAddRow={addNew}
              onDelRows={delRows}
              onMoveRow={moveItem}
              checked={checked}
              setChecked={setChecked}
              searchQ={searchQ}
              confirm={confirm}
              onMailTo={it=>{setMailTarget(it);setMailPopup(true);}}
              exFl={exFl}
              setExFl={setExFl}
            />
          )}
        </div>

      {showColMgr&&<ColMgr cols={cols} setCols={setCols} onClose={()=>setShowColMgr(false)}/>}
      {mailPopup&&<MailComposer
        recipients={mailTarget?[{name:mailTarget.name,email:mailTarget.email,emails:mailTarget.emails||[mailTarget.email],region:mailTarget.region,city:mailTarget.city,teachingAge:mailTarget.teachingAge}]:checkedRecipients}
        onClose={()=>{setMailPopup(false);setMailTarget(null);}}
      />}
    </div>
  );
}
