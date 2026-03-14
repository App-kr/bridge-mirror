'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export default function EarthGlobe() {
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const W = mount.clientWidth
    const H = mount.clientHeight

    // ── Renderer (alpha 투명) ──
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(W, H)
    renderer.setClearColor(0x000000, 0)
    mount.appendChild(renderer.domElement)

    // ── Scene & Camera ──
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 200)
    camera.position.set(0, 0, 6)

    const R = 7
    const yOffset = -6.9

    const geo = new THREE.SphereGeometry(R, 80, 80)
    const mat = new THREE.MeshPhongMaterial({
      specular: new THREE.Color(0x1a1a2e),
      shininess: 10,
      opacity: 0.32,
      transparent: true,
    })

    new THREE.TextureLoader().load(
      '/earth-map.jpg',  // NASA Blue Marble — 고해상도, 대륙색 선명
      (tex) => { mat.map = tex; mat.needsUpdate = true },
      undefined,
      (e) => console.error('[EarthGlobe] texture error:', e)
    )

    // ── Group 구조: 기울기(tilt) 고정 / 자전(spin)은 내부 earth만 ──
    const tiltGroup = new THREE.Group()
    tiltGroup.position.y = yOffset
    tiltGroup.rotation.x = -0.45   // 적도 정면 기울기 (고정)
    tiltGroup.scale.set(1.28, 1, 1)
    scene.add(tiltGroup)

    const earth = new THREE.Mesh(geo, mat)
    earth.rotation.y = 1.8         // 아프리카·유럽·아시아 시작
    tiltGroup.add(earth)

    // ── 대기권 glow ──
    const atm = new THREE.Mesh(
      new THREE.SphereGeometry(R + 0.15, 64, 64),
      new THREE.MeshPhongMaterial({
        color: 0x3366cc,
        transparent: true,
        opacity: 0.055,
        side: THREE.BackSide,
      })
    )
    tiltGroup.add(atm)

    // ── 조명 ──
    scene.add(new THREE.AmbientLight(0xffffff, 0.72))  // 밝게 — 대륙색 살리기
    const sun = new THREE.DirectionalLight(0xffffff, 1.2)
    sun.position.set(4, 1, 6)  // 정면 가까이 — 보이는 면 밝게
    scene.add(sun)

    // ── 자전 ──
    let id: number
    const loop = () => {
      id = requestAnimationFrame(loop)
      earth.rotation.y += 0.0014  // earth만 Y축 자전 (tiltGroup 기울기 유지)
      renderer.render(scene, camera)
    }
    loop()

    const onResize = () => {
      const w = mount.clientWidth, h = mount.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(id)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
    }
  }, [])

  return (
    <div
      ref={mountRef}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        WebkitMaskImage: 'linear-gradient(to right, transparent 0%, black 20%, black 80%, transparent 100%)',
        maskImage: 'linear-gradient(to right, transparent 0%, black 20%, black 80%, transparent 100%)',
      }}
    />
  )
}
