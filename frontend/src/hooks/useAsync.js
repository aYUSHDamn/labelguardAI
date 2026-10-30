import { useCallback, useEffect, useRef, useState } from 'react'

// Tiny data-loading hook: { data, error, loading, run, setData }.
export function useAsync(fn, deps = [], { immediate = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: immediate })
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(async (...args) => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await fn(...args)
      if (alive.current) setState({ data, error: null, loading: false })
      return data
    } catch (error) {
      if (alive.current) setState((s) => ({ ...s, error, loading: false }))
      return null
    }
  }, deps)

  useEffect(() => {
    if (immediate) run()
  }, [run, immediate])

  const setData = useCallback((data) => setState((s) => ({ ...s, data })), [])
  return { ...state, run, setData }
}
