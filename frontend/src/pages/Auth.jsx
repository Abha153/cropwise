import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import { useI18n } from '../i18n/I18nContext'

const DEMO_ACCOUNTS = [
  { label: 'Ramesh Kumar (Farmer, Bilaspur)', email: 'ramesh@cropwise.demo', role: 'farmer' },
  { label: 'Sunita Verma (Farmer, Raigarh)', email: 'sunita@cropwise.demo', role: 'farmer' },
  { label: 'FreshFoods Processing (Buyer)', email: 'freshfoods@cropwise.demo', role: 'buyer' },
  { label: 'GreenBasket Retail (Buyer)', email: 'greenbasket@cropwise.demo', role: 'buyer' },
]

const CROP_OPTIONS = ['Tomato', 'Paddy (Rice)', 'Wheat', 'Potato', 'Onion', 'Soybean', 'Maize', 'Chana (Gram)', 'Groundnut', 'Sugarcane']

export default function Auth({ mode = 'login' }) {
  const [tab, setTab] = useState(mode)
  const [userType, setUserType] = useState('farmer')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { loginFarmer, registerFarmer, registerBuyer } = useAuth()
  const { code: uiLanguage } = useI18n()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [location, setLocation] = useState('Bilaspur')
  const [phone, setPhone] = useState('')
  const [crops, setCrops] = useState([])
  const [buyerType, setBuyerType] = useState('wholesaler')

  async function afterLogin(role) {
    navigate(role === 'buyer' ? '/buyer/dashboard' : '/farmer/dashboard')
  }

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginFarmer(email, password) // login endpoint handles both roles
      await afterLogin(data.role)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (userType === 'farmer') {
        const data = await registerFarmer({ name, email, password, location, phone, crops, preferred_language: uiLanguage })
        await afterLogin(data.role)
      } else {
        const data = await registerBuyer({ company_name: name, email, password, location, phone, buyer_type: buyerType, crops_of_interest: crops, preferred_language: uiLanguage })
        await afterLogin(data.role)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function toggleCrop(c) {
    setCrops(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])
  }

  async function quickDemoLogin(demoEmail) {
    setError('')
    setLoading(true)
    try {
      const data = await loginFarmer(demoEmail, 'demo1234')
      await afterLogin(data.role)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper dark:bg-ink flex flex-col lg:flex-row">
      {/* Branding panel -- desktop/tablet-landscape only. This is what makes the
          page use the available screen width properly instead of floating a
          small mobile-style card in a sea of empty space on large monitors. */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-3/5 bg-forest text-paper flex-col justify-between p-10 xl:p-16 relative overflow-hidden">
        <div className="absolute -right-24 -bottom-24 w-96 h-96 bg-marigold/10 rounded-full blur-3xl" aria-hidden="true" />
        <div className="absolute -left-16 -top-16 w-72 h-72 bg-white/5 rounded-full blur-3xl" aria-hidden="true" />

        <Link to="/" className="relative z-10 font-display font-bold text-2xl">🌱 CropWise</Link>

        <div className="relative z-10 max-w-lg">
          <h1 className="font-display text-4xl xl:text-5xl font-bold leading-tight mb-5">
            Know the price.<br />Find the buyer.<br /><span className="text-marigold-light">Sell with confidence.</span>
          </h1>
          <p className="text-paper/70 text-lg leading-relaxed">
            CropWise tells farmers their actual expected profit after transport and costs,
            predicts market opportunities, and connects them directly with the right buyer.
          </p>
        </div>

        <p className="relative z-10 font-mono-data text-sm text-marigold-light">
          Smart Markets. Better Prices. Stronger Farmers.
        </p>
      </div>

      {/* Form panel -- full-width single column on mobile/tablet, right-hand
          panel with a professional max-width on desktop. */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-10 xl:p-16">
        <div className="w-full max-w-md">
          <Link to="/" className="lg:hidden font-display font-bold text-2xl text-forest block text-center mb-8">🌱 CropWise</Link>

          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6 sm:p-8">
          <div className="flex bg-wheat dark:bg-white/5 rounded-xl p-1 mb-6">
            <button onClick={() => setTab('login')} className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${tab === 'login' ? 'bg-forest text-paper' : 'text-forest/70'}`}>Log in</button>
            <button onClick={() => setTab('register')} className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${tab === 'register' ? 'bg-forest text-paper' : 'text-forest/70'}`}>Register</button>
          </div>

          {tab === 'register' && (
            <div className="flex gap-2 mb-5">
              <button onClick={() => setUserType('farmer')} className={`flex-1 py-2 rounded-lg text-sm font-medium border ${userType === 'farmer' ? 'border-marigold bg-marigold/10 text-marigold-dark' : 'border-black/10 dark:border-white/15 text-ink/60 dark:text-paper/60'}`}>🌾 Farmer</button>
              <button onClick={() => setUserType('buyer')} className={`flex-1 py-2 rounded-lg text-sm font-medium border ${userType === 'buyer' ? 'border-rain bg-rain/10 text-rain' : 'border-black/10 dark:border-white/15 text-ink/60 dark:text-paper/60'}`}>🏢 Buyer</button>
            </div>
          )}

          {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}

          {tab === 'login' ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper" placeholder="you@example.com" />
              </div>
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Password</label>
                <input type="password" required value={password} onChange={e => setPassword(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper" placeholder="••••••••" />
              </div>
              <button disabled={loading} type="submit" className="w-full bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-60">
                {loading ? 'Logging in...' : 'Log in'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">{userType === 'farmer' ? 'Full name' : 'Company name'}</label>
                <input required value={name} onChange={e => setName(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper" />
              </div>
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper" />
              </div>
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Password</label>
                <input type="password" required minLength={6} value={password} onChange={e => setPassword(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Location</label>
                  <input required value={location} onChange={e => setLocation(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper" placeholder="Bilaspur" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Phone</label>
                  <input value={phone} onChange={e => setPhone(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper" placeholder="+91 ..." />
                </div>
              </div>
              {userType === 'buyer' && (
                <div>
                  <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Buyer type</label>
                  <select value={buyerType} onChange={e => setBuyerType(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-forest/30 bg-white dark:bg-white/5 dark:text-paper">
                    <option value="wholesaler">Wholesaler</option>
                    <option value="retailer">Retailer</option>
                    <option value="processor">Food processor</option>
                    <option value="exporter">Exporter</option>
                    <option value="fpo">FPO / Cooperative</option>
                  </select>
                </div>
              )}
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">{userType === 'farmer' ? 'Crops you grow' : 'Crops you buy'}</label>
                <div className="flex flex-wrap gap-1.5">
                  {CROP_OPTIONS.map(c => (
                    <button type="button" key={c} onClick={() => toggleCrop(c)} className={`text-xs px-2.5 py-1.5 rounded-full border ${crops.includes(c) ? 'bg-forest text-paper border-forest' : 'border-black/10 dark:border-white/15 text-ink/60 dark:text-paper/60'}`}>
                      {c}
                    </button>
                  ))}
                </div>
              </div>
              <button disabled={loading} type="submit" className="w-full bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-60">
                {loading ? 'Creating account...' : 'Create account'}
              </button>
            </form>
          )}

          <div className="mt-6 pt-5 border-t border-black/5 dark:border-white/10">
            <p className="text-xs font-semibold text-ink/50 dark:text-paper/50 mb-2">Or try instantly with a demo account (password: demo1234)</p>
            <div className="grid grid-cols-1 gap-1.5">
              {DEMO_ACCOUNTS.map(d => (
                <button key={d.email} onClick={() => quickDemoLogin(d.email)} className="text-left text-xs bg-wheat dark:bg-white/5 hover:bg-marigold/20 rounded-lg px-3 py-2 transition-colors">
                  {d.label}
                </button>
              ))}
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  )
}
