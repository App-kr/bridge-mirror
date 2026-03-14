const { useState, useEffect } = React;

const STARS = [
  { top:'15%', left:'5%',  size:2.5, delay:0,   dur:1.8 },
  { top:'22%', left:'85%', size:3.5, delay:0.6, dur:1.5 },
  { top:'10%', left:'50%', size:2,   delay:0.3, dur:2.0 },
  { top:'28%', left:'30%', size:3,   delay:1.0, dur:1.6 },
  { top:'18%', left:'70%', size:2.8, delay:0.4, dur:1.9 },
  { top:'30%', left:'10%', size:2.2, delay:0.8, dur:1.7 },
  { top:'12%', left:'92%', size:3.2, delay:1.2, dur:1.4 },
];
const TAGLINE = 'A career that changes your life';

const css = `
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#000; overflow-x:hidden; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }

  .hero {
    position:relative; height:85vh; min-height:500px;
    display:flex; align-items:center; justify-content:center;
    overflow:hidden;
    background:linear-gradient(to bottom,#000,#0a0a0a,#000);
  }

  /* ── 지구 ── */
  .earth-photo-img {
    position:absolute; left:-10%; width:120%; height:74%;
    object-fit:cover; object-position:center top;
    opacity:0.22; will-change:transform;
    animation:earthSpin 140s ease-in-out infinite alternate;
    pointer-events:none; z-index:0;
  }
  @keyframes earthSpin {
    from { transform:translateX(0%); }
    to   { transform:translateX(-9%); }
  }

  /* ── 별 ── */
  .hero-star {
    position:absolute; border-radius:50%; background:white;
    opacity:0; animation:starTwinkle ease-in-out infinite;
    pointer-events:none; z-index:1;
  }
  @keyframes starTwinkle {
    0%,100% { opacity:0.1; transform:scale(0.7); box-shadow:0 0 2px 1px rgba(255,255,255,0.2); }
    50%     { opacity:1;   transform:scale(1.2); box-shadow:0 0 6px 2px rgba(255,255,255,0.45); }
  }

  /* ── 다리 ── */
  .bridge-wrap { position:absolute; inset:0; overflow:hidden; pointer-events:none; z-index:0; }
  .bridge-svg  { position:absolute; width:100%; height:100%; }

  .bridge-arc,.bridge-tower,.bridge-stay,.bridge-sweep { opacity:0; }

  .bridge-arc { stroke-dasharray:2200; stroke-dashoffset:2200; }
  .bridge-active .bridge-arc {
    opacity:0.35;
    animation:arcDraw 2.5s ease-out forwards;
  }
  @keyframes arcDraw {
    from { stroke-dashoffset:2200; }
    to   { stroke-dashoffset:0; }
  }

  .bridge-sweep { stroke-dasharray:80 2200; stroke-dashoffset:80; }
  .bridge-active .bridge-sweep { animation:sweepMove 2.5s ease-out forwards; }
  @keyframes sweepMove {
    0%   { stroke-dashoffset:80;    opacity:0.5; }
    85%  {                           opacity:0.35; }
    100% { stroke-dashoffset:-2200; opacity:0; }
  }

  .bridge-active .bridge-tower { animation:towerReveal 0.6s ease-out forwards; }
  @keyframes towerReveal {
    from { transform:translateY(20px); opacity:0; }
    to   { transform:translateY(0);    opacity:0.45; }
  }

  .bridge-stay { stroke-dasharray:var(--len); stroke-dashoffset:var(--len); }
  .bridge-active .bridge-stay { animation:stayDraw 0.8s ease-out forwards; }
  @keyframes stayDraw { to { stroke-dashoffset:0; opacity:0.12; } }
  .bridge-active .bridge-stay-l1 { animation-delay:0.30s; }
  .bridge-active .bridge-stay-l2 { animation-delay:0.35s; }
  .bridge-active .bridge-stay-r1 { animation-delay:0.30s; }
  .bridge-active .bridge-stay-r2 { animation-delay:0.35s; }

  .bridge-active .bridge-arc-group { animation:arcBreath 4s ease-in-out 3s infinite; }
  @keyframes arcBreath {
    0%,100% { filter:drop-shadow(0 0 4px rgba(255,255,255,0.1)); }
    50%     { filter:drop-shadow(0 0 12px rgba(255,255,255,0.3)); }
  }

  /* ── 텍스트 ── */
  .hero-title {
    font-size:clamp(70px,14vw,180px); font-weight:600; color:#fff;
    letter-spacing:-0.02em; line-height:1; margin-bottom:24px;
    animation:fadeIn 1.5s ease-out forwards;
  }
  @keyframes fadeIn { from{opacity:0} to{opacity:1} }

  .hero-tagline { font-size:clamp(20px,2.5vw,30px); font-weight:300; letter-spacing:-0.01em; }

  .letter-star {
    opacity:0; display:inline-block;
    animation:letterTwinkle 0.8s ease-out both;
  }
  @keyframes letterTwinkle {
    0%   { opacity:0;   color:transparent; text-shadow:0 0 0 transparent; }
    40%  { opacity:1;   color:#ffffff;     text-shadow:0 0 12px rgba(255,255,255,0.6); }
    70%  { opacity:0.9; color:#d0d0da;     text-shadow:0 0 6px rgba(255,255,255,0.25); }
    100% { opacity:1;   color:#a1a1a6;     text-shadow:none; }
  }

  /* ── 스크롤 ── */
  .scroll-hint {
    position:absolute; bottom:32px; left:50%; transform:translateX(-50%);
    display:flex; flex-direction:column; align-items:center; gap:12px; z-index:10;
  }
  .scroll-label {
    font-size:11px; text-transform:uppercase; letter-spacing:0.3em;
    color:#636366; font-weight:600;
    animation:scrollPulse 2s ease-in-out infinite;
  }
  @keyframes scrollPulse { 0%,100%{opacity:0.4} 50%{opacity:1} }
  .scroll-arrow { color:#636366; animation:scrollBounce 2s ease infinite; }
  @keyframes scrollBounce {
    0%,20%,50%,80%,100% { transform:translateY(0); }
    40% { transform:translateY(14px); }
    60% { transform:translateY(7px); }
  }

  /* ── 조절 패널 ── */
  .panel {
    position:fixed; bottom:16px; right:16px; z-index:999;
    background:rgba(0,0,0,0.9); border:1px solid rgba(255,255,255,0.14);
    border-radius:12px; padding:14px 18px;
    color:#fff; font-size:11px; font-family:monospace; min-width:210px;
  }
  .pt { font-size:10px; letter-spacing:0.12em; color:#636366; margin-bottom:10px; }
  .row { margin-bottom:10px; }
  .row label { display:flex; justify-content:space-between; color:#a1a1a6; margin-bottom:4px; }
  .row label span { color:#2997ff; font-weight:bold; }
  .row input { width:100%; accent-color:#2997ff; cursor:pointer; }
`;

export default function App() {
  const [bridgeActive, setBridgeActive] = useState(false);
  const [showTagline,  setShowTagline]  = useState(false);
  const [op,  setOp]  = useState(0.22);
  const [top, setTop] = useState(34);
  const [spd, setSpd] = useState(140);

  useEffect(() => {
    const t1 = setTimeout(() => setBridgeActive(true), 50);
    const t2 = setTimeout(() => setShowTagline(true),  50);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  return (
    <>
      <style>{css}</style>

      <div className="hero">

        {/* 지구 사진 */}
        <img
          className="earth-photo-img"
          style={{ top: top+'%', opacity: op, animationDuration: spd+'s' }}
          src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/The_Blue_Marble_%28remastered%29.jpg/1200px-The_Blue_Marble_%28remastered%29.jpg"
          alt=""
        />

        {/* 그라데이션 오버레이 */}
        <div style={{
          position:'absolute', inset:0, zIndex:0, pointerEvents:'none',
          background:'linear-gradient(to bottom,#000 0%,#000 22%,rgba(0,0,0,0.82) 40%,rgba(0,0,0,0.45) 60%,rgba(0,0,0,0.3) 80%,rgba(0,0,0,0.5) 100%)'
        }}/>

        {/* 별 */}
        {STARS.map((s,i) => (
          <div key={i} className="hero-star" style={{
            top:s.top, left:s.left, width:s.size, height:s.size,
            animationDelay:s.delay+'s', animationDuration:s.dur+'s',
          }}/>
        ))}

        {/* 다리 */}
        <div className={`bridge-wrap${bridgeActive ? ' bridge-active' : ''}`}>
          <svg className="bridge-svg" viewBox="0 0 1400 800" preserveAspectRatio="xMidYMid slice" fill="none">
            <defs>
              <filter id="cableGlow">
                <feGaussianBlur stdDeviation="4" result="blur"/>
                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <filter id="sweepGlow">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
              <mask id="taperMask">
                <linearGradient id="taperGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0"    stopColor="white" stopOpacity="0"/>
                  <stop offset="0.12" stopColor="white" stopOpacity="0.25"/>
                  <stop offset="0.5"  stopColor="white" stopOpacity="1"/>
                  <stop offset="0.88" stopColor="white" stopOpacity="0.25"/>
                  <stop offset="1"    stopColor="white" stopOpacity="0"/>
                </linearGradient>
                <rect x="0" y="0" width="1400" height="800" fill="url(#taperGrad)"/>
              </mask>
              <linearGradient id="postSweep" gradientUnits="userSpaceOnUse" x1="-700" y1="400" x2="0" y2="400">
                <stop offset="0"    stopColor="white" stopOpacity="0"/>
                <stop offset="0.35" stopColor="white" stopOpacity="0"/>
                <stop offset="0.5"  stopColor="white" stopOpacity="0.35"/>
                <stop offset="0.65" stopColor="white" stopOpacity="0"/>
                <stop offset="1"    stopColor="white" stopOpacity="0"/>
                <animate attributeName="x1" values="-700;1400" dur="3.5s" repeatCount="indefinite" begin="3s"/>
                <animate attributeName="x2" values="0;2100"   dur="3.5s" repeatCount="indefinite" begin="3s"/>
              </linearGradient>
            </defs>

            <g className="bridge-arc-group">
              <path d="M 0 520 Q 700 180, 1400 520" className="bridge-arc"
                stroke="white" strokeWidth={0.8} strokeLinecap="round" filter="url(#cableGlow)"/>
              <path d="M 0 520 Q 700 180, 1400 520" className="bridge-arc"
                stroke="white" strokeWidth={2.5} strokeLinecap="round"
                mask="url(#taperMask)" filter="url(#cableGlow)"/>
            </g>

            <path d="M 0 520 Q 700 180, 1400 520" className="bridge-sweep"
              stroke="rgba(255,255,255,0.5)" strokeWidth={3} strokeLinecap="round" filter="url(#sweepGlow)"/>

            <line x1={420} y1={520} x2={420} y2={280} className="bridge-tower"
              stroke="white" strokeWidth={2} strokeLinecap="round"/>
            <line x1={980} y1={520} x2={980} y2={280} className="bridge-tower"
              stroke="white" strokeWidth={2} strokeLinecap="round"/>

            <line x1={420} y1={280} x2={280} y2={410} className="bridge-stay bridge-stay-l1"
              stroke="white" strokeWidth={0.8} strokeLinecap="round" style={{'--len':'191'}}/>
            <line x1={420} y1={280} x2={200} y2={465} className="bridge-stay bridge-stay-l2"
              stroke="white" strokeWidth={0.8} strokeLinecap="round" style={{'--len':'287'}}/>
            <line x1={980} y1={280} x2={1120} y2={410} className="bridge-stay bridge-stay-r1"
              stroke="white" strokeWidth={0.8} strokeLinecap="round" style={{'--len':'191'}}/>
            <line x1={980} y1={280} x2={1200} y2={465} className="bridge-stay bridge-stay-r2"
              stroke="white" strokeWidth={0.8} strokeLinecap="round" style={{'--len':'287'}}/>

            <path d="M 0 520 Q 700 180, 1400 520"
              stroke="url(#postSweep)" strokeWidth={4} strokeLinecap="round"
              opacity={0.5} filter="url(#cableGlow)"/>
          </svg>
        </div>

        {/* 텍스트 */}
        <div style={{ position:'relative', zIndex:10, textAlign:'center', padding:'0 16px' }}>
          <h1 className="hero-title">BRIDGE</h1>
          <p className="hero-tagline">
            {TAGLINE.split('').map((char, i) => (
              <span
                key={i}
                className={showTagline ? 'letter-star' : ''}
                style={{
                  opacity: showTagline ? undefined : 0,
                  animationDelay: showTagline ? `${i * 0.025}s` : undefined,
                  minWidth: char === ' ' ? '0.3em' : undefined,
                }}
              >
                {char}
              </span>
            ))}
          </p>
        </div>

        {/* 스크롤 힌트 */}
        <div className="scroll-hint">
          <span className="scroll-label">Scroll</span>
          <svg className="scroll-arrow" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
          </svg>
        </div>
      </div>

      {/* 조절 패널 */}
      <div className="panel">
        <div className="pt">⚙ PREVIEW CONTROLS</div>
        <div className="row">
          <label>지구 투명도 <span>{op.toFixed(2)}</span></label>
          <input type="range" min="5" max="70" value={Math.round(op*100)} onChange={e=>setOp(e.target.value/100)}/>
        </div>
        <div className="row">
          <label>위치 top% <span>{top}%</span></label>
          <input type="range" min="10" max="70" value={top} onChange={e=>setTop(+e.target.value)}/>
        </div>
        <div className="row">
          <label>회전속도(초) <span>{spd}s</span></label>
          <input type="range" min="30" max="300" value={spd} onChange={e=>setSpd(+e.target.value)}/>
        </div>
      </div>
    </>
  );
}
