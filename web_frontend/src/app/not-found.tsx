import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center bg-[#000000]">
      <div className="text-center px-6">
        <h1 className="text-[120px] sm:text-[160px] font-bold text-white/10 leading-none select-none">
          404
        </h1>
        <p className="text-2xl sm:text-3xl font-semibold text-white -mt-6 mb-3">
          Page Not Found
        </p>
        <p className="text-[#86868b] text-sm mb-8 max-w-md mx-auto">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-white text-black text-sm font-medium rounded-full hover:bg-[#f5f5f7] transition-colors"
        >
          ← Back to Home
        </Link>
      </div>
    </div>
  )
}
