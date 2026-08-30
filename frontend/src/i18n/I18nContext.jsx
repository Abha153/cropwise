import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { LANGUAGES, getLanguage, FULLY_SUPPORTED } from './languages'

const I18nContext = createContext(null)

// Lazy-loaded, cached per language so we never ship/parse translation JSON
// the user hasn't selected (performance requirement from the spec).
const translationCache = {}
async function loadTranslations(code) {
  if (translationCache[code]) return translationCache[code]
  if (!FULLY_SUPPORTED.includes(code)) {
    translationCache[code] = {} // no shipped resource -- will fall back to English per-key
    return translationCache[code]
  }
  try {
    const mod = await import(`./translations/${code}.json`)
    translationCache[code] = mod.default || mod
  } catch (e) {
    translationCache[code] = {}
  }
  return translationCache[code]
}

export function I18nProvider({ children }) {
  const [code, setCode] = useState(() => localStorage.getItem('cropwise_language') || 'en')
  const [dict, setDict] = useState({})
  const [enDict, setEnDict] = useState({})
  const [loading, setLoading] = useState(true)

  // English is always loaded as the fallback dictionary
  useEffect(() => { loadTranslations('en').then(setEnDict) }, [])

  useEffect(() => {
    setLoading(true)
    loadTranslations(code).then(d => { setDict(d); setLoading(false) })
    localStorage.setItem('cropwise_language', code)
  }, [code])

  const setLanguage = useCallback((newCode) => {
    setCode(newCode)
  }, [])

  const t = useCallback((key) => {
    return dict[key] || enDict[key] || key
  }, [dict, enDict])

  const languageInfo = useMemo(() => getLanguage(code), [code])
  const isFullySupported = FULLY_SUPPORTED.includes(code)

  useEffect(() => {
    document.documentElement.lang = code
    document.documentElement.dir = languageInfo.rtl ? 'rtl' : 'ltr'
  }, [code, languageInfo])

  const value = {
    code, setLanguage, t, loading,
    languageInfo, isFullySupported,
    languages: LANGUAGES,
    rtl: languageInfo.rtl,
  }

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
