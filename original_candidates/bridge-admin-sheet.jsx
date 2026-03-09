'use client';
import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";

const STAGES=[{key:"none",label:"\u2014",color:"#fff",text:"#000"},{key:"interview",label:"\uc778\ud130\ubdf0",color:"#fef9c3",text:"#000"},{key:"proposal",label:"\uacc4\uc57d\uc81c\uc548",color:"#fde68a",text:"#000"},{key:"signed",label:"\uc11c\uba85\uc644\ub8cc",color:"#bbf7d0",text:"#000"},{key:"guide_sent",label:"\uc548\ub0b4\ubc1c\uc1a1",color:"#93c5fd",text:"#000"},{key:"guide_done",label:"\uc548\ub0b4\uc644\ub8cc",color:"#dbeafe",text:"#000"},{key:"caution",label:"\uc8fc\uc758",color:"#fecaca",text:"#000"},{key:"lost",label:"\ub450\uc808",color:"#e5e7eb",text:"#666"}];
const MTP=[{key:"interview",label:"Interview",s:"[BRIDGE] Interview",b:"Dear {{name}},\n\nInterview arranged.\n\nBRIDGE"},{key:"contract",label:"Contract",s:"[BRIDGE] Contract",b:"Dear {{name}},\n\nContract attached.\n\nBRIDGE"},{key:"visa",label:"Visa",s:"[BRIDGE] Visa Guide",b:"Dear {{name}},\n\nVisa guide attached.\n\nBRIDGE"},{key:"settle",label:"Settlement",s:"[BRIDGE] Settlement",b:"Dear {{name}},\n\nSettlement guide.\n\nBRIDGE"},{key:"tax",label:"Tax",s:"[BRIDGE] Tax Info",b:"Dear {{name}},\n\nTax info.\n\nBRIDGE"},{key:"transfer",label:"Transfer",s:"[BRIDGE] Transfer",b:"Dear {{name}},\n\nTransfer guide.\n\nBRIDGE"},{key:"renewal",label:"Renewal",s:"[BRIDGE] Renewal",b:"Dear {{name}},\n\nRenewal info.\n\nBRIDGE"},{key:"custom",label:"Write",s:"",b:""}];
const MTAGS=[{key:"guide_done",label:"\uac00\uc774\ub4dc\u2713",c:"#16a34a"},{key:"contract_sent",label:"\uacc4\uc57d\ubc1c\uc1a1",c:"#2563eb"},{key:"contract_done",label:"\uacc4\uc57d\u2713",c:"#16a34a"},{key:"visa_sent",label:"\ube44\uc790\u2713",c:"#7c3aed"},{key:"housing_sent",label:"\uc219\uc18c\u2713",c:"#0891b2"},{key:"ot_done",label:"OT\u2713",c:"#16a34a"}];
const H_OPTS=["\uc219\uc18c\uc81c\uacf5","\uc6d4\uc138\uc81c\uacf5","\ubcf4\uc99d+\uc6d4\uc138","\ubd88\ud544\uc694","\uc790\uccb4"];
const FEE_OPTS=["\uc120\uae08\uc644\ub8cc","\uc794\uae08\uc644\ub8cc","\uc77c\uc2dc\ub0a9\uc644\ub8cc","\uc5f0\uccb4\uc911","14\uc77c\uc5f0\uccb4","\uc7a5\uae30\uc5f0\uccb4"];
const PROC_OPTS=["\uc9c4\ud589\uc911","\uc644\ub8cc","\ubcf4\ub958","\ucde8\uc18c","\ubb34\ub2e8\uc774\ud0c8"];
const initCols=()=>[
{key:"rowNum",label:"#",w:42,type:"idx",v:false},{key:"email",label:"메일",w:190,type:"t",v:true},{key:"name",label:"이름",w:140,type:"t",v:true},{key:"photo",label:"사진",w:65,type:"photo",v:true},{key:"mgtNum",label:"번호",w:65,type:"t",v:true},{key:"nationality",label:"국적",w:62,type:"t",v:true},{key:"background",label:"배경",w:75,type:"t",v:true},{key:"age",label:"나이",w:46,type:"t",v:true},{key:"gender",label:"성별",w:46,type:"t",v:true},{key:"currentLoc",label:"현위치",w:62,type:"t",v:true},{key:"startDate",label:"시작",w:78,type:"t",v:true},{key:"university",label:"대상",w:50,type:"t",v:true},{key:"prefRegion",label:"선호지역",w:75,type:"t",v:true},{key:"reference",label:"레퍼런스/근무처확인",w:210,type:"long",v:true},{key:"totalExp",label:"총경력",w:62,type:"t",v:true},{key:"notice",label:"한국",w:52,type:"t",v:true},{key:"preference",label:"선호사항/리크루터",w:190,type:"long",v:true},{key:"applied",label:"인터뷰지원한곳",w:175,type:"long",v:true},{key:"proposal",label:"포지션제안/진행",w:175,type:"long",v:true},{key:"mailAction",label:"메일발송",w:85,type:"mail",v:true},{key:"mailStatus",label:"발송상태",w:210,type:"tags",v:true},{key:"stage",label:"진행단계",w:140,type:"stage",v:true},{key:"curSalary",label:"현급여",w:62,type:"t",v:true},{key:"hopeSalary",label:"희망",w:62,type:"t",v:true},{key:"interviewCol",label:"시간",w:78,type:"t",v:true},{key:"degree",label:"학위",w:58,type:"t",v:true},{key:"major",label:"전공",w:72,type:"t",v:true},{key:"cert",label:"자격증",w:70,type:"t",v:true},{key:"docs",label:"서류",w:65,type:"t",v:true},{key:"health",label:"건강",w:52,type:"t",v:true},{key:"tattooPiercing",label:"동물피어",w:75,type:"t",v:true},{key:"family",label:"가족",w:52,type:"t",v:true},{key:"married",label:"결혼",w:48,type:"t",v:true},{key:"housing",label:"숙소",w:100,type:"dropdown",opts:H_OPTS,v:true},{key:"religion",label:"종교",w:52,type:"t",v:true},{key:"e2visa",label:"비자",w:52,type:"t",v:true},{key:"kakao",label:"카톡",w:100,type:"t",v:true},{key:"phone",label:"번호",w:125,type:"t",v:true},{key:"crimCheck",label:"범죄",w:55,type:"t",v:true},{key:"domesticCrim",label:"국범",w:70,type:"t",v:true},{key:"infoProvide",label:"정보",w:65,type:"t",v:true},{key:"verified",label:"사실",w:65,type:"t",v:true},{key:"source",label:"경로",w:65,type:"t",v:true},{key:"timestamp",label:"타임",w:85,type:"t",v:true},{key:"hired",label:"채용",w:65,type:"t",v:true},{key:"wage",label:"임금",w:60,type:"t",v:true},{key:"moveIn",label:"개시",w:70,type:"t",v:true},{key:"housingCost",label:"숙박",w:55,type:"t",v:true},{key:"introFee",label:"비용",w:100,type:"dropdown",opts:FEE_OPTS,v:true},{key:"process",label:"처리",w:100,type:"dropdown",opts:PROC_OPTS,v:true},{key:"history",label:"과거기록",w:150,type:"long",v:true}
];
const SROWS_I=[{id:"s1",label:"\uc778\ud130\ubdf0",bg:"#fff",text:"\uc544\ub974\ud14c4977 \uac15\uc11c\ud504\ud30c5513 5271",h:40},{id:"s2",label:"\uc81c\uc548",bg:"#ffff00",text:"\uc5d0\ub354\ube145092",h:40},{id:"s3",label:"\uccb4\uacb0",bg:"#ff9900",text:"\ud0a4\ube444918/\ud574\uc6b4\ud790\uc0ac4583/\uc2e4\ub9ac4763/\uc11c\ucd08\ud504\ud30c4681",h:40}];
const mkRow=(id,cat)=>{const r={id,category:cat,stage:"none",mailStatus:"",photoUrl:"",photoSize:50};initCols().forEach(c=>{if(!["rowNum","stage","mailStatus","photo"].includes(c.key))r[c.key]="";});return r;};
const mkD=()=>({active:[
  {id:59,email:"aceyumull@gmail.com",name:"Ace Darrick Yumul",photoUrl:"",photoSize:50,mgtNum:"5671",arc:"E2 26/06/28",nationality:"\ubbf8\uad6d",background:"EPIK 2yr",age:"91",gender:"M",currentLoc:"\uc11c\uc6b8",startDate:"26.03.08",university:"\ubb34",prefRegion:"\uc218\ub3c4\uad8c",reference:"SLA\uc804\uc8fc2511",totalExp:"7\ub144",notice:"",preference:"LOR",applied:"",proposal:"",mailAction:"",mailStatus:"",stage:"interview",curSalary:"2.2",hopeSalary:"",interviewCol:"",degree:"\ud559\uc0ac",major:"\uacbd\uc601",cert:"",docs:"",health:"",tattooPiercing:"",family:"",married:"",housing:"\uc219\uc18c\uc81c\uacf5",religion:"",e2visa:"E2",kakao:"aceyumul",phone:"010-1234-5678",crimCheck:"",domesticCrim:"",infoProvide:"",verified:"",source:"CL",timestamp:"26.01.15",hired:"",wage:"",moveIn:"",housingCost:"",introFee:"",process:"",history:"",category:"active"},
  {id:53,email:"sarahm@gmail.com",name:"Sarah Mitchell",photoUrl:"",photoSize:50,mgtNum:"5680",arc:"E2 31/12/2025",nationality:"\uce90\ub098\ub2e4",background:"Hagwon",age:"97",gender:"F",currentLoc:"\ud55c\uad6d",startDate:"26.05.01",university:"\uc720",prefRegion:"\ubd80\uc0b0",reference:"ABC Gijang\n010-9876-5432",totalExp:"1\ub144",notice:"",preference:"\ucd08\ub4f1/\uc720\uce58\uc6d0",applied:"\uae30\uc7a5",proposal:"\uae30\uc7a5A \uc81c\uc548",mailAction:"",mailStatus:"guide_done,contract_sent",stage:"proposal",curSalary:"2.3",hopeSalary:"2.5",interviewCol:"3/5",degree:"\ud559\uc0ac",major:"\uad50\uc721",cert:"CELTA",docs:"O",health:"\uc591\ud638",tattooPiercing:"X/\uadc0",family:"\ubbf8\ud63c",married:"X",housing:"\uc6d4\uc138\uc81c\uacf5",religion:"\uae30\ub3c5\uad50",e2visa:"O",kakao:"sarah_m93",phone:"010-5555-1234",crimCheck:"\uc644\ub8cc",domesticCrim:"\uc5c6\uc74c",infoProvide:"O",verified:"O",source:"FB",timestamp:"26.02.01",hired:"",wage:"",moveIn:"",housingCost:"",introFee:"\uc120\uae08\uc644\ub8cc",process:"\uc9c4\ud589\uc911",history:"",category:"active"},
  {id:54,email:"jamesw@hotmail.com",name:"James Watson",photoUrl:"",photoSize:50,mgtNum:"5695",arc:"E2 2026.09.11",nationality:"\uc601\uad6d",background:"5yr",age:"89",gender:"M",currentLoc:"\ud55c\uad6d",startDate:"26.03.15",university:"\uc720",prefRegion:"\uc11c\uc6b8",reference:"XYZ Gangnam\n010-3333-4444",totalExp:"5\ub144",notice:"",preference:"\uc131\uc778/\ube44\uc988\ub2c8\uc2a4",applied:"\uac15\ub0a8/\uc11c\ucd08",proposal:"",mailAction:"",mailStatus:"guide_done,contract_done",stage:"guide_sent",curSalary:"3.2",hopeSalary:"3.5",interviewCol:"\uc644\ub8cc",degree:"\ud559\uc0ac",major:"\uc601\ubb38\ud559",cert:"DELTA",docs:"O",health:"\uc591\ud638",tattooPiercing:"\ud314/X",family:"\uae30\ud63c",married:"O",housing:"\uc790\uccb4",religion:"\ubb34",e2visa:"F-2",kakao:"james_w_uk",phone:"010-7777-8888",crimCheck:"\uc644\ub8cc",domesticCrim:"\uc5c6\uc74c",infoProvide:"O",verified:"O",source:"\uc9c1\uc811",timestamp:"26.01.20",hired:"",wage:"",moveIn:"",housingCost:"",introFee:"\uc77c\uc2dc\ub0a9\uc644\ub8cc",process:"\uc644\ub8cc",history:"\uc804\uc9c1 1\ub144",category:"active"}
],past:[{id:101,email:"tomh@gmail.com",name:"Tom Hughes",photoUrl:"",photoSize:50,mgtNum:"5500",arc:"E2 \ub9cc\ub8cc",nationality:"\uc544\uc77c\ub79c\ub4dc",background:"2yr",age:"91",gender:"M",currentLoc:"\uadc0\uad6d",startDate:"25.03.01",university:"\uc720",prefRegion:"\uc11c\uc6b8",reference:"GHI\n010-2222-3333",totalExp:"2\ub144",notice:"",preference:"",applied:"",proposal:"\uc885\ub85cA\u2192\uc644\ub8cc",mailAction:"",mailStatus:"guide_done,contract_done,ot_done",stage:"guide_done",curSalary:"2.5",hopeSalary:"",interviewCol:"\uc644\ub8cc",degree:"\ud559\uc0ac",major:"\uc5ed\uc0ac",cert:"",docs:"O",health:"\uc591\ud638",tattooPiercing:"X",family:"\ubbf8\ud63c",married:"X",housing:"\uc219\uc18c\uc81c\uacf5",religion:"\uac00\ud1a8\ub9ad",e2visa:"\ub9cc\ub8cc",kakao:"tom_ire",phone:"010-1111-2222",crimCheck:"\uc644\ub8cc",domesticCrim:"\uc5c6\uc74c",infoProvide:"O",verified:"O",source:"FB",timestamp:"25.01",hired:"O",wage:"2.5",moveIn:"25.03",housingCost:"\ud559\uc6d0",introFee:"\uc794\uae08\uc644\ub8cc",process:"\uc644\ub8cc",history:"\uacc4\uc57d\ub9cc\ub8cc",category:"past"}],blacklist:[{id:201,email:"chrisx@gmail.com",name:"Chris Xavier",photoUrl:"",photoSize:50,mgtNum:"5400",arc:"",nationality:"\ubbf8\uad6d",background:"",age:"94",gender:"M",currentLoc:"\ubd88\uba85",startDate:"25.06",university:"",prefRegion:"\uc11c\uc6b8",reference:"",totalExp:"",notice:"",preference:"",applied:"",proposal:"",mailAction:"",mailStatus:"",stage:"lost",curSalary:"",hopeSalary:"",interviewCol:"",degree:"",major:"",cert:"",docs:"",health:"",tattooPiercing:"",family:"",married:"",housing:"",religion:"",e2visa:"\ucde8\uc18c",kakao:"chris_x",phone:"010-9999-0000",crimCheck:"",domesticCrim:"",infoProvide:"",verified:"",source:"CL",timestamp:"25.05",hired:"X",wage:"",moveIn:"",housingCost:"",introFee:"\uc7a5\uae30\uc5f0\uccb4",process:"\ubb34\ub2e8\uc774\ud0c8",history:"\ubb34\ub2e8\uc774\ud0c8",category:"blacklist"}]});
const PC=["#3b82f6","#ef4444","#22c55e","#eab308","#a855f7","#06b6d4","#f43e5e","#84cc16","#d946ef","#14b8a6"];
const TABS=[{key:"active",label:"\uad6c\uc9c1\ud65c\ub3d9\uc911",color:"#2563eb",bg:"#dbeafe",accent:"#1d4ed8",icon:"\ud83d\udc64"},{key:"past",label:"\uccb4\uacb0\uc644\ub8cc",color:"#16a34a",bg:"#dcfce7",accent:"#166534",icon:"\u2705"},{key:"blacklist",label:"\ube14\ub799\ub9ac\uc2a4\ud2b8",color:"#dc2626",bg:"#fee2e2",accent:"#991b1b",icon:"\u26d4"},{key:"all",label:"\uc804\uccb4",color:"#0f172a",bg:"#e2e8f0",accent:"#020617",icon:"\ud83d\udccb"}];
const SK="bridge-v11";
function Hov({children,bg,style,...p}){const[h,setH]=useState(false);return <div onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{...style,background:h?(bg||"#f0f0f0"):(style?.background||"transparent")}} {...p}>{children}</div>;}

const NAV=[{key:"dashboard",icon:"⊞",label:"대시보드"},{key:"candidates",icon:"👤",label:"원어민 관리"},{key:"sheet",icon:"📊",label:"지원자 관리"},{key:"mail",icon:"✉",label:"메일 발송"},{key:"jobs",icon:"💼",label:"채용공고"},{key:"settings",icon:"⚙",label:"설정"}];

class ErrBound extends React.Component{constructor(p){super(p);this.state={err:null};}static getDerivedStateFromError(e){return{err:e};}render(){if(this.state.err)return(<div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"100vh",flexDirection:"column",gap:16,fontFamily:"sans-serif"}}><div style={{fontSize:48}}>⚠️</div><div style={{fontSize:20,fontWeight:700,color:"#dc2626"}}>{"오류가 발생했습니다"}</div><div style={{fontSize:14,color:"#6b7280",maxWidth:400,textAlign:"center"}}>{String(this.state.err?.message||this.state.err)}</div><button onClick={()=>this.setState({err:null})} style={{padding:"10px 24px",background:"#2563eb",color:"#fff",border:"none",borderRadius:8,fontSize:15,cursor:"pointer",fontWeight:700}}>{"↺ 다시 시도"}</button></div>);return this.props.children;}}

export function BridgeAdminSheetWrapper(){return <ErrBound><B/></ErrBound>;}

function B(){
  const[data,setData]=useState(mkD);const[tab,setTab]=useState("active");const[cols,setCols]=useState(initCols);const[rh,setRh]=useState({});const[q,setQ]=useState("");const[filters,setFi]=useState({});const[showFi,setShowFi]=useState(null);const[ec,setEc]=useState(null);const[ev,setEv]=useState("");const[sel,setSel]=useState(new Set());const[ctx,setCtx]=useState(null);const[sk,setSk]=useState(null);const[sd,setSd]=useState("asc");const[ready,setReady]=useState(false);const[mmOpen,setMmOpen]=useState(false);const[mmRecs,setMmRecs]=useState([]);const[mmTmpl,setMmTmpl]=useState("custom");const[mmSubj,setMmSubj]=useState("");const[mmBody,setMmBody]=useState("");const[mmFiles,setMmFiles]=useState([]);const[mmFrom,setMmFrom]=useState("gmail");const[mmSel,setMmSel]=useState(new Set());const[mmImportant,setMmImportant]=useState(false);const[mmEditorMode,setMmEditorMode]=useState("editor");const[ivOpen,setIvOpen]=useState(false);const[ivName,setIvName]=useState("");const[ivDate,setIvDate]=useState("");const[ivTime,setIvTime]=useState("");const[ivDur,setIvDur]=useState(60);const[ivNote,setIvNote]=useState("");const[ivList,setIvList]=useState([]);const[ivRec,setIvRec]=useState(null);const[ivSearch,setIvSearch]=useState("");const[ivMailSubj,setIvMailSubj]=useState("");const[ivMailBody,setIvMailBody]=useState("");const[ivShowDrop,setIvShowDrop]=useState(false);const[ivSchool,setIvSchool]=useState("");const[ivMeetLink,setIvMeetLink]=useState("");const[ivLoading,setIvLoading]=useState(false);const[ivEventId,setIvEventId]=useState("");const[frozenCols,setFC]=useState(3);const[colMenu,setColMenu]=useState(null);const[rnCol,setRnCol]=useState(null);const[rnVal,setRnVal]=useState("");const[photoTarget,setPT]=useState(null);const[selCol,setSelCol]=useState(null);
  // 셀별 서식: {[id_key]: {fontSize, fontWeight, bgColor, color}}
  const[cellFmt,setCellFmt]=useState(()=>{try{const s=localStorage.getItem(SK+"-fmt");return s?JSON.parse(s):{};}catch(e){return{};}});
  useEffect(()=>{try{localStorage.setItem(SK+"-fmt",JSON.stringify(cellFmt));}catch(e){};},[cellFmt]);
  // 선택된 셀 서식 상태 (툴바용) + 마지막 클릭 셀
  const[selFmtSize,setSelFmtSize]=useState(15);
  const[selFmtBold,setSelFmtBold]=useState(false);
  const[selFmtBg,setSelFmtBg]=useState("#ffffff");
  const[selFmtColor,setSelFmtColor]=useState("#000000");
  const[lastCell,setLastCell]=useState(null); // {id, key}
  // 서식 즉시 적용 함수
  const[theadH,setTheadH]=useState(()=>{try{return Number(localStorage.getItem(SK+"-thH"))||36;}catch(e){return 36;}});
  const thHRef=useRef(theadH);useEffect(()=>{thHRef.current=theadH;try{localStorage.setItem(SK+"-thH",theadH);}catch(e){};},[theadH]);
  // ★ Undo
  const[newSeen,setNewSeen]=useState(false);
  const[undoStack,setUS]=useState([]);
  const[blink,setBlink]=useState(true);
  const[autoSaveTime,setAutoSaveTime]=useState(new Date());
  const[fontSize,setFontSize]=useState(15);
  // ★ 메모패널 state — 테이블과 완전 분리
  const[memo,setMemo]=useState(()=>{try{const s=localStorage.getItem(SK+"-memo");return s||"인터뷰:\n제안:\n체결:";}catch(e){return"인터뷰:\n제안:\n체결:";}});
  const[memoH,setMemoH]=useState(()=>{try{return Number(localStorage.getItem(SK+"-memoh"))||80;}catch(e){return 80;}});
  const memoHRef=useRef(memoH);
  useEffect(()=>{memoHRef.current=memoH;try{localStorage.setItem(SK+"-memoh",memoH);}catch(e){};},[memoH]);
  useEffect(()=>{try{localStorage.setItem(SK+"-memo",memo);}catch(e){};},[memo]);
  const pushU=useCallback(()=>{setUS(p=>[...p,JSON.parse(JSON.stringify(data))].slice(-10));},[data]);
  const undo=useCallback(()=>{if(!undoStack.length)return;setData(undoStack[undoStack.length-1]);setUS(p=>p.slice(0,-1));},[undoStack]);
  const eR=useRef(null);const topRef=useRef(null);const tblRef=useRef(null);const syncR=useRef(false);const fRef=useRef(null);const editorRef=useRef(null);const savedSelRef=useRef(null);const photoRef=useRef(null);
  const onTS=useCallback(()=>{if(syncR.current)return;syncR.current=true;if(tblRef.current)tblRef.current.scrollLeft=topRef.current.scrollLeft;syncR.current=false;},[]);
  const onBS=useCallback(()=>{if(syncR.current)return;syncR.current=true;if(topRef.current)topRef.current.scrollLeft=tblRef.current.scrollLeft;syncR.current=false;},[]);
  useEffect(()=>{try{const s=localStorage.getItem(SK);if(s){const p=JSON.parse(s);if(p.cw)setCols(pv=>pv.map(c=>({...c,w:p.cw[c.key]??c.w,label:p.cl?.[c.key]||c.label,v:p.cv?.[c.key]!==undefined?p.cv[c.key]:true})));if(p.rh)setRh(p.rh);if(p.fc!==undefined)setFC(p.fc);}}catch(e){}setReady(true);},[]);
  useEffect(()=>{if(!ready)return;try{const cw={},cl={},cv={};cols.forEach(c=>{cw[c.key]=c.w;cl[c.key]=c.label;cv[c.key]=c.v!==false;});localStorage.setItem(SK,JSON.stringify({cw,cl,cv,rh,fc:frozenCols}));}catch(e){}},[cols,rh,ready,frozenCols]);
  useEffect(()=>{const h=e=>{if((e.ctrlKey||e.metaKey)&&e.key==="z"){e.preventDefault();undo();}};document.addEventListener("keydown",h);return()=>document.removeEventListener("keydown",h);},[undo]);
  // ★ 이미지 저장 공통 함수
  const savePhoto=useCallback((blob,targetId)=>{if(!blob||!targetId)return;const rd=new FileReader();rd.onload=ev=>{pushU();setData(p=>{const u={};for(const[k,r]of Object.entries(p))u[k]=r.map(x=>x.id===targetId?{...x,photoUrl:ev.target.result}:x);return u;});setPT(null);};rd.readAsDataURL(blob);},[pushU]);
  const allTDRef=useRef([]);
  // ★ 클립보드 붙여넣기 — Ctrl+V 이미지
  useEffect(()=>{const h=e=>{const items=e.clipboardData?.items;if(!items)return;for(const item of items){if(item.type.startsWith("image/")){e.preventDefault();const blob=item.getAsFile();if(!blob)return;const t=photoTarget||(sel.size>0?[...sel][0]:null)||(allTDRef.current.length>0?allTDRef.current[0].id:null);savePhoto(blob,t);break;}}};document.addEventListener("paste",h);return()=>document.removeEventListener("paste",h);},[photoTarget,sel,savePhoto]);
  // ★ 드래그&드롭 이미지 — JPG/PNG 테이블에 드롭 시 해당 행 자동 저장
  const onImgDrop=useCallback((e,rowId)=>{e.preventDefault();e.stopPropagation();const f=[...e.dataTransfer.files].find(f=>f.type.startsWith("image/"));if(f)savePhoto(f,rowId);},[savePhoto]);
  const onImgDragOver=useCallback(e=>{e.preventDefault();e.dataTransfer.dropEffect="copy";},[]);
  // ★ 실시간 자동백업
  useEffect(()=>{try{sessionStorage.setItem("bridge-autosave",JSON.stringify({data,ts:Date.now()}));}catch(e){}},[data]);
  // ★ 깜박임 (ADMIN 배지 + NEW 뱃지)
  useEffect(()=>{const iv=setInterval(()=>setBlink(b=>!b),800);return()=>clearInterval(iv);},[]);
  // ★ 1분 자동저장
  useEffect(()=>{const iv=setInterval(()=>setAutoSaveTime(new Date()),60000);return()=>clearInterval(iv);},[]);
  const IV_SUBJ="<BRIDGE>Interview Guide";
  const IV_BODY="Hello, This is BRIDGE Agency. Here are the interview guidelines for you.\n\nPrivacy Protocol\nTo ensure your safety and legal protection, please remember to NEVER share your personal contact details (Email, Phone, or Social Media) directly with the school during this stage. Keeping all communication EXCLUSIVELY through us is the best way we can safeguard your professional interests.\n\nIF the interviewer asks for your contact details, shares theirs, or proposes a private meeting, please notify us immediately so we can safeguard your interests regarding any contract deals.\n\n\u25a3 Essential Candidate Guide\n\n1. Strategic Inquiry\nFeel free to ask about everything here, including your assigned tasks, work content, break times, meals, items provided in the accommodation, distance information, and if you have furniture, whether there is enough space to accommodate it.\n\n2. Salary Discussions\nIf the topic of salary comes up, the best way to handle it is to say: \"I\u2019d prefer to review the offer first and will get back to you through my recruiter after giving it careful thought.\" If you don\u2019t have a specific figure in mind, or if you feel it would be more effective for our BRIDGE team to negotiate on your behalf, please stick with that response.\n\n3. Attendance & Rescheduling\nWe completely understand that plans can change. If you can\u2019t make it or need to reschedule, it is absolutely fine\u2014just please let us know at least 1 hour in advance so we can update the school.\n\n4. Additional Support\nIf you\u2019d like to request a school visit or speak with a current teacher there of course you can ask, just let us know. If you have any questions at all, feel free to reply to this email - we\u2019re here to help!\n\nPlease share your feedback promptly after the interview. Whether it was a good fit or not, let us know comfortably so we can continue to support you with the best opportunities.\n\n\u25a3 Interview Access & Info\n\nCandidate: {{name}}\nTime: {{date}} {{time}} KST\nLink: {{meetLink}}\n\u2756 Interviews are typically conducted via Google Meet. We recommend installing the app or testing your connection in advance.\nInformation: {{schoolInfo}}\n\nBest of luck with your interview!\nBRIDGE Agency Team";
  const openIv=(row)=>{
    const r=row||null;
    setIvRec(r);setIvSearch(r?r.name:"");setIvName(r?r.name:"");
    setIvDate("");setIvTime("");setIvDur(60);setIvNote("");setIvSchool("");
    setIvMailSubj(IV_SUBJ);setIvMailBody(IV_BODY);
    setIvShowDrop(false);setIvOpen(true);
  };
  const openMM=r=>{setMmRecs(r);setMmTmpl("custom");setMmSubj("");setMmBody("");setMmFiles([]);setMmOpen(true);};
  useEffect(()=>{if(!mmOpen)return;const t=MTP.find(m=>m.key===mmTmpl);if(t&&mmTmpl!=="custom"){setMmSubj(t.s);setMmBody(t.b);}},[mmTmpl,mmOpen]);
  useEffect(()=>{if(mmOpen&&mmEditorMode==="editor"&&editorRef.current){editorRef.current.innerHTML=mmBody||"";}},[mmOpen]);
  useEffect(()=>{if(mmEditorMode==="editor"&&editorRef.current){editorRef.current.innerHTML=mmBody||"";}},[mmEditorMode]);
  const visCols=useMemo(()=>cols.filter(c=>c.v!==false),[cols]);
  const allTD=useMemo(()=>tab==="all"?[...data.active,...data.past,...data.blacklist]:data[tab]||[],[tab,data]);
  useEffect(()=>{allTDRef.current=allTD;},[allTD]);
  const cur=useMemo(()=>{
    let it=[...allTD];
    Object.entries(filters).forEach(([k,v])=>{if(v?.size>0)it=it.filter(r=>v.has(String(r[k]||"")));});
    if(q.trim()){const s=q.toLowerCase();it=it.filter(r=>Object.values(r).some(v=>String(v).toLowerCase().includes(s)));}
    if(sk){it=[...it].sort((a,b)=>{const av=String(a[sk]||""),bv=String(b[sk]||"");const n=Number(av)-Number(bv);if(!isNaN(n)&&av!=="")return sd==="asc"?n:-n;return sd==="asc"?av.localeCompare(bv,"ko"):bv.localeCompare(av,"ko");});}
    return it;
  },[allTD,filters,q,sk,sd]);
  const cnt=useMemo(()=>({active:data.active.length,past:data.past.length,blacklist:data.blacklist.length,all:data.active.length+data.past.length+data.blacklist.length}),[data]);
  const gFO=useCallback(k=>{const v=new Set();allTD.forEach(r=>{const val=String(r[k]||"");if(val)v.add(val);});return[...v].sort();},[allTD]);
  // ★ applyFmt — cur/visCols/sel/selCol/lastCell 모두 선언 후 정의
  const applyFmt=useCallback((fmtPatch)=>{
    setCellFmt(p=>{
      const n={...p};
      const applyToKey=k=>{n[k]={...(n[k]||{}),...fmtPatch};};
      if(selCol){
        cur.forEach(r=>applyToKey(`${r.id}_${selCol}`));
      } else if(sel.size>0){
        sel.forEach(id=>{visCols.forEach(c=>{if(!["rowNum","photo","mailAction","mailStatus","stage"].includes(c.key))applyToKey(`${id}_${c.key}`);});});
      } else if(lastCell){
        applyToKey(`${lastCell.id}_${lastCell.key}`);
      }
      return n;
    });
  },[selCol,sel,cur,visCols,lastCell]);
  // ★ 인터뷰 모달용 계산값 — JSX 내 IIFE 대신 useMemo 사용
  const ivDropdown=useMemo(()=>{
    if(!ivShowDrop||!ivSearch||ivSearch.length===0||ivRec)return null;
    const matches=data.active.filter(r=>(r.name||"").toLowerCase().includes(ivSearch.toLowerCase())||(r.email||"").toLowerCase().includes(ivSearch.toLowerCase())).slice(0,8);
    if(!matches.length)return null;
    return matches;
  },[ivShowDrop,ivSearch,ivRec,data.active]);
  const ivPreviewData=useMemo(()=>{
    const name=ivRec?ivRec.name:(ivSearch||"{{name}}");
    const meetLink=ivMeetLink||"{{meetLink}}";
    const schoolInfo=ivSchool||"Check details";
    const repl=s=>s.replace(/{{name}}/g,name).replace(/{{date}}/g,ivDate||"{{date}}").replace(/{{time}}/g,ivTime||"{{time}}").replace(/{{dur}}/g,String(ivDur)).replace(/{{meetLink}}/g,meetLink).replace(/{{schoolInfo}}/g,schoolInfo);
    return {subj:repl(ivMailSubj),body:repl(ivMailBody),name,toEmail:ivRec?ivRec.email:"",toName:ivRec?ivRec.name:""};
  },[ivRec,ivSearch,ivDate,ivTime,ivDur,ivSchool,ivMailSubj,ivMailBody]);
  // ★ 단일 전역 드래그 ref — 리렌더와 무관하게 항상 같은 리스너
  const dragRef=useRef(null); // {type, startX, startY, startVal, key/id}
  useEffect(()=>{
    const onMove=e=>{
      const d=dragRef.current;if(!d)return;
      if(d.type==="col"){
        const w=Math.max(20,d.startVal+(e.clientX-d.startX));
        setCols(p=>p.map(c=>c.key===d.key?{...c,w}:c));
      }else if(d.type==="row"){
        const h=Math.max(20,d.startVal+(e.clientY-d.startY));
        setRh(p=>({...p,[d.id]:h}));
      }else if(d.type==="memoH"){
        setMemoH(Math.max(30,d.startVal+(e.clientY-d.startY)));
      }else if(d.type==="theadH"){
        setTheadH(Math.max(20,d.startVal+(e.clientY-d.startY)));
      }
    };
    const onUp=()=>{dragRef.current=null;};
    document.addEventListener("mousemove",onMove);
    document.addEventListener("mouseup",onUp);
    return()=>{document.removeEventListener("mousemove",onMove);document.removeEventListener("mouseup",onUp);};
  },[]);
  const startColDrag=useCallback((e,col)=>{
    if(e.button!==0)return;e.preventDefault();
    dragRef.current={type:"col",startX:e.clientX,startVal:col.w,key:col.key};
  },[]);
  const startRowDrag=useCallback((e,id)=>{
    if(e.button!==0)return;e.preventDefault();e.stopPropagation();
    dragRef.current={type:"row",startY:e.clientY,startVal:rhRef.current[id]||58,id};
  },[]);
  const rhRef=useRef(rh);useEffect(()=>{rhRef.current=rh;},[rh]);
  const gH=useCallback(id=>rhRef.current[id]||58,[]);
  const tS=k=>{if(sk===k)setSd(d=>d==="asc"?"desc":"asc");else{setSk(k);setSd("asc");}};
  // ★ 편집: dropdown/mail/stage/tags 외 모든 셀 더블클릭 편집 가능
  const sE=(id,key,val)=>{if(["rowNum","photo","mailAction","mailStatus","stage"].includes(key))return;const col=cols.find(c=>c.key===key);if(col?.type==="dropdown")return;setEc({id,key});setEv(val||"");};
  const cE=()=>{if(!ec)return;pushU();setData(p=>{const u={};for(const[t,r]of Object.entries(p))u[t]=r.map(x=>x.id===ec.id?{...x,[ec.key]:ev}:x);return u;});setEc(null);};
  useEffect(()=>{if(ec&&eR.current)eR.current.focus();},[ec]);
  const setSt=(rid,s)=>{pushU();setData(p=>{const u={};for(const[t,r]of Object.entries(p))u[t]=r.map(x=>x.id===rid?{...x,stage:s}:x);return u;});};
  const setField=(rid,key,val)=>{pushU();setData(p=>{const u={};for(const[t,r]of Object.entries(p))u[t]=r.map(x=>x.id===rid?{...x,[key]:val}:x);return u;});};
  const tMT=(rid,tk)=>{pushU();setData(p=>{const u={};for(const[t,r]of Object.entries(p))u[t]=r.map(x=>{if(x.id!==rid)return x;const c=(x.mailStatus||"").split(",").filter(Boolean);const n=c.includes(tk)?c.filter(k=>k!==tk):[...c,tk];return{...x,mailStatus:n.join(",")};});return u;});};
  const hC=(e,row)=>{e.preventDefault();setCtx({x:e.clientX,y:e.clientY,row});};
  const mv=(row,cat)=>{pushU();setData(p=>{const u={};for(const[t,r]of Object.entries(p))u[t]=r.filter(x=>x.id!==row.id);u[cat]=[...u[cat],{...row,category:cat}];return u;});setCtx(null);};
  const dR=row=>{pushU();setData(p=>{const u={};for(const[t,r]of Object.entries(p))u[t]=r.filter(x=>x.id!==row.id);return u;});setCtx(null);};
  useEffect(()=>{const h=()=>{setCtx(null);setShowFi(null);setColMenu(null);};document.addEventListener("click",h);return()=>document.removeEventListener("click",h);},[]);
  const addN=()=>{pushU();const mx=Math.max(...[...data.active,...data.past,...data.blacklist].map(r=>r.id),0);const tt=tab==="all"?"active":tab;setData(p=>({...p,[tt]:[...p[tt],mkRow(mx+1,tt)]}));};
  const addRow=aid=>{pushU();const tt=tab==="all"?"active":tab;const mx=Math.max(...[...data.active,...data.past,...data.blacklist].map(r=>r.id),0);setData(p=>{const u={...p};const a=[...u[tt]];const i=a.findIndex(r=>r.id===aid);a.splice(i+1,0,mkRow(mx+1,tt));u[tt]=a;return u;});};
  const handlePhoto=e=>{if(!photoTarget)return;const f=e.target.files?.[0];if(!f)return;const rd=new FileReader();rd.onload=ev=>{pushU();setData(p=>{const u={};for(const[t,rows]of Object.entries(p))u[t]=rows.map(x=>x.id===photoTarget?{...x,photoUrl:ev.target.result}:x);return u;});};rd.readAsDataURL(f);setPT(null);};
  const expCSV=()=>{const fc=visCols.filter(c=>!["rowNum","photo","mailAction"].includes(c.key));const h=fc.map(c=>c.label).join(",");const rs=cur.map(r=>fc.map(c=>`"${String(r[c.key]||"").replace(/"/g,'""').replace(/\n/g," ")}"`).join(","));const b=new Blob(["\uFEFF"+[h,...rs].join("\n")],{type:"text/csv;charset=utf-8;"});const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=`bridge_${tab}_${new Date().toISOString().slice(0,10)}.csv`;a.click();};
  const tR=id=>setSel(p=>{const n=new Set(p);n.has(id)?n.delete(id):n.add(id);return n;});
  const tA=()=>setSel(p=>p.size===cur.length?new Set():new Set(cur.map(r=>r.id)));
  const tF=(ck,v)=>{setFi(p=>{const c=p[ck]?new Set(p[ck]):new Set();c.has(v)?c.delete(v):c.add(v);const n={...p};if(!c.size)delete n[ck];else n[ck]=c;return n;});};
  const af=Object.keys(filters).length;const hdn=cols.filter(c=>!c.v).length;
  const tw=visCols.reduce((s,c)=>s+c.w,0)+36;const cti=TABS.find(t=>t.key===tab);
  const getBg=(row,ri,isSel)=>{if(isSel)return"#bfdbfe";const st=STAGES.find(s=>s.key===(row.stage||"none"));if(st&&st.key!=="none")return st.color;if(row.category==="blacklist")return"#fee2e2";if(row.category==="past")return"#f3f4f6";return ri%2===0?"#fff":"#fafbfc";};
  const isRed=v=>v&&(v.includes("\uc5f0\uccb4")||v.includes("\ubb34\ub2e8"));
  if(!ready)return <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"100vh",fontSize:16,color:"#6b7280"}}>{"로딩 중..."}</div>;
  return(
    <div style={{fontFamily:"'Malgun Gothic',sans-serif",background:"#eaecf0",minHeight:"100vh",fontSize:15,display:"flex",flexDirection:"column",color:"#000"}}>
      <input ref={photoRef} type="file" accept="image/*" onChange={handlePhoto} style={{display:"none"}}/>
      {/* ★ 헤더 */}
      <div style={{background:"#fff",padding:"12px 20px",display:"flex",alignItems:"center",justifyContent:"space-between",flexShrink:0,flexWrap:"wrap",gap:8,borderBottom:"3px solid #2563eb"}}>
        <div style={{display:"flex",alignItems:"center",gap:14,flexWrap:"wrap"}}>
          <b style={{fontSize:26,letterSpacing:4}}>{"BRIDGE"}</b>
          <span style={{fontSize:18,fontWeight:700}}>{"지원자 관리"}</span>
          <span style={{fontSize:13,color:"#374151",background:blink?"#FEE2E2":"#FEF9F9",padding:"4px 14px",borderRadius:6,fontWeight:700,transition:"background 0.8s",letterSpacing:2,border:"1px solid #FECACA"}}>{"ADMIN"}</span>
          <span style={{fontSize:17,fontWeight:900,color:"#111"}}>{cur.length+" / 전체 "+cnt.all+"건 로드됨 · "+autoSaveTime.toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit",second:"2-digit"})}</span>
          <span style={{fontSize:12,color:"#16a34a",fontWeight:800}}>{"● 1분 자동저장"}</span>
        </div>
        <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
          <button onClick={undo} disabled={!undoStack.length} style={{padding:"10px 22px",fontSize:17,border:undoStack.length?"3px solid #ef4444":"2px solid #ddd",borderRadius:8,background:undoStack.length?"#fef2f2":"#f8f8f8",color:undoStack.length?"#dc2626":"#aaa",cursor:undoStack.length?"pointer":"default",fontWeight:900}}>{"↩ 되돌리기 ("+undoStack.length+")"}</button>
          {sel.size>0&&<button onClick={()=>{const a=[...data.active,...data.past,...data.blacklist];openMM(a.filter(r=>sel.has(r.id)));}} style={{padding:"8px 18px",fontSize:14,border:"none",borderRadius:8,background:"#7c3aed",color:"#fff",cursor:"pointer",fontWeight:800}}>{"✉ "+sel.size+"명"}</button>}
          <button onClick={expCSV} style={{padding:"6px 12px",fontSize:13,border:"1px solid #ddd",borderRadius:6,cursor:"pointer"}}>{"↓CSV"}</button>
          <button onClick={addN} style={{padding:"8px 18px",fontSize:14,border:"none",borderRadius:8,background:"#2563eb",color:"#fff",cursor:"pointer",fontWeight:900}}>{"+새후보자"}</button>
        </div>
      </div>
      {/* ★ 탭 — 슬림 pill 스타일 */}
      <div style={{display:"flex",gap:8,padding:"8px 16px",background:"#f0f2f5",flexShrink:0,alignItems:"center"}}>
        {TABS.map(t=>{const ia=tab===t.key;return(
          <div key={t.key} onClick={()=>{setTab(t.key);setSel(new Set());setFi({});if(t.key==="active")setNewSeen(true);}}
            style={{display:"flex",alignItems:"center",gap:6,padding:"6px 14px",borderRadius:20,cursor:"pointer",
              background:ia?t.color:"#fff",color:ia?"#fff":t.color,
              border:"1.5px solid "+(ia?t.color:t.color+"44"),
              fontWeight:ia?700:500,fontSize:13,transition:"all 0.15s",position:"relative",
              boxShadow:ia?"0 2px 8px "+t.color+"44":"none"}}>
            <span style={{fontSize:14}}>{t.icon}</span>
            <span>{t.label}</span>
            <span style={{background:ia?"rgba(255,255,255,0.25)":"#f3f4f6",color:ia?"#fff":t.color,fontSize:12,fontWeight:800,padding:"1px 7px",borderRadius:10,minWidth:20,textAlign:"center"}}>{cnt[t.key]}</span>
            {t.key==="active"&&cnt.active>0&&!newSeen&&<div style={{position:"absolute",top:-6,right:-6,background:blink?"#EF4444":"#FCA5A5",color:"#fff",fontSize:9,fontWeight:800,padding:"2px 5px",borderRadius:10,transition:"background 0.8s"}}>{"N"}</div>}
          </div>
        );})}
      </div>
      {/* ★ 툴바: 검색 + 열고정 + 폰트크기 + 색구분 */}
      <div style={{background:"#f8fafc",padding:"8px 20px",display:"flex",alignItems:"center",gap:12,borderBottom:"1px solid #e2e8f0",flexShrink:0,flexWrap:"wrap"}}>
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder={"⌕ 검색..."} style={{padding:"8px 14px",fontSize:15,border:"2px solid #cbd5e1",borderRadius:8,outline:"none",width:220}}/>
        <button onClick={()=>openIv(sel.size===1?cur.find(r=>sel.has(r.id)):null)} style={{padding:"7px 14px",borderRadius:7,border:"2px solid #16a34a",background:"#f0fdf4",color:"#16a34a",cursor:"pointer",fontSize:14,fontWeight:800,whiteSpace:"nowrap"}}>{"📅 인터뷰"}</button>
        <span style={{fontSize:14,fontWeight:700}}>{"열고정:"}</span>
        <select value={frozenCols} onChange={e=>setFC(Number(e.target.value))} style={{fontSize:14,padding:"4px 8px",borderRadius:6,border:"1px solid #cbd5e1"}}>{[0,1,2,3,4,5].map(n=><option key={n} value={n}>{n}</option>)}</select>
        <span style={{fontSize:14,fontWeight:700}}>{"폰트크기"}</span>
        <button onClick={()=>setFontSize(f=>Math.max(10,f-1))} style={{padding:"4px 10px",borderRadius:6,border:"1px solid #cbd5e1",background:"#fff",cursor:"pointer",fontWeight:700}}>{"A−"}</button>
        <span style={{fontSize:13,fontWeight:700,minWidth:20,textAlign:"center"}}>{fontSize}</span>
        <button onClick={()=>setFontSize(f=>Math.min(20,f+1))} style={{padding:"4px 10px",borderRadius:6,border:"1px solid #cbd5e1",background:"#fff",cursor:"pointer",fontWeight:700}}>{"A+"}</button>
        {/* ★ 셀 서식 — 즉시 적용 (선택 셀/행/열 자동 감지) */}
        <div style={{width:1,height:24,background:"#cbd5e1",margin:"0 2px"}}/>
        <span style={{fontSize:12,color:"#64748b",fontWeight:700}}>{"셀서식"}</span>
        <button onClick={()=>{const ns=Math.max(8,selFmtSize-1);setSelFmtSize(ns);applyFmt({fontSize:ns});}} style={{padding:"3px 8px",borderRadius:5,border:"1px solid #cbd5e1",background:"#fff",cursor:"pointer",fontSize:13,fontWeight:700}}>{"−"}</button>
        <input type="number" value={selFmtSize} min={8} max={32}
          onChange={e=>{const ns=Number(e.target.value)||15;setSelFmtSize(ns);applyFmt({fontSize:ns});}}
          style={{width:38,fontSize:13,fontWeight:700,textAlign:"center",border:"1px solid #cbd5e1",borderRadius:5,padding:"3px 4px"}}/>
        <button onClick={()=>{const ns=Math.min(32,selFmtSize+1);setSelFmtSize(ns);applyFmt({fontSize:ns});}} style={{padding:"3px 8px",borderRadius:5,border:"1px solid #cbd5e1",background:"#fff",cursor:"pointer",fontSize:13,fontWeight:700}}>{"+"}</button>
        <button onClick={()=>{const nb=!selFmtBold;setSelFmtBold(nb);applyFmt({fontWeight:nb?"bold":"normal"});}}
          style={{padding:"3px 10px",borderRadius:5,border:"1px solid "+(selFmtBold?"#1e40af":"#cbd5e1"),background:selFmtBold?"#1e40af":"#fff",color:selFmtBold?"#fff":"#000",cursor:"pointer",fontWeight:900,fontSize:15}}>{"B"}</button>
        {/* 배경색 */}
        <span style={{fontSize:12,color:"#64748b"}}>{"배경"}</span>
        <div style={{position:"relative",display:"inline-flex",alignItems:"center"}}>
          <div style={{width:26,height:22,borderRadius:4,border:"2px solid #94a3b8",background:selFmtBg,cursor:"pointer"}}
            onClick={e=>{e.currentTarget.nextSibling.click();}}/>
          <input type="color" value={selFmtBg}
            onChange={e=>{setSelFmtBg(e.target.value);applyFmt({bgColor:e.target.value});}}
            style={{position:"absolute",opacity:0,width:1,height:1,pointerEvents:"none"}}/>
        </div>
        {/* 글자색 */}
        <span style={{fontSize:12,color:"#64748b"}}>{"글자"}</span>
        <div style={{position:"relative",display:"inline-flex",alignItems:"center"}}>
          <div style={{width:26,height:22,borderRadius:4,border:"2px solid #94a3b8",background:selFmtColor,cursor:"pointer"}}
            onClick={e=>{e.currentTarget.nextSibling.click();}}/>
          <input type="color" value={selFmtColor}
            onChange={e=>{setSelFmtColor(e.target.value);applyFmt({color:e.target.value});}}
            style={{position:"absolute",opacity:0,width:1,height:1,pointerEvents:"none"}}/>
        </div>
        {/* 서식 초기화 */}
        <button onClick={()=>{
          setCellFmt(p=>{const n={...p};
            if(selCol){cur.forEach(r=>{delete n[`${r.id}_${selCol}`];});}
            else if(sel.size>0){sel.forEach(id=>{visCols.forEach(c=>{delete n[`${id}_${c.key}`];});});}
            else if(lastCell){delete n[`${lastCell.id}_${lastCell.key}`];}
            return n;});
        }} style={{padding:"3px 8px",borderRadius:5,border:"1px solid #e2e8f0",background:"#f8fafc",color:"#94a3b8",cursor:"pointer",fontSize:12}}>{"↺"}</button>
        {hdn>0&&<button onClick={()=>setCols(p=>p.map(c=>({...c,v:true})))} style={{padding:"4px 12px",fontSize:13,border:"1px solid #06b6d4",borderRadius:6,background:"#ecfeff",color:"#0e7490",cursor:"pointer"}}>{"숨긴"+hdn+"열"}</button>}
        <div style={{display:"flex",gap:6,marginLeft:"auto",alignItems:"center",flexWrap:"wrap"}}>
          <span style={{fontSize:14,fontWeight:700}}>{"색구분:"}</span>
          {STAGES.filter(s=>s.key!=="none").map(s=><span key={s.key} style={{fontSize:12,padding:"3px 8px",borderRadius:6,background:s.color,color:s.text,border:"1px solid #d1d5db",fontWeight:600}}>{s.label}</span>)}
        </div>
      </div>
      <div ref={topRef} onScroll={onTS} style={{overflowX:"auto",overflowY:"hidden",flexShrink:0,height:16,background:"#e2e8f0"}}><div style={{width:tw,height:1}}/></div>
      {/* ★ 메모 패널 — 테이블과 완전 분리, 독립적 높이 조절 */}
      <div style={{flexShrink:0,background:"#fffbeb",borderBottom:"2px solid #fde68a",position:"relative",overflow:"hidden",height:memoH}}>
        <textarea
          value={memo}
          onChange={e=>setMemo(e.target.value)}
          style={{width:"100%",height:"100%",border:"none",background:"transparent",resize:"none",fontSize:14,lineHeight:1.6,fontFamily:"'Malgun Gothic',sans-serif",color:"#000",outline:"none",padding:"6px 12px",boxSizing:"border-box"}}
          placeholder={"인터뷰:\n제안:\n체결:"}
        />
        {/* 하단 드래그 핸들 */}
        <div
          style={{position:"absolute",bottom:0,left:0,right:0,height:6,cursor:"row-resize",background:"#fde68a",opacity:0.7,zIndex:10}}
          onMouseDown={e=>{
            if(e.button!==0)return;e.preventDefault();
            dragRef.current={type:"memoH",startY:e.clientY,startVal:memoHRef.current};
          }}
        />
      </div>
      <div ref={tblRef} onScroll={onBS} style={{flex:1,overflow:"auto",background:"#fff"}}>
        <table style={{borderCollapse:"collapse",width:tw,minWidth:"100%",tableLayout:"fixed"}}>
          <colgroup><col style={{width:34,minWidth:0}}/>{visCols.map((c,i)=><col key={i} style={{width:c.w,minWidth:0}}/>)}</colgroup>
          <thead>
            <tr style={{position:"sticky",top:0,zIndex:30,height:theadH}}>
              <th onClick={e=>{const rect=e.currentTarget.getBoundingClientRect();if((e.clientY-rect.top)<rect.height*0.6)tA();}}
                style={{padding:0,background:"#e2e8f0",border:"1px solid #94a3b8",cursor:"pointer",userSelect:"none",width:34,textAlign:"center",position:"relative",verticalAlign:"top"}}
                onMouseDown={e=>{const rect=e.currentTarget.getBoundingClientRect();if((e.clientY-rect.top)>=rect.height*0.6){e.preventDefault();e.stopPropagation();dragRef.current={type:"theadH",startY:e.clientY,startVal:thHRef.current};}}}
              >
                {sel.size>0&&sel.size===cur.length?"☑":"☐"}
                <div style={{position:"absolute",bottom:0,left:0,right:0,height:5,cursor:"row-resize"}}/>
              </th>
              {visCols.map((col,i)=>{const hf=filters[col.key]?.size>0;const isFr=i<frozenCols;const isSelC=selCol===col.key;return <th key={col.key}
                onClick={e=>{if(!e._wasResize){setSelCol(selCol===col.key?null:col.key);}}}
                onDoubleClick={()=>{setRnCol(col.key);setRnVal(col.label);}}
                onContextMenu={e=>{e.preventDefault();e.stopPropagation();setColMenu({x:e.clientX,y:e.clientY,key:col.key});}}
                style={{padding:"6px 4px",textAlign:"center",fontWeight:900,fontSize:14,userSelect:"none",position:isFr?"sticky":"relative",left:isFr?(34+visCols.slice(0,i).reduce((s,c)=>s+c.w,0))+"px":undefined,zIndex:isFr?31:undefined,whiteSpace:"normal",wordBreak:"break-all",background:isSelC?"#93c5fd":hf?"#dbeafe":"#e2e8f0",border:"1px solid #94a3b8",cursor:"pointer"}}>
                {rnCol===col.key?<input value={rnVal} onChange={e=>setRnVal(e.target.value)} onBlur={()=>{setCols(p=>p.map(c=>c.key===rnCol?{...c,label:rnVal}:c));setRnCol(null);}} onKeyDown={e=>{if(e.key==="Enter"){setCols(p=>p.map(c=>c.key===rnCol?{...c,label:rnVal}:c));setRnCol(null);}if(e.key==="Escape")setRnCol(null);}} autoFocus style={{width:"100%",fontSize:13,border:"2px solid #2563eb",padding:"2px",textAlign:"center",fontWeight:800,borderRadius:3,boxSizing:"border-box"}}/>:
                <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:3,flexWrap:"wrap"}}>
                  <span>{col.label}</span>
                  {sk===col.key&&<span style={{fontSize:10,color:"#2563eb"}}>{sd==="asc"?"\u25b2":"\u25bc"}</span>}
                  {!["rowNum","photo","mailAction","stage"].includes(col.key)&&col.type!=="dropdown"&&<span onClick={e=>{e.stopPropagation();setShowFi(showFi===col.key?null:col.key);}} style={{cursor:"pointer",fontSize:10,color:hf?"#2563eb":"#94a3b8"}}>{"\u25bc"}</span>}
                </div>}
                {showFi===col.key&&<div onClick={e=>e.stopPropagation()} style={{position:"absolute",top:"100%",left:0,zIndex:100,background:"#fff",border:"1px solid #cbd5e1",borderRadius:8,boxShadow:"0 4px 20px rgba(0,0,0,0.12)",minWidth:180,maxHeight:240,overflow:"auto",textAlign:"left",padding:6}}><div style={{padding:"6px 10px",borderBottom:"1px solid #f1f5f9",display:"flex",justifyContent:"space-between"}}><b style={{fontSize:13}}>{col.label}</b>{hf&&<span onClick={()=>{setFi(p=>{const n={...p};delete n[col.key];return n;});}} style={{fontSize:12,color:"#2563eb",cursor:"pointer"}}>{"\ucd08\uae30\ud654"}</span>}</div>{gFO(col.key).map(opt=><label key={opt} style={{display:"flex",alignItems:"center",gap:6,padding:"4px 10px",cursor:"pointer",fontSize:14}}><input type="checkbox" checked={!!filters[col.key]?.has(opt)} onChange={()=>tF(col.key,opt)} style={{width:15,height:15}}/>{opt}</label>)}</div>}
                <div onMouseDown={e=>{e._wasResize=true;startColDrag(e,col);}} style={{position:"absolute",right:0,top:0,bottom:0,width:5,cursor:"col-resize"}}/>
              </th>;})}
            </tr>
          </thead>
          <tbody>
            {cur.length===0&&<tr><td colSpan={visCols.length+1} style={{textAlign:"center",padding:60,color:"#aaa",fontSize:16}}>{"No data"}</td></tr>}
            {cur.map((row,ri)=>{
              const h=gH(row.id);const isSel=sel.has(row.id);const bg=getBg(row,ri,isSel);
              const stI=STAGES.find(s=>s.key===(row.stage||"none"))||STAGES[0];
              const mTags=(row.mailStatus||"").split(",").filter(Boolean);
              return <tr key={row.id} onContextMenu={e=>hC(e,row)} style={{height:h,maxHeight:h,background:bg}}>
                <td style={{width:34,minWidth:34,maxWidth:34,padding:0,border:"1px solid #94a3b8",background:isSel?"#bfdbfe":"#e2e8f0",textAlign:"center",userSelect:"none",position:"relative",verticalAlign:"top",overflow:"hidden"}}
                  onMouseDown={e=>{
                    if(e.button!==0)return;
                    const rect=e.currentTarget.getBoundingClientRect();
                    if((e.clientY-rect.top)<rect.height*0.6){e.preventDefault();tR(row.id);return;}
                    startRowDrag(e,row.id);
                  }}
                >
                  <span style={{fontSize:11,fontWeight:700,color:isSel?"#1d4ed8":"#64748b"}}>{row.id}</span>
                  <div style={{position:"absolute",bottom:0,left:0,right:0,height:"40%",cursor:"s-resize"}}/>
                </td>
                {visCols.map((col,ci)=>{
                  const val=col.key==="rowNum"?String(row.id):String(row[col.key]||"");
                  const isE=ec?.id===row.id&&ec?.key===col.key;
                  const isFr=ci<frozenCols;
                  const frS=isFr?{position:"sticky",left:(34+visCols.slice(0,ci).reduce((s,c)=>s+c.w,0))+"px",zIndex:10,background:bg}:{};
                  const selHl=selCol===col.key?{outline:"2px solid #3b82f6",outlineOffset:"-2px"}:{};
                  if(col.key==="photo")return <td key={col.key} onDrop={e=>onImgDrop(e,row.id)} onDragOver={onImgDragOver} style={{padding:0,border:"1px solid #d1d5db",cursor:"pointer",overflow:"hidden",position:"relative",...frS,...selHl}} onClick={()=>setPT(row.id)} onDoubleClick={()=>{setPT(row.id);photoRef.current?.click();}}>{row.photoUrl?<img src={row.photoUrl} style={{position:"absolute",top:0,left:0,width:"100%",height:"100%",objectFit:"cover",objectPosition:"top center",display:"block"}}/>:<div style={{position:"absolute",top:0,left:0,width:"100%",height:"100%",background:PC[row.id%PC.length],color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontSize:20,fontWeight:900}}>{(String(row.name)||"?")[0]?.toUpperCase()}</div>}</td>;
                  if(col.key==="mailAction")return <td key={col.key} style={{padding:0,border:"1px solid #d1d5db",overflow:"hidden",position:"relative",height:0,...frS,...selHl}}><div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center"}}><button onClick={()=>openMM([row])} style={{padding:"4px 8px",fontSize:13,border:"2px solid #2563eb",borderRadius:6,background:"#eff6ff",color:"#2563eb",cursor:"pointer",fontWeight:800}}>{"\uba54\uc77c\ubc1c\uc1a1"}</button></div></td>;
                  if(col.key==="mailStatus")return <td key={col.key} style={{padding:0,border:"1px solid #d1d5db",overflow:"hidden",position:"relative",height:0,...frS,...selHl}}><div style={{position:"absolute",inset:0,padding:"2px 3px",overflow:"hidden",display:"flex",flexWrap:"wrap",gap:2,alignContent:"flex-start"}}>{MTAGS.map(mt=>{const a=mTags.includes(mt.key);return <span key={mt.key} onClick={()=>tMT(row.id,mt.key)} style={{fontSize:11,padding:"1px 5px",borderRadius:4,cursor:"pointer",fontWeight:a?800:500,background:a?mt.c+"25":"#f1f5f9",color:a?mt.c:"#999",border:"1px solid "+(a?mt.c:"#e2e8f0"),whiteSpace:"nowrap"}}>{"\u2713 "===mt.label?(a?"\u2713 ":"")+mt.label:(a?"\u2713 ":"")+mt.label}</span>;})}</div></td>;
                  if(col.key==="stage")return <td key={col.key} style={{padding:0,border:"1px solid #d1d5db",overflow:"hidden",position:"relative",height:0,...frS,...selHl}}><div style={{position:"absolute",inset:0,display:"flex",alignItems:"center"}}><select value={row.stage||"none"} onChange={e=>setSt(row.id,e.target.value)} style={{width:"100%",height:"100%",fontSize:13,padding:"2px 4px",border:"none",background:stI.color,color:stI.text,fontWeight:700,cursor:"pointer",outline:"none"}}>{STAGES.map(s=><option key={s.key} value={s.key}>{s.label}</option>)}</select></div></td>;
                  if(col.type==="dropdown")return <td key={col.key} style={{padding:0,border:"1px solid #d1d5db",overflow:"hidden",position:"relative",height:0,...frS,...selHl}}><div style={{position:"absolute",inset:0,display:"flex",alignItems:"center"}}><select value={val} onChange={e=>setField(row.id,col.key,e.target.value)} style={{width:"100%",height:"100%",fontSize:13,padding:"2px 4px",border:"none",background:isRed(val)?"#fee2e2":"transparent",color:isRed(val)?"#dc2626":"#000",fontWeight:isRed(val)?800:500,cursor:"pointer",outline:"none"}}><option value="">{"--"}</option>{col.opts.map(o=><option key={o} value={o}>{o}</option>)}</select></div></td>;
                  // ★ 일반 셀 — td position:relative + 내부 절대위치 div로 높이 완전 고정
                  const fmtKey=`${row.id}_${col.key}`;const cf=cellFmt[fmtKey]||{};
                  const cellFs=cf.fontSize||fontSize;
                  const cellFw=cf.fontWeight||"normal";
                  const cellBg=cf.bgColor||null;
                  const cellColor=cf.color||"#000";
                  // 배경색: 셀 서식 > 행 배경
                  const tdBg=cellBg||"transparent";
                  return <td key={col.key}
                    onClick={()=>{
                      setLastCell({id:row.id,key:col.key});
                      setSelFmtSize(cellFs);
                      setSelFmtBold(cellFw==="bold");
                      setSelFmtBg(cellBg||"#ffffff");
                      setSelFmtColor(cellColor);
                    }}
                    onDoubleClick={()=>sE(row.id,col.key,val)}
                    style={{padding:0,border:"1px solid #d1d5db",position:"relative",cursor:"cell",minWidth:0,overflow:"hidden",height:0,background:tdBg,...frS,...selHl}}>
                    {isE
                      ?<textarea ref={eR} value={ev} onChange={e=>setEv(e.target.value)} onBlur={cE}
                          onKeyDown={e=>{if(e.key==="Escape"){setEc(null);}else if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();cE();}}}
                          style={{position:"absolute",inset:0,width:"100%",height:"100%",fontSize:cellFs,fontWeight:cellFw,color:cellColor,border:"2px solid #2563eb",padding:"3px 5px",resize:"none",background:cellBg||"#eff6ff",borderRadius:0,boxSizing:"border-box",fontFamily:"inherit",whiteSpace:"pre-wrap",outline:"none"}}/>
                      :<div style={{position:"absolute",inset:0,padding:"3px 5px",fontSize:cellFs,fontWeight:cellFw,lineHeight:"1.35",overflow:"hidden",whiteSpace:"pre-wrap",wordBreak:"break-word",color:cellColor}}>{val||""}</div>
                    }
                  </td>;
                })}
              </tr>;})}
          </tbody>
        </table>
      </div>
      <div style={{background:"#f1f5f9",padding:"10px 20px",display:"flex",justifyContent:"space-between",alignItems:"center",borderTop:"3px solid #cbd5e1",flexShrink:0,flexWrap:"wrap",gap:8}}>
        <div style={{display:"flex",gap:20,fontSize:17,fontWeight:800}}><span>{"\uc804\uccb4 "}<b style={{fontSize:22}}>{cnt.all}</b></span><span>{"\ud83d\udc64"}<b style={{color:"#2563eb",fontSize:22}}>{cnt.active}</b></span><span>{"\u2705"}<b style={{color:"#16a34a",fontSize:22}}>{cnt.past}</b></span><span>{"\u26d4"}<b style={{color:"#dc2626",fontSize:22}}>{cnt.blacklist}</b></span></div>
        <div style={{display:"flex",gap:14,fontSize:14,color:"#475569"}}><span>{"dbl=\ud3b8\uc9d1"}</span><span>{"Ctrl+Z=\ub418\ub3cc\ub9ac\uae30"}</span><span style={{color:"#16a34a",fontWeight:800}}>{"\u2713\uc800\uc7a5"}</span></div>
      </div>
      {colMenu&&<div onClick={e=>e.stopPropagation()} style={{position:"fixed",top:colMenu.y,left:colMenu.x,background:"#fff",border:"1px solid #e2e8f0",borderRadius:10,zIndex:1000,minWidth:170,fontSize:15,boxShadow:"0 6px 24px rgba(0,0,0,0.12)",overflow:"hidden"}}>
        <Hov bg="#f0f0f0" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>{setRnCol(colMenu.key);setRnVal(cols.find(c=>c.key===colMenu.key)?.label||"");setColMenu(null);}}>{"\u270f\ufe0f\uc774\ub984"}</Hov>
        <Hov bg="#f0f0f0" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>{setCols(p=>p.map(c=>c.key===colMenu.key?{...c,v:false}:c));setColMenu(null);}}>{"\ud83d\udc41\uc228\uae30\uae30"}</Hov>
      </div>}
      {ctx&&<div onClick={e=>e.stopPropagation()} style={{position:"fixed",top:ctx.y,left:ctx.x,background:"#fff",border:"1px solid #e2e8f0",borderRadius:10,zIndex:1000,minWidth:200,fontSize:15,boxShadow:"0 6px 24px rgba(0,0,0,0.12)",overflow:"hidden"}}>
        <div style={{padding:"8px 16px",fontSize:12,color:"#94a3b8",borderBottom:"1px solid #f1f5f9"}}>{"#"+ctx.row.id+" "+ctx.row.name}</div>
        <Hov bg="#eff6ff" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>{openMM([ctx.row]);setCtx(null);}}>{"✉메일"}</Hov>
        <Hov bg="#f0f9ff" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>{setPT(ctx.row.id);setCtx(null);setTimeout(()=>photoRef.current?.click(),50);}}>{"🖼 사진 파일 선택"}</Hov>
        <Hov bg="#f0f9ff" style={{padding:"10px 16px",cursor:"pointer",fontSize:13,color:"#0369a1"}} onClick={()=>{setPT(ctx.row.id);setCtx(null);alert("Ctrl+V 로 붙여넣기 하세요");}}>{" 📋 클립보드 붙여넣기 (Ctrl+V)"}</Hov>
        <Hov bg="#f0f0f0" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>{addRow(ctx.row.id);setCtx(null);}}>{"+ 행"}</Hov>
        {ctx.row.category!=="active"&&<Hov bg="#dbeafe" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>mv(ctx.row,"active")}>{"\ud83d\udc64\uad6c\uc9c1"}</Hov>}
        {ctx.row.category!=="past"&&<Hov bg="#dcfce7" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>mv(ctx.row,"past")}>{"\u2705\uccb4\uacb0"}</Hov>}
        {ctx.row.category!=="blacklist"&&<Hov bg="#fee2e2" style={{padding:"10px 16px",cursor:"pointer"}} onClick={()=>mv(ctx.row,"blacklist")}>{"\u26d4BL"}</Hov>}
        <div style={{borderTop:"1px solid #f1f5f9"}}/>
        <Hov bg="#fee2e2" style={{padding:"10px 16px",cursor:"pointer",color:"#dc2626"}} onClick={()=>dR(ctx.row)}>{"\u2715\uc0ad\uc81c"}</Hov>
      </div>}
      {ivOpen&&<div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.75)",zIndex:9999,display:"flex",alignItems:"center",justifyContent:"center"}} onClick={e=>{if(e.target===e.currentTarget)setIvOpen(false);}}>
        <div style={{background:"#111827",borderRadius:16,width:"92vw",maxWidth:1300,boxShadow:"0 24px 80px rgba(0,0,0,0.7)",display:"flex",flexDirection:"column",maxHeight:"94vh",border:"1px solid #374151"}} onClick={e=>e.stopPropagation()}>
          {/* 헤더 */}
          <div style={{padding:"14px 24px",borderBottom:"1px solid #374151",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0,background:"#0f172a",borderRadius:"16px 16px 0 0"}}>
            <span style={{fontSize:18,fontWeight:900,color:"#f1f5f9"}}>{"⚡ 인터뷰 세팅"}</span>
            <button onClick={()=>setIvOpen(false)} style={{fontSize:24,border:"none",background:"none",cursor:"pointer",color:"#64748b"}}>{"×"}</button>
          </div>
          {/* 2단 레이아웃 */}
          <div style={{display:"flex",flex:1,overflow:"hidden",minHeight:0}}>
            {/* ★ 왼쪽 편집 패널 */}
            <div style={{width:"42%",borderRight:"1px solid #374151",overflow:"auto",padding:"18px 20px",display:"flex",flexDirection:"column",gap:12,flexShrink:0,background:"#1e293b"}}>
              {/* 후보자 검색 */}
              <div style={{position:"relative"}}>
                <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8"}}>{"후보자 (구직활동중)"}</div>
                <input value={ivSearch} onChange={e=>{setIvSearch(e.target.value);setIvShowDrop(true);setIvRec(null);}} onFocus={()=>setIvShowDrop(true)}
                  placeholder={"이름 또는 이메일..."}
                  style={{width:"100%",padding:"8px 12px",fontSize:14,border:"2px solid "+(ivRec?"#22c55e":"#374151"),borderRadius:7,outline:"none",boxSizing:"border-box",background:"#0f172a",color:"#f1f5f9"}}/>
                {ivRec&&<div style={{fontSize:12,color:"#22c55e",fontWeight:700,marginTop:2}}>{"✓ "+ivRec.email}</div>}
                {ivDropdown&&<div style={{position:"absolute",top:"100%",left:0,right:0,background:"#1e293b",border:"2px solid #374151",borderRadius:8,boxShadow:"0 8px 24px rgba(0,0,0,0.5)",zIndex:100,maxHeight:200,overflow:"auto",marginTop:2}}>
                  {ivDropdown.map(r=><div key={r.id} onClick={()=>{setIvRec(r);setIvSearch(r.name);setIvName(r.name);setIvShowDrop(false);}} style={{padding:"8px 12px",cursor:"pointer",borderBottom:"1px solid #374151",display:"flex",justifyContent:"space-between",color:"#f1f5f9"}} onMouseEnter={e=>e.currentTarget.style.background="#0f172a"} onMouseLeave={e=>e.currentTarget.style.background="transparent"}>
                    <span style={{fontWeight:700,fontSize:13}}>{r.name}</span>
                    <span style={{fontSize:12,color:"#64748b"}}>{r.email}</span>
                  </div>)}
                </div>}
              </div>
              {/* 날짜/시간 */}
              <div style={{display:"flex",gap:8}}>
                <div style={{flex:1}}>
                  <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8"}}>{"날짜"}</div>
                  <input type="date" value={ivDate} onChange={e=>setIvDate(e.target.value)} style={{width:"100%",padding:"8px 10px",fontSize:14,border:"2px solid #374151",borderRadius:7,outline:"none",boxSizing:"border-box",background:"#0f172a",color:"#f1f5f9",colorScheme:"dark"}}/>
                </div>
                <div style={{flex:1}}>
                  <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8"}}>{"시간 (KST)"}</div>
                  <input type="time" value={ivTime} onChange={e=>setIvTime(e.target.value)} style={{width:"100%",padding:"8px 10px",fontSize:14,border:"2px solid #374151",borderRadius:7,outline:"none",boxSizing:"border-box",background:"#0f172a",color:"#f1f5f9",colorScheme:"dark"}}/>
                </div>
              </div>
              {/* 면접시간 */}
              <div>
                <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8"}}>{"면접 시간"}</div>
                <div style={{display:"flex",gap:6}}>
                  {[30,45,60].map(d=><button key={d} onClick={()=>setIvDur(d)} style={{padding:"7px 16px",borderRadius:7,border:"2px solid "+(ivDur===d?"#3b82f6":"#374151"),background:ivDur===d?"#1d4ed8":"#0f172a",color:ivDur===d?"#fff":"#94a3b8",fontWeight:ivDur===d?800:500,cursor:"pointer",fontSize:13}}>{d+"분"}</button>)}
                </div>
              </div>
              {/* School Info */}
              <div>
                <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8"}}>{"School Info"}</div>
                <input value={ivSchool} onChange={e=>setIvSchool(e.target.value)} placeholder={"ex) Gangnam Elementary / 02-1234-5678"} style={{width:"100%",padding:"8px 12px",fontSize:13,border:"2px solid #374151",borderRadius:7,outline:"none",boxSizing:"border-box",background:"#0f172a",color:"#f1f5f9"}}/>
              </div>
              {/* 이메일 제목 */}
              <div>
                <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8"}}>{"이메일 제목"}</div>
                <input value={ivMailSubj} onChange={e=>setIvMailSubj(e.target.value)} style={{width:"100%",padding:"8px 12px",fontSize:13,fontWeight:700,border:"2px solid #374151",borderRadius:7,outline:"none",boxSizing:"border-box",background:"#0f172a",color:"#f1f5f9"}}/>
              </div>
              {/* 이메일 본문 */}
              <div style={{flex:1,display:"flex",flexDirection:"column"}}>
                <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8",display:"flex",justifyContent:"space-between"}}>
                  <span>{"이메일 본문"}</span>
                  <span style={{fontSize:11,color:"#475569",fontWeight:400}}>{"{{name}} {{date}} {{time}} {{meetLink}} {{schoolInfo}}"}</span>
                </div>
                <textarea value={ivMailBody} onChange={e=>setIvMailBody(e.target.value)}
                  style={{flex:1,minHeight:220,width:"100%",padding:"8px 10px",fontSize:12,border:"2px solid #374151",borderRadius:7,outline:"none",resize:"none",boxSizing:"border-box",fontFamily:"monospace",lineHeight:"1.6",background:"#0f172a",color:"#a5f3fc"}}/>
              </div>
              {/* 메모 */}
              <div>
                <div style={{fontSize:12,fontWeight:700,marginBottom:3,color:"#94a3b8"}}>{"메모 (내부용)"}</div>
                <textarea value={ivNote} onChange={e=>setIvNote(e.target.value)} placeholder={"Optional notes..."} rows={2} style={{width:"100%",padding:"7px 10px",fontSize:13,border:"2px solid #374151",borderRadius:7,outline:"none",resize:"none",boxSizing:"border-box",fontFamily:"inherit",background:"#0f172a",color:"#f1f5f9"}}/>
              </div>
            </div>
            {/* ★ 오른쪽 미리보기 */}
            <div style={{flex:1,overflow:"auto",padding:"20px 24px",background:"#111827"}}>
              <div style={{fontSize:12,fontWeight:700,color:"#475569",marginBottom:10,textTransform:"uppercase",letterSpacing:"0.05em"}}>{"Preview"}</div>
              {ivPreviewData&&<div style={{background:"#1e293b",borderRadius:10,border:"1px solid #374151",overflow:"hidden"}}>
                <div style={{background:"#0f172a",padding:"12px 18px",borderBottom:"1px solid #374151"}}>
                  <div style={{fontWeight:800,fontSize:16,marginBottom:4,color:"#f1f5f9"}}>{ivPreviewData.subj}</div>
                  <div style={{fontSize:12,color:"#64748b"}}>{"From: BRIDGE <bridgejobkr@gmail.com>"}</div>
                  <div style={{fontSize:12,color:"#64748b"}}>{"To: "+(ivPreviewData.toName?ivPreviewData.toName+" <"+ivPreviewData.toEmail+">":"(수신자 선택)")}</div>
                </div>
                <div style={{padding:"20px 24px",fontSize:14,lineHeight:"1.85",color:"#cbd5e1",fontFamily:"Arial,sans-serif"}}>
                  {ivPreviewData.body.split("\n").map((line,i)=>{
                    if(!line.trim())return <div key={i} style={{height:8}}/>;
                    if(line.startsWith("▣"))return <div key={i} style={{fontWeight:900,fontSize:16,borderLeft:"4px solid #3b82f6",paddingLeft:12,marginTop:16,marginBottom:8,color:"#93c5fd"}}>{line}</div>;
                    if(/^\d\./.test(line))return <div key={i} style={{fontWeight:800,marginTop:12,marginBottom:2,color:"#e2e8f0"}}>{line}</div>;
                    if(line.startsWith("IF the ")||line.startsWith("Please share"))return <div key={i} style={{background:"#1c1917",border:"1px solid #78350f",borderRadius:6,padding:"8px 12px",fontSize:13,marginTop:6,marginBottom:6,color:"#fcd34d"}}>{line}</div>;
                    if(line.startsWith("Link:"))return <div key={i} style={{fontWeight:800,color:"#60a5fa",fontSize:15,marginTop:8,textDecoration:"underline"}}>{line}</div>;
                    if(line.startsWith("Time:"))return <div key={i} style={{fontWeight:800,fontSize:15,marginTop:4,color:"#f1f5f9"}}>{line}</div>;
                    if(line.startsWith("❖"))return <div key={i} style={{fontSize:12,color:"#475569",marginTop:4}}>{line}</div>;
                    return <div key={i}>{line}</div>;
                  })}
                </div>
              </div>}
            </div>
          </div>
          {/* 하단 버튼 */}
          <div style={{padding:"12px 24px",borderTop:"1px solid #374151",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0,background:"#0f172a",borderRadius:"0 0 16px 16px"}}>
            <span style={{fontSize:13,color:"#22c55e",fontWeight:700}}>{"📅 Google Calendar + Meet 자동생성  |  📧 후보자(영문)·구인처(한국어) 자동발송"}</span>
            <div style={{display:"flex",gap:10}}>
              <button onClick={()=>setIvOpen(false)} style={{padding:"9px 20px",fontSize:14,border:"1px solid #374151",borderRadius:8,background:"#1e293b",cursor:"pointer",color:"#94a3b8"}}>{"✕ 취소"}</button>
              <button onClick={async()=>{
                if(!ivRec&&!ivName){alert("후보자를 선택하세요");return;}
                if(!ivDate||!ivTime){alert("날짜와 시간을 입력하세요");return;}
                setIvLoading(true);
                try{
                  const res=await fetch("https://bridge-n7hk.onrender.com/api/calendar/create-meet",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate_name:ivRec?ivRec.name:ivName,candidate_email:ivRec?.email||"",date:ivDate,time:ivTime,duration_min:ivDur,school_info:ivSchool||"",notes:ivNote||""})});
                  if(!res.ok)throw new Error("API "+res.status);
                  const d=await res.json();
                  setIvMeetLink(d.meet_link);setIvEventId(d.event_id);
                  const entry={name:ivPreviewData.name,email:ivRec?.email||"",date:ivDate,time:ivTime,dur:ivDur,note:ivNote,subj:ivPreviewData.subj,body:ivPreviewData.body,meetLink:d.meet_link,eventId:d.event_id,calendarLink:d.calendar_link,id:Date.now()};
                  setIvList(p=>[...p,entry]);
                  alert("✅ Google Meet 생성 완료!\n링크: "+d.meet_link+"\n수신: "+(ivRec?.email||"없음"));
                  setIvOpen(false);
                }catch(e){alert("❌ Meet 생성 실패: "+e.message);}finally{setIvLoading(false);}
              }} disabled={ivLoading||(!((ivRec||ivName)&&ivDate&&ivTime))} style={{padding:"9px 24px",fontSize:15,fontWeight:900,border:"none",borderRadius:8,background:ivLoading?"#374151":(ivRec||ivName)&&ivDate&&ivTime?"#2563eb":"#374151",color:"#fff",cursor:ivLoading?"wait":(ivRec||ivName)&&ivDate&&ivTime?"pointer":"default",minWidth:160}}>{ivLoading?"⏳ 생성 중...":"⚡ Google Meet 확정"}</button>
            </div>
          </div>
        </div>
      </div>}
      {mmOpen&&<div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.75)",zIndex:9999,display:"flex",alignItems:"center",justifyContent:"center"}} onClick={()=>setMmOpen(false)}>
        <div onClick={e=>e.stopPropagation()} style={{background:"#111827",borderRadius:12,width:"94vw",maxWidth:1400,height:"93vh",boxShadow:"0 24px 80px rgba(0,0,0,0.7)",display:"flex",flexDirection:"column",overflow:"hidden",border:"1px solid #374151"}}>
          {/* ── 상단 헤더 (네이버 초록) ── */}
          <div style={{background:"#03c75a",padding:"0 20px",display:"flex",alignItems:"center",justifyContent:"space-between",height:50,flexShrink:0}}>
            <div style={{display:"flex",alignItems:"center",gap:12}}>
              <span style={{color:"#fff",fontSize:19,fontWeight:900,letterSpacing:-1}}>{"BRIDGE Mail"}</span>
              <div style={{display:"flex",gap:3}}>{MTP.map(m=><button key={m.key} onClick={()=>setMmTmpl(m.key)} style={{padding:"3px 11px",fontSize:12,borderRadius:20,border:"none",background:mmTmpl===m.key?"#fff":"rgba(255,255,255,0.2)",color:mmTmpl===m.key?"#03c75a":"#fff",cursor:"pointer",fontWeight:mmTmpl===m.key?800:500}}>{m.label}</button>)}</div>
            </div>
            <button onClick={()=>setMmOpen(false)} style={{color:"#fff",fontSize:24,border:"none",background:"none",cursor:"pointer",lineHeight:1}}>{"×"}</button>
          </div>
          {/* ── 2단 레이아웃 ── */}
          <div style={{display:"flex",flex:1,overflow:"hidden",minHeight:0}}>
            {/* ★ 좌: 작성 패널 */}
            <div style={{width:"50%",borderRight:"1px solid #374151",display:"flex",flexDirection:"column",background:"#1e293b",overflow:"hidden"}}>
              {/* 보내는사람 — gmail/naver 토글 */}
              <div style={{padding:"10px 20px",borderBottom:"1px solid #374151",display:"flex",alignItems:"center",gap:10,flexShrink:0}}>
                <span style={{fontSize:13,color:"#64748b",width:64,flexShrink:0}}>{"보내는 사람"}</span>
                <div style={{display:"flex",gap:4}}>
                  <button onClick={()=>setMmFrom("gmail")} style={{padding:"4px 12px",fontSize:13,borderRadius:6,border:"2px solid "+(mmFrom==="gmail"?"#EA4335":"#374151"),background:mmFrom==="gmail"?"#450a0a":"#0f172a",color:mmFrom==="gmail"?"#f87171":"#64748b",fontWeight:mmFrom==="gmail"?800:500,cursor:"pointer"}}>{"📧 Gmail"}</button>
                  <button onClick={()=>setMmFrom("naver")} style={{padding:"4px 12px",fontSize:13,borderRadius:6,border:"2px solid "+(mmFrom==="naver"?"#03c75a":"#374151"),background:mmFrom==="naver"?"#052e16":"#0f172a",color:mmFrom==="naver"?"#03c75a":"#64748b",fontWeight:mmFrom==="naver"?800:500,cursor:"pointer"}}>{"🟢 Naver"}</button>
                </div>
                <span style={{fontSize:13,color:"#94a3b8",fontWeight:600,marginLeft:4}}>{mmFrom==="gmail"?"bridgejobkr@gmail.com":"bridgejobkr@naver.com"}</span>
              </div>
              {/* 받는사람 — 개별 체크박스 */}
              <div style={{padding:"10px 20px",borderBottom:"1px solid #374151",display:"flex",alignItems:"flex-start",gap:10,flexShrink:0}}>
                <span style={{fontSize:13,color:"#64748b",width:64,paddingTop:4,flexShrink:0,flexShrink:0}}>{"받는 사람"}</span>
                <div style={{display:"flex",flexWrap:"wrap",gap:4,flex:1}}>
                  {mmRecs.map(r=>{
                    const checked=mmSel.has(r.id);
                    return <label key={r.id} style={{display:"flex",alignItems:"center",gap:5,padding:"3px 10px",borderRadius:12,border:"2px solid "+(checked?"#3b82f6":"#374151"),background:checked?"#1e3a5f":"#0f172a",cursor:"pointer",userSelect:"none"}}>
                      <input type="checkbox" checked={checked} onChange={e=>{setMmSel(p=>{const n=new Set(p);e.target.checked?n.add(r.id):n.delete(r.id);return n;});}} style={{width:14,height:14,accentColor:"#3b82f6",cursor:"pointer"}}/>
                      <span style={{fontSize:13,color:checked?"#93c5fd":"#64748b",fontWeight:checked?700:500}}>{r.name+" <"+r.email+">"}</span>
                    </label>;
                  })}
                  {mmRecs.length>1&&<button onClick={()=>setMmSel(mmSel.size===mmRecs.length?new Set():new Set(mmRecs.map(r=>r.id)))} style={{padding:"3px 10px",fontSize:12,border:"1px solid #374151",borderRadius:10,background:"#0f172a",color:"#64748b",cursor:"pointer"}}>{mmSel.size===mmRecs.length?"전체해제":"전체선택"}</button>}
                </div>
              </div>
              {/* 첨부파일 — 제목 위 */}
              <div style={{padding:"8px 20px",borderBottom:"1px solid #374151",flexShrink:0}}>
                <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:4}}>
                  <span style={{fontSize:13,color:"#64748b",width:64,flexShrink:0}}>{"파일 첨부"}</span>
                  <button onClick={()=>fRef.current?.click()} style={{padding:"4px 14px",fontSize:12,border:"1.5px solid #374151",borderRadius:6,background:"#0f172a",color:"#94a3b8",cursor:"pointer"}}>{"내 PC"}</button>
                  <span style={{fontSize:11,color:"#bbb"}}>{"일반 0KB/10MB | 대용량 0KB/2.00GB×10개"}</span>
                </div>
                <input ref={fRef} type="file" multiple onChange={e=>{setMmFiles(p=>[...p,...Array.from(e.target.files||[])]);}} style={{display:"none"}}/>
                <div style={{border:"1px dashed #374151",borderRadius:6,padding:"8px 12px",minHeight:36,display:"flex",alignItems:"center",flexWrap:"wrap",gap:4,background:"#0f172a"}}>
                  {mmFiles.length===0?<span style={{fontSize:12,color:"#bbb"}}>{"📄 파일을 마우스로 끌어 오세요"}</span>:mmFiles.map((f,i)=>{const kb=f.size?Math.round(f.size/1024)+"KB":"";const exp=new Date(Date.now()+30*24*60*60*1000).toISOString().slice(0,10).replace(/-/g,".");return <span key={i} style={{fontSize:12,padding:"3px 10px",background:"#fff",borderRadius:6,border:"1px solid #e2e8f0",display:"flex",alignItems:"center",gap:4}}>{"📎 "+f.name+(kb?" "+kb:"")}<span style={{fontSize:11,color:"#999"}}>{"~"+exp}</span><span onClick={()=>setMmFiles(p=>p.filter((_,j)=>j!==i))} style={{cursor:"pointer",color:"#ef4444",marginLeft:4,fontWeight:700}}>{"×"}</span></span>;})}
                </div>
              </div>
              {/* 제목 + 중요표시 */}
              <div style={{padding:"8px 20px",borderBottom:"1px solid #374151",display:"flex",alignItems:"center",gap:8,flexShrink:0,background:"#1e293b"}}>
                <span style={{fontSize:13,color:"#64748b",width:64,flexShrink:0}}>{"제목"}</span>
                <button onClick={()=>setMmImportant(p=>!p)} title="중요 표시" style={{fontSize:18,border:"none",background:"none",cursor:"pointer",padding:"0 4px",color:mmImportant?"#f59e0b":"#d1d5db",flexShrink:0}}>{"★"}</button>
                <input value={mmSubj} onChange={e=>setMmSubj(e.target.value)} placeholder="제목을 입력하세요" style={{flex:1,padding:"6px 0",fontSize:15,fontWeight:600,border:"none",outline:"none",boxSizing:"border-box",background:"transparent",color:"#f1f5f9"}}/>
              </div>
              {/* ── 에디터 모드 탭 + 툴바 ── */}
              <div style={{borderBottom:"1px solid #374151",flexShrink:0,background:"#0f172a"}}>
                {/* 모드 탭 */}
                <div style={{display:"flex",justifyContent:"flex-end",borderBottom:"1px solid #374151"}}>
                  {["editor","html","text"].map(mode=><button key={mode} onClick={()=>{
                    if(mode!=="editor"&&mmEditorMode==="editor"&&editorRef.current)setMmBody(editorRef.current.innerHTML);
                    if(mode==="editor"&&mmEditorMode!=="editor"){setTimeout(()=>{if(editorRef.current){editorRef.current.focus();}},50);}
                    setMmEditorMode(mode);
                  }} style={{padding:"5px 16px",fontSize:12,border:"none",borderBottom:mmEditorMode===mode?"3px solid #03c75a":"3px solid transparent",background:mmEditorMode===mode?"#1e293b":"transparent",color:mmEditorMode===mode?"#03c75a":"#475569",fontWeight:mmEditorMode===mode?800:500,cursor:"pointer",textTransform:"uppercase",letterSpacing:0.5}}>{mode}</button>)}
                </div>
                {/* 서식 툴바 — Editor 모드만 */}
                {mmEditorMode==="editor"&&<div style={{display:"flex",gap:2,padding:"5px 10px",alignItems:"center",flexWrap:"wrap",background:"#0f172a"}}>
                  {/* 폰트 */}
                  <select onChange={e=>{editorRef.current?.focus();document.execCommand("fontName",false,e.target.value);}} style={{fontSize:12,border:"1px solid #374151",borderRadius:4,padding:"2px 4px",background:"#1e293b",color:"#94a3b8",cursor:"pointer"}}>
                    <option value="Malgun Gothic">{"맑은고딕"}</option>
                    <option value="Arial">{"Arial"}</option>
                    <option value="Times New Roman">{"Times"}</option>
                  </select>
                  {/* 폰트 크기 */}
                  <select onChange={e=>{editorRef.current?.focus();document.execCommand("fontSize",false,e.target.value);}} style={{fontSize:12,border:"1px solid #374151",borderRadius:4,padding:"2px 4px",background:"#1e293b",color:"#94a3b8",cursor:"pointer",width:50}}>
                    {[["1","10px"],["2","13px"],["3","16px"],["4","18px"],["5","24px"]].map(([v,l])=><option key={v} value={v}>{l}</option>)}
                  </select>
                  {/* B I U S */}
                  {[["B","bold","fontWeight","900"],["I","italic","fontStyle","italic"],["U","underline","textDecoration","underline"],["S","strikethrough","textDecoration","line-through"]].map(([lbl,cmd])=><button key={cmd} onMouseDown={e=>{e.preventDefault();editorRef.current?.focus();document.execCommand(cmd);}} style={{width:26,height:26,border:"1px solid #374151",borderRadius:4,background:"#1e293b",cursor:"pointer",color:"#94a3b8",fontWeight:lbl==="B"?900:400,fontStyle:lbl==="I"?"italic":"normal",textDecoration:lbl==="U"?"underline":lbl==="S"?"line-through":"none",fontSize:13,flexShrink:0}}>{lbl}</button>)}
                  <span style={{color:"#d1d5db",margin:"0 2px"}}>{"│"}</span>
                  {/* 정렬 */}
                  {[["◀","justifyLeft"],["▬","justifyCenter"],["▶","justifyRight"]].map(([lbl,cmd])=><button key={cmd} onMouseDown={e=>{e.preventDefault();editorRef.current?.focus();document.execCommand(cmd);}} style={{width:26,height:26,border:"1px solid #374151",borderRadius:4,background:"#1e293b",cursor:"pointer",color:"#94a3b8",fontSize:10,flexShrink:0}}>{lbl}</button>)}
                  <span style={{color:"#d1d5db",margin:"0 2px"}}>{"│"}</span>
                  {/* 글자색 팔레트 */}
                  <span style={{fontSize:11,color:"#888",marginRight:2}}>{"A"}</span>
                  {["#000000","#dc2626","#2563eb","#16a34a","#d97706","#7c3aed","#0891b2"].map(c=><button key={c} onMouseDown={e=>{e.preventDefault();editorRef.current?.focus();document.execCommand("foreColor",false,c);}} style={{width:18,height:18,borderRadius:3,background:c,border:"1px solid rgba(0,0,0,0.15)",cursor:"pointer",flexShrink:0}}/>)}
                  <span style={{color:"#d1d5db",margin:"0 2px"}}>{"│"}</span>
                  {/* 배경색 팔레트 */}
                  <span style={{fontSize:10,color:"#888",marginRight:2}}>{"BG"}</span>
                  {["#ffffff","#fef9c3","#fee2e2","#dcfce7","#dbeafe","#ede9fe","#ffedd5","#f1f5f9"].map(c=><button key={c} onMouseDown={e=>{e.preventDefault();editorRef.current?.focus();document.execCommand("backColor",false,c);}} style={{width:18,height:18,borderRadius:3,background:c,border:"1px solid rgba(0,0,0,0.2)",cursor:"pointer",flexShrink:0}}/>)}
                </div>}
                {mmEditorMode==="html"&&<div style={{padding:"5px 12px",fontSize:11,color:"#888"}}>{"HTML 태그 직접 입력 — 미리보기에서 렌더링됩니다"}</div>}
                {mmEditorMode==="text"&&<div style={{padding:"5px 12px",fontSize:11,color:"#888"}}>{"Plain text 모드"}</div>}
              </div>
              {/* ── 본문 에디터 ── */}
              <div style={{flex:1,overflow:"hidden",position:"relative"}}>
                <div ref={editorRef} contentEditable={mmEditorMode==="editor"} suppressContentEditableWarning
                  onInput={e=>{if(mmEditorMode==="editor")setMmBody(e.currentTarget.innerHTML);}}
                  style={{display:mmEditorMode==="editor"?"block":"none",width:"100%",height:"100%",padding:"14px 20px",fontSize:14,lineHeight:1.9,outline:"none",overflowY:"auto",boxSizing:"border-box",fontFamily:"'Malgun Gothic','Apple SD Gothic Neo',Arial,sans-serif",background:"#1e293b",color:"#e2e8f0"}}
                />
                {mmEditorMode==="html"&&<textarea value={mmBody} onChange={e=>{setMmBody(e.target.value);}} style={{width:"100%",height:"100%",padding:"14px 20px",fontSize:13,lineHeight:1.7,border:"none",outline:"none",resize:"none",boxSizing:"border-box",fontFamily:"monospace",background:"#0d1117",color:"#a6e3a1"}}/>}
                {mmEditorMode==="text"&&<textarea value={mmBody} onChange={e=>setMmBody(e.target.value)} placeholder="내용을 입력하세요" style={{width:"100%",height:"100%",padding:"14px 20px",fontSize:14,lineHeight:1.9,border:"none",outline:"none",resize:"none",boxSizing:"border-box",fontFamily:"inherit",background:"#1e293b",color:"#e2e8f0"}}/>}
              </div>
              <div style={{padding:"4px 20px 6px",background:"#0f172a",borderTop:"1px solid #374151",flexShrink:0}}>
                <span style={{fontSize:11,color:"#475569"}}>{"Vars: {{name}} {{region}} {{city}} {{teachingAge}} {{email}}"}</span>
              </div>
              {/* 하단 전송 */}
              <div style={{padding:"10px 20px",borderTop:"1px solid #374151",background:"#0f172a",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
                <div style={{display:"flex",flexDirection:"column",gap:3}}>
                  <span style={{fontSize:13,fontWeight:800,background:"#1c1917",padding:"2px 10px",borderRadius:4,border:"1px solid #44403c",color:"#fcd34d"}}>{mmFrom==="gmail"?"bridgejobkr@gmail.com":"bridgejobkr@naver.com"}</span>
                  <div style={{display:"flex",alignItems:"center",gap:5,fontSize:12,fontWeight:700,color:"#22c55e"}}>
                    <span>{"✓ "}</span><span>{"1:1 Individual send"}</span>
                    <span style={{background:"#14532d",padding:"1px 7px",borderRadius:10,color:"#86efac",fontSize:11}}>{(mmSel.size||mmRecs.length)+"명 선택"}</span>
                  </div>
                  <span style={{fontSize:11,color:"#ef4444",fontWeight:700}}>{"* No other recipient info exposed"}</span>
                </div>
                <button onClick={()=>{const subj=(mmImportant?"[중요] ":"")+mmSubj;alert("Sent via "+mmFrom+"\\nTo: "+mmRecs.map(r=>r.email).join(", ")+"\\nSubj: "+subj);setMmOpen(false);}} disabled={!mmSubj||!mmBody} style={{padding:"10px 26px",fontSize:15,border:"none",borderRadius:8,background:mmSubj&&mmBody?"#03c75a":"#aaa",color:"#fff",cursor:mmSubj&&mmBody?"pointer":"default",fontWeight:900,boxShadow:mmSubj&&mmBody?"0 4px 12px rgba(3,199,90,0.35)":"none"}}>{"✉ Send ("+(mmSel.size||mmRecs.length)+" individual)"}</button>
              </div>
            </div>
            {/* ★ 우: 미리보기 패널 */}
            <div style={{width:"50%",display:"flex",flexDirection:"column",background:"#0f172a",overflow:"hidden"}}>
              <div style={{padding:"10px 20px",borderBottom:"1px solid #374151",flexShrink:0,display:"flex",alignItems:"center",justifyContent:"space-between",background:"#111827"}}>
                <span style={{fontSize:14,fontWeight:800,color:"#f1f5f9"}}>{"📧 미리보기"}</span>
                <span style={{fontSize:12,color:"#999"}}>{"실제 수신 화면 시뮬레이션"}</span>
              </div>
              <div style={{flex:1,overflow:"auto",padding:"16px"}}>
                {mmRecs.length>0?mmRecs.map(r=>{
                  const fromAddr=mmFrom==="gmail"?"bridgejobkr@gmail.com":"bridgejobkr@naver.com";
                  const rp=s=>s.replace(/{{name}}/g,r.name||"").replace(/{{email}}/g,r.email||"").replace(/{{region}}/g,r.prefRegion||"").replace(/{{city}}/g,r.currentLoc||"").replace(/{{teachingAge}}/g,r.totalExp||"");
                  const dispSubj=(mmImportant?"🔔 ":"")+rp(mmSubj)||"(제목 없음)";
                  const now=new Date();const dateStr=now.getFullYear()+"년 "+(now.getMonth()+1)+"월 "+now.getDate()+"일 ("+["일","월","화","수","목","금","토"][now.getDay()]+") 오전 "+now.getHours()+":"+String(now.getMinutes()).padStart(2,"0");
                  return <div key={r.id} style={{background:"#1e293b",borderRadius:8,boxShadow:"0 2px 16px rgba(0,0,0,0.4)",marginBottom:16,overflow:"hidden",border:"1px solid #374151"}}>
                    {/* 메일 헤더 */}
                    <div style={{padding:"14px 20px",borderBottom:"1px solid #374151",background:"#0f172a"}}>
                      <div style={{fontSize:17,fontWeight:900,color:"#f1f5f9",marginBottom:10,display:"flex",alignItems:"center",gap:6}}>
                        {mmImportant&&<span style={{fontSize:16,color:"#f59e0b"}}>{"★"}</span>}
                        {dispSubj}
                      </div>
                      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6}}>
                        <div style={{width:36,height:36,borderRadius:"50%",background:"#03c75a",color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,fontWeight:900,flexShrink:0}}>{"B"}</div>
                        <div>
                          <div style={{fontSize:14,fontWeight:700,color:"#e2e8f0"}}>{"Bridge"}<span style={{fontSize:13,color:"#888",fontWeight:400,marginLeft:6}}>{"<"+fromAddr+">"}</span></div>
                          <div style={{fontSize:13,color:"#555",display:"flex",alignItems:"center",gap:4}}>
                            <span style={{background:"#e0f2fe",borderRadius:4,padding:"1px 6px",fontSize:12,color:"#0369a1",fontWeight:600}}>{"개별"}</span>
                            <span style={{fontWeight:600,color:"#1d4ed8",fontSize:13}}>{r.name}</span>
                            <span style={{color:"#888",fontSize:12}}>{"<"+r.email+">"}</span>
                          </div>
                        </div>
                        <div style={{marginLeft:"auto",fontSize:12,color:"#999",textAlign:"right"}}>{dateStr}</div>
                      </div>
                    </div>
                    {/* 첨부파일 (있을 때) */}
                    {mmFiles.length>0&&<div style={{padding:"10px 20px",borderBottom:"1px solid #eef0f3",background:"#f8f9fa"}}>
                      <div style={{fontSize:12,color:"#666",marginBottom:6,fontWeight:700}}>{("첨부 "+mmFiles.length+"개 "+(mmFiles.reduce((s,f)=>s+(f.size||0),0)>0?Math.round(mmFiles.reduce((s,f)=>s+(f.size||0),0)/1024)+"KB":""))}</div>
                      <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>{mmFiles.map((f,i)=>{
                        const kb=f.size?Math.round(f.size/1024)+"KB":"";
                        const exp=new Date(Date.now()+30*24*60*60*1000).toISOString().slice(0,10).replace(/-/g,".");
                        return <div key={i} style={{background:"#0f172a",border:"1px solid #374151",borderRadius:6,padding:"6px 12px",fontSize:12,display:"flex",flexDirection:"column",gap:2,minWidth:140}}>
                          <span style={{fontWeight:700,color:"#e2e8f0"}}>{"📎 "+f.name}</span>
                          <div style={{display:"flex",gap:8,color:"#888",fontSize:11}}>
                            {kb&&<span>{kb}</span>}
                            <span style={{color:"#f59e0b"}}>{"~"+exp}</span>
                            <span style={{color:"#3b82f6",cursor:"pointer",fontWeight:600}}>{"⬇ 다운로드"}</span>
                          </div>
                          <span style={{fontSize:10,color:"#bbb"}}>{"30일 보관 | 100회 다운로드 가능"}</span>
                        </div>;
                      })}</div>
                    </div>}
                    {/* 본문 */}
                    <div style={{padding:"20px 22px",fontSize:14,lineHeight:1.9,color:"#cbd5e1",fontFamily:"'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif",background:"#1e293b"}} dangerouslySetInnerHTML={{__html:rp(mmBody)||"<span style='color:#475569'>(본문 없음)</span>"}}/>
                  </div>;
                }):<div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"200px",color:"#374151",fontSize:14}}>{"수신자를 선택하면 미리보기가 표시됩니다"}</div>}
              </div>
            </div>
          </div>
        </div>
      </div>}
    </div>);
}

export default BridgeAdminSheetWrapper;
