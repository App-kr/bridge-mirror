'use client';

import { useEffect, useState } from 'react';

export default function HeroBackground() {
  const [animateLines, setAnimateLines] = useState(false);
  const [animatePlane, setAnimatePlane] = useState(false);

  useEffect(() => {
    // 선 애니메이션 시작
    const t1 = setTimeout(() => setAnimateLines(true), 500);
    // 비행기 애니메이션 시작
    const t2 = setTimeout(() => setAnimatePlane(true), 1500);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      overflow: 'hidden',
      pointerEvents: 'none',
      zIndex: 0,
    }}>
      {/* 지구본 - 왼쪽 하단 */}
      <svg
        viewBox="0 0 200 200"
        style={{
          position: 'absolute',
          left: '3%',
          bottom: '10%',
          width: '140px',
          height: '140px',
          opacity: 0.12,
          animation: 'globeSpin 40s linear infinite',
        }}
      >
        {/* 외곽 원 */}
        <circle cx="100" cy="100" r="90" fill="none" stroke="white" strokeWidth="1.2" />
        {/* 위선 */}
        <ellipse cx="100" cy="60" rx="85" ry="15" fill="none" stroke="white" strokeWidth="0.6" />
        <ellipse cx="100" cy="100" rx="90" ry="15" fill="none" stroke="white" strokeWidth="0.6" />
        <ellipse cx="100" cy="140" rx="85" ry="15" fill="none" stroke="white" strokeWidth="0.6" />
        {/* 경선 */}
        <ellipse cx="100" cy="100" rx="15" ry="90" fill="none" stroke="white" strokeWidth="0.6" />
        <ellipse cx="100" cy="100" rx="45" ry="90" fill="none" stroke="white" strokeWidth="0.6" />
        <ellipse cx="100" cy="100" rx="70" ry="90" fill="none" stroke="white" strokeWidth="0.6" />
        <ellipse cx="100" cy="100" rx="90" ry="90" fill="none" stroke="white" strokeWidth="0.6" />
      </svg>

      {/* 한반도 실루엣 - 오른쪽 */}
      <svg
        viewBox="0 0 120 280"
        style={{
          position: 'absolute',
          right: '6%',
          top: '15%',
          width: '80px',
          height: '190px',
          opacity: 0.07,
        }}
      >
        <path
          d="M60,5 L65,8 L70,15 L72,25 L68,35 L72,42 L80,48 L85,55 L88,65 L90,78 L92,85 L95,95 L93,105 L90,112 L85,118 L80,125 L78,135 L82,142 L85,150 L83,160 L78,168 L72,175 L68,182 L70,190 L72,200 L68,210 L62,218 L58,225 L55,235 L50,242 L45,248 L42,255 L38,260 L35,265 L32,268 L30,270 L28,272 L25,270 L22,265 L20,258 L22,250 L25,242 L28,235 L30,228 L28,220 L25,212 L22,205 L20,198 L18,190 L15,182 L12,175 L10,168 L8,160 L10,150 L12,142 L15,135 L18,128 L22,120 L25,112 L28,105 L32,98 L35,90 L38,82 L40,72 L42,62 L45,52 L48,42 L50,32 L52,22 L55,12 L58,8 Z"
          fill="white"
          stroke="none"
        />
      </svg>

      {/* 연결선 - 지구본에서 한반도까지 */}
      <svg
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
        }}
        viewBox="0 0 1200 700"
        preserveAspectRatio="none"
      >
        {/* 선 1 - 위쪽 경로 */}
        <path
          d="M 130 480 Q 400 200, 680 280 T 1050 180"
          fill="none"
          stroke="white"
          strokeWidth="0.8"
          opacity="0.12"
          strokeDasharray="1200"
          strokeDashoffset={animateLines ? '0' : '1200'}
          style={{
            transition: 'stroke-dashoffset 3s ease-in-out',
          }}
        />
        {/* 선 2 - 중간 경로 */}
        <path
          d="M 130 490 Q 450 320, 700 350 T 1060 250"
          fill="none"
          stroke="white"
          strokeWidth="0.6"
          opacity="0.09"
          strokeDasharray="1200"
          strokeDashoffset={animateLines ? '0' : '1200'}
          style={{
            transition: 'stroke-dashoffset 4s ease-in-out 0.5s',
          }}
        />
        {/* 선 3 - 아래쪽 경로 */}
        <path
          d="M 135 500 Q 500 450, 750 400 T 1065 320"
          fill="none"
          stroke="white"
          strokeWidth="0.5"
          opacity="0.07"
          strokeDasharray="1200"
          strokeDashoffset={animateLines ? '0' : '1200'}
          style={{
            transition: 'stroke-dashoffset 5s ease-in-out 1s',
          }}
        />
      </svg>

      {/* 비행기 */}
      <div
        style={{
          position: 'absolute',
          fontSize: '22px',
          opacity: animatePlane ? 0.3 : 0,
          animation: animatePlane ? 'flyToKorea 6s ease-in-out infinite' : 'none',
          zIndex: 2,
        }}
      >
        ✈
      </div>

      <style>{`
        @keyframes globeSpin {
          0% { transform: rotateY(0deg); }
          100% { transform: rotateY(360deg); }
        }

        @keyframes flyToKorea {
          0% {
            left: 8%;
            top: 65%;
            opacity: 0;
            transform: rotate(25deg) scale(0.8);
          }
          10% {
            opacity: 0.35;
          }
          50% {
            left: 50%;
            top: 35%;
            opacity: 0.3;
            transform: rotate(15deg) scale(1);
          }
          85% {
            left: 85%;
            top: 22%;
            opacity: 0.2;
            transform: rotate(5deg) scale(0.9);
          }
          100% {
            left: 90%;
            top: 20%;
            opacity: 0;
            transform: rotate(0deg) scale(0.7);
          }
        }
      `}</style>
    </div>
  );
}
