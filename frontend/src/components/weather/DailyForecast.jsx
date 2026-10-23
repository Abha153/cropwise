import React from 'react'
import { Droplets, Sunrise, Sunset } from 'lucide-react'
import { useI18n } from '../../i18n/I18nContext'
import { iconForWeatherCode, weatherConditionKey } from '../../utils/weatherCodes'
import { formatDayShort, formatDayLong, formatClock, roundOrDash } from '../../utils/weatherFormat'

/** 7-day FORECAST. The first row is today (highlighted) -- it mixes hours
 *  already past with hours to come, so its values describe the whole day. */
export default function DailyForecast({ forecast }) {
  const { t, code } = useI18n()
  return (
    <section aria-labelledby="wx-daily-title" className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 sm:p-5">
      <div className="flex items-baseline justify-between gap-2 mb-3 flex-wrap">
        <h2 id="wx-daily-title" className="font-display font-semibold text-base">{t('weatherPage.daily.title', { n: forecast.length })}</h2>
        <span className="text-[11px] text-ink/50 dark:text-paper/50">{t('weatherPage.daily.forecastNote')}</span>
      </div>
      <ul className="divide-y divide-black/5 dark:divide-white/10">
        {forecast.map((d, i) => {
          const Icon = iconForWeatherCode(d.weather_code)
          return (
            <li key={d.date} aria-current={i === 0 ? 'date' : undefined}
              className={`py-2.5 px-2 -mx-2 rounded-lg grid grid-cols-[3.2rem_1.6rem_1fr_auto] sm:grid-cols-[5.5rem_1.6rem_1fr_auto_auto] items-center gap-x-3 gap-y-1 ${i === 0 ? 'bg-forest/5 dark:bg-white/5' : ''}`}>
              <div>
                <div className="text-sm font-semibold">{i === 0 ? t('weatherPage.daily.today') : formatDayShort(d.date, code)}</div>
                <div className="text-[10px] text-ink/50 dark:text-paper/50 hidden sm:block">{formatDayLong(d.date, code)}</div>
              </div>
              <Icon size={20} className="text-forest dark:text-forest-light" aria-label={t(weatherConditionKey(d.weather_code))} />
              <div className="min-w-0">
                <div className="text-xs text-ink/70 dark:text-paper/70 truncate">{t(weatherConditionKey(d.weather_code))}</div>
                <div className="text-[11px] text-rain dark:text-sky-300 flex items-center gap-2 flex-wrap">
                  <span className="flex items-center gap-0.5"><Droplets size={11} aria-hidden="true" />{roundOrDash(d.rainfall_probability)}%</span>
                  <span>{roundOrDash(d.rainfall_mm, 1)} mm</span>
                  {d.et0_mm != null && <span className="text-ink/50 dark:text-paper/50">ET₀ {roundOrDash(d.et0_mm, 1)}</span>}
                </div>
              </div>
              <div className="font-mono-data text-sm text-right whitespace-nowrap">
                <span className="font-semibold">{roundOrDash(d.temp_max)}°</span>
                <span className="text-ink/50 dark:text-paper/50"> / {roundOrDash(d.temp_min)}°</span>
              </div>
              <div className="hidden sm:flex flex-col text-[10px] text-ink/50 dark:text-paper/50 items-end">
                {d.sunrise && <span className="flex items-center gap-0.5"><Sunrise size={10} aria-hidden="true" />{formatClock(d.sunrise, code)}</span>}
                {d.sunset && <span className="flex items-center gap-0.5"><Sunset size={10} aria-hidden="true" />{formatClock(d.sunset, code)}</span>}
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
