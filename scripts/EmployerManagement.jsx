import { useState, useMemo, useCallback, useEffect, useRef } from "react";

// ─── 데이터 ─────────────────────────────────────────────
const INIT_DATA = [
  { jNumber:"1003",region:"부산",city:"해운대",name:"브릿지영어1호점",email:"bridge@nave.com",phone:"010-4560-0333",teachingAge:"Kindy - Elem",salary:"2,400,000",status:"active",blacklist:false,active:true,isNew:false,confirmed:true,
    memo:"(부산 해운대 브릿지영어1호점 원장0104560333 부장010555 bridge@nave.com 담임교사아님-영어만/1:1한국어보조교사있음/긴방학; 방학 겨울3주 여름2주, 병가3일, 주당 25시간 프렙 하루2시간, 점심자유, 남자 교육전공선호)Native Teacher (Numbers can change) : Approx. 2 / 400 k",
    rawText:"Busan\nJob. 1003\nStarting Date : September, March\nTeaching Age : Kindy - Elem\nClass size : around ~10\nWorking Hours : 09:00~16 (line 10)\nMonthly Salary : 2,40m KRW Not negotiable\nAverage Teaching Hours per Week : 23\nVacation : total 5 weeks, plus 2 days for sick leave\nNative Teacher (Numbers can change) : Approx. 3\nHousing: allowance 400k, No deposit or additional cost support provided.\nOnly hiring teachers residing in Korea, Good reputation and team players preferred.\nEmployee Benefits : Visa sponsorship, severance pay, pension, insurance, paid vacation, flexible lunch and airfare support." },
  { jNumber:"1204",region:"서울",city:"구로",name:"해피해피",email:"test@gmail.com",phone:"010-2542-6545",teachingAge:"Elem, Adult",salary:"2,300,000",status:"active",blacklist:false,active:true,isNew:false,confirmed:true,
    memo:"(서울 구로 해피해피 김테스원장 010-2542-6545 test@gmail.com 남아공외지원가, 짧은시간)",
    rawText:"Seoul Guro\nJob. 1204\nStarting Date : March, June\nTeaching Age : Elem, Sometimes adult\nClass size : around ~8\nWorking Hours : 09:00~15:00\nMonthly Salary : 2,30m KRW Not negotiable\nAverage Teaching Hours per Week : 20\nVacation : 16 days\nNative Teacher (Numbers can change) : Approx. 1\nHousing: provided or allowance 700k, 5M deposit.\nBachelor's or higher with an F visa kyopo or native speakers are also welcome\nEmployee Benefits : Visa sponsorship, severance pay, pension, insurance, paid vacation, renewal Bonus, flexible lunch and airfare support." },
  { jNumber:"1087",region:"경기",city:"수원시",name:"광교SLP",email:"hwangjungah@gmail.com",phone:"010-9647-9060",teachingAge:"Kinder",salary:"2,500,000",status:"active",blacklist:false,active:true,isNew:false,confirmed:true,memo:"",rawText:"Gyeonggi Suwon\nJob. 1087\nStarting Date : August\nTeaching Age : Kinder" },
  { jNumber:"1088",region:"경기",city:"수지",name:"수지 폴리어학원",email:"itsjenny@naver.com",phone:"010-5678-5500",teachingAge:"Kinder",salary:"2,600,000",status:"new",blacklist:false,active:true,isNew:false,confirmed:true,memo:"",rawText:"Gyeonggi Suji\nJob. 1088\nStarting Date : September\nTeaching Age : Kinder" },
  { jNumber:"1045",region:"부산",city:"동래구",name:"브릿지",email:"airel@naver.com",phone:"010-5900-2221",teachingAge:"Kinder - Elem",salary:"2,400,000",status:"active",blacklist:false,active:true,isNew:false,confirmed:true,memo:"",rawText:"Busan Dongnae\nJob. 1045" },
  { jNumber:"1046",region:"부산",city:"동래구",name:"브릿지에이전시",email:"airel@naver.com",phone:"010-5900-2221",teachingAge:"Pre-K, Kinder",salary:"2,300,000",status:"active",blacklist:false,active:true,isNew:false,confirmed:true,memo:"",rawText:"Busan Dongnae\nJob. 1046" },
  { jNumber:"0823",region:"경북",city:"경주",name:"브라이트스타",email:"brightstarenglish1@gmail.com",phone:"",teachingAge:"초중",salary:"",status:"active",blacklist:true,active:false,isNew:false,confirmed:true,memo:"(경북 경주 브라이트스타 — 연락두절 3회, 급여 지연 이력)",rawText:"Job. 0823" },
  { jNumber:"0714",region:"제주",city:"서귀",name:"브라이트잉글리쉬",email:"bright4566@naver.com",phone:"070-7756-4566",teachingAge:"초중",salary:"",status:"active",blacklist:true,active:false,isNew:false,confirmed:true,memo:"(제주 서귀 브라이트잉글리쉬 — 계약 위반 2건, 교사 불만 다수)",rawText:"Job. 0714" },
];
let _nxt=1101;function nextId(){const n=_nxt;_nxt+=2;return `N${n}`;}
function uniq(a,k){return [...new Set(a.map(d=>d[k]).filter(Boolean))].sort();}

// ─── 메일 양식 ──────────────────────────────────────────
const TEMPLATES=[
  {id:"recruit",name:"채용 안내 (기본)",subject:"[BRIDGE] Native English Teacher Position Available",
    html:`<p>Dear <strong>{{name}}</strong>,</p><p>I hope this email finds you well.</p><p>We are reaching out to inform you that we currently have a teaching position available that may be of interest.</p><h3>Position Details</h3><ul><li><strong>Location:</strong> {{region}} {{city}}</li><li><strong>Teaching Age:</strong> {{teachingAge}}</li></ul><p>Please let us know if you are interested or if you have any questions.</p><br/><p>Best regards,<br/><strong>BRIDGE Recruitment Team</strong><br/><a href="https://bridgejob.co.kr">bridgejob.co.kr</a></p>`},
  {id:"followup",name:"팔로업 (리마인더)",subject:"[BRIDGE] Following Up — Teaching Position",
    html:`<p>Dear <strong>{{name}}</strong>,</p><p>I wanted to follow up on our previous communication regarding the teaching position.</p><p>We are still looking for qualified candidates and would love to hear from you.</p><p>Please don't hesitate to reach out if you have any questions.</p><br/><p>Best regards,<br/><strong>BRIDGE Recruitment Team</strong></p>`},
  {id:"urgent",name:"긴급 채용",subject:"[BRIDGE] URGENT: Immediate Teaching Position",
    html:`<p>Dear <strong>{{name}}</strong>,</p><p style="color:#dc2626;font-weight:bold;">We have an URGENT opening for a native English teacher.</p><ul><li><strong>Location:</strong> {{region}} {{city}}</li><li><strong>Start Date:</strong> ASAP</li><li><strong>Teaching Age:</strong> {{teachingAge}}</li></ul><p>If you are available, please reply at your earliest convenience.</p><br/><p>Best regards,<br/><strong>BRIDGE Recruitment Team</strong></p>`},
  {id:"custom",name:"직접 작성",subject:"",html:"<p>여기에 내용을 작성하세요...</p>"},
];

const SENDER_OPTIONS=["bridgejobkr@naver.com","bridgejobkr@gmail.com"];

// ─── HTML 에디터 툴바 ───────────────────────────────────
const EditorToolbar=({editorRef})=>{
  const exec=(cmd,val=null)=>{document.execCommand(cmd,false,val);editorRef.current?.focus();};
  const FONTS=["나눔고딕","맑은 고딕","Arial","Georgia","Verdana","Courier New"];
  const SIZES=["1","2","3","4","5","6","7"];
  const COLORS=["#000000","#dc2626","#2563eb","#16a34a","#f59e0b","#7c3aed","#6b7280"];

  const insertLink=()=>{const url=prompt("URL 입력:","https://");if(url)exec("createLink",url);};

  return (
    <div style={{display:"flex",alignItems:"center",gap:2,padding:"6px 8px",borderBottom:"1px solid #ddd",background:"#f8f8f8",flexWrap:"wrap"}}>
      {/* 폰트 */}
      <select onChange={e=>{exec("fontName",e.target.value);e.target.value="";}} defaultValue="" style={{padding:"3px 4px",border:"1px solid #ccc",borderRadius:3,fontSize:"0.75rem",minWidth:80}}>
        <option value="" disabled>폰트</option>
        {FONTS.map(f=> <option key={f} value={f} style={{fontFamily:f}}>{f}</option>)}
      </select>
      {/* 사이즈 */}
      <select onChange={e=>{exec("fontSize",e.target.value);e.target.value="";}} defaultValue="" style={{padding:"3px 4px",border:"1px solid #ccc",borderRadius:3,fontSize:"0.75rem",width:50}}>
        <option value="" disabled>크기</option>
        {SIZES.map(s=> <option key={s} value={s}>{parseInt(s)*4+8}px</option>)}
      </select>
      <div style={{width:1,height:20,background:"#ddd",margin:"0 3px"}}/>
      {/* 서식 */}
      {[
        {cmd:"bold",icon:"B",style:{fontWeight:800}},
        {cmd:"italic",icon:"I",style:{fontStyle:"italic"}},
        {cmd:"underline",icon:"U",style:{textDecoration:"underline"}},
        {cmd:"strikeThrough",icon:"S",style:{textDecoration:"line-through"}},
      ].map(b=> (
        <button key={b.cmd} onClick={()=>exec(b.cmd)} title={b.cmd} style={{width:28,height:28,border:"1px solid #ccc",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.85rem",display:"flex",alignItems:"center",justifyContent:"center",...b.style}}>{b.icon}</button>
      ))}
      <div style={{width:1,height:20,background:"#ddd",margin:"0 3px"}}/>
      {/* 색상 */}
      <div style={{display:"flex",gap:1}}>
        {COLORS.map(c=> (
          <button key={c} onClick={()=>exec("foreColor",c)} style={{width:20,height:20,border:"1px solid #ddd",borderRadius:2,background:c,cursor:"pointer"}} title={c}/>
        ))}
      </div>
      <div style={{width:1,height:20,background:"#ddd",margin:"0 3px"}}/>
      {/* 정렬 */}
      {[
        {cmd:"justifyLeft",icon:"≡L"},
        {cmd:"justifyCenter",icon:"≡C"},
        {cmd:"justifyRight",icon:"≡R"},
      ].map(b=> (
        <button key={b.cmd} onClick={()=>exec(b.cmd)} style={{width:28,height:28,border:"1px solid #ccc",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.65rem"}}>{b.icon}</button>
      ))}
      <div style={{width:1,height:20,background:"#ddd",margin:"0 3px"}}/>
      {/* 리스트/링크 */}
      <button onClick={()=>exec("insertUnorderedList")} style={{width:28,height:28,border:"1px solid #ccc",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.75rem"}} title="글머리 목록">•</button>
      <button onClick={()=>exec("insertOrderedList")} style={{width:28,height:28,border:"1px solid #ccc",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.75rem"}} title="번호 목록">1.</button>
      <button onClick={insertLink} style={{width:28,height:28,border:"1px solid #ccc",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.85rem"}} title="링크">🔗</button>
      <button onClick={()=>exec("removeFormat")} style={{width:28,height:28,border:"1px solid #ccc",borderRadius:3,background:"#fff",cursor:"pointer",fontSize:"0.7rem",color:"#999"}} title="서식 제거">Tx</button>
    </div>
  );
};

// ─── 메일 작성 팝업 ─────────────────────────────────────
const MailComposer=({recipients,onClose})=>{
  const[tplId,setTplId]=useState("recruit");
  const[sender,setSender]=useState(SENDER_OPTIONS[0]);
  const[subject,setSubject]=useState(TEMPLATES[0].subject);
  const[attachments,setAttachments]=useState([]);
  const[sending,setSending]=useState(false);
  const[sent,setSent]=useState(false);
  const editorRef=useRef(null);
  const dropRef=useRef(null);

  const selectTemplate=useCallback((id)=>{
    setTplId(id);
    const t=TEMPLATES.find(x=>x.id===id);
    if(t){setSubject(t.subject);if(editorRef.current)editorRef.current.innerHTML=t.html;}
  },[]);

  useEffect(()=>{
    if(editorRef.current){editorRef.current.innerHTML=TEMPLATES[0].html;}
  },[]);

  const getPreviewHtml=useCallback(()=>{
    const raw=editorRef.current?.innerHTML||"";
    if(!recipients.length) return raw;
    const r=recipients[0];
    return raw.replace(/\{\{name\}\}/g,r.name).replace(/\{\{region\}\}/g,r.region).replace(/\{\{city\}\}/g,r.city).replace(/\{\{teachingAge\}\}/g,r.teachingAge).replace(/\{\{email\}\}/g,r.email);
  },[recipients]);

  const[previewHtml,setPreviewHtml]=useState("");
  const updatePreview=useCallback(()=>{setPreviewHtml(getPreviewHtml());},[getPreviewHtml]);
  useEffect(()=>{const t=setInterval(updatePreview,500);return ()=>clearInterval(t);},[updatePreview]);

  const handleDrop=useCallback((e)=>{e.preventDefault();const files=[...e.dataTransfer.files];setAttachments(prev=>[...prev,...files.map(f=>({name:f.name,size:(f.size/1024).toFixed(1)+"KB"}))]);},[]);
  const removeAttach=useCallback((i)=>setAttachments(prev=>prev.filter((_,idx)=>idx!==i)),[]);

  const handleSend=useCallback(()=>{
    if(!subject.trim()){alert("제목을 입력하세요");return;}
    setSending(true);setTimeout(()=>{setSending(false);setSent(true);setTimeout(()=>onClose(),2000);},1500);
  },[subject,onClose]);

  if(sent) return (
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",backdropFilter:"blur(4px)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000}}>
      <div style={{background:"#fff",borderRadius:16,padding:"60px 40px",textAlign:"center",boxShadow:"0 20px 60px rgba(0,0,0,0.25)"}}>
        <div style={{fontSize:"3rem",marginBottom:12}}>✓</div>
        <h2 style={{fontSize:"1.3rem",fontWeight:800,color:"#16a34a"}}>발송 완료!</h2>
        <p style={{fontSize:"0.9rem",color:"#666",marginTop:6}}>From: {sender}</p>
        <p style={{fontSize:"0.9rem",color:"#666"}}>{recipients.length}건 개별 발송 (1:1, BCC 없음)</p>
      </div>
    </div>
  );

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",backdropFilter:"blur(4px)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000}} onClick={onClose}>
      <div onClick={e=>e.stopPropagation()} style={{background:"#fff",borderRadius:14,width:"min(1200px,96vw)",height:"min(88vh,800px)",overflow:"hidden",boxShadow:"0 20px 60px rgba(0,0,0,0.3)",display:"flex",flexDirection:"column"}}>
        {/* 헤더 */}
        <div style={{padding:"14px 20px",borderBottom:"1px solid #e5e5e5",display:"flex",justifyContent:"space-between",alignItems:"center",background:"#f8f8f8",flexShrink:0}}>
          <div>
            <h3 style={{fontSize:"1.1rem",fontWeight:800,color:"#111"}}>메일 보내기</h3>
            <p style={{fontSize:"0.78rem",color:"#666",marginTop:2}}>받는 사람: {recipients.length}명 · 개별 1:1 발송</p>
          </div>
          <button onClick={onClose} style={{width:32,height:32,borderRadius:"50%",background:"#e5e5e5",border:"none",cursor:"pointer",fontSize:"1rem",fontWeight:700,color:"#666"}}>✕</button>
        </div>

        {/* 좌: 작성 / 우: 미리보기 */}
        <div style={{display:"flex",flex:1,overflow:"hidden"}}>
          {/* 좌측 작성 */}
          <div style={{flex:1,display:"flex",flexDirection:"column",borderRight:"1px solid #e5e5e5",overflow:"hidden"}}>
            <div style={{padding:"14px 20px",overflowY:"auto",flex:1}}>
              {/* 양식 선택 */}
              <div style={{marginBottom:12}}>
                <label style={{fontSize:"0.78rem",fontWeight:700,color:"#333",display:"block",marginBottom:5}}>메일 양식</label>
                <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
                  {TEMPLATES.map(t=> (
                    <button key={t.id} onClick={()=>selectTemplate(t.id)} style={{padding:"6px 16px",borderRadius:6,border:tplId===t.id?"2px solid #2563eb":"1px solid #ccc",background:tplId===t.id?"#eff6ff":"#fff",color:tplId===t.id?"#2563eb":"#555",fontSize:"0.82rem",fontWeight:tplId===t.id?700:400,cursor:"pointer"}}>{t.name}</button>
                  ))}
                </div>
              </div>

              {/* 보내는 사람 */}
              <div style={{marginBottom:12}}>
                <label style={{fontSize:"0.78rem",fontWeight:700,color:"#333",display:"block",marginBottom:4}}>보내는 사람</label>
                <div style={{display:"flex",gap:6}}>
                  {SENDER_OPTIONS.map(s=> (
                    <button key={s} onClick={()=>setSender(s)} style={{padding:"6px 14px",borderRadius:6,border:sender===s?"2px solid #111":"1px solid #ccc",background:sender===s?"#111":"#fff",color:sender===s?"#fff":"#555",fontSize:"0.82rem",fontWeight:sender===s?700:400,cursor:"pointer"}}>{s}</button>
                  ))}
                </div>
              </div>

              {/* 받는 사람 */}
              <div style={{marginBottom:12}}>
                <label style={{fontSize:"0.78rem",fontWeight:700,color:"#333",display:"block",marginBottom:4}}>받는 사람 ({recipients.length}명 — 각각 개별 발송)</label>
                <div style={{background:"#f8f8f8",borderRadius:6,padding:"8px 10px",maxHeight:60,overflowY:"auto",fontSize:"0.78rem",color:"#555",display:"flex",flexWrap:"wrap",gap:3}}>
                  {recipients.map((r,i)=> <span key={i} style={{background:"#e8f0fe",padding:"2px 8px",borderRadius:4,fontSize:"0.75rem"}}>{r.name} &lt;{r.email}&gt;</span>)}
                </div>
              </div>

              {/* 제목 */}
              <div style={{marginBottom:12}}>
                <label style={{fontSize:"0.78rem",fontWeight:700,color:"#333",display:"block",marginBottom:4}}>제목</label>
                <input value={subject} onChange={e=>setSubject(e.target.value)} style={{width:"100%",padding:"8px 12px",borderRadius:6,border:"1px solid #ccc",fontSize:"0.88rem",outline:"none"}} onFocus={e=>e.target.style.borderColor="#2563eb"} onBlur={e=>e.target.style.borderColor="#ccc"}/>
              </div>

              {/* HTML 에디터 */}
              <div style={{marginBottom:12}}>
                <label style={{fontSize:"0.78rem",fontWeight:700,color:"#333",display:"block",marginBottom:4}}>
                  본문 <span style={{fontWeight:400,color:"#999"}}>({"{{name}} {{region}} {{city}} {{teachingAge}}"} 자동 치환)</span>
                </label>
                <div style={{border:"1px solid #ccc",borderRadius:6,overflow:"hidden"}}>
                  <EditorToolbar editorRef={editorRef}/>
                  <div
                    ref={editorRef}
                    contentEditable
                    onInput={updatePreview}
                    style={{
                      minHeight:200,maxHeight:300,overflowY:"auto",
                      padding:"12px 14px",fontSize:"0.88rem",lineHeight:1.7,
                      outline:"none",fontFamily:"'Malgun Gothic',sans-serif",
                      color:"#111",
                    }}
                  />
                </div>
              </div>

              {/* 첨부 드래그드롭 */}
              <div ref={dropRef} onDrop={handleDrop} onDragOver={e=>e.preventDefault()}
                style={{border:"2px dashed #ccc",borderRadius:8,padding:"14px",textAlign:"center",background:"#fafafa",cursor:"pointer",marginBottom:12}}
                onDragEnter={e=>{e.currentTarget.style.borderColor="#2563eb";e.currentTarget.style.background="#eff6ff";}}
                onDragLeave={e=>{e.currentTarget.style.borderColor="#ccc";e.currentTarget.style.background="#fafafa";}}>
                <p style={{fontSize:"0.82rem",color:"#888"}}>파일을 드래그 & 드롭 (또는 클릭)</p>
                {attachments.length>0&&(
                  <div style={{marginTop:8,display:"flex",flexWrap:"wrap",gap:4,justifyContent:"center"}}>
                    {attachments.map((a,i)=> (
                      <span key={i} style={{display:"inline-flex",alignItems:"center",gap:4,background:"#e8f0fe",padding:"3px 10px",borderRadius:4,fontSize:"0.75rem",color:"#2563eb"}}>
                        {a.name} ({a.size})
                        <button onClick={()=>removeAttach(i)} style={{background:"none",border:"none",color:"#999",cursor:"pointer",fontSize:"0.8rem",padding:0}}>✕</button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 발송 버튼 */}
            <div style={{padding:"12px 20px",borderTop:"1px solid #eee",background:"#f8f8f8",flexShrink:0}}>
              <button onClick={handleSend} disabled={sending} style={{width:"100%",padding:"12px",borderRadius:8,border:"none",background:sending?"#94a3b8":"#2563eb",color:"#fff",fontSize:"0.95rem",fontWeight:700,cursor:sending?"not-allowed":"pointer"}}>
                {sending?"발송 중...":`메일 발송 (${recipients.length}명 개별 발송)`}
              </button>
              <p style={{textAlign:"center",fontSize:"0.68rem",color:"#999",marginTop:5}}>From: {sender} · 각 수신자에게 1:1 개별 발송 · 타인 정보 절대 미노출</p>
            </div>
          </div>

          {/* 우측 미리보기 */}
          <div style={{width:420,display:"flex",flexDirection:"column",background:"#f5f5f5",flexShrink:0,overflow:"hidden"}}>
            <div style={{padding:"12px 16px",borderBottom:"1px solid #e5e5e5",background:"#f0f0f0",flexShrink:0}}>
              <h4 style={{fontSize:"0.88rem",fontWeight:700,color:"#333"}}>미리보기 {recipients.length>0&&`— ${recipients[0].name}`}</h4>
            </div>
            <div style={{flex:1,overflowY:"auto",padding:"16px"}}>
              <div style={{background:"#fff",borderRadius:8,boxShadow:"0 1px 4px rgba(0,0,0,0.08)",overflow:"hidden"}}>
                {/* 메일 헤더 */}
                <div style={{padding:"14px 16px",borderBottom:"1px solid #eee",fontSize:"0.78rem",color:"#666"}}>
                  <p><strong style={{color:"#333"}}>From:</strong> BRIDGE &lt;{sender}&gt;</p>
                  <p><strong style={{color:"#333"}}>To:</strong> {recipients[0]?.email||"—"} <span style={{color:"#16a34a",fontSize:"0.68rem"}}>(개별발송)</span></p>
                  <p style={{marginTop:6,fontWeight:700,color:"#111",fontSize:"0.9rem"}}>{subject.replace(/\{\{name\}\}/g,recipients[0]?.name||"")}</p>
                </div>
                {/* 메일 본문 */}
                <div style={{padding:"16px",fontSize:"0.85rem",lineHeight:1.7,color:"#333"}} dangerouslySetInnerHTML={{__html:previewHtml}}/>
                {/* 첨부 */}
                {attachments.length>0&&(
                  <div style={{padding:"10px 16px",borderTop:"1px solid #eee"}}>
                    <p style={{fontSize:"0.72rem",color:"#999",marginBottom:4}}>첨부파일:</p>
                    {attachments.map((a,i)=> <span key={i} style={{display:"inline-block",background:"#f0f0f0",padding:"2px 8px",borderRadius:4,marginRight:4,fontSize:"0.72rem"}}>{a.name}</span>)}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── 필터/열관리/블록 (이전 버전 동일) ──────────────────
const XF=({label,options,selected,onChange,w=110})=>{const[open,setOpen]=useState(false);const[q,setQ]=useState("");const ref=useRef(null);useEffect(()=>{const h=e=>{if(ref.current&&!ref.current.contains(e.target))setOpen(false)};document.addEventListener("mousedown",h);return()=>document.removeEventListener("mousedown",h)},[]);const opts=options.filter(o=>o.toLowerCase().includes(q.toLowerCase()));const all=selected.length===0;return (<div ref={ref} style={{position:"relative"}}><button onClick={()=>setOpen(!open)} style={{padding:"6px 10px",background:selected.length?"#dbeafe":"#fff",border:"1px solid #bbb",fontSize:"0.82rem",cursor:"pointer",display:"flex",alignItems:"center",gap:4,minWidth:w,justifyContent:"space-between",color:"#111",fontWeight:500}}><span style={{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{selected.length?`${label}(${selected.length})`:label}</span><span style={{fontSize:"0.6rem",color:"#888"}}>▼</span></button>{open&&(<div style={{position:"absolute",top:"100%",left:0,zIndex:200,background:"#fff",border:"1px solid #bbb",boxShadow:"0 6px 20px rgba(0,0,0,0.18)",minWidth:Math.max(w,170),maxHeight:300,display:"flex",flexDirection:"column"}}><input value={q} onChange={e=>setQ(e.target.value)} placeholder="검색..." style={{padding:"7px 10px",border:"none",borderBottom:"1px solid #ddd",fontSize:"0.82rem",outline:"none"}}/><div style={{overflowY:"auto",flex:1}}><label style={{display:"flex",alignItems:"center",gap:7,padding:"6px 10px",cursor:"pointer",fontSize:"0.82rem",fontWeight:700,borderBottom:"1px solid #eee"}}><input type="checkbox" checked={all} onChange={()=>onChange([])} style={{accentColor:"#2563eb",width:15,height:15}}/>(전체)</label>{opts.map(o=> (<label key={o} style={{display:"flex",alignItems:"center",gap:7,padding:"5px 10px",cursor:"pointer",fontSize:"0.82rem"}} onMouseEnter={e=>e.currentTarget.style.background="#f0f0f0"} onMouseLeave={e=>e.currentTarget.style.background=""}><input type="checkbox" checked={all||selected.includes(o)} onChange={()=>onChange(selected.includes(o)?selected.filter(s=>s!==o):[...selected,o])} style={{accentColor:"#2563eb",width:15,height:15}}/>{o}</label>))}</div></div>)}</div>);};

const ALL_COLUMNS=[{key:"jNumber",label:"NO.",w:80},{key:"region",label:"지역",w:70},{key:"city",label:"도시",w:80},{key:"name",label:"업체명",w:140},{key:"email",label:"이메일",w:180},{key:"phone",label:"연락처",w:130},{key:"teachingAge",label:"연령",w:120},{key:"salary",label:"급여",w:110},{key:"memo",label:"메모",w:280},{key:"status",label:"상태",w:80}];

const ColManager=({cols,setCols,onClose})=>{const allKeys=ALL_COLUMNS.map(c=>c.key);const activeKeys=cols.map(c=>c.key);const toggle=k=>{if(activeKeys.includes(k)){setCols(prev=>prev.filter(c=>c.key!==k));}else{const def=ALL_COLUMNS.find(c=>c.key===k);if(def)setCols(prev=>[...prev,{...def}]);}};const moveUp=i=>{if(i>0)setCols(prev=>{const n=[...prev];[n[i-1],n[i]]=[n[i],n[i-1]];return n;});};const moveDown=i=>{setCols(prev=>{if(i<prev.length-1){const n=[...prev];[n[i],n[i+1]]=[n[i+1],n[i]];return n;}return prev;});};return (<div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.4)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:500}} onClick={onClose}><div onClick={e=>e.stopPropagation()} style={{background:"#fff",borderRadius:12,padding:"24px",width:360,boxShadow:"0 10px 40px rgba(0,0,0,0.2)"}}><h3 style={{fontSize:"1rem",fontWeight:800,marginBottom:14}}>열 관리</h3><p style={{fontSize:"0.75rem",color:"#888",marginBottom:12}}>체크: 표시/숨기기 · 화살표: 순서</p>{allKeys.map(k=>{const active=activeKeys.includes(k);const idx=cols.findIndex(c=>c.key===k);const def=ALL_COLUMNS.find(c=>c.key===k);return (<div key={k} style={{display:"flex",alignItems:"center",gap:8,padding:"5px 0",borderBottom:"1px solid #f0f0f0"}}><input type="checkbox" checked={active} onChange={()=>toggle(k)} style={{accentColor:"#2563eb",width:16,height:16}}/><span style={{flex:1,fontSize:"0.85rem",fontWeight:active?600:400,color:active?"#111":"#aaa"}}>{def?.label}</span>{active&&<><button onClick={()=>moveUp(idx)} style={{border:"none",background:"none",cursor:"pointer",fontSize:"0.8rem",color:"#666"}}>▲</button><button onClick={()=>moveDown(idx)} style={{border:"none",background:"none",cursor:"pointer",fontSize:"0.8rem",color:"#666"}}>▼</button></>}</div>);})}<button onClick={onClose} style={{marginTop:14,width:"100%",padding:"8px",borderRadius:6,border:"none",background:"#111",color:"#fff",fontWeight:700,cursor:"pointer"}}>완료</button></div></div>);};

const DocBlock=({item,onConfirm})=>{const lines=item.rawText.split("\n");return (<div id={`job-${item.jNumber}`} style={{marginBottom:16,padding:"20px 28px",background:"#fff",borderLeft:item.isNew&&!item.confirmed?"5px solid #2563eb":item.blacklist?"5px solid #dc2626":"5px solid #e5e5e5",position:"relative",animation:item.isNew&&!item.confirmed?"glow 1.2s ease-in-out infinite":"none",boxShadow:item.isNew&&!item.confirmed?"0 0 18px rgba(37,99,235,0.35)":"0 1px 3px rgba(0,0,0,0.06)"}}>{item.blacklist&&<div style={{position:"absolute",inset:0,background:"rgba(220,38,38,0.06)",pointerEvents:"none",border:"1px solid rgba(220,38,38,0.15)"}}/>}{item.isNew&&!item.confirmed&&(<button onClick={()=>onConfirm(item.jNumber)} style={{position:"absolute",top:10,right:10,background:"#2563eb",color:"#fff",border:"none",borderRadius:8,padding:"7px 18px",fontSize:"0.85rem",fontWeight:700,cursor:"pointer",animation:"blink 0.8s step-end infinite",zIndex:2}}>★ NEW — 확인</button>)}<div style={{display:"flex",alignItems:"center",gap:12,marginBottom:8,position:"relative",zIndex:1}}><span style={{fontFamily:"'Consolas',monospace",fontSize:"1.05rem",fontWeight:800,background:item.jNumber.startsWith("N")?"#2563eb":"#111",color:"#fff",padding:"3px 14px",borderRadius:5}}>{item.jNumber}</span><span style={{fontSize:"0.95rem",color:"#444",fontWeight:600}}>{item.region} {item.city}</span><span style={{fontSize:"0.95rem",fontWeight:700,color:"#111"}}>{item.name}</span>{item.blacklist&&<span style={{fontSize:"0.75rem",background:"#dc2626",color:"#fff",padding:"3px 10px",borderRadius:999,fontWeight:800}}>BLACKLIST</span>}</div>{item.memo&&(<div style={{background:"#fffde7",border:"1px solid #f0e68c",padding:"10px 14px",borderRadius:5,marginBottom:12,fontSize:"0.9rem",lineHeight:1.7,color:"#5d4e0f",position:"relative",zIndex:1,animation:item.isNew&&!item.confirmed?"blink 0.8s step-end infinite":"none"}}><span style={{fontWeight:800,color:"#b8860b",fontSize:"0.75rem",marginRight:8}}>MEMO</span>{item.memo}</div>)}<div style={{fontFamily:"'Malgun Gothic',sans-serif",fontSize:"0.92rem",lineHeight:1.85,color:"#111",whiteSpace:"pre-wrap",wordBreak:"break-word",position:"relative",zIndex:1}}>{lines.map((line,i)=>{const t=line.trim();if(!t) return <div key={i} style={{height:6}}/>;const kv=t.match(/^(.+?)\s*:\s*(.+)$/);if(kv) return (<div key={i} style={{display:"flex",gap:6}}><span style={{color:"#555",fontWeight:600,minWidth:280,flexShrink:0}}>{kv[1]} :</span><span style={{color:"#111",fontWeight:500}}>{kv[2]}</span></div>);return <div key={i} style={{fontWeight:500}}>{t}</div>;})}</div></div>);};

// ─── 메인 ───────────────────────────────────────────────
export default function EmployerManagement(){
  const[data,setData]=useState(INIT_DATA);
  const[tab,setTab]=useState("active");
  const[mode,setMode]=useState("doc");
  const[fl,setFl]=useState({region:[],city:[],age:[],status:[]});
  const[cols,setCols]=useState(ALL_COLUMNS.map(c=>({...c})));
  const[showColMgr,setShowColMgr]=useState(false);
  const[mailPopup,setMailPopup]=useState(false);
  const[checked,setChecked]=useState(new Set());
  const cRef=useRef(null);

  const sf=useCallback((k,v)=>setFl(p=>({...p,[k]:v})),[]);
  const filtered=useMemo(()=>{
    let r=[...data];
    if(tab==="active")r=r.filter(d=>d.active&&!d.blacklist);
    else if(tab==="blacklist")r=r.filter(d=>d.blacklist);
    else if(tab==="mailing")r=r.filter(d=>!d.blacklist);
    if(fl.region.length)r=r.filter(d=>fl.region.includes(d.region));
    if(fl.city.length)r=r.filter(d=>fl.city.includes(d.city));
    if(fl.age.length)r=r.filter(d=>fl.age.includes(d.teachingAge));
    if(fl.status.length)r=r.filter(d=>fl.status.includes(d.status));
    return r;
  },[data,tab,fl]);

  const confirm=useCallback(jn=>setData(p=>p.map(d=>d.jNumber===jn?{...d,confirmed:true}:d)),[]);
  const addNew=useCallback(()=>{
    const id=nextId();
    setData(p=>[{jNumber:id,region:"서울",city:"강남",name:"NEW 어학원",email:"new@test.com",phone:"010-0000-0000",teachingAge:"Elementary",salary:"2,500,000",status:"new",blacklist:false,active:true,isNew:true,confirmed:false,memo:`(서울 강남 NEW어학원 010-0000-0000 new@test.com 신규접수 확인필요)`,rawText:`Seoul Gangnam\nJob. ${id}\nStarting Date : September\nTeaching Age : Elementary`},...p]);
    if(cRef.current)cRef.current.scrollTop=0;
  },[]);

  const toggleCheck=useCallback(jn=>setChecked(p=>{const n=new Set(p);n.has(jn)?n.delete(jn):n.add(jn);return n;}),[]);
  const checkAll=useCallback(()=>setChecked(new Set(filtered.map(d=>d.jNumber))),[filtered]);
  const uncheckAll=useCallback(()=>setChecked(new Set()),[]);
  const checkFirst10=useCallback(()=>setChecked(new Set(filtered.slice(0,10).map(d=>d.jNumber))),[filtered]);
  const checkedRecipients=useMemo(()=>filtered.filter(d=>checked.has(d.jNumber)),[filtered,checked]);

  const startResize=useCallback((idx,e)=>{e.preventDefault();const sx=e.clientX;const sw=cols[idx].w;const onMove=ev=>{setCols(prev=>{const n=[...prev];n[idx]={...n[idx],w:Math.max(40,sw+(ev.clientX-sx))};return n;});};const onUp=()=>{document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);};document.addEventListener("mousemove",onMove);document.addEventListener("mouseup",onUp);},[cols]);

  const newCount=data.filter(d=>d.isNew&&!d.confirmed&&d.active&&!d.blacklist).length;
  const hasF=Object.values(fl).some(v=>v.length>0);
  const isMailing=tab==="mailing";

  return (
    <div style={{display:"flex",minHeight:"100vh",fontFamily:"'Malgun Gothic',-apple-system,sans-serif",background:"#f0f0f0"}}>
      <style>{`
        @keyframes glow{0%,100%{box-shadow:0 0 10px rgba(37,99,235,0.2)}50%{box-shadow:0 0 28px rgba(37,99,235,0.55)}}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
        @keyframes slideDown{from{opacity:0;transform:translateY(-18px)}to{opacity:1;transform:translateY(0)}}
        *{box-sizing:border-box;margin:0}
        ::-webkit-scrollbar{width:8px}::-webkit-scrollbar-thumb{background:#b0b0b0;border-radius:4px}
        ::selection{background:#2563eb;color:#fff}
        .rh{position:absolute;right:0;top:0;bottom:0;width:5px;cursor:col-resize;background:transparent}.rh:hover,.rh:active{background:#2563eb}
      `}</style>

      {/* 사이드바 */}
      <div style={{width:170,background:"#fff",borderRight:"1px solid #ddd",padding:"14px 0",flexShrink:0}}>
        <div style={{padding:"0 14px 14px",borderBottom:"1px solid #eee"}}><h1 style={{fontSize:"1.1rem",fontWeight:800}}>BRIDGE</h1><span style={{fontSize:"0.7rem",color:"#999"}}>Admin</span></div>
        <nav style={{padding:"8px 6px"}}>{["대시보드","수신함","원어민 관리","구인자관리","인터뷰","프로필 매칭","게시판 관리","게시글","보드 관리","배너"].map(m=> (<button key={m} style={{display:"block",width:"100%",textAlign:"left",padding:"7px 11px",borderRadius:5,border:"none",background:m==="구인자관리"?"#dbeafe":"transparent",color:m==="구인자관리"?"#1d4ed8":"#444",fontSize:"0.85rem",fontWeight:m==="구인자관리"?700:400,cursor:"pointer",marginBottom:1}}>{m}</button>))}</nav>
      </div>

      {/* 메인 */}
      <div style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>
        <div style={{background:"#fff",borderBottom:"1px solid #ddd",padding:"14px 22px"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
            <div><h2 style={{fontSize:"1.4rem",fontWeight:800,color:"#111"}}>구인자관리</h2><span style={{fontSize:"0.85rem",color:"#666",fontWeight:500}}>{filtered.length}건{isMailing&&checked.size>0&&` · ${checked.size}명 선택`}</span></div>
            <div style={{display:"flex",gap:8,alignItems:"center"}}>
              {!isMailing&&<div style={{display:"flex",border:"2px solid #111",overflow:"hidden",borderRadius:6}}>{[{id:"doc",l:"워드뷰"},{id:"table",l:"엑셀뷰"}].map(v=> (<button key={v.id} onClick={()=>setMode(v.id)} style={{padding:"6px 16px",border:"none",background:mode===v.id?"#111":"#fff",color:mode===v.id?"#fff":"#111",fontSize:"0.88rem",fontWeight:700,cursor:"pointer"}}>{v.l}</button>))}</div>}
              {(mode==="table"||isMailing)&&<button onClick={()=>setShowColMgr(true)} style={{padding:"6px 12px",borderRadius:6,border:"1px solid #999",background:"#fff",fontSize:"0.78rem",fontWeight:600,cursor:"pointer",color:"#444"}}>열 관리</button>}
              <button onClick={addNew} style={{padding:"6px 18px",borderRadius:6,border:"none",background:"#2563eb",color:"#fff",fontSize:"0.88rem",fontWeight:700,cursor:"pointer"}}>+ 새 접수</button>
            </div>
          </div>

          {/* 탭 */}
          <div style={{display:"flex",borderBottom:"3px solid #eee",marginBottom:10}}>
            {[
              {id:"active",l:"활발한 채용보기",c:data.filter(d=>d.active&&!d.blacklist).length,color:"#2563eb"},
              {id:"all",l:"전체보기",c:data.length,color:"#111"},
              {id:"mailing",l:"메일링",c:data.filter(d=>!d.blacklist).length,color:"#f59e0b"},
              {id:"blacklist",l:"블랙리스트",c:data.filter(d=>d.blacklist).length,color:"#dc2626"},
            ].map(t=>{
              const nc=t.id==="active"?newCount:0;
              return (<button key={t.id} onClick={()=>{setTab(t.id);if(t.id==="mailing")setMode("table");setChecked(new Set());}} style={{padding:"8px 20px",border:"none",background:"transparent",borderBottom:tab===t.id?`3px solid ${t.color}`:"3px solid transparent",color:tab===t.id?t.color:"#888",fontSize:"0.92rem",fontWeight:tab===t.id?700:500,cursor:"pointer",marginBottom:-3,position:"relative"}}>
                {nc>0&&<span style={{position:"absolute",top:-4,left:"50%",transform:"translateX(-50%)",background:"#dc2626",color:"#fff",fontSize:"0.62rem",fontWeight:800,padding:"1px 8px",borderRadius:10,animation:"blink 0.8s step-end infinite",whiteSpace:"nowrap",boxShadow:"0 1px 4px rgba(220,38,38,0.4)"}}>NEW {nc}</span>}
                {t.l}<span style={{marginLeft:6,fontSize:"0.72rem",fontWeight:700,background:tab===t.id?(t.id==="blacklist"?"#fecaca":t.id==="mailing"?"#fef3c7":"#dbeafe"):"#f0f0f0",color:tab===t.id?t.color:"#999",padding:"2px 8px",borderRadius:12}}>{t.c}</span>
              </button>);
            })}
          </div>

          {isMailing&&(<div style={{display:"flex",gap:6,alignItems:"center",marginBottom:10,flexWrap:"wrap"}}>
            <button onClick={checkAll} style={{padding:"5px 12px",borderRadius:5,border:"1px solid #2563eb",background:"#eff6ff",color:"#2563eb",fontSize:"0.8rem",fontWeight:600,cursor:"pointer"}}>전체선택</button>
            <button onClick={uncheckAll} style={{padding:"5px 12px",borderRadius:5,border:"1px solid #999",background:"#fff",color:"#666",fontSize:"0.8rem",fontWeight:500,cursor:"pointer"}}>선택취소</button>
            <button onClick={checkFirst10} style={{padding:"5px 12px",borderRadius:5,border:"1px solid #f59e0b",background:"#fef3c7",color:"#92400e",fontSize:"0.8rem",fontWeight:600,cursor:"pointer"}}>10개선택</button>
            <span style={{fontSize:"0.82rem",fontWeight:600,color:checked.size>0?"#2563eb":"#aaa"}}>{checked.size}명 선택</span>
            <div style={{flex:1}}/>
            <button onClick={()=>{if(!checked.size){alert("발송할 대상을 선택하세요");return;}setMailPopup(true);}} style={{padding:"7px 20px",borderRadius:6,border:"none",background:checked.size>0?"#2563eb":"#94a3b8",color:"#fff",fontSize:"0.88rem",fontWeight:700,cursor:checked.size>0?"pointer":"not-allowed"}}>메일 보내기 ({checked.size}명)</button>
          </div>)}

          <div style={{display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
            <XF label="전체 지역" options={uniq(data,"region")} selected={fl.region} onChange={v=>sf("region",v)} w={100}/>
            <XF label="전체 도시" options={uniq(data,"city")} selected={fl.city} onChange={v=>sf("city",v)} w={100}/>
            <XF label="전체 대상" options={uniq(data,"teachingAge")} selected={fl.age} onChange={v=>sf("age",v)} w={120}/>
            <XF label="상태" options={uniq(data,"status")} selected={fl.status} onChange={v=>sf("status",v)} w={80}/>
            {hasF&&<button onClick={()=>setFl({region:[],city:[],age:[],status:[]})} style={{padding:"5px 12px",border:"1px solid #ccc",background:"#fff",fontSize:"0.78rem",color:"#888",cursor:"pointer",borderRadius:4}}>초기화</button>}
            <span style={{fontSize:"0.72rem",color:"#aaa",marginLeft:8}}>Ctrl+F 검색</span>
          </div>
        </div>

        <div ref={cRef} style={{flex:1,overflow:"auto",padding:(mode==="doc"&&!isMailing)?"16px 22px":0}}>
          {mode==="doc"&&!isMailing&&(
            <div style={{maxWidth:860,margin:"0 auto"}}><div style={{background:"#fff",padding:"28px 0",boxShadow:"0 1px 6px rgba(0,0,0,0.08)"}}>
              <div style={{textAlign:"center",padding:"0 32px 16px",borderBottom:"3px solid #111",margin:"0 28px 18px"}}><h1 style={{fontSize:"1.1rem",fontWeight:800,letterSpacing:"0.1em"}}>BRIDGE — 구인자 채용공고</h1><p style={{fontSize:"0.78rem",color:"#999",marginTop:2}}>{filtered.length}건</p></div>
              {filtered.map((item,i)=> (<div key={item.jNumber} style={{padding:"0 28px",animation:item.isNew?"slideDown 0.35s ease":"none"}}><DocBlock item={item} onConfirm={confirm}/>{(i+1)%2===0&&i<filtered.length-1&&<div style={{display:"flex",alignItems:"center",padding:"12px 0"}}><div style={{flex:1,height:1,background:"#ccc"}}/><span style={{padding:"0 14px",fontSize:"0.7rem",color:"#aaa",fontFamily:"monospace"}}>— page {Math.floor(i/2)+2} —</span><div style={{flex:1,height:1,background:"#ccc"}}/></div>}</div>))}
              {!filtered.length&&<div style={{textAlign:"center",padding:60,color:"#bbb",fontSize:"1rem"}}>검색 결과 없음</div>}
            </div></div>
          )}

          {(mode==="table"||isMailing)&&(
            <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",fontSize:"0.85rem",background:"#fff",tableLayout:"fixed",width:(isMailing?50:0)+cols.reduce((a,c)=>a+c.w,0)+(isMailing?60:0)}}>
              <thead><tr style={{background:"#f3f3f3"}}>
                {isMailing&&<th style={{width:50,padding:"10px 8px",textAlign:"center",fontWeight:700,color:"#111",fontSize:"0.82rem",borderBottom:"3px solid #111",position:"sticky",top:0,background:"#f3f3f3",zIndex:10}}><input type="checkbox" checked={checked.size===filtered.length&&filtered.length>0} onChange={()=>checked.size===filtered.length?uncheckAll():checkAll()} style={{accentColor:"#2563eb",width:16,height:16}}/></th>}
                {cols.map((col,ci)=> (<th key={col.key} style={{width:col.w,minWidth:40,padding:"10px 8px",textAlign:"left",fontWeight:700,color:"#111",fontSize:"0.82rem",borderBottom:"3px solid #111",whiteSpace:"nowrap",position:"sticky",top:0,background:"#f3f3f3",zIndex:10,userSelect:"none",overflow:"hidden"}}>{col.label}<div className="rh" onMouseDown={e=>startResize(ci,e)}/></th>))}
                {isMailing&&<th style={{width:60,padding:"10px",textAlign:"center",fontWeight:700,borderBottom:"3px solid #111",position:"sticky",top:0,background:"#f3f3f3",zIndex:10,fontSize:"0.82rem"}}>메뉴</th>}
              </tr></thead>
              <tbody>{filtered.map(item=>{
                const isGlow=item.isNew&&!item.confirmed;const isBL=item.blacklist;const isChk=checked.has(item.jNumber);
                return (<tr key={item.jNumber} style={{borderBottom:"1px solid #e8e8e8",animation:isGlow?"glow 1.2s ease-in-out infinite":"none",background:isGlow?"#eff6ff":isBL?"rgba(220,38,38,0.06)":isChk?"#fffbeb":"transparent"}}
                  onMouseEnter={e=>{if(!isGlow&&!isBL&&!isChk)e.currentTarget.style.background="#f8f8f8"}}
                  onMouseLeave={e=>{if(!isGlow&&!isBL&&!isChk)e.currentTarget.style.background="";}}>
                  {isMailing&&<td style={{padding:"8px",textAlign:"center"}}><input type="checkbox" checked={isChk} onChange={()=>toggleCheck(item.jNumber)} style={{accentColor:"#2563eb",width:16,height:16}}/></td>}
                  {cols.map(c=>{
                    if(c.key==="jNumber") return <td key={c.key} style={{padding:"8px",width:c.w}}><span style={{fontFamily:"'Consolas',monospace",fontSize:"0.88rem",fontWeight:800,background:item.jNumber.startsWith("N")?"#2563eb":"#111",color:"#fff",padding:"2px 10px",borderRadius:4,animation:isGlow?"blink 0.8s step-end infinite":"none"}}>{item.jNumber}</span></td>;
                    if(c.key==="memo") return <td key={c.key} style={{padding:"8px",width:c.w}}>{item.memo? <div style={{background:"#fffde7",border:"1px solid #f0e68c",padding:"4px 8px",borderRadius:4,fontSize:"0.78rem",color:"#5d4e0f",lineHeight:1.5,whiteSpace:"normal",wordBreak:"break-word"}}>{item.memo}</div>:<span style={{color:"#ccc"}}>—</span>}</td>;
                    if(c.key==="status") return <td key={c.key} style={{padding:"8px",width:c.w}}>{isGlow? <button onClick={()=>confirm(item.jNumber)} style={{background:"#2563eb",color:"#fff",border:"none",borderRadius:5,padding:"4px 12px",fontSize:"0.78rem",fontWeight:700,cursor:"pointer",animation:"blink 0.8s step-end infinite"}}>New ✓</button>:isBL? <span style={{fontSize:"0.78rem",fontWeight:800,color:"#dc2626",background:"#fecaca",padding:"2px 8px",borderRadius:4}}>BLOCK</span>: <span style={{fontSize:"0.78rem",fontWeight:600,color:item.status==="new"?"#2563eb":"#16a34a"}}>{item.status==="new"?"New":"Active"}</span>}</td>;
                    return <td key={c.key} style={{padding:"8px",width:c.w,fontWeight:c.key==="name"?700:c.key==="region"?600:400,color:c.key==="name"||c.key==="region"?"#111":"#333",fontSize:c.key==="email"||c.key==="phone"?"0.8rem":"0.85rem"}}>{item[c.key]||"—"}</td>;
                  })}
                  {isMailing&&<td style={{padding:"8px",textAlign:"center"}}><button onClick={()=>{setChecked(new Set([item.jNumber]));setMailPopup(true);}} style={{background:"none",border:"1px solid #ccc",borderRadius:4,padding:"3px 8px",fontSize:"0.72rem",cursor:"pointer",color:"#555"}}>메일</button></td>}
                </tr>);
              })}</tbody>
            </table></div>
          )}
        </div>
      </div>

      {showColMgr&&<ColManager cols={cols} setCols={setCols} onClose={()=>setShowColMgr(false)}/>}
      {mailPopup&&<MailComposer recipients={checkedRecipients} onClose={()=>setMailPopup(false)}/>}
    </div>
  );
}
