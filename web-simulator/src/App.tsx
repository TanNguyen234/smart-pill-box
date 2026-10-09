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
    throw new Error(typeof body.detail === 'string' ? body.detail : `Yêu cầu lỗi (${response.status})`)
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
        if (alive) setConnectionError(error instanceof Error ? error.message : 'Không kết nối được backend')
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
        setLoginError('Tài khoản này không có quyền điều khiển mô phỏng.')
        return
      }
      setUser(result.user)
      setToken(result.access_token)
      setPassword('')
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Đăng nhập thất bại')
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
      setConnectionError(error instanceof Error ? error.message : 'Không lưu được thao tác')
    } finally {
      setBusySlot(null)
    }
  }

  if (!token) {
    return (
      <main className="login-screen">
        <div className="login-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="art-box"><PillBoxMark /><span>SIM—001</span></div>
          <div className="art-caption">THREE SLOTS<br />ONE SHARED API</div>
        </div>
        <section className="login-panel">
          <div className="brand-lockup"><span className="brand-icon"><PillBoxMark /></span><span>SMART PILL BOX<small>SIMULATOR / 01</small></span></div>
          <div className="login-copy">
            <p className="eyebrow">BÀN ĐIỀU KHIỂN THIẾT BỊ</p>
            <h1>Một chiếc hộp.<br /><em>Ba ngăn thuốc.</em></h1>
            <p className="muted">Đăng nhập bằng tài khoản điều khiển để xem trạng thái và thao tác nắp hộp mô phỏng.</p>
          </div>
          <form className="login-form" onSubmit={login}>
            <label htmlFor="email">Email điều khiển</label>
            <input id="email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <label htmlFor="password">Mật khẩu</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            {loginError && <p className="form-error" role="alert">{loginError}</p>}
            <button className="primary-button login-button" type="submit">Đăng nhập <span aria-hidden="true">↗</span></button>
          </form>
          <p className="login-footnote">Dữ liệu demo · Không dùng hồ sơ bệnh nhân thật</p>
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
          <div className={`connection ${connectionError ? 'is-offline' : ''}`}><span className="status-dot" />{connectionError ? 'Mất kết nối' : 'Backend trực tuyến'}</div>
          <span className="user-chip">{user?.display_name ?? 'Operator'}</span>
          <button className="text-button" type="button" onClick={() => { setToken(null); setUser(null); setDevice(null) }}>Đăng xuất</button>
        </div>
      </header>

      <main id="top" className="dashboard">
        <section className="intro-row">
          <div>
            <p className="eyebrow">MÔ PHỎNG THIẾT BỊ <span>·</span> {device?.device_id ?? 'SIM—001'}</p>
            <h1>Chào buổi sáng<span className="heading-period">.</span></h1>
            <p className="muted">Theo dõi trạng thái hộp thuốc và lịch đã lưu trên backend.</p>
          </div>
          <div className="clock-card">
            <span className="clock-label">GIỜ MÔ PHỎNG · GMT+7</span>
            <strong>{device ? clockLabel(device.virtual_clock) : '— — : — —'}</strong>
            <span className="clock-date">{device ? new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'long' }).format(new Date(device.virtual_clock)) : 'Đang tải trạng thái'}</span>
          </div>
        </section>

        {connectionError && <div className="alert-banner" role="status"><span>!</span><div><strong>Không thể đồng bộ với backend</strong><small>{connectionError} · Đang thử kết nối lại mỗi 2 giây.</small></div></div>}
        {loading && !device && <div className="loading-card"><span className="loader" />Đang tải trạng thái từ SQLite…</div>}

        <section className="overview-row">
          <div className="section-heading"><div><p className="eyebrow">TRẠNG THÁI THIẾT BỊ</p><h2>Ba ngăn, một lịch trình</h2></div><span className="live-label"><span className="status-dot" /> CẬP NHẬT 2 GIÂY</span></div>
          <div className="compartment-grid">
            {(device?.compartments ?? []).map((item, index) => (
              <article className={`compartment-card ${item.lid_open ? 'lid-open' : ''}`} key={item.slot} style={{ animationDelay: `${index * 90}ms` }}>
                <div className="card-topline"><span className="slot-label">NGĂN {String(item.slot).padStart(2, '0')}</span><span className={`lid-badge ${item.lid_open ? 'opened' : ''}`}><i />{item.lid_open ? 'Đang mở' : 'Đang đóng'}</span></div>
                <div className="medication-title"><h3>{item.medication_name}</h3><span className="medication-index">0{item.slot}</span></div>
                <div className="dose-visual" aria-label={`${item.pill_count} viên mẫu`}><div className="pill-stack">{Array.from({ length: Math.min(item.pill_count, 8) }, (_, pill) => <span key={pill} />)}</div><div><strong>{item.pill_count}</strong><small>viên mẫu</small></div></div>
                <div className="card-metrics"><div><span>KHỐI LƯỢNG</span><strong>{item.weight_grams.toFixed(1)} <small>g</small></strong></div><div><span>ĐÈN BÁO</span><strong><i className={`led ${item.led === 'Bật' ? 'led-on' : ''}`} />{item.led}</strong></div></div>
                <div className="reminder-line"><span>NHẮC UỐNG</span><strong>{item.reminder}</strong></div>
                <button className={`lid-button ${item.lid_open ? 'secondary-button' : 'primary-button'}`} type="button" disabled={busySlot === item.slot} onClick={() => void toggleLid(item.slot, !item.lid_open)}>
                  {busySlot === item.slot ? 'Đang gửi…' : item.lid_open ? 'Đóng nắp' : 'Mở nắp'} <span aria-hidden="true">{item.lid_open ? '↙' : '↗'}</span>
                </button>
              </article>
            ))}
            {!device && !loading && <div className="empty-state">Chưa có trạng thái hộp. Kiểm tra backend và đăng nhập operator.</div>}
          </div>
        </section>

        <section className="lower-grid">
          <div className="schedule-panel">
            <div className="section-heading compact"><div><p className="eyebrow">ĐỒNG BỘ TỪ DATABASE</p><h2>Lịch đang bật</h2></div><span className="count-pill">{device?.active_schedules.length ?? 0}</span></div>
            {nextSchedule && <div className="next-dose"><div className="next-icon">↗</div><div><span>LỊCH SẮP TỚI</span><strong>{nextSchedule.medication_name}</strong><small>Ngăn {nextSchedule.slot} · {nextSchedule.time}</small></div><time>{nextSchedule.time}</time></div>}
            <div className="schedule-list">
              {(device?.active_schedules ?? []).map((schedule, index) => <div className="schedule-row" key={`${schedule.slot}-${schedule.time}-${schedule.medication_name}-${index}`}><time>{schedule.time}</time><span className="schedule-slot">N{schedule.slot}</span><strong>{schedule.medication_name}</strong><span className="active-tag">ĐANG BẬT</span></div>)}
              {device && device.active_schedules.length === 0 && <p className="empty-schedules">Chưa có lịch đang bật. Lịch mới từ ứng dụng Flutter sẽ xuất hiện tại đây.</p>}
            </div>
            <p className="sync-note"><span className="sync-arrows">↻</span> Tải lại tự động mỗi 2 giây · cùng dữ liệu với ứng dụng Flutter</p>
          </div>
          <aside className="disabled-panel">
            <div className="section-heading compact"><div><p className="eyebrow">GIAI ĐOẠN SAU</p><h2>Thao tác khác</h2></div><span className="lock-mark">Ⅱ</span></div>
            <div className="disabled-actions">
              {['Lấy một viên', 'Xác nhận đã uống', '+1 phút', '+2 phút', '+5 phút', 'Đặt lại hộp'].map((action) => <button type="button" disabled key={action}><span>{action}</span><small>CHƯA TRIỂN KHAI</small></button>)}
            </div>
            <p className="safety-note">Mở nắp không xác nhận người dùng đã uống thuốc.</p>
          </aside>
        </section>
        <footer className="page-footer"><span>SMART PILL BOX <i>·</i> BẢN MÔ PHỎNG</span><span>Dữ liệu giả · Không dùng cho chăm sóc y tế thực tế</span></footer>
      </main>
    </div>
  )
}

export default App
