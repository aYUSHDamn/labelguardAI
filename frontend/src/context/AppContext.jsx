import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../api/client.js'

const AppContext = createContext(null)

// Per-viewer conveniences only; the app works fine if storage is blocked.
function load(key, fallback) {
  try {
    const v = localStorage.getItem(key)
    return v === null ? fallback : JSON.parse(v)
  } catch {
    return fallback
  }
}
function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* ignore */
  }
}

export function AppProvider({ children }) {
  const [household, setHousehold] = useState({ members: [] })
  const [profileSaved, setProfileSaved] = useState(false)
  const [member, setMemberState] = useState(() => load('lg.member', 'all'))
  const [language, setLanguageState] = useState(() => load('lg.language', 'en'))
  const [eli12, setEli12State] = useState(() => load('lg.eli12', false))
  const [lastScan, setLastScan] = useState(null)
  const [health, setHealth] = useState(null)

  const refreshProfile = useCallback(async () => {
    try {
      const p = await api.getProfile()
      setHousehold(p.household)
      setProfileSaved(p.saved)
    } catch {
      /* the header shows backend status */
    }
  }, [])

  useEffect(() => {
    refreshProfile()
    api.health().then(setHealth).catch(() => setHealth({ status: 'down' }))
  }, [refreshProfile])

  // If the selected member was removed from the profile, fall back to everyone.
  useEffect(() => {
    if (member !== 'all' && household.members.length && !household.members.some((m) => m.name === member)) {
      setMemberState('all')
    }
  }, [household, member])

  const value = {
    household,
    setHousehold,
    profileSaved,
    setProfileSaved,
    refreshProfile,
    member,
    setMember: (m) => {
      setMemberState(m)
      save('lg.member', m)
    },
    language,
    setLanguage: (l) => {
      setLanguageState(l)
      save('lg.language', l)
    },
    eli12,
    setEli12: (b) => {
      setEli12State(b)
      save('lg.eli12', b)
    },
    lastScan,
    setLastScan,
    health,
  }
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export const useApp = () => useContext(AppContext)
