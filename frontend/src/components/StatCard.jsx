import React from 'react'

export default function StatCard({ label, value, sub, icon, tone = 'default' }) {
  const toneClasses = tone === 'marigold'
    ? 'bg-forest text-paper'
    : 'bg-white dark:bg-white/5 text-ink dark:text-paper'
  return (
    <div className={`rounded-2xl p-5 shadow-card border border-black/5 dark:border-white/10 ${toneClasses}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs uppercase tracking-wide font-semibold ${tone === 'marigold' ? 'text-marigold-light' : 'text-forest/60'}`}>{label}</span>
        {icon && <span className="text-xl">{icon}</span>}
      </div>
      <div className="font-mono-data text-2xl font-semibold">{value}</div>
      {sub && <div className={`text-xs mt-1 ${tone === 'marigold' ? 'text-paper/70' : 'text-ink/50 dark:text-paper/50'}`}>{sub}</div>}
    </div>
  )
}
