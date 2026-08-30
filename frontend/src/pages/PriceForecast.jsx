import React, { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, ReferenceLine } from 'recharts'
import { api } from '../api/client'
import { useTheme } from '../context/ThemeContext'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

export default function PriceForecast() {
  const { theme } = useTheme()
  const axisColor = theme === 'dark' ? '#F7F3EA' : '#12261F'
  const gridColor = theme === 'dark' ? 'rgba(247,243,234,0.12)' : '#eee'
  const [crops, setCrops] = useState([])
  const [markets, setMarkets] = useState([])
  const [crop, setCrop] = useState('Tomato')
  const [market, setMarket] = useState('Bilaspur')
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

  const trendIcon = result?.trend_direction === 'increasing' ? '📈' : result?.trend_direction === 'decreasing' ? '📉' : '➖'

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">📈 Price Forecast</h1>
      <p className="text-ink/60 dark:text-paper/60 mb-3">Historical trend and a transparent 7-day forecast, with a visible confidence score.</p>

      <label className="flex items-center gap-2 text-xs text-ink/60 dark:text-paper/60 mb-4 select-none">
        <input type="checkbox" checked={showDemo} onChange={e => setShowDemo(e.target.checked)} />
        Show demo simulation (not real government data) — only if not enough real mandi history has been captured yet
      </label>

      <form onSubmit={run} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Crop</label>
          <select value={crop} onChange={e => setCrop(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Market</label>
          <select value={market} onChange={e => setMarket(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {markets.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
        </div>
        <button disabled={loading} className="bg-forest text-paper font-semibold rounded-lg py-2.5 hover:bg-forest-dark transition-colors disabled:opacity-60">
          {loading ? 'Forecasting...' : 'Get forecast'}
        </button>
      </form>

      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}
      {loading && <LoadingSpinner label="Running the forecast model..." />}

      {result && !loading && !result.available && (
        <div className="bg-wheat/50 border border-black/5 dark:border-white/10 text-ink/70 dark:text-paper/70 text-sm rounded-xl px-4 py-4">
          📭 {result.message || 'Historical mandi data is currently unavailable.'}
          {!showDemo && (
            <div className="mt-2 text-xs text-ink/50 dark:text-paper/50">
              No real accumulated mandi history exists yet for this crop/market. You can check "Show demo simulation" above to see the forecast methodology on a clearly-labeled synthetic dataset instead.
            </div>
          )}
        </div>
      )}

      {result && !loading && result.available && (
        <>
          {result.is_demo && (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-xs rounded-xl px-4 py-2 mb-4">
              🟡 DEMO SIMULATION — {result.demo_disclaimer || 'Not based on real government mandi data.'}
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">Current price</div>
              <div className="font-mono-data text-xl font-semibold">₹{result.current_price}/kg</div>
            </div>
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">Predicted (7d)</div>
              <div className="font-mono-data text-xl font-semibold">₹{result.predicted_price_low}--{result.predicted_price_high}</div>
            </div>
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">Trend</div>
              <div className="text-xl font-semibold">{trendIcon} {result.trend_direction}</div>
            </div>
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">Confidence</div>
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
                <ReferenceLine x={result.history[result.history.length - 1]?.date} stroke="#A65B3F" strokeDasharray="4 4" label={{ value: 'Today', fontSize: 10, fill: '#A65B3F' }} />
                <Line type="monotone" dataKey="actual" name="Historical price" stroke="#1F4D3D" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="predicted" name="Predicted price" stroke="#F2A93B" strokeWidth={2} strokeDasharray="5 4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-sm rounded-xl px-4 py-3 mb-4">
            ⚠️ Forecast range reflects historical variability and is not a guarantee -- actual market conditions may change.
          </div>

          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <h3 className="font-display font-semibold mb-3 text-sm">📐 Forecast methodology (technical transparency)</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs mb-3">
              <div><div className="text-ink/40 dark:text-paper/40">Method</div><div className="font-medium">{result.methodology.model_type}</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">Uses machine learning?</div><div className="font-medium">{result.methodology.is_machine_learning ? 'Yes' : 'No'}</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">Forecast horizon</div><div className="font-medium">{result.methodology.forecast_horizon_days} days</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">Historical data used</div><div className="font-medium">{result.methodology.historical_records_used} daily records</div></div>
              <div><div className="text-ink/40 dark:text-paper/40">Data source</div><div className="font-medium">{result.is_demo ? '🟡 Demo dataset' : '🟢 Government Data / Agmarknet'}</div></div>
            </div>
            {result.backtested_accuracy ? (
              <div className="bg-wheat/50 rounded-lg p-3">
                <div className="text-xs font-semibold mb-2">Genuine backtested accuracy ({result.backtested_accuracy.backtested_predictions} real walk-forward predictions on this crop/market's own history):</div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div><div className="font-mono-data text-lg font-bold">₹{result.backtested_accuracy.mae}</div><div className="text-[11px] text-ink/50 dark:text-paper/50">MAE</div></div>
                  <div><div className="font-mono-data text-lg font-bold">₹{result.backtested_accuracy.rmse}</div><div className="text-[11px] text-ink/50 dark:text-paper/50">RMSE</div></div>
                  <div><div className="font-mono-data text-lg font-bold">{result.backtested_accuracy.mape_pct}%</div><div className="text-[11px] text-ink/50 dark:text-paper/50">MAPE</div></div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-ink/40 dark:text-paper/40">Not enough historical data yet to compute a genuine backtested accuracy score for this crop/market.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
