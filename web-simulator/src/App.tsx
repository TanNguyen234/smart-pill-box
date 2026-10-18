import { useEffect, useRef, useState, type FormEvent } from 'react'
import './App.css'

type User = { email: string; display_name: string; role: string }
type Compartment = {
  slot: number
  compartment_id?: number
  medication_name: string
  pill_count: number
  weight_grams: number
  lid_open: boolean
  led: string
  buzzer_on: boolean
  reminder: string
  current_occurrence_id: number | null
  can_confirm: boolean
}
type Schedule = { id: number; medication_name: string; slot: number; time: string }
type SimulationEvent = {
  id: number
  event_uuid: string
  event_type: string
  payload: Record<string, string | number | boolean | null>
  created_at: string
}
type Occurrence = {
  id: number
  schedule_id: number
  medication_name: string
  slot: number
  scheduled_at: string
  confirmed_at: string | null
  status: string
}
type DeviceState = {
  device_id: string
  virtual_clock: string
  next_milestone_minutes?: number
  compartments: Compartment[]
  active_schedules: Schedule[]
  active_occurrences: Occurrence[]
  recent_occurrences: Occurrence[]
  recent_events: SimulationEvent[]
}
type EventType =
  | 'LID_OPENED'
  | 'LID_CLOSED'
  | 'WEIGHT_READING'
  | 'CONFIRM_PRESSED'
  | 'PILL_DISPENSED'
  | 'DOSE_CONFIRMED'

class ApiRequestError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
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
    throw new ApiRequestError(typeof body.detail === 'string' ? body.detail : `Yêu cầu lỗi (${response.status})`, response.status)
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

function dateLabel(value: string) {
  return new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'long' }).format(new Date(value))
}

function nextScheduleFor(device: DeviceState): Schedule | undefined {
  if (device.active_schedules.length === 0) return undefined
  const now = new Date(device.virtual_clock).getTime()
  const dateParts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date(device.virtual_clock))
  const date = `${dateParts.find((part) => part.type === 'year')?.value}-${dateParts.find((part) => part.type === 'month')?.value}-${dateParts.find((part) => part.type === 'day')?.value}`
  return [...device.active_schedules]
    .map((schedule) => {
      let timestamp = Date.parse(`${date}T${schedule.time}:00+07:00`)
      if (timestamp <= now) timestamp += 24 * 60 * 60 * 1000
      return { schedule, timestamp }
    })
    .sort((left, right) => left.timestamp - right.timestamp)[0]?.schedule
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

function eventLabel(event: SimulationEvent) {
  if (event.event_type === 'REMINDER_SENT') return Number(event.payload.reminder_level) === 2 ? 'Nhắc lại lần hai' : 'Bắt đầu nhắc thuốc'
  if (event.event_type === 'ALERT_CREATED') return 'Đã tạo cảnh báo quá hạn'
  if (event.event_type === 'CLOCK_ADVANCED') return `Tiến đồng hồ +${event.payload.minutes} phút`
  if (event.event_type === 'SIMULATION_RESET') return 'Đặt lại hộp mô phỏng'
  if (event.event_type === 'WEIGHT_READING') {
    const weight = event.payload.weight_g
    return typeof weight === 'number' ? `Cảm biến cân: ${weight.toFixed(1)} g` : 'Cảm biến tải trọng đọc khối lượng'
  }
  if (event.event_type === 'CONFIRM_PRESSED') return 'Nút hộp: Bấm xác nhận uống thuốc'
  return {
    LID_OPENED: 'Mở nắp ngăn',
    LID_CLOSED: 'Đóng nắp ngăn',
    PILL_DISPENSED: 'Lấy một viên mô phỏng',
    DOSE_CONFIRMED: 'Người dùng xác nhận đã uống',
  }[event.event_type] ?? event.event_type
}

function App() {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [email, setEmail] = useState('operator@example.test')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [connectionError, setConnectionError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [device, setDevice] = useState<DeviceState | null>(null)
  const [busySlot, setBusySlot] = useState<number | null>(null)
  const [busyControl, setBusyControl] = useState(false)
  const [audioEnabled, setAudioEnabled] = useState(false)
  const audioContext = useRef<AudioContext | null>(null)
  const lastReminderEventId = useRef<number | null>(null)
  const recentEvents = device?.recent_events

  function playReminderTone() {
    try {
      const context = audioContext.current ?? new window.AudioContext()
      audioContext.current = context
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.value = 880
      gain.gain.setValueAtTime(0.0001, context.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.13, context.currentTime + 0.025)
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.35)
      oscillator.connect(gain)
      gain.connect(context.destination)
      oscillator.start()
      oscillator.stop(context.currentTime + 0.36)
    } catch {
      // Audio is an optional browser feature; the visual alarm remains authoritative.
    }
  }

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
        if (alive) {
          setConnectionError(error instanceof Error ? error.message : 'Không kết nối được backend')
        }
      }
    }
    void refresh()
    const timer = window.setInterval(() => void refresh(), 2000)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [token])

  useEffect(() => {
    if (!recentEvents) return
    const reminderEvents = recentEvents.filter((event) => event.event_type === 'REMINDER_SENT')
    const newestId = reminderEvents.reduce((latest, event) => Math.max(latest, event.id), 0)
    const previousId = lastReminderEventId.current
    if (previousId === null || newestId < previousId) {
      lastReminderEventId.current = newestId
      return
    }
    if (newestId > previousId) {
      lastReminderEventId.current = newestId
      if (audioEnabled) playReminderTone()
    }
  }, [recentEvents, audioEnabled])

  async function toggleAudio() {
    try {
      if (!audioContext.current) audioContext.current = new window.AudioContext()
      await audioContext.current.resume()
      setAudioEnabled((enabled) => !enabled)
      setActionMessage('')
    } catch {
      setActionMessage('Trình duyệt không cho phép bật âm thanh. Đèn và chữ nhắc vẫn hoạt động.')
    }
  }

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
      lastReminderEventId.current = null
      setPassword('')
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Đăng nhập thất bại')
    }
  }

  function logout() {
    setToken(null)
    setUser(null)
    setDevice(null)
    setConnectionError('')
    setActionMessage('')
    setAudioEnabled(false)
    lastReminderEventId.current = null
  }

  async function sendEvent(slot: number, eventType: EventType, extraPayload: Record<string, unknown> = {}) {
    if (!token) return
    setBusySlot(slot)
    setActionMessage('')
    try {
      const updated = await request<DeviceState>('/api/simulation/events', token, {
        method: 'POST',
        body: JSON.stringify({
          event_uuid: crypto.randomUUID(),
          slot,
          compartment_id: slot,
          event_type: eventType,
          payload: extraPayload,
          ...extraPayload,
        }),
      })
      setDevice(updated)
      setConnectionError('')
    } catch (error) {
      if (error instanceof ApiRequestError) setActionMessage(error.message)
      else setConnectionError(error instanceof Error ? error.message : 'Không lưu được thao tác')
    } finally {
      setBusySlot(null)
    }
  }

  async function takeOnePill(item: Compartment) {
    const nextWeight = Math.max(0, Number((item.weight_grams - 0.5).toFixed(1)))
    await sendEvent(item.slot, 'WEIGHT_READING', { weight_g: nextWeight })
  }

  async function injectNoise(item: Compartment) {
    const nextWeight = Math.max(0, Number((item.weight_grams - 0.1).toFixed(1)))
    await sendEvent(item.slot, 'WEIGHT_READING', { weight_g: nextWeight })
  }

  async function confirmDose(item: Compartment) {
    await sendEvent(
      item.slot,
      'CONFIRM_PRESSED',
      item.current_occurrence_id ? { occurrence_id: item.current_occurrence_id } : {}
    )
  }

  async function advanceClock(minutes: number) {
    if (!token) return
    setBusyControl(true)
    setActionMessage('')
    try {
      // API accepts at most 60 minutes per request; span later milestones safely.
      let remaining = minutes
      while (remaining > 0) {
        const chunk = Math.min(60, remaining)
        const updated = await request<DeviceState>('/api/simulation/advance', token, {
          method: 'POST',
          body: JSON.stringify({ event_uuid: crypto.randomUUID(), minutes: chunk }),
        })
        setDevice(updated)
        remaining -= chunk
      }
      setConnectionError('')
    } catch (error) {
      if (error instanceof ApiRequestError) setActionMessage(error.message)
      else setConnectionError(error instanceof Error ? error.message : 'Không thể tiến đồng hồ mô phỏng')
    } finally {
      setBusyControl(false)
    }
  }

  async function resetSimulation() {
    if (!token || !window.confirm('Đặt lại hộp sẽ xóa lịch sử thao tác, lần nhắc và cảnh báo của phiên demo hiện tại. Các tài khoản và lịch thuốc vẫn được giữ; nhật ký sẽ ghi thao tác đặt lại. Tiếp tục?')) return
    setBusyControl(true)
    setActionMessage('')
    try {
      const updated = await request<DeviceState>('/api/simulation/reset', token, {
        method: 'POST',
        body: JSON.stringify({ confirmation: 'RESET_DEMO', event_uuid: crypto.randomUUID() }),
      })
      setDevice(updated)
      lastReminderEventId.current = 0
      setConnectionError('')
    } catch (error) {
      if (error instanceof ApiRequestError) setActionMessage(error.message)
      else setConnectionError(error instanceof Error ? error.message : 'Không thể đặt lại mô phỏng')
    } finally {
      setBusyControl(false)
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
            <p className="muted">Đăng nhập operator để thao tác hộp mô phỏng, chạy đồng hồ và xem dữ liệu đã lưu trên máy chủ.</p>
          </div>
          <form className="login-form" onSubmit={login}>
            <label htmlFor="email">Email điều khiển</label>
            <input id="email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <label htmlFor="password">Mật khẩu</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            {loginError && <p className="form-error" role="alert">{loginError}</p>}
            <button className="primary-button login-button" type="submit">Đăng nhập <span aria-hidden="true">↗</span></button>
            <button
              type="button"
              className="demo-account-hint"
              onClick={() => { setEmail('operator@example.test'); setPassword('Password123!'); }}
              title="Bấm để điền tài khoản Operator mặc định"
            >
              🔑 Điền nhanh: operator@example.test • Password123!
            </button>
          </form>
          <p className="login-footnote">Dữ liệu demo · Không dùng hồ sơ bệnh nhân thật</p>
        </section>
      </main>
    )
  }

  const nextSchedule = device ? nextScheduleFor(device) : undefined
  const events = device?.recent_events ?? []
  const loading = Boolean(token && !device && !connectionError)
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand-lockup" href="#top" aria-label="Smart Pill Box">
          <span className="brand-icon"><PillBoxMark /></span>
          <span>SMART PILL BOX<small>SIMULATOR / 01</small></span>
        </a>
        <div className="topbar-right">
          <div className={`connection ${connectionError ? 'is-offline' : ''}`}><span className="status-dot" />{connectionError ? 'Mất kết nối' : 'Backend trực tuyến'}</div>
          <button className={`audio-toggle ${audioEnabled ? 'audio-on' : ''}`} type="button" onClick={() => void toggleAudio()} aria-pressed={audioEnabled}>{audioEnabled ? '♫ Còi đang bật' : '♫ Bật âm thanh'}</button>
          <span className="user-chip">{user?.display_name ?? 'Operator'}</span>
          <button className="text-button" type="button" onClick={logout}>Đăng xuất</button>
        </div>
      </header>

      <main id="top" className="dashboard">
        <section className="intro-row">
          <div>
            <p className="eyebrow">MÔ PHỎNG THIẾT BỊ <span>·</span> {device?.device_id ?? 'SIM—001'}</p>
            <h1>Bàn điều khiển<span className="heading-period">.</span></h1>
            <p className="muted">Một hộp ảo, ba ngăn thật dữ liệu. Mỗi thao tác được máy chủ xác nhận trước khi giao diện cập nhật.</p>
          </div>
          <div className="clock-card">
            <span className="clock-label">GIỜ MÔ PHỎNG · GMT+7</span>
            <strong>{device ? clockLabel(device.virtual_clock) : '— — : — —'}</strong>
            <span className="clock-date">{device ? dateLabel(device.virtual_clock) : 'Đang tải trạng thái'}</span>
          </div>
        </section>

        {connectionError && <div className="alert-banner" role="status"><span>!</span><div><strong>Không thể đồng bộ với backend</strong><small>{connectionError} · Đang thử kết nối lại mỗi 2 giây.</small></div></div>}
        {actionMessage && <div className="action-banner" role="alert"><span>!</span><div><strong>Thao tác chưa hoàn tất</strong><small>{actionMessage}</small></div><button type="button" onClick={() => setActionMessage('')} aria-label="Đóng thông báo">×</button></div>}
        {loading && !device && <div className="loading-card"><span className="loader" />Đang tải trạng thái từ SQLite…</div>}

        <section className="simulation-console" aria-label="Điều khiển đồng hồ mô phỏng">
          <div className="console-copy"><span className="console-icon">◷</span><div><p className="eyebrow">ĐIỀU KHIỂN THỜI GIAN</p><strong>Tiến đồng hồ ảo</strong><small>Chạy qua mốc nhắc mà không đổi giờ máy tính.</small></div></div>
          <div className="clock-buttons">
            {[1, 2, 5].map((minutes) => <button type="button" key={minutes} disabled={!device || busyControl} onClick={() => void advanceClock(minutes)}>{busyControl ? 'Đang chạy…' : `+${minutes} phút`}</button>)}
            <button className="milestone-button" type="button" disabled={!device || busyControl} onClick={() => void advanceClock(device?.next_milestone_minutes ?? 1)} title="Nhảy đến mốc nhắc thuốc hoặc quá hạn gần nhất">Mốc tiếp theo (+{device?.next_milestone_minutes ?? 1}p)</button>
            <button className="reset-button" type="button" disabled={!device || busyControl} onClick={() => void resetSimulation()}>Đặt lại hộp</button>
          </div>
        </section>

        <section className="overview-row">
          <div className="section-heading"><div><p className="eyebrow">TRẠNG THÁI THIẾT BỊ</p><h2>Ba ngăn, một lịch trình</h2></div><span className={`live-label ${connectionError ? 'offline-label' : ''}`}><span className="status-dot" />{connectionError ? 'CHỜ KẾT NỐI' : 'CẬP NHẬT 2 GIÂY'}</span></div>
          <div className="compartment-grid">
            {(device?.compartments ?? []).map((item, index) => (
              <article className={`compartment-card slot-${item.slot} ${item.lid_open ? 'lid-open' : ''} ${item.buzzer_on ? 'reminder-active' : ''}`} key={item.slot} style={{ animationDelay: `${index * 90}ms` }}>
                <div className="card-topline">
                  <div className="slot-identity">
                    <span className="slot-pill-badge">0{item.slot}</span>
                    <span className="slot-label">NGĂN SỐ {item.slot}</span>
                  </div>
                  <span className={`lid-badge ${item.lid_open ? 'opened' : 'closed'}`}>
                    <span className="lid-dot" />
                    {item.lid_open ? 'Nắp đang mở' : 'Nắp đã đóng'}
                  </span>
                </div>

                <div className={`physical-chamber ${item.lid_open ? 'is-open' : 'is-closed'}`} aria-label={item.lid_open ? 'Nắp ngăn đang mở' : 'Nắp ngăn đang đóng'}>
                  <div className="chamber-hinge" />
                  <div className="chamber-lid">
                    <div className="lid-frost-glass">
                      <span className="lid-grip-handle" />
                    </div>
                  </div>
                  <div className="chamber-interior">
                    <div className="led-lamp-container">
                      <div className={`led-lens ${item.led === 'Bật' ? 'led-active' : ''}`} title={`Đèn LED: ${item.led}`}>
                        <div className="led-glow-ring" />
                      </div>
                      <span className="led-text">{item.led === 'Bật' ? 'LED BẬT' : 'LED TẮT'}</span>
                    </div>

                    <div className="pill-well" aria-label={`${item.pill_count} viên thuốc trong ngăn`}>
                      <div className="pills-scatter">
                        {Array.from({ length: Math.min(item.pill_count, 8) }, (_, pill) => (
                          <div className={`pill-unit pill-type-${item.slot}`} key={pill}>
                            <span className="pill-half-left" />
                            <span className="pill-half-right" />
                          </div>
                        ))}
                      </div>
                      <div className="pill-counter-tag">
                        <strong>{item.pill_count}</strong>
                        <span>viên mẫu</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="medication-title">
                  <h3>{item.medication_name}</h3>
                  <span className="medication-type-tag">Cữ uống theo lịch</span>
                </div>

                <div className="card-metrics">
                  <div className="metric-box scale-metric">
                    <span className="metric-label">CẢM BIẾN TẢI TRỌNG</span>
                    <div className="oled-scale-readout">
                      <span className="oled-tag">LOADCELL</span>
                      <strong className="oled-value">{item.weight_grams.toFixed(1)} <small>g</small></strong>
                    </div>
                  </div>
                  <div className="metric-box reminder-metric">
                    <span className="metric-label">TRẠNG THÁI NHẮC</span>
                    <strong className={`reminder-status-chip ${item.buzzer_on ? 'reminder-text-active' : ''}`}>
                      {item.buzzer_on && <span className="urgent-pulse-dot" />}
                      {item.reminder}
                    </strong>
                  </div>
                </div>

                <div className={`buzzer-line ${item.buzzer_on ? 'buzzer-active' : ''}`}>
                  <span className={`buzzer-indicator ${item.buzzer_on ? 'buzzer-on' : ''}`}>
                    {item.buzzer_on ? '🔊' : '🔈'}
                  </span>
                  <div className="buzzer-copy">
                    <span>Còi nhắc hộp thuốc</span>
                    <strong>{item.buzzer_on ? 'Đang phát âm thanh nhắc nhở' : 'Còi đang im lặng'}</strong>
                  </div>
                  {item.buzzer_on && (
                    <div className="sound-wave-bars" aria-hidden="true">
                      <span /><span /><span />
                    </div>
                  )}
                </div>

                <div className="compartment-actions">
                  <button className={`lid-button ${item.lid_open ? 'secondary-button' : 'primary-button'}`} type="button" disabled={busySlot === item.slot || busyControl} onClick={() => void sendEvent(item.slot, item.lid_open ? 'LID_CLOSED' : 'LID_OPENED')}>
                    <span className="btn-icon">{item.lid_open ? '📥' : '📤'}</span>
                    <span>{busySlot === item.slot ? 'Đang gửi…' : item.lid_open ? 'Đóng nắp ngăn' : 'Mở nắp ngăn'}</span>
                  </button>
                  <button className="dispense-button" type="button" disabled={!item.lid_open || item.pill_count <= 0 || busySlot === item.slot || busyControl} onClick={() => void takeOnePill(item)} title={!item.lid_open ? 'Mở nắp ngăn trước' : item.pill_count <= 0 ? 'Ngăn đã hết thuốc mẫu' : undefined}>
                    <span className="btn-icon">💊</span>
                    <span>Lấy một viên</span>
                    <span className="btn-weight-change">−0,5 g</span>
                  </button>
                  <button className="noise-button" type="button" disabled={!item.lid_open || busySlot === item.slot || busyControl} onClick={() => void injectNoise(item)} title="Thử nhiễu tải trọng 0.1g (kiểm thử T033, không làm giảm viên)">
                    <span className="btn-icon">⚡</span>
                    <span>Thử nhiễu cân</span>
                    <span className="btn-weight-change">−0,1 g</span>
                  </button>
                  {item.can_confirm && (
                    <button className="confirm-button" type="button" disabled={busySlot === item.slot || busyControl} onClick={() => void confirmDose(item)}>
                      <span className="confirm-glow" />
                      <span>✓ Nút xác nhận trên hộp</span>
                    </button>
                  )}
                </div>
                <p className="safety-note">Cảm biến chỉ ghi nhận khi thao tác thật • Không chứng minh đã uống</p>
              </article>
            ))}

            {!device && !loading && <div className="empty-state">Chưa có trạng thái hộp. Kiểm tra backend và đăng nhập operator.</div>}
          </div>
        </section>

        <section className="lower-grid">
          <div className="schedule-panel">
            <div className="section-heading compact"><div><p className="eyebrow">ĐỒNG BỘ TỪ DATABASE</p><h2>Lịch đang bật</h2></div><span className="count-pill">{device?.active_schedules.length ?? 0}</span></div>
            {nextSchedule && <div className="next-dose"><div className="next-icon">↗</div><div><span>LỊCH TIẾP THEO</span><strong>{nextSchedule.medication_name}</strong><small>Ngăn {nextSchedule.slot} · {nextSchedule.time}</small></div><time>{nextSchedule.time}</time></div>}
            <div className="schedule-list">
              {(device?.active_schedules ?? []).map((schedule) => <div className="schedule-row" key={schedule.id}><time>{schedule.time}</time><span className="schedule-slot">N{schedule.slot}</span><strong>{schedule.medication_name}</strong><span className="active-tag">ĐANG BẬT</span></div>)}
              {device && device.active_schedules.length === 0 && <p className="empty-schedules">Chưa có lịch đang bật. Lịch mới từ ứng dụng Flutter sẽ xuất hiện tại đây.</p>}
            </div>
            <p className="sync-note"><span className="sync-arrows">↻</span> Đồng bộ mỗi 2 giây · lịch dùng chung với ứng dụng Flutter</p>
          </div>

          <aside className="activity-panel">
            <div className="section-heading compact"><div><p className="eyebrow">NHẬT KÝ THIẾT BỊ</p><h2>Thao tác gần đây</h2></div><span className="count-pill">{events.length}</span></div>
            <div className="activity-list">
              {events.map((event) => <div className="activity-row" key={event.id}><span className={`activity-symbol ${event.event_type === 'ALERT_CREATED' ? 'activity-alert' : event.event_type === 'DOSE_CONFIRMED' ? 'activity-confirmed' : ''}`}>{event.event_type === 'LID_OPENED' ? '↗' : event.event_type === 'LID_CLOSED' ? '↙' : event.event_type === 'PILL_DISPENSED' ? '−' : event.event_type === 'DOSE_CONFIRMED' ? '✓' : event.event_type === 'ALERT_CREATED' ? '!' : event.event_type === 'CLOCK_ADVANCED' ? '↻' : event.event_type === 'SIMULATION_RESET' ? '⟲' : '♫'}</span><div className="activity-copy"><strong>{eventLabel(event)}</strong><small>{event.payload.slot ? `Ngăn ${event.payload.slot}` : 'Hộp mô phỏng'} · {event.payload.virtual_time ? clockLabel(String(event.payload.virtual_time)) : new Date(event.created_at).toLocaleTimeString('vi-VN')}</small></div></div>)}
              {device && events.length === 0 && <p className="empty-activity">Chưa có thao tác trong phiên demo. Mở nắp hoặc tiến đồng hồ để bắt đầu.</p>}
              {!device && <p className="empty-activity">Nhật ký sẽ xuất hiện sau khi tải trạng thái thiết bị.</p>}
            </div>
            <p className="sync-note"><span className="sync-arrows">↻</span> Lịch sử sự kiện được lưu trên backend</p>
          </aside>
        </section>

        <footer className="page-footer"><span>SMART PILL BOX <i>·</i> BẢN MÔ PHỎNG</span><span>Dữ liệu giả · Không dùng cho chăm sóc y tế thực tế</span></footer>
      </main>
    </div>
  )
}

export default App
