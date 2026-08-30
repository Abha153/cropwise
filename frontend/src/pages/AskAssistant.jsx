import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useI18n } from '../i18n/I18nContext'
import { getSpeechProvider, isSpeechSupportedAtAll, isVoiceInputSupportedForLanguage, VOICE_INPUT_SUPPORTED_LANGUAGES } from '../i18n/speech'
import { getTTSProvider, subscribeToVoicesChanged } from '../i18n/tts'
import { FULLY_SUPPORTED } from '../i18n/languages'
import LanguageSelector from '../components/LanguageSelector'

const EXAMPLES_BY_LANG = {
  en: ['Where should I sell my tomatoes from Bilaspur?', 'I have 20 quintals of soybean in Raipur'],
  hi: ['मेरे पास 10 क्विंटल धान है बिलासपुर में, कहाँ बेचूं?'],
  mr: ['माझ्याकडे २० क्विंटल सोयाबीन आहे रायपुर मध्ये, मला कुठे विकल्यास जास्त फायदा होईल?'],
  bn: ['আমার কাছে ৫ কুইন্টাল পেঁয়াজ আছে দুর্গ-এ'],
  ta: ['எனக்கு பிலாஸ்பூரில் இருந்து 5 குவிண்டல் தக்காளி விற்க வேண்டும்'],
}

export default function AskAssistant() {
  const { user } = useAuth()
  const { code, t, languages, setLanguage } = useI18n()
  const langInfo = languages.find(l => l.code === code) || languages[0]

  const [messages, setMessages] = useState([]) // {role, text, language}
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [listening, setListening] = useState(false)
  const [micError, setMicError] = useState('')
  const [voiceReplies, setVoiceReplies] = useState(true)
  const [voicesTick, setVoicesTick] = useState(0) // bumped whenever the device's voice list changes
  // Voice recognition confirmation step: never auto-execute a recognized
  // command silently -- always show what was heard first.
  const [pendingTranscript, setPendingTranscript] = useState(null)
  const recognitionRef = useRef(null)
  const knownRef = useRef({ crop: null, quantity_kg: null, location: null })
  const scrollRef = useRef(null)

  const speechApiSupported = isSpeechSupportedAtAll()
  const voiceOfferedForLanguage = isVoiceInputSupportedForLanguage(code)
  const speechSupported = speechApiSupported && voiceOfferedForLanguage
  const nativeAI = FULLY_SUPPORTED.includes(code)

  useEffect(() => {
    // Some languages' voices register with the browser later than common
    // ones -- keep listening for changes rather than checking once, and
    // also poll a few times as a safety net for browsers that never fire
    // the `voiceschanged` event at all.
    const recompute = () => setVoicesTick(v => v + 1)
    const unsubscribe = subscribeToVoicesChanged(recompute)
    const timers = [0, 150, 500, 1200, 2500].map(ms => setTimeout(recompute, ms))
    return () => { unsubscribe(); timers.forEach(clearTimeout) }
  }, [])
  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { setPendingTranscript(null); setMicError('') }, [code])

  const ttsProvider = getTTSProvider('browser')
  // eslint-disable-next-line no-unused-vars -- voicesTick forces this to recompute live
  const ttsAvailable = voicesTick >= 0 && ttsProvider.isAvailable(code)

  function startListening() {
    setMicError('')
    setPendingTranscript(null)
    const provider = getSpeechProvider('browser')
    const rec = provider.listen({
      languageCode: code,
      onStart: () => setListening(true),
      onEnd: () => setListening(false),
      onResult: (transcript) => {
        // Never auto-execute -- show what was heard and let the farmer
        // confirm, edit, or re-record before it's sent anywhere.
        setPendingTranscript(transcript)
      },
      onError: (err) => {
        setListening(false)
        setMicError(err.message)
      },
    })
    recognitionRef.current = rec
  }

  function stopListening() {
    recognitionRef.current?.stop?.()
    setListening(false)
  }

  function confirmTranscript() {
    const text = pendingTranscript
    setPendingTranscript(null)
    submit(text)
  }

  function editTranscript() {
    setQuestion(pendingTranscript)
    setPendingTranscript(null)
  }

  function retryListening() {
    setPendingTranscript(null)
    startListening()
  }

  async function submit(overrideText) {
    const text = (overrideText ?? question).trim()
    if (!text) return
    setQuestion('')
    setMessages(m => [...m, { role: 'user', text, language: code }])
    setLoading(true)
    try {
      const res = await api.askAssistant({
        question: text, language: code,
        known_crop: knownRef.current.crop,
        known_quantity_kg: knownRef.current.quantity_kg,
        known_location: knownRef.current.location,
      })
      knownRef.current = {
        crop: res.crop ?? knownRef.current.crop,
        quantity_kg: res.quantity_kg ?? knownRef.current.quantity_kg,
        location: res.location ?? knownRef.current.location,
      }
      setMessages(m => [...m, {
        role: 'assistant', text: res.answer, language: code,
        native: res.native_response, meta: res,
      }])
      if (voiceReplies && ttsProvider.isAvailable(code)) {
        ttsProvider.speak(res.answer, code, {})
      }
    } catch (err) {
      setMessages(m => [...m, { role: 'assistant', text: `⚠️ ${err.message}`, language: code, error: true }])
    } finally {
      setLoading(false)
    }
  }

  function speak(text) {
    ttsProvider.speak(text, code, {
      onError: (e) => setMicError(e.message),
    })
  }

  const examples = EXAMPLES_BY_LANG[code] || EXAMPLES_BY_LANG.en
  const voiceLangNames = VOICE_INPUT_SUPPORTED_LANGUAGES.map(c => languages.find(l => l.code === c)?.native || c).join(' & ')

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-1 gap-3 flex-wrap">
        <h1 className="font-display text-3xl font-bold">🌐 Global Farm Assistant</h1>
        <LanguageSelector compact />
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-1">Speak or type in {langInfo.native} -- switch languages anytime without losing context.</p>
      <p className="text-xs text-ink/40 dark:text-paper/40 mb-1">⚙️ Powered by CropWise's rule-based multilingual intent engine (crop/quantity/location extraction + market comparison) -- not a general-purpose LLM. It's fast, transparent, and works offline, but can't yet answer open-ended questions outside its supported intents.</p>
      <p className="text-xs text-ink/40 dark:text-paper/40 mb-4">🎤 Multilingual text and interface support, with reliable voice assistance currently offered in {voiceLangNames} only -- see below.</p>

      {/* Live capability status -- honest, never fake */}
      <div className="flex flex-wrap gap-2 mb-2">
        <span className={`text-xs px-2.5 py-1 rounded-full border ${nativeAI ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900' : 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 border-amber-200 dark:border-amber-900'}`}>
          🧠 AI understanding: {nativeAI ? `native ${langInfo.native}` : 'English fallback'}
        </span>
        <span className={`text-xs px-2.5 py-1 rounded-full border ${speechSupported ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900' : 'bg-stone-100 dark:bg-white/10 text-stone-500 dark:text-stone-400 border-stone-200 dark:border-white/10'}`}>
          🎤 Voice input: {!speechApiSupported ? 'not supported in this browser' : voiceOfferedForLanguage ? 'available (device-dependent)' : `not offered for ${langInfo.native}`}
        </span>
        <span className={`text-xs px-2.5 py-1 rounded-full border ${ttsAvailable ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900' : 'bg-stone-100 dark:bg-white/10 text-stone-500 dark:text-stone-400 border-stone-200 dark:border-white/10'}`}>
          🔊 Voice output: {ttsAvailable ? 'available on this device' : 'no voice installed for this language'}
        </span>
      </div>
      {speechApiSupported && !voiceOfferedForLanguage && (
        <div className="bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-900 text-sky-800 dark:text-sky-300 text-xs rounded-lg px-3 py-2 mb-3 flex items-center justify-between gap-2 flex-wrap">
          <span>Voice input is currently available in {voiceLangNames} only, for reliability. Please type your request in {langInfo.native}, or switch voice language.</span>
          <button onClick={() => setLanguage('en')} className="shrink-0 text-xs font-semibold bg-sky-600 text-white rounded-full px-3 py-1">Switch to English</button>
        </div>
      )}
      {!ttsAvailable && (
        <p className="text-xs text-ink/40 dark:text-paper/40 mb-4">
          Your browser/device doesn't currently have a {langInfo.native} text-to-speech voice installed, so replies will
          be shown as text only. This is a device limitation, not a CropWise limitation.
        </p>
      )}

      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 mb-4 h-96 overflow-y-auto flex flex-col gap-3">
        {messages.length === 0 && !pendingTranscript && (
          <div className="text-sm text-ink/40 dark:text-paper/40 m-auto text-center px-6">
            {t('speakNow')}
            <div className="flex flex-wrap gap-2 justify-center mt-3">
              {examples.map(ex => (
                <button key={ex} onClick={() => { setQuestion(ex); submit(ex) }} className="text-xs bg-wheat dark:bg-white/5 hover:bg-marigold/20 rounded-full px-3 py-1.5 transition-colors">
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${m.role === 'user' ? 'self-end bg-marigold/20 text-ink dark:text-paper' : m.error ? 'self-start bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300' : 'self-start bg-forest text-paper'}`}>
            <p>{m.text}</p>
            {m.role === 'assistant' && !m.error && (
              <div className="flex items-center gap-2 mt-2">
                <button onClick={() => speak(m.text)} className="text-xs bg-white/15 hover:bg-white/25 rounded-full px-2.5 py-1 transition-colors" aria-label={`${t('listenBtn')}: ${m.text}`}>
                  🔊 {t('listenBtn')}
                </button>
                {m.meta?.clarification_needed && (
                  <span className="text-xs text-paper/60">waiting for: {m.meta.clarification_needed}</span>
                )}
                {!m.native && <span className="text-xs text-paper/60">(English fallback)</span>}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="self-start text-xs text-ink/40 dark:text-paper/40">…</div>}

        {/* Recognized-speech confirmation -- never auto-execute a voice command */}
        {pendingTranscript && (
          <div className="self-center w-full max-w-sm bg-wheat dark:bg-white/5 rounded-2xl p-4 text-center">
            <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">🎤 I heard:</div>
            <p className="font-medium mb-3">"{pendingTranscript}"</p>
            <div className="flex flex-wrap gap-2 justify-center">
              <button onClick={confirmTranscript} className="text-xs bg-forest text-paper font-semibold rounded-full px-3 py-1.5">✓ Confirm</button>
              <button onClick={editTranscript} className="text-xs bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 font-semibold rounded-full px-3 py-1.5">✏ Edit</button>
              <button onClick={retryListening} className="text-xs bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 font-semibold rounded-full px-3 py-1.5">🔄 Speak Again</button>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {micError && (
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-sm rounded-lg px-3 py-2 mb-3 flex items-center justify-between gap-2">
          <span>⚠️ {micError}</span>
          <button onClick={() => setMicError('')} className="text-xs underline shrink-0">dismiss</button>
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); submit() }} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-3">
        <div className="flex items-center gap-2">
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder={t('askPlaceholder')}
            className="flex-1 border border-black/10 dark:border-white/15 rounded-lg px-3 py-3 text-sm bg-white dark:bg-white/5 dark:text-paper"
            dir={langInfo.rtl ? 'rtl' : 'ltr'}
          />
          {speechSupported && (
            <button
              type="button"
              onClick={listening ? stopListening : startListening}
              className={`w-11 h-11 rounded-lg flex items-center justify-center text-lg transition-colors shrink-0 ${listening ? 'bg-red-500 text-white animate-pulse' : 'bg-wheat dark:bg-white/5 hover:bg-marigold/20'}`}
              title={listening ? t('listening') : t('speakNow')}
              aria-label={listening ? t('listening') : t('speakNow')}
              aria-pressed={listening}
            >
              🎤
            </button>
          )}
          <button disabled={loading} className="bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold rounded-lg px-5 py-3 transition-colors disabled:opacity-60 shrink-0">
            {loading ? '...' : t('askButton')}
          </button>
        </div>
        <label className="flex items-center gap-2 mt-2 text-xs text-ink/50 dark:text-paper/50">
          <input type="checkbox" checked={voiceReplies} onChange={e => setVoiceReplies(e.target.checked)} />
          Automatically speak responses when voice output is available
        </label>
        {!speechApiSupported && <p className="text-xs text-ink/40 dark:text-paper/40 mt-1">{t('voiceNotAvailable')}</p>}
      </form>
    </div>
  )
}
