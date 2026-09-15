import React, { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, BarChart3, Check, CheckCircle2, ChevronRight,
  CloudSun, Database, LocateFixed, MapPin, MessageCircle, PackagePlus,
  RefreshCw, Scale, Sprout, TrendingUp, Truck, Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useI18n } from '../i18n/I18nContext'
import { resolveDefaultLocation } from '../utils/location'
import Badge from '../components/Badge'

const FACTOR_ICONS = {
  Demand: TrendingUp,
  'Supply / Arrivals': BarChart3,
  'Weather Risk': CloudSun,
  'Transport Cost': Truck,
  'Price Trend': TrendingUp,
}

function money(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'Not available'
  return `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: digits })}`
}

function perQuintal(value, quantity) {
  if (!quantity || value === null || value === undefined) return null
  return money((Number(value) / Number(quantity)) * 100)
}

function sourceSummary(options = []) {
  const sources = [...new Set(options.map(option => option.data_source).filter(Boolean))]
  if (sources.length === 1 && sources[0] === 'live') return { label: 'LIVE DATA', tone: 'live' }
  if (sources.length === 1 && sources[0] === 'demo') return { label: 'DEMO DATA', tone: 'demo' }
  if (sources.length > 1) return { label: 'MIXED SOURCES', tone: 'mixed' }
  return { label: 'SOURCE UNAVAILABLE', tone: 'unknown' }
}

function factorReason(factor) {
  const value = String(factor.value || '').toLowerCase()
  if (factor.label === 'Demand') return value === 'high' ? 'Buyer interest supports selling here.' : value === 'low' ? 'Demand is a caution signal for timing.' : 'Demand is steady for this comparison.'
  if (factor.label === 'Supply / Arrivals') return value === 'low' ? 'Lower arrivals can support firmer prices.' : value === 'high' ? 'Higher arrivals may put pressure on prices.' : 'Arrivals are not showing a strong pressure signal.'
  if (factor.label === 'Weather Risk') return value === 'low' ? 'Conditions add little disruption risk.' : value === 'high' ? 'Weather can affect transport and spoilage risk.' : 'Some disruption risk remains in the decision.'
  if (factor.label === 'Transport Cost') return value === 'low' ? 'The logistics burden is comparatively light.' : value === 'high' ? 'Transport takes a meaningful share of realization.' : 'Transport is a moderate cost in this option.'
  if (factor.label === 'Price Trend') return value === 'increasing' ? 'Recent prices are moving upward.' : value === 'decreasing' ? 'Recent prices are moving downward.' : 'Recent prices are broadly stable.'
  return factor.note || 'This factor was included in the recommendation.'
}

function LoadingAnalysis() {
  const steps = ['Checking available market prices', 'Comparing transport economics', 'Evaluating demand and arrivals', 'Reviewing current conditions']
  return <div className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 rounded-2xl p-6 shadow-card"><div className="flex items-center gap-3 mb-5"><div className="w-9 h-9 rounded-full bg-forest/10 flex items-center justify-center"><RefreshCw size={17} className="text-forest animate-spin" /></div><div><h2 className="font-display font-semibold">Analyzing your selling options</h2><p className="text-xs text-ink/45 dark:text-paper/45">Building a decision from the available market context.</p></div></div><div className="grid sm:grid-cols-2 gap-3">{steps.map((step, index) => <div key={step} className="flex items-center gap-2 text-sm text-ink/65 dark:text-paper/65"><span className={`w-5 h-5 rounded-full flex items-center justify-center ${index < 2 ? 'bg-forest text-paper' : 'border border-black/15 dark:border-white/20'}`}>{index < 2 && <Check size={13} />}</span>{step}</div>)}</div></div>
}

function DecisionInputs({ crop, quantity, quality, location, crops, setCrop, setQuantity, setQuality, setLocation, loading, ask, t }) {
  return <form onSubmit={ask} className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 rounded-2xl shadow-card p-5 md:p-6"><div className="flex items-start justify-between gap-4 mb-5"><div><p className="text-[10px] uppercase tracking-[0.18em] text-forest/60 dark:text-paper/45 font-bold">Your selling decision</p><p className="text-sm text-ink/55 dark:text-paper/55 mt-1">Give CropWise the context behind this harvest.</p></div><Scale size={21} className="text-marigold-dark flex-shrink-0" /></div><div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"><label className="block"><span className="flex items-center gap-2 text-xs font-semibold text-ink/60 dark:text-paper/60 mb-1.5"><Sprout size={14} className="text-forest" />{t('common.crop')}</span><select value={crop} onChange={e => setCrop(e.target.value)} className="advisor-input">{crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}</select></label><label className="block"><span className="flex items-center gap-2 text-xs font-semibold text-ink/60 dark:text-paper/60 mb-1.5"><Scale size={14} className="text-forest" />{t('common.quantityKg')}</span><input type="number" min="1" value={quantity} onChange={e => setQuantity(Number(e.target.value))} className="advisor-input" /><span className="block text-[11px] text-ink/40 dark:text-paper/40 mt-1">Your available quantity</span></label><label className="block"><span className="flex items-center gap-2 text-xs font-semibold text-ink/60 dark:text-paper/60 mb-1.5"><CheckCircle2 size={14} className="text-forest" />{t('common.qualityGrade')}</span><select value={quality} onChange={e => setQuality(e.target.value)} className="advisor-input"><option value="A">A -- Premium</option><option value="B">B -- Standard</option><option value="C">C -- Basic</option></select></label><label className="block"><span className="flex items-center gap-2 text-xs font-semibold text-ink/60 dark:text-paper/60 mb-1.5"><MapPin size={14} className="text-forest" />{t('common.location')}</span><input value={location} onChange={e => setLocation(e.target.value)} className="advisor-input" /><span className="block text-[11px] text-ink/40 dark:text-paper/40 mt-1">Used for nearby market comparison</span></label></div><div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-6 pt-5 border-t border-black/5 dark:border-white/10"><div className="flex items-center gap-2 text-xs text-ink/50 dark:text-paper/50"><LocateFixed size={14} /> {crop} · {Number(quantity || 0).toLocaleString('en-IN')} kg · {location || 'Location needed'}</div><button disabled={loading || !location || quantity <= 0} className="inline-flex items-center justify-center gap-2 bg-marigold hover:bg-marigold-dark text-ink font-semibold rounded-lg px-5 py-3 transition-colors disabled:opacity-60">{loading ? 'Analyzing...' : 'Analyze My Options'} <ArrowRight size={16} /></button></div></form>
}

function RecommendationHero({ result, quantity, onAsk }) {
  const recommendation = result.recommendation
  const options = recommendation.market_options_considered || []
  const best = options.find(option => option.market === recommendation.recommended_market) || options[0]
  const summary = best ? `CropWise favors ${best.market} because it provides the strongest estimated net realization for this quantity while transport is estimated at ${money(best.transport_cost)}.` : recommendation.recommendation_text
  return <section className="relative overflow-hidden rounded-2xl bg-forest text-paper p-6 md:p-8 shadow-card"><div className="absolute -right-16 -top-20 w-56 h-56 rounded-full border border-white/10" /><div className="absolute right-7 top-7 w-24 h-24 rounded-full border border-marigold/20" /><div className="relative"><div className="flex flex-wrap items-start justify-between gap-4 mb-7"><div><p className="text-[10px] uppercase tracking-[0.2em] text-marigold font-bold">CropWise recommendation</p><p className="text-paper/60 text-sm mt-2">Based on your current crop and market conditions</p></div><Badge tone={recommendation.confidence_label === 'High' ? 'success' : recommendation.confidence_label === 'Medium' ? 'marigold' : 'warning'}>{recommendation.confidence_label} confidence · {recommendation.confidence_pct}%</Badge></div><div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-8 items-end"><div><h2 className="font-display text-3xl md:text-4xl font-bold leading-tight max-w-2xl">{recommendation.recommendation_text}</h2><p className="text-paper/75 text-sm leading-relaxed mt-4 max-w-2xl">{summary}</p><div className="flex flex-wrap gap-2 mt-6"><button onClick={onAsk} className="inline-flex items-center gap-2 bg-marigold text-ink font-semibold rounded-lg px-4 py-2.5 text-sm hover:bg-marigold-dark">Ask about this result <MessageCircle size={15} /></button><Link to="/market-intelligence" className="inline-flex items-center gap-2 border border-white/20 text-paper font-semibold rounded-lg px-4 py-2.5 text-sm hover:bg-white/10">View market analysis <ArrowRight size={15} /></Link></div></div><div className="lg:border-l lg:border-white/15 lg:pl-7"><p className="text-xs text-paper/55 uppercase tracking-[0.14em]">Expected net realization</p><div className="font-mono-data text-3xl md:text-4xl font-bold mt-2">{best ? perQuintal(best.net_profit, quantity) : 'Not available'}<span className="text-base font-sans font-normal text-paper/60"> / q</span></div>{best && <div className="mt-4 space-y-2 text-sm"><div className="flex justify-between gap-4 text-paper/75"><span>Recommended market</span><strong className="text-paper">{best.market}</strong></div><div className="flex justify-between gap-4 text-paper/75"><span>Market price</span><strong className="text-paper">{money(best.modal_price_per_kg, 2)}/kg</strong></div><div className="flex justify-between gap-4 text-paper/75"><span>Transport estimate</span><strong className="text-paper">{money(best.transport_cost)}</strong></div></div>}</div></div></div></section>
}

function SourceNote({ options, latestDate }) {
  const source = sourceSummary(options)
  const tone = source.tone === 'live' ? 'text-emerald-700 bg-emerald-50 dark:bg-emerald-950/30' : source.tone === 'demo' ? 'text-amber-700 bg-amber-50 dark:bg-amber-950/30' : 'text-ink/60 bg-black/5 dark:text-paper/60 dark:bg-white/5'
  return <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-ink/50 dark:text-paper/50"><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-bold tracking-wide ${tone}`}><Database size={12} />{source.label}</span>{latestDate && <span>Updated from market record: {latestDate}</span>}<span>Estimates are labeled where applicable.</span></div>
}

function Reasoning({ factors }) {
  return <section><div className="flex items-end justify-between gap-3 mb-3"><div><p className="text-[10px] uppercase tracking-[0.18em] text-forest/60 dark:text-paper/45 font-bold">Why this recommendation</p><h2 className="font-display text-xl font-bold mt-1">Decision reasoning</h2></div><span className="text-xs text-ink/45 dark:text-paper/45">Decision -&gt; evidence -&gt; implication</span></div><div className="grid md:grid-cols-2 gap-3">{factors.map(factor => { const Icon = FACTOR_ICONS[factor.label] || CheckCircle2; const caution = ['high', 'decreasing'].includes(String(factor.value).toLowerCase()); return <div key={factor.label} className={`bg-white dark:bg-white/5 rounded-xl border p-4 ${caution ? 'border-amber-200 dark:border-amber-800/50' : 'border-black/5 dark:border-white/10'}`}><div className="flex gap-3"><div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${caution ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/30' : 'bg-forest/10 text-forest dark:text-marigold'}`}>{caution ? <AlertTriangle size={16} /> : <Icon size={16} />}</div><div><div className="flex items-center gap-2"><span className="text-[10px] uppercase tracking-[0.12em] font-bold text-ink/45 dark:text-paper/45">{factor.label}</span><span className="text-xs font-bold">{factor.value}</span></div><p className="text-sm text-ink/65 dark:text-paper/65 mt-1 leading-relaxed">{factorReason(factor)}</p></div></div></div> })}</div></section>
}

function MarketComparison({ result, quantity }) {
  const options = result.recommendation.market_options_considered || []
  return <section><div className="mb-3"><p className="text-[10px] uppercase tracking-[0.18em] text-forest/60 dark:text-paper/45 font-bold">Compare your options</p><h2 className="font-display text-xl font-bold mt-1">Where the money goes further</h2></div><div className="overflow-x-auto bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 shadow-card"><div className="min-w-[690px]"><div className="grid grid-cols-[1.35fr_0.8fr_0.8fr_0.9fr_0.95fr] gap-4 px-5 py-3 text-[10px] uppercase tracking-[0.12em] font-bold text-ink/40 dark:text-paper/40 border-b border-black/5 dark:border-white/10"><span>Market</span><span>Price/kg</span><span>Transport</span><span>Net/q</span><span>Signal</span></div>{options.map(option => { const recommended = option.market === result.recommendation.recommended_market; return <div key={option.market} className={`grid grid-cols-[1.35fr_0.8fr_0.8fr_0.9fr_0.95fr] items-center gap-4 px-5 py-4 text-sm border-b last:border-0 border-black/5 dark:border-white/10 ${recommended ? 'bg-marigold/10' : ''}`}><div><div className="font-semibold flex items-center gap-2">{recommended && <CheckCircle2 size={15} className="text-forest" />}{option.market}</div><div className="text-[11px] text-ink/45 dark:text-paper/45 mt-0.5">{option.distance_km} km · {option.data_source === 'live' ? 'Live record' : 'Demo record'}</div></div><span className="font-mono-data">{money(option.modal_price_per_kg, 2)}</span><span className="font-mono-data text-ink/65 dark:text-paper/65">{money(option.transport_cost)}</span><span className="font-mono-data font-bold">{perQuintal(option.net_profit, quantity)}</span><span>{recommended ? <Badge tone="success">Recommended</Badge> : <span className="text-xs text-ink/45 dark:text-paper/45">Alternative</span>}</span></div> })}</div></div></section>
}

function DecisionStory({ result, quantity }) {
  const recommendation = result.recommendation
  const best = (recommendation.market_options_considered || []).find(option => option.market === recommendation.recommended_market)
  if (!best) return null
  return <section className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 shadow-card p-5 md:p-6"><div className="mb-5"><p className="text-[10px] uppercase tracking-[0.18em] text-forest/60 dark:text-paper/45 font-bold">How the decision is built</p><h2 className="font-display text-xl font-bold mt-1">Price is only the starting point.</h2><p className="text-sm text-ink/55 dark:text-paper/55 mt-1">CropWise compares what the market pays with what it costs to reach it.</p></div><div className="grid md:grid-cols-3 gap-3 items-stretch"><div className="rounded-xl bg-forest/5 dark:bg-white/5 p-4"><p className="text-[10px] uppercase tracking-wide text-ink/45 dark:text-paper/45 font-bold">Market price</p><p className="font-mono-data text-2xl font-bold mt-2">{money(best.modal_price_per_kg, 2)}<span className="text-xs font-sans font-normal"> / kg</span></p><p className="text-xs text-ink/55 dark:text-paper/55 mt-1">Gross signal from {best.market}</p></div><div className="rounded-xl bg-amber-50/80 dark:bg-amber-950/20 p-4"><p className="text-[10px] uppercase tracking-wide text-ink/45 dark:text-paper/45 font-bold">Costs considered</p><p className="font-mono-data text-2xl font-bold mt-2">{money(Number(best.transport_cost) + Number(best.mandi_charges || 0) + Number(best.handling_cost || 0))}</p><p className="text-xs text-ink/55 dark:text-paper/55 mt-1">Transport, mandi and handling estimates</p></div><div className="rounded-xl bg-forest text-paper p-4"><p className="text-[10px] uppercase tracking-wide text-paper/55 font-bold">Net realization</p><p className="font-mono-data text-2xl font-bold mt-2">{perQuintal(best.net_profit, quantity)}<span className="text-xs font-sans font-normal text-paper/65"> / q</span></p><p className="text-xs text-paper/65 mt-1">What remains after estimated costs</p></div></div></section>
}

function WaitComparison({ result, quantity }) {
  const forecast = result.forecast
  const recommendation = result.recommendation
  const best = (recommendation.market_options_considered || []).find(option => option.market === recommendation.recommended_market)
  if (!forecast || !best) return null
  return <section className="bg-[#f4f0e4] dark:bg-white/5 rounded-2xl border border-[#e7ddc8] dark:border-white/10 p-5 md:p-6"><div className="flex items-start justify-between gap-4 mb-5"><div><p className="text-[10px] uppercase tracking-[0.18em] text-forest/60 dark:text-paper/45 font-bold">What if I wait?</p><h2 className="font-display text-xl font-bold mt-1">Sell now or hold part of the crop</h2></div><TrendingUp size={20} className="text-marigold-dark" /></div><div className="grid md:grid-cols-2 gap-3"><div className="bg-white/70 dark:bg-black/10 rounded-xl p-4 border border-black/5 dark:border-white/10"><p className="text-xs uppercase tracking-wide text-ink/45 dark:text-paper/45 font-bold">Sell now</p><p className="font-mono-data text-2xl font-bold mt-2">{perQuintal(best.net_profit, quantity)}<span className="text-sm font-sans font-normal"> / q</span></p><p className="text-xs text-ink/55 dark:text-paper/55 mt-1">Estimated net realization at {best.market}</p></div><div className="bg-white/70 dark:bg-black/10 rounded-xl p-4 border border-black/5 dark:border-white/10"><p className="text-xs uppercase tracking-wide text-ink/45 dark:text-paper/45 font-bold">Forecast market price</p><p className="font-mono-data text-2xl font-bold mt-2">{money(forecast.predicted_price_low, 2)} - {money(forecast.predicted_price_high, 2)}<span className="text-sm font-sans font-normal"> / kg</span></p><p className="text-xs text-ink/55 dark:text-paper/55 mt-1">{forecast.confidence_pct}% forecast confidence · {result.forecast_is_demo ? 'Demo history' : 'Live accumulated history'}</p></div></div><p className="text-sm text-ink/70 dark:text-paper/70 mt-4 leading-relaxed">{recommendation.wait_rationale}</p><p className="text-[11px] text-ink/45 dark:text-paper/45 mt-2">Storage cost is not included in this advisor comparison unless returned by the backend.</p></section>
}

function NextActions({ result }) {
  const market = result?.recommendation?.recommended_market
  return <section className="bg-forest text-paper rounded-2xl p-5 md:p-6"><div className="flex items-start justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.18em] text-marigold font-bold">Next best action</p><h2 className="font-display text-xl font-bold mt-1">Your market decision is ready.</h2><p className="text-sm text-paper/65 mt-2">Move from analysis to a practical next step{market ? ` for ${market}` : ''}.</p></div><ArrowRight size={20} className="text-marigold" /></div><div className="grid sm:grid-cols-3 gap-2 mt-5"><Link to="/market-intelligence" className="advisor-action"><BarChart3 size={16} /> View market analysis <ChevronRight size={14} className="ml-auto" /></Link><Link to="/marketplace" className="advisor-action"><Users size={16} /> Find matching buyers <ChevronRight size={14} className="ml-auto" /></Link><Link to="/lots" className="advisor-action"><PackagePlus size={16} /> Create a lot <ChevronRight size={14} className="ml-auto" /></Link></div></section>
}

export default function AIAdvisor() {
  const { t } = useI18n()
  const { user } = useAuth()
  const [crops, setCrops] = useState([])
  const [crop, setCrop] = useState('Tomato')
  const [quantity, setQuantity] = useState(1000)
  const [quality, setQuality] = useState('B')
  const [location, setLocation] = useState(() => resolveDefaultLocation(user))
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { api.getCrops().then(setCrops) }, [])
  useEffect(() => { if (user?.location) setLocation(user.location) }, [user])
  useEffect(() => { if (user?.crops?.[0]) setCrop(user.crops[0]) }, [user])

  async function ask(e) {
    e?.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await api.advisorRecommend({ crop, quantity_kg: quantity, quality_grade: quality, location })
      setResult(data)
    } catch (err) {
      setResult(null)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const confTone = result?.recommendation.confidence_label === 'High' ? 'success' : result?.recommendation.confidence_label === 'Medium' ? 'marigold' : 'warning'
  const options = result?.recommendation?.market_options_considered || []
  const latestDate = useMemo(() => options.map(option => option.as_of_date).filter(Boolean).sort().at(-1), [options])

  function askAboutResult() {
    window.location.href = '/ask'
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <header className="relative overflow-hidden rounded-2xl bg-[#e8f1e7] dark:bg-forest/45 border border-forest/10 dark:border-white/10 px-6 py-7 md:px-8 md:py-9">
        <div className="absolute -right-12 -top-16 w-52 h-52 rounded-full border border-forest/10 dark:border-white/10" />
        <div className="relative flex flex-col md:flex-row md:items-center gap-6">
          <div className="w-20 h-20 rounded-2xl bg-white/75 dark:bg-white/10 p-2 shadow-card flex-shrink-0">
            <img src="/apple-touch-icon.png" alt="CropWise advisor" className="w-full h-full rounded-xl object-cover" />
          </div>
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-forest dark:text-marigold text-xs uppercase tracking-[0.2em] font-bold"><Sprout size={16} /> {t('advisor.title')} <span className="text-marigold-dark">✦</span></div>
            <h1 className="font-display text-3xl md:text-4xl font-bold text-ink dark:text-paper mt-2">Your CropWise decision companion.</h1>
            <p className="text-ink/60 dark:text-paper/65 mt-2 max-w-2xl leading-relaxed">{t('advisor.subtitle')}</p>
            <p className="text-[11px] text-ink/40 dark:text-paper/45 mt-3">{t('advisor.disclaimer')}</p>
          </div>
        </div>
      </header>

      <DecisionInputs crop={crop} quantity={quantity} quality={quality} location={location} crops={crops} setCrop={setCrop} setQuantity={setQuantity} setQuality={setQuality} setLocation={setLocation} loading={loading} ask={ask} t={t} />

      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 rounded-2xl p-5"><div className="flex items-start gap-3"><AlertTriangle size={18} className="mt-0.5 flex-shrink-0" /><div><h2 className="font-semibold">{t('advisor.errorTitle')}</h2><p className="text-sm mt-1">{error}</p><button onClick={ask} className="inline-flex items-center gap-2 text-sm font-semibold mt-3 underline">{t('advisor.tryAgain')} <RefreshCw size={14} /></button></div></div></div>}
      {loading && <LoadingAnalysis />}
      {!loading && !result && !error && <div className="bg-white dark:bg-white/5 border border-dashed border-forest/20 dark:border-white/15 rounded-2xl p-7 text-center"><div className="w-11 h-11 rounded-full bg-marigold/20 text-forest mx-auto flex items-center justify-center"><LocateFixed size={20} /></div><p className="text-[10px] uppercase tracking-[0.18em] text-forest/60 dark:text-paper/45 font-bold mt-4">{t('advisor.readyLabel')}</p><h2 className="font-display text-xl font-bold mt-1">{t('advisor.readyTitle')}</h2><p className="text-sm text-ink/55 dark:text-paper/55 max-w-md mx-auto mt-2">{t('advisor.readyDescription')}</p></div>}
      {!loading && result && <div className="space-y-7"><RecommendationHero result={result} quantity={quantity} onAsk={askAboutResult} /><SourceNote options={options} latestDate={latestDate} /><Reasoning factors={result.recommendation.factors || []} /><DecisionStory result={result} quantity={quantity} /><MarketComparison result={result} quantity={quantity} /><WaitComparison result={result} quantity={quantity} /><section className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 shadow-card p-5 md:p-6"><div className="flex items-center justify-between gap-3 mb-4"><div><p className="text-[10px] uppercase tracking-[0.18em] text-forest/60 dark:text-paper/45 font-bold">{t('advisor.voiceLabel')}</p><h2 className="font-display text-xl font-bold mt-1">{t('advisor.voiceTitle')}</h2></div><Link to="/ask" className="inline-flex items-center gap-2 bg-forest text-paper rounded-lg px-4 py-2 text-sm font-semibold"><MessageCircle size={15} /> {t('advisor.openAssistant')}</Link></div><p className="text-sm text-ink/60 dark:text-paper/60">{t('advisor.voiceDescription')}</p><div className="flex flex-wrap gap-2 mt-4">{['advisor.quickSell', 'advisor.quickWait', 'advisor.quickCompare', 'advisor.quickEarn'].map(key => <Link key={key} to="/ask" className="text-xs border border-forest/15 dark:border-white/15 rounded-full px-3 py-2 text-forest dark:text-paper hover:bg-forest/5 dark:hover:bg-white/10">{t(key)}</Link>)}</div></section><NextActions result={result} /></div>}
    </div>
  )

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <BrainCircuit size={22} className="text-forest" />
        <h1 className="font-display text-3xl font-bold">{t('advisor.title')}</h1>
      </div>
      <p className="text-xs text-ink/40 dark:text-paper/40 mb-1">{t('advisor.disclaimer')}</p>
      <p className="text-ink/60 dark:text-paper/60 mb-6">{t('advisor.subtitle')}</p>

      <form onSubmit={ask} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">{t('common.crop')}</label>
          <select value={crop} onChange={e => setCrop(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">{t('common.quantityKg')}</label>
          <input type="number" min="1" value={quantity} onChange={e => setQuantity(Number(e.target.value))} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">{t('common.qualityGrade')}</label>
          <select value={quality} onChange={e => setQuality(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            <option value="A">A -- Premium</option>
            <option value="B">B -- Standard</option>
            <option value="C">C -- Basic</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1 flex items-center gap-2"><MapPin size={12} className="text-forest" />{t('common.location')}</label>
          <input value={location} onChange={e => setLocation(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <button disabled={loading} className="bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold rounded-lg py-2.5 transition-colors disabled:opacity-60">
          {loading ? t('advisor.thinking') : t('advisor.getRecommendation')}
        </button>
      </form>

      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}
      {loading && <LoadingSpinner label={t('advisor.analyzing')} />}

      {result && !loading && (
        <div className="space-y-6">
          <div className="bg-forest text-paper rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <Badge tone={confTone}>{result.recommendation.confidence_label} confidence · {result.recommendation.confidence_pct}%</Badge>
            </div>
            <p className="font-display text-xl md:text-2xl font-semibold leading-snug mb-3">
              {result.recommendation.recommendation_text}
            </p>
            <p className="text-paper/80 text-sm">{result.recommendation.wait_rationale}</p>
            <div className="grid grid-cols-2 gap-4 mt-5 pt-5 border-t border-white/10">
              <div>
                <div className="text-xs text-paper/60 mb-0.5">{t('advisor.expectedPriceRange')}</div>
                <div className="font-mono-data font-semibold">₹{result.recommendation.expected_price_range.low} -- ₹{result.recommendation.expected_price_range.high}/kg</div>
              </div>
              <div>
                <div className="text-xs text-paper/60 mb-0.5">{t('advisor.mainRisk')}</div>
                <div className="text-sm">{result.recommendation.primary_risk}</div>
              </div>
            </div>
          </div>

          <div>
            <h2 className="font-display font-semibold text-lg mb-3">{t('advisor.why')}</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {result.recommendation.factors.map(f => (
                <div key={f.label} className="bg-white dark:bg-white/5 rounded-xl border border-black/5 dark:border-white/10 shadow-card p-4 text-center">
                  <div className="text-2xl mb-1">{f.icon}</div>
                  <div className="text-xs text-ink/50 dark:text-paper/50 mb-0.5">{f.label}</div>
                  <div className="font-semibold text-sm">{f.value}</div>
                  {f.label === 'Weather Risk' && <div className="text-[10px] text-amber-600 mt-1 inline-flex items-center gap-1"><CloudSun size={10} /> Demo weather (simulated)</div>}
                  {f.label === 'Supply / Arrivals' && <div className="text-[10px] text-amber-600 mt-1 inline-flex items-center gap-1"><Sparkles size={10} /> Demo market data</div>}
                </div>
              ))}
            </div>
            <p className="text-xs text-ink/40 dark:text-paper/40 mt-2">Every factor above is a real input the recommendation engine used to reach its answer -- none are decorative. Market and weather figures come from CropWise's demo dataset, not a live feed.</p>
          </div>

          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <h2 className="font-display font-semibold text-lg mb-3">{t('advisor.marketOptions')}</h2>
            <div className="space-y-2">
              {result.recommendation.market_options_considered.map(m => (
                <div key={m.market} className={`flex items-center justify-between text-sm px-3 py-2 rounded-lg ${m.market === result.recommendation.recommended_market ? 'bg-marigold/10 font-semibold' : ''}`}>
                  <span>{m.market === result.recommendation.recommended_market ? '🟢 ' : ''}{m.market} ({m.distance_km} km)</span>
                  <span className="font-mono-data">₹{m.net_profit.toLocaleString()} net profit</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
