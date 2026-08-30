import React from 'react'

export default function LoadingSpinner({ label = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-forest/70">
      <div className="w-8 h-8 border-4 border-forest/20 border-t-forest rounded-full animate-spin mb-3" />
      <p className="font-mono-data text-sm">{label}</p>
    </div>
  )
}
