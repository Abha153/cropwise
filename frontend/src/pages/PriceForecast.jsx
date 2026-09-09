import React, { useEffect, useState } from 'react'
import { TrendingUp, ArrowUpRight, AlertTriangle, LineChart as LineChartIcon } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, ReferenceLine } from 'recharts'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { resolveDefaultLocation } from '../utils/location'
import { useTheme } from '../context/ThemeContext'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'
import { useI18n } from '../i18n/I18nContext'

export default function PriceForecast() {
  const { user } = useAuth()
  const { t } = useI18n()
  const { theme } = useTheme()
  const axisColor = theme === 'dark' ? '#F7F3EA' : '#12261F'
  const gridColor = theme === 'dark' ? 'rgba(247,243,234,0.12)' : '#eee'
  const [crops, setCrops] = useState([])
  const [markets, setMarkets] = useState([])
  const [crop, setCrop] = useState('Tomato')
  const [market, setMarket] = useState(() => resolveDefaultLocation(user))
  const [showDemo, setShowDemo] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getCrops().then(setCrops)
    api.getMarkets().then(setMarkets)
  }, [])

  async function run(e) {
    e?.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await api.getForecast(crop, market, showDemo)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { run() }, [showDemo]) // eslint-disable-line

  const chartData = result?.available ? [
    ...result.history.map(h => ({ date: h.date, actual: h.modal_price })),
    ...result.forecast_series.map(f => ({ date: f.date, predicted: f.predicted_price })),
  ] : []

  const trendIcon = result?.trend_direction === 'increasing' ? <TrendingUp size={16} /> : result?.trend_direction === 'decreasing' ? <ArrowUpRight size={16} className="rotate-90" /> : <LineChartIcon size={16} />

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <TrendingUp size={22} className="text-forest" />
        <h1 className="font-display text-3xl font-bold">{t('forecast.title')}</h1>
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-3">{t('forecast.subtitle')}</p>

      <label className="flex items-center gap-2 text-xs text-ink/60 dark:text-paper/60 mb-4 select-none">
        <input type="checkbox" checked={showDemo} onChange={e => setShowDemo(e.target.checked)} />
        {t('forecast.demoToggle')}
      </label>

      <form onSubmit={run} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">{t('common.crop')}</label>
          <select value={crop} onChange={e => setCrop(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">{t('ui.market')}</label>
          <select value={market} onChange={e => setMarket(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {markets.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
        </div>
        <button disabled={loading} className="bg-forest text-paper font-semibold rounded-lg py-2.5 hover:bg-forest-dark transition-colors disabled:opacity-60">
          {loading ? t('forecast.loading') : t('forecast.getForecast')}
        </button>
      </form>

      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}
      {loading && <LoadingSpinner label={t('forecast.running')} />}

      {result && !loading && !result.available && (
        <div className="bg-wheat/50 border border-black/5 dark:border-white/10 text-ink/70 dark:text-paper/70 text-sm rounded-xl px-4 py-4 inline-flex items-center gap-2">
          <LineChartIcon size={16} /> {result.message || t('forecast.historyUnavailable')}
          {!showDemo && (
            <div className="mt-2 text-xs text-ink/50 dark:text-paper/50">
              {t('forecast.noHistoryHelp')}
            </div>
          )}
        </div>
      )}

      {result && !loading && result.available && (
        <>
          {result.is_demo && (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-xs rounded-xl px-4 py-2 mb-4">
              🟡 {t('forecast.demoSimulationLabel')} — {result.demo_disclaimer || t('forecast.demoDisclaimerDefault')}
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">{t('forecast.currentPrice')}</div>
              <div className="font-mono-data text-xl font-semibold">₹{result.current_price}/kg</div>
            </div>
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">{t('forecast.predicted7Days')}</div>
              <div className="font-mono-data text-xl font-semibold">₹{result.predicted_price_low}--{result.predicted_price_high}</div>
            </div>
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">{t('forecast.trend')}</div>
              <div className="text-xl font-semibold">{trendIcon} {t(`forecast.trendDirection.${result.trend_direction}`)}</div>
            </div>
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">{t('forecast.confidence')}</div>
              <div className="text-xl font-semibold">{result.confidence_pct}%</div>
            </div>
          </div>

          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-4">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: axisColor }} interval={Math.floor(chartData.length / 8)} />
                <YAxis tick={{ fontSize: 12, fill: axisColor }} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={theme === 'dark' ? { background: '#1F4D3D', border: '1px solid rgba(255,255,255,0.15)', color: '#F7F3EA' } : undefined}
                  labelStyle={theme === 'dark' ? { color: '#F7F3EA' } : undefined}
                />
                <Legend />
                <ReferenceLine x={result.history[result.history.length - 1]?.date} stroke="#A65B3F" strokeDasharray="4 4" label={{ value: t('forecast.today'), fontSize: 10, fill: '#A65B3F' }} />
                <Line type="monotone" dataKey="actual" name={t('forecast.historicalPrice')} stroke="#1F4D3D" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="predicted" name={t('forecast.predictedPrice')} stroke="#F2A93B" strokeWidth={2} strokeDasharray="5 4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-sm rounded-xl px-4 py-3 mb-4 inline-flex items-center gap-2">
            <AlertTriangle size={16} /> {t('forecast.rangeDisclaimer')}
          </div>

          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <h3 className="font-display font-semibold mb-3 text-sm">📐 {t('forecast.methodologyHeading')}</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs mb-3">
              <div><div className="text-ink/40 dark:text-paper/40">{t('forecast.method')}</div><div className="font-medium">{result.methodology.model_type}</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">{t('forecast.machineLearning')}</div><div className="font-medium">{result.methodology.is_machine_learning ? t('forecast.yes') : t('forecast.no')}</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">{t('forecast.horizon')}</div><div className="font-medium">{result.methodology.forecast_horizon_days} {t('forecast.days')}</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">{t('forecast.historyUsed')}</div><div className="font-medium">{result.methodology.historical_records_used} {t('forecast.dailyRecords')}</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">{t('forecast.dataSource')}</div><div className="font-medium">{result.is_demo ? `🟡 ${t('forecast.demoDataset')}` : `🟢 ${t('forecast.govDataSource')}`}</div></div>
            </div>
            {result.backtested_accuracy ? (
              <div className="bg-wheat/50 rounded-lg p-3">
                <div className="text-xs font-semibold mb-2">{t('forecast.backtestedAccuracy', { count: result.backtested_accuracy.backtested_predictions })}</div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div><div className="font-mono-data text-lg font-bold">₹{result.backtested_accuracy.mae}</div><div className="text-[11px] text-ink/50 dark:text-paper/50">MAE</div></div>
                  <div><div className="font-mono-data text-lg font-bold">₹{result.backtested_accuracy.rmse}</div><div className="text-[11px] text-ink/50 dark:text-paper/50">RMSE</div></div>
                  <div><div className="font-mono-data text-lg font-bold">{result.backtested_accuracy.mape_pct}%</div><div className="text-[11px] text-ink/50 dark:text-paper/50">MAPE</div></div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-ink/40 dark:text-paper/40">{t('forecast.noBacktestData')}</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
