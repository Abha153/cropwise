import React, { useMemo } from 'react'
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts'
import { Droplets, Wind } from 'lucide-react'
import { useI18n } from '../../i18n/I18nContext'
import { useTheme } from '../../context/ThemeContext'
import { iconForWeatherCode } from '../../utils/weatherCodes'
import { formatHour, formatDayShort, roundOrDash } from '../../utils/weatherFormat'

const PAST_SHOWN = 3
const FUTURE_SHOWN = 24

/** Hourly FORECAST for the next 24 h (with the last few hours dimmed as
 *  "earlier" and the current hour highlighted). */
export default function HourlyForecast({ hourly }) {
  const { t, code } = useI18n()
  const { theme } = useTheme()
  const dark = theme === 'dark'

  const rows = useMemo(() => {
    const past = hourly.filter((h) => h.phase === 'past').slice(-PAST_SHOWN)
    const now = hourly.filter((h) => h.phase === 'current')
    const future = hourly.filter((h) => h.phase === 'future').slice(0, FUTURE_SHOWN)
    return [...past, ...now, ...future]
  }, [hourly])

  if (!rows.length) {
    return (
      <section aria-labelledby="wx-hourly-title" className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 sm:p-5">
        <h2 id="wx-hourly-title" className="font-display font-semibold text-base mb-2">{t('weatherPage.hourly.title')}</h2>
        <p className="text-sm text-ink/60 dark:text-paper/60">{t('weatherPage.hourly.unavailable')}</p>
      </section>
    )
  }

  // x is the full local timestamp (unique); only the tick LABEL is shortened.
  const chart = rows.map((h) => ({ time: h.time, temp: h.temperature, rain: h.rain_probability, phase: h.phase }))
  const nowLabel = (rows.find((h) => h.phase === 'current') || {}).time
  const axis = dark ? '#F7F3EA' : '#17372D'
  const grid = dark ? 'rgba(247,243,234,0.12)' : '#e6ece8'

  return (
    <section aria-labelledby="wx-hourly-title" className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 sm:p-5">
      <div className="flex items-baseline justify-between gap-2 mb-3 flex-wrap">
        <h2 id="wx-hourly-title" className="font-display font-semibold text-base">{t('weatherPage.hourly.title')}</h2>
        <span className="text-[11px] text-ink/50 dark:text-paper/50">{t('weatherPage.hourly.forecastNote')}</span>
      </div>

      <div className="h-44 -ml-2" role="img" aria-label={t('weatherPage.hourly.chartAria')}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={grid} />
            <XAxis dataKey="time" tickFormatter={(value) => formatHour(value, code)} tick={{ fontSize: 10, fill: axis }} interval="preserveStartEnd" minTickGap={24} />
            <YAxis yAxisId="t" tick={{ fontSize: 10, fill: axis }} width={32} unit="°" />
            <YAxis yAxisId="r" orientation="right" domain={[0, 100]} tick={{ fontSize: 10, fill: axis }} width={36} unit="%" />
            <Tooltip
              contentStyle={dark ? { background: '#1F4D3D', border: '1px solid rgba(255,255,255,0.15)', color: '#F7F3EA' } : undefined}
              labelStyle={dark ? { color: '#F7F3EA' } : undefined}
              labelFormatter={(v) => `${formatDayShort(v, code)} ${formatHour(v, code)}`}
              formatter={(v, name) => [name === 'rain' ? `${v}%` : `${v}°C`, name === 'rain' ? t('weatherPage.hourly.rainChance') : t('weatherPage.hourly.temp')]}
            />
            <Bar yAxisId="r" dataKey="rain" fill={dark ? '#6FA8B8' : '#3E6F7F'} fillOpacity={0.45} radius={[2, 2, 0, 0]} />
            <Line yAxisId="t" type="monotone" dataKey="temp" stroke={dark ? '#F2D08B' : '#C58B34'} strokeWidth={2} dot={false} connectNulls />
            {nowLabel && <ReferenceLine yAxisId="t" x={nowLabel} stroke="#B76C4B" strokeDasharray="4 4" />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <ul className="flex gap-2 overflow-x-auto pb-2 mt-3 -mx-1 px-1 snap-x" aria-label={t('weatherPage.hourly.listAria')}>
        {rows.map((h) => {
          const Icon = iconForWeatherCode(h.weather_code, h.is_day)
          const isNow = h.phase === 'current'
          const isPast = h.phase === 'past'
          const newDay = h.time.endsWith('T00:00')
          return (
            <li
              key={h.time}
              aria-current={isNow ? 'time' : undefined}
              className={`snap-start shrink-0 w-[72px] flex flex-col items-center py-2 rounded-xl border text-center ${
                isNow ? 'bg-forest/10 border-forest/40 dark:bg-white/10'
                  : isPast ? 'opacity-55 border-dashed border-black/15 dark:border-white/20'
                    : 'border-black/5 dark:border-white/10'}`}
            >
              <div className="text-[10px] font-semibold text-ink/60 dark:text-paper/60">
                {isNow ? t('weatherPage.hourly.now') : isPast ? t('weatherPage.hourly.earlier') : newDay ? formatDayShort(h.time, code) : formatHour(h.time, code)}
              </div>
              <Icon size={20} className="my-1 text-forest dark:text-forest-light" aria-label={h.condition || undefined} />
              <div className="font-mono-data text-sm font-semibold">{roundOrDash(h.temperature)}°</div>
              <div className="text-[10px] text-rain dark:text-sky-300 flex items-center gap-0.5 mt-0.5">
                <Droplets size={10} aria-hidden="true" />{roundOrDash(h.rain_probability)}%
              </div>
              {h.rainfall_mm != null && h.rainfall_mm > 0 && <div className="text-[10px] text-ink/60 dark:text-paper/60">{roundOrDash(h.rainfall_mm, 1)} mm</div>}
              <div className="text-[10px] text-ink/50 dark:text-paper/50 flex items-center gap-0.5"><Wind size={10} aria-hidden="true" />{roundOrDash(h.wind_speed_kmh)}</div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
