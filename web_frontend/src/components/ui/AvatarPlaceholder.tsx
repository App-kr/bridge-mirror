/**
 * AvatarPlaceholder — cute person silhouette with pastel background
 * Background color is deterministically derived from the name.
 */

const PASTEL_COLORS = [
  '#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF',
  '#E8BAFF', '#FFB3E6', '#B3FFD9', '#B3D4FF', '#FFD9B3',
  '#D4B3FF', '#B3FFFF', '#FFB3B3', '#C9BAFF', '#BAFFED',
  '#FFE0B3',
]

function hashName(name: string): number {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

interface AvatarPlaceholderProps {
  name: string
  photoUrl?: string | null
  size?: number
}

export default function AvatarPlaceholder({ name, photoUrl, size = 48 }: AvatarPlaceholderProps) {
  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={name}
        width={size}
        height={size}
        className="rounded-xl object-cover shrink-0"
        style={{ width: size, height: size }}
      />
    )
  }

  const bg = PASTEL_COLORS[hashName(name) % PASTEL_COLORS.length]
  const r = size * 0.5

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="rounded-xl shrink-0"
      style={{ background: bg, width: size, height: size }}
    >
      {/* Head */}
      <circle cx={r} cy={r * 0.7} r={r * 0.32} fill="white" opacity={0.7} />
      {/* Body */}
      <ellipse cx={r} cy={size * 1.05} rx={r * 0.55} ry={r * 0.55} fill="white" opacity={0.7} />
    </svg>
  )
}
