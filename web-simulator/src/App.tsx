import { useEffect, useState, type FormEvent } from 'react'
import './App.css'

type User = { email: string; display_name: string; role: string }
type Compartment = {
  slot: number
  medication_name: string
  pill_count: number
  weight_grams: number
  lid_open: boolean
  led: string
  reminder: string
}
type Schedule = { medication_name: string; slot: number; time: string }
type DeviceState = {
  device_id: string
  virtual_clock: string
  compartments: Compartment[]
  active_schedules: Schedule[]
}

const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, token?: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail : `YÃªu cáº§u lá»—i (${response.status})`)
  }
  return body as T
}

function clockLabel(value: string) {
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function PillBoxMark() {
  return (
    <svg viewBox="0 0 38 38" aria-hidden="true">
      <rect x="4" y="6" width="30" height="27" rx="8" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M19 7v25M8 15h7M23 15h7M8 24h7M23 24h7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="19" cy="19" r="2" fill="currentColor" />
    </svg>
  )
}

function App() {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [email, setEmail] = useState('operator@example.test')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [connectionError, setConnectionError] = useState('')
  const [device, setDevice] = useState<DeviceState | null>(null)
  const [loading, setLoading] = useState(false)
  const [busySlot, setBusySlot] = useState<number | null>(null)

  useEffect(() => {
    if (!token) return
    let alive = true
    const refresh = async () => {
      try {
        const result = await request<DeviceState>('/api/simulation/state', token)
        if (alive) {
          setDevice(result)
          setConnectionError('')
        }
      } catch (error) {
        if (alive) setConnectionError(error instanceof Error ? error.message : 'KhÃ´ng káº¿t ná»‘i Ä‘Æ°á»£c backend')
      } finally {
        if (alive) setLoading(false)
      }
    }
    setLoading(true)
    void refresh()
    const timer = window.setInterval(() => void refresh(), 2000)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [token])

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginError('')
    try {
      const result = await request<{ access_token: string; user: User }>('/api/auth/login', undefined, {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      if (result.user.role !== 'operator') {
        setLoginError('TÃ i khoáº£n nÃ y khÃ´ng cÃ³ quyá»n Ä‘iá»u khiá»ƒn mÃ´ phá»ng.')
        return
      }
      setUser(result.user)
      setToken(result.access_token)
      setPassword('')
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'ÄÄƒng nháº­p tháº¥t báº¡i')
    }
  }

  async function toggleLid(slot: number, open: boolean) {
    if (!token) return
    setBusySlot(slot)
    setConnectionError('')
    try {
      const updated = await request<DeviceState>('/api/simulation/events', token, {
        method: 'POST',
        body: JSON.stringify({
          event_uuid: crypto.randomUUID(),
          slot,
          event_type: open ? 'LID_OPENED' : 'LID_CLOSED',
        }),
      })
      setDevice(updated)
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : 'KhÃ´ng lÆ°u Ä‘Æ°á»£c thao tÃ¡c')
    } finally {
      setBusySlot(null)
    }
  }

  async function advanceClock(minutes: number) {
    if (!token) return
    setConnectionError('')
    try {
      const updated = await request<DeviceState>('/api/simulation/clock/advance', token, {
        method: 'POST',
        body: JSON.stringify({ minutes }),
      })
      setDevice(updated)
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : 'Loi chinh dong ho')
    }
  }

  if (!token) {
    return (
      <main className="login-screen">
        <div className="login-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="art-box"><PillBoxMark /><span>SIMâ€”001</span></div>
          <div className="art-caption">THREE SLOTS<br />ONE SHARED API</div>
        </div>
        <section className="login-panel">
          <div className="brand-lockup"><span className="brand-icon"><PillBoxMark /></span><span>SMART PILL BOX<small>SIMULATOR / 01</small></span></div>
          <div className="login-copy">
            <p className="eyebrow">BÃ€N ÄIá»€U KHIá»‚N THIáº¾T Bá»Š</p>
            <h1>Má»™t chiáº¿c há»™p.<br /><em>Ba ngÄƒn thuá»‘c.</em></h1>
            <p className="muted">ÄÄƒng nháº­p báº±ng tÃ i khoáº£n Ä‘iá»u khiá»ƒn Ä‘á»ƒ xem tráº¡ng thÃ¡i vÃ  thao tÃ¡c náº¯p há»™p mÃ´ phá»ng.</p>
          </div>
          <form className="login-form" onSubmit={login}>
            <label htmlFor="email">Email Ä‘iá»u khiá»ƒn</label>
            <input id="email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <label htmlFor="password">Máº­t kháº©u</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            {loginError && <p className="form-error" role="alert">{loginError}</p>}
            <button className="primary-button login-button" type="submit">ÄÄƒng nháº­p <span aria-hidden="true">â†—</span></button>
          </form>
          <p className="login-footnote">Dá»¯ liá»‡u demo Â· KhÃ´ng dÃ¹ng há»“ sÆ¡ bá»‡nh nhÃ¢n tháº­t</p>
        </section>
      </main>
    )
  }

  const nextSchedule = device?.active_schedules[0]
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand-lockup" href="#top" aria-label="Smart Pill Box">
          <span className="brand-icon"><PillBoxMark /></span>
          <span>SMART PILL BOX<small>SIMULATOR / 01</small></span>
        </a>
        <div className="topbar-right">
          <div className={`connection ${connectionError ? 'is-offline' : ''}`}><span className="status-dot" />{connectionError ? 'Máº¥t káº¿t ná»‘i' : 'Backend trá»±c tuyáº¿n'}</div>
          <span className="user-chip">{user?.display_name ?? 'Operator'}</span>
          <button className="text-button" type="button" onClick={() => { setToken(null); setUser(null); setDevice(null) }}>ÄÄƒng xuáº¥t</button>
        </div>
      </header>

      <main id="top" className="dashboard">
        <section className="intro-row">
          <div>
            <p className="eyebrow">MÃ” PHá»ŽNG THIáº¾T Bá»Š <span>Â·</span> {device?.device_id ?? 'SIMâ€”001'}</p>
            <h1>ChÃ o buá»•i sÃ¡ng<span className="heading-period">.</span></h1>
            <p className="muted">Theo dÃµi tráº¡ng thÃ¡i há»™p thuá»‘c vÃ  lá»‹ch Ä‘Ã£ lÆ°u trÃªn backend.</p>
          </div>
          <div className="clock-card">
            <span className="clock-label">GIá»œ MÃ” PHá»ŽNG Â· GMT+7</span>
            <strong>{device ? clockLabel(device.virtual_clock) : 'â€” â€” : â€” â€”'}</strong>
            <span className="clock-date">{device ? new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'long' }).format(new Date(device.virtual_clock)) : 'Äang táº£i tráº¡ng thÃ¡i'}</span>
          </div>
        </section>

        {connectionError && <div className="alert-banner" role="status"><span>!</span><div><strong>KhÃ´ng thá»ƒ Ä‘á»“ng bá»™ vá»›i backend</strong><small>{connectionError} Â· Äang thá»­ káº¿t ná»‘i láº¡i má»—i 2 giÃ¢y.</small></div></div>}
        {loading && !device && <div className="loading-card"><span className="loader" />Äang táº£i tráº¡ng thÃ¡i tá»« SQLiteâ€¦</div>}

        <section className="overview-row">
          <div className="section-heading"><div><p className="eyebrow">TRáº NG THÃI THIáº¾T Bá»Š</p><h2>Ba ngÄƒn, má»™t lá»‹ch trÃ¬nh</h2></div><span className="live-label"><span className="status-dot" /> Cáº¬P NHáº¬T 2 GIÃ‚Y</span></div>
          <div className="compartment-grid">
            {(device?.compartments ?? []).map((item, index) => (
              <article className={`compartment-card ${item.lid_open ? 'lid-open' : ''}`} key={item.slot} style={{ animationDelay: `${index * 90}ms` }}>
                <div className="card-topline"><span className="slot-label">NGÄ‚N {String(item.slot).padStart(2, '0')}</span><span className={`lid-badge ${item.lid_open ? 'opened' : ''}`}><i />{item.lid_open ? 'Äang má»Ÿ' : 'Äang Ä‘Ã³ng'}</span></div>
                <div className="medication-title"><h3>{item.medication_name}</h3><span className="medication-index">0{item.slot}</span></div>
                <div className="dose-visual" aria-label={`${item.pill_count} viÃªn máº«u`}><div className="pill-stack">{Array.from({ length: Math.min(item.pill_count, 8) }, (_, pill) => <span key={pill} />)}</div><div><strong>{item.pill_count}</strong><small>viÃªn máº«u</small></div></div>
                <div className="card-metrics"><div><span>KHá»I LÆ¯á»¢NG</span><strong>{item.weight_grams.toFixed(1)} <small>g</small></strong></div><div><span>ÄÃˆN BÃO</span><strong><i className={`led ${item.led === 'Báº­t' ? 'led-on' : ''}`} />{item.led}</strong></div></div>
                <div className="reminder-line"><span>NHáº®C Uá»NG</span><strong>{item.reminder}</strong></div>
                <button className={`lid-button ${item.lid_open ? 'secondary-button' : 'primary-button'}`} type="button" disabled={busySlot === item.slot} onClick={() => void toggleLid(item.slot, !item.lid_open)}>
                  {busySlot === item.slot ? 'Äang gá»­iâ€¦' : item.lid_open ? 'ÄÃ³ng náº¯p' : 'Má»Ÿ náº¯p'} <span aria-hidden="true">{item.lid_open ? 'â†™' : 'â†—'}</span>
                </button>
              </article>
            ))}
            {!device && !loading && <div className="empty-state">ChÆ°a cÃ³ tráº¡ng thÃ¡i há»™p. Kiá»ƒm tra backend vÃ  Ä‘Äƒng nháº­p operator.</div>}
          </div>
        </section>

        <section className="lower-grid">
          <div className="schedule-panel">
            <div className="section-heading compact"><div><p className="eyebrow">Äá»’NG Bá»˜ Tá»ª DATABASE</p><h2>Lá»‹ch Ä‘ang báº­t</h2></div><span className="count-pill">{device?.active_schedules.length ?? 0}</span></div>
            {nextSchedule && <div className="next-dose"><div className="next-icon">â†—</div><div><span>Lá»ŠCH Sáº®P Tá»šI</span><strong>{nextSchedule.medication_name}</strong><small>NgÄƒn {nextSchedule.slot} Â· {nextSchedule.time}</small></div><time>{nextSchedule.time}</time></div>}
            <div className="schedule-list">
              {(device?.active_schedules ?? []).map((schedule, index) => <div className="schedule-row" key={`${schedule.slot}-${schedule.time}-${schedule.medication_name}-${index}`}><time>{schedule.time}</time><span className="schedule-slot">N{schedule.slot}</span><strong>{schedule.medication_name}</strong><span className="active-tag">ÄANG Báº¬T</span></div>)}
              {device && device.active_schedules.length === 0 && <p className="empty-schedules">ChÆ°a cÃ³ lá»‹ch Ä‘ang báº­t. Lá»‹ch má»›i tá»« á»©ng dá»¥ng Flutter sáº½ xuáº¥t hiá»‡n táº¡i Ä‘Ã¢y.</p>}
            </div>
            <p className="sync-note"><span className="sync-arrows">â†»</span> Táº£i láº¡i tá»± Ä‘á»™ng má»—i 2 giÃ¢y Â· cÃ¹ng dá»¯ liá»‡u vá»›i á»©ng dá»¥ng Flutter</p>
          </div>
          <aside className="disabled-panel">
            <div className="section-heading compact"><div><p className="eyebrow">GIAI ÄOáº N SAU</p><h2>Thao tÃ¡c khÃ¡c</h2></div><span className="lock-mark">â…¡</span></div>
            <div className="disabled-actions">
              <button type="button" onClick={() => advanceClock(1)}><span>+1 phút</span></button>
              <button type="button" onClick={() => advanceClock(2)}><span>+2 phút</span></button>
              <button type="button" onClick={() => advanceClock(5)}><span>+5 phút</span></button>
                <button type="button" onClick={() => advanceClock(60)}><span>+1 tiếng</span></button>
              {['L?y m?t viên', 'Xác nh?n dã u?ng', 'Ð?t l?i h?p'].map((action) => <button type="button" disabled key={action}><span>{action}</span><small>CHUA TRI?N KHAI</small></button>)}
            </div>
            <p className="safety-note">Má»Ÿ náº¯p khÃ´ng xÃ¡c nháº­n ngÆ°á»i dÃ¹ng Ä‘Ã£ uá»‘ng thuá»‘c.</p>
          </aside>
        </section>
        <footer className="page-footer"><span>SMART PILL BOX <i>Â·</i> Báº¢N MÃ” PHá»ŽNG</span><span>Dá»¯ liá»‡u giáº£ Â· KhÃ´ng dÃ¹ng cho chÄƒm sÃ³c y táº¿ thá»±c táº¿</span></footer>
      </main>
    </div>
  )
}

export default App




