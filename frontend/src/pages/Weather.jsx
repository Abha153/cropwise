import React, { useCallback, useEffect, useState } from 'react'
import { CloudOff, MapPinned, RefreshCw, AlertTriangle, Info, SearchX } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useI18n } from '../i18n/I18nContext'
import { useWeatherData } from '../hooks/useWeatherData'
import LocationPicker from '../components/weather/LocationPicker'
import WeatherOverview, { WeatherOverviewSkeleton } from '../components/weather/WeatherOverview'
import HourlyForecast from '../components/weather/HourlyForecast'
import DailyForecast from '../components/weather/DailyForecast'
import AdvisoryPanel, { AdvisorySkeleton } from '../components/weather/AdvisoryPanel'
import {
  loadLocation, saveLocation, clearLocation, loadCropChoice, saveCropChoice,
} from '../utils/weatherLocationStore'

function Banner({ tone, Icon, children, action }) {
  const tones = {
    warn: 'bg-amber-50 text-amber-900 border-amber-300 dark:bg-amber-400/10 dark:text-amber-200 dark:border-amber-300/30',
    error: 'bg-red-50 text-red-900 border-red-300 dark:bg-red-400/10 dark:text-red-200 dark:border-red-300/30',
    info: 'bg-sky-50 text-sky-900 border-sky-200 dark:bg-sky-400/10 dark:text-sky-200 dark:border-sky-300/30',
  }
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`flex items-start gap-2 border rounded-xl px-4 py-3 text-sm ${tones[tone]}`}>
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="flex-1">{children}</div>
      {action}
    </div>
  )
}

export default function Weather() {
  const { t, code } = useI18n()
  const { user } = useAuth()
  const [location, setLocation] = useState(() => loadLocation())
  const [{ crop, stage }, setCropChoice] = useState(() => loadCropChoice())

  const { status, data, error, refresh } = useWeatherData(location, { crop, stage })

  const onSelect = useCallback((loc) => { setLocation(loc); saveLocation(loc) }, [])
  const onClear = useCallback(() => { setLocation(null); clearLocation() }, [])
  function updateCrop(next) { setCropChoice(next); saveCropChoice(next) }

  useEffect(() => { document.title = `${t('weatherPage.title')} · CropWise` }, [t])

  const profilePlace = user && user.location ? user.location : null
  const loading = status === 'loading'
  const hasData = data && data.status !== 'UNAVAILABLE' && data.current
  const unavailable = data && data.status === 'UNAVAILABLE'

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <header>
        <h1 className="font-display text-3xl font-bold">{t('weatherPage.title')}</h1>
        <p className="text-sm text-ink/60 dark:text-paper/60 mt-1">{t('weatherPage.subtitle')}</p>
      </header>

      <LocationPicker selected={location} onSelect={onSelect} onClear={onClear} />

      {/* ---- no location chosen yet ---- */}
      {!location && (
        <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-8 text-center">
          <MapPinned size={36} className="mx-auto text-forest dark:text-forest-light mb-3" aria-hidden="true" />
          <h2 className="font-display font-semibold text-lg mb-1">{t('weatherPage.empty.title')}</h2>
          <p className="text-sm text-ink/60 dark:text-paper/60 max-w-md mx-auto">{t('weatherPage.empty.body')}</p>
          {profilePlace && (
            <button
              type="button"
              onClick={async () => {
                // Explicit choice only: resolve the profile place by name, pick the first match.
                try {
                  const { api } = await import('../api/client')
                  const res = await api.searchLocations(profilePlace, { language: ['bho', 'mai'].includes(code) ? 'hi' : code })
                  const r = res.results && res.results[0]
                  if (r) onSelect({ label: r.label, name: r.name, admin1: r.admin1, admin2: r.admin2, country: r.country, latitude: r.latitude, longitude: r.longitude, source: 'search' })
                } catch (e) { /* the search box above remains available */ }
              }}
              className="mt-4 text-sm underline text-forest dark:text-forest-light focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold rounded"
            >
              {t('weatherPage.empty.useProfile', { place: profilePlace })}
            </button>
          )}
        </div>
      )}

      {/* ---- first load ---- */}
      {location && loading && !data && (
        <>
          <WeatherOverviewSkeleton />
          <AdvisorySkeleton />
        </>
      )}

      {/* ---- error with nothing to show ---- */}
      {location && status === 'error' && !data && (
        <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-8 text-center" role="alert">
          <CloudOff size={36} className="mx-auto text-clay mb-3" aria-hidden="true" />
          <h2 className="font-display font-semibold text-lg mb-1">{t('weatherPage.error.title')}</h2>
          <p className="text-sm text-ink/60 dark:text-paper/60 mb-4">{t('weatherPage.error.body')}</p>
          <button type="button" onClick={refresh} className="inline-flex items-center gap-2 bg-forest text-paper font-semibold rounded-lg px-4 py-2.5 text-sm hover:bg-forest-dark min-h-[44px] focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold">
            <RefreshCw size={14} aria-hidden="true" /> {t('weatherPage.retry')}
          </button>
        </div>
      )}

      {/* ---- provider says nothing for this place ---- */}
      {location && unavailable && (
        <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-8 text-center">
          <SearchX size={36} className="mx-auto text-clay mb-3" aria-hidden="true" />
          <h2 className="font-display font-semibold text-lg mb-1">{t('weatherPage.unavailable.title')}</h2>
          <p className="text-sm text-ink/60 dark:text-paper/60 mb-4">{t('weatherPage.unavailable.body')}</p>
          <button type="button" onClick={refresh} className="inline-flex items-center gap-2 border border-black/10 dark:border-white/15 rounded-lg px-4 py-2.5 text-sm hover:bg-mist dark:hover:bg-white/10 min-h-[44px] focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold">
            <RefreshCw size={14} aria-hidden="true" /> {t('weatherPage.retry')}
          </button>
        </div>
      )}

      {/* ---- data ---- */}
      {location && hasData && (
        <>
          {status === 'error' && (
            <Banner tone="warn" Icon={AlertTriangle}
              action={<button type="button" onClick={refresh} className="underline text-sm shrink-0">{t('weatherPage.retry')}</button>}>
              {t('weatherPage.error.refreshFailed')}
            </Banner>
          )}
          {data.status === 'STALE' && (
            <Banner tone="warn" Icon={AlertTriangle}
              action={<button type="button" onClick={refresh} className="underline text-sm shrink-0">{t('weatherPage.retry')}</button>}>
              <strong>{t('weatherPage.stale.title')}</strong>
            </Banner>
          )}
          {data.status === 'DEMO' && (
            <Banner tone="info" Icon={Info}>
              <strong>{t('weatherPage.demo.title')}</strong> {t('weatherPage.demo.body')}
            </Banner>
          )}

          <WeatherOverview weather={data} onRefresh={refresh} refreshing={loading} />
          {data.status !== 'DEMO' && <HourlyForecast hourly={data.hourly || []} />}
          <DailyForecast forecast={data.forecast || []} />
          <AdvisoryPanel
            advisory={data.advisory} crop={crop} stage={stage}
            onCropChange={(c) => updateCrop({ crop: c, stage: c ? stage : '' })}
            onStageChange={(s) => updateCrop({ crop, stage: s })}
          />

          <footer className="text-[11px] text-ink/50 dark:text-paper/50 leading-relaxed pb-6">
            {data.attribution ? (
              <p>
                {t('weatherPage.attribution.prefix')}{' '}
                <a href={data.attribution.url} target="_blank" rel="noopener noreferrer" className="underline">{data.attribution.provider}</a>
                {' '}({data.attribution.license}). {t('weatherPage.attribution.geocoding')}
              </p>
            ) : (
              <p>{t('weatherPage.attribution.demo')}</p>
            )}
            <p className="mt-1">{t('weatherPage.attribution.notImd')}</p>
          </footer>
        </>
      )}
    </div>
  )
}
