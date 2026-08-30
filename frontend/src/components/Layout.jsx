import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useI18n } from '../i18n/I18nContext'
import LanguageSelector from './LanguageSelector'

function useNavLinks(role) {
  const farmer = [
    { to: '/farmer/dashboard', label: 'Dashboard', icon: '🏠' },
    { to: '/best-option', label: 'Best Selling Option', icon: '🎯' },
    { to: '/market-intelligence', label: 'Market Prices', icon: '📊' },
    { to: '/arrivals', label: 'Arrival Intelligence', icon: '📦' },
    { to: '/advisor', label: 'AgriAdvisor', icon: '🤖' },
    { to: '/forecast', label: 'Price Forecast', icon: '📈' },
    { to: '/marketplace', label: 'AgriMarket', icon: '🌾' },
    { to: '/lots', label: 'My Lots', icon: '🌾' },
    { to: '/buyer-demands', label: 'Buyer Demands', icon: '🛒' },
    { to: '/transactions', label: 'Transactions', icon: '💼' },
    { to: '/storage', label: 'Storage', icon: '🏭' },
    { to: '/transport', label: 'Transport', icon: '🚛' },
    { to: '/farmpool', label: 'FarmPool', icon: '🚚' },
    { to: '/profit-calculator', label: 'Profit Calculator', icon: '🧮' },
    { to: '/group-selling', label: 'Group Selling', icon: '🤝' },
    { to: '/notifications', label: 'Alerts', icon: '🔔' },
    { to: '/ask', label: 'Ask Assistant', icon: '🌐' },
    { to: '/profile', label: 'Profile', icon: '👤' },
  ]
  const buyer = [
    { to: '/buyer/dashboard', label: 'Dashboard', icon: '🏠' },
    { to: '/buyer-demands', label: 'My Demands', icon: '🛒' },
    { to: '/marketplace', label: 'AgriMarket', icon: '🌾' },
    { to: '/lots', label: 'Browse Lots', icon: '📦' },
    { to: '/transactions', label: 'Transactions', icon: '💼' },
    { to: '/buyer-verification', label: 'Verification', icon: '🏢' },
    { to: '/arrivals', label: 'Arrival Intelligence', icon: '📦' },
    { to: '/market-intelligence', label: 'Market Prices', icon: '📊' },
    { to: '/ask', label: 'Ask Assistant', icon: '🌐' },
    { to: '/profile', label: 'Profile', icon: '👤' },
  ]
  return role === 'buyer' ? buyer : farmer
}

export default function Layout({ children }) {
  const { role, user, logout } = useAuth()
  const { t } = useI18n()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const links = useNavLinks(role)

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-paper dark:bg-ink flex">
      <aside className={`fixed md:static z-30 inset-y-0 left-0 w-64 bg-forest dark:bg-forest-dark text-paper flex flex-col transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
        <div className="px-5 py-5 border-b border-white/10">
          <div className="font-display font-bold text-xl tracking-tight">🌱 CropWise</div>
          <div className="text-[11px] text-marigold-light font-mono-data mt-0.5">{t('tagline')}</div>
        </div>
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {links.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-marigold text-ink' : 'text-paper/80 hover:bg-white/10 hover:text-paper'
                }`
              }
            >
              <span>{link.icon}</span>
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-white/10">
          <div className="text-sm font-semibold truncate">{role === 'buyer' ? user?.company_name : user?.name}</div>
          <div className="text-xs text-paper/50 truncate mb-3">{user?.email}</div>
          <button onClick={handleLogout} className="w-full text-sm bg-white/10 hover:bg-white/20 rounded-lg py-2 transition-colors">
            {t('logout')}
          </button>
        </div>
      </aside>

      {open && <div className="fixed inset-0 bg-black/40 z-20 md:hidden" onClick={() => setOpen(false)} />}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between bg-forest text-paper px-4 py-3 sticky top-0 z-10 md:bg-transparent md:text-ink md:dark:text-paper md:px-8 md:py-4">
          <button onClick={() => setOpen(true)} className="text-2xl leading-none md:hidden" aria-label="Open navigation menu">☰</button>
          <div className="hidden md:block" />
          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="text-sm px-3 py-1.5 rounded-lg border border-white/20 md:border-black/10 md:dark:border-white/20 hover:bg-white/10 md:hover:bg-black/5 transition-colors"
              aria-label="Toggle dark mode"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <LanguageSelector />
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto text-ink dark:text-paper">
          {children}
        </main>
      </div>
    </div>
  )
}
