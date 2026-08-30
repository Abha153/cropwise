import React from 'react'
import { Link } from 'react-router-dom'
import PriceTicker from '../components/PriceTicker'
import LanguageSelector from '../components/LanguageSelector'
import { useI18n } from '../i18n/I18nContext'

const FEATURES = [
  { icon: '📊', title: 'Smart Price Discovery', desc: 'Compare mandi prices across nearby markets, not just the one closest to you (demo dataset -- see Market Intelligence for data source).' },
  { icon: '🤖', title: 'AgriAdvisor AI', desc: 'Get an explainable recommendation on where, when, and how much to sell -- with the reasons shown, never a black box.' },
  { icon: '📈', title: 'Price Forecasting', desc: '7-day price forecasts with a visible confidence score, built from real historical trends.' },
  { icon: '🌾', title: 'AgriMarket', desc: 'Post your harvest, receive competing offers from verified buyers, and negotiate directly.' },
  { icon: '⭐', title: 'Smart Buyer Matching', desc: 'Buyers ranked by net profit, reliability, and distance -- with the reasons spelled out.' },
  { icon: '🚚', title: 'FarmPool Logistics', desc: 'Share transport with nearby farmers heading to the same market and split the cost.' },
]

const STEPS = [
  { step: '1', title: 'Tell us your harvest', desc: 'Crop, quantity, quality grade, and location.' },
  { step: '2', title: 'See real net profit', desc: 'Not just price -- profit after transport, handling, and mandi charges.' },
  { step: '3', title: 'Sell with confidence', desc: 'Best market, best buyer, best timing -- all explained.' },
]

export default function Landing() {
  const { t } = useI18n()
  return (
    <div className="min-h-screen bg-paper dark:bg-ink text-ink dark:text-paper">
      <header className="flex items-center justify-between px-6 md:px-12 py-5">
        <div className="font-display font-bold text-xl text-forest">🌱 CropWise</div>
        <div className="flex items-center gap-3">
          <LanguageSelector compact />
          <Link to="/login" className="text-sm font-medium text-forest hover:underline">{t('login')}</Link>
          <Link to="/register" className="text-sm font-semibold bg-forest text-paper px-4 py-2 rounded-lg hover:bg-forest-dark transition-colors">
            {t('getStarted')}
          </Link>
        </div>
      </header>

      <PriceTicker />

      <section className="px-6 md:px-12 py-16 md:py-24 max-w-5xl mx-auto text-center">
        <div className="inline-block bg-marigold/15 text-marigold-dark border border-marigold/30 rounded-full px-4 py-1 text-xs font-semibold font-mono-data mb-6">
          A decision-support platform, not another mandi price app
        </div>
        <h1 className="font-display text-4xl md:text-6xl font-bold leading-tight mb-6">
          {t('heroTitle1')}<br />{t('heroTitle2')}<br /><span className="text-forest">{t('heroTitle3')}</span>
        </h1>
        <p className="text-lg text-ink/70 dark:text-paper/70 max-w-2xl mx-auto mb-4">
          {t('heroSubtitle')}
        </p>
        <p className="font-mono-data text-sm text-forest font-semibold mb-2">
          {t('tagline')}
        </p>
        <p className="text-xs text-ink/40 dark:text-paper/40 mb-8">
          🌐 Multilingual text and interface support · reliable Hindi & English voice assistance
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/register" className="w-full sm:w-auto bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold px-8 py-3.5 rounded-xl shadow-card transition-colors">
            {t('imFarmer')} 🌾
          </Link>
          <Link to="/register" className="w-full sm:w-auto bg-white dark:bg-white/5 hover:bg-wheat dark:bg-white/5 border border-forest/20 text-forest font-semibold px-8 py-3.5 rounded-xl shadow-card transition-colors">
            {t('imBuyer')} 🏢
          </Link>
        </div>
      </section>

      <section className="bg-white dark:bg-white/5 py-14">
        <div className="max-w-5xl mx-auto px-6 md:px-12">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {STEPS.map(s => (
              <div key={s.step} className="text-center">
                <div className="w-10 h-10 rounded-full bg-forest text-paper font-mono-data font-bold flex items-center justify-center mx-auto mb-3">{s.step}</div>
                <h3 className="font-display font-semibold text-lg mb-1">{s.title}</h3>
                <p className="text-sm text-ink/60 dark:text-paper/60">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 md:px-12 py-16 max-w-6xl mx-auto">
        <h2 className="font-display text-3xl font-bold text-center mb-3">Everything a farmer needs to sell smarter</h2>
        <p className="text-center text-ink/60 dark:text-paper/60 mb-12">One platform, from price discovery to the final sale.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map(f => (
            <div key={f.title} className="bg-white dark:bg-white/5 rounded-2xl p-6 shadow-card border border-black/5 dark:border-white/10 hover:-translate-y-0.5 transition-transform">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-display font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-sm text-ink/60 dark:text-paper/60">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-forest text-paper py-16">
        <div className="max-w-4xl mx-auto px-6 md:px-12 text-center">
          <h2 className="font-display text-3xl font-bold mb-4">"Why would a farmer use CropWise instead of asking a local trader?"</h2>
          <p className="text-paper/80 max-w-2xl mx-auto">
            Existing platforms tell farmers the market price. CropWise tells them their actual expected
            profit after transportation and other costs, predicts market opportunities, and directly
            connects them with suitable buyers -- helping them decide where, when, and to whom they should sell.
          </p>
        </div>
      </section>

      <footer className="px-6 md:px-12 py-8 text-center text-xs text-ink/40 dark:text-paper/40 font-mono-data">
        CropWise -- built for the Strengthening Market Linkages and Price Discovery for Farmers hackathon track. Demo data only.
      </footer>
    </div>
  )
}
