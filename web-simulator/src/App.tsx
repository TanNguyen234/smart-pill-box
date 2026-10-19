import { useEffect, useRef, useState, type FormEvent } from 'react'
import './App.css'
import {
  IconPillBox,
  IconPill,
  IconLidOpen,
  IconLidClosed,
  IconSpeaker,
  IconSpeakerMuted,
  IconBellRing,
  IconClock,
  IconClockRealtime,
  IconKey,
  IconVibrate,
  IconCheck,
  IconCheckCircle,
  IconAlertTriangle,
  IconAlertCircle,
  IconRotateCcw,
  IconFastForward,
  IconRefresh,
  IconArrowRight,
  IconX,
  IconCalendarClock,
  IconActivity,
} from './components/Icons'
import {
  unlockAudio,
  playBuzzerAlarm,
  playConfirmationChime,
  subscribeAudioUnlock,
  isAudioReady,
} from './audio/buzzerAudio'

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
  dose_taken?: boolean
  schedule_times?: string[]
  schedule_count?: number
}
type Schedule = { id: number; medication_name: string; slot: number; time: string; days_of_week?: string | null }
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
  clock_mode: 'SIMULATION' | 'REALTIME'
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
  | 'PILL_REFILLED'
  | 'REFILL'

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
  return <IconPillBox size={30} />
}

function formatDaysOfWeek(daysStr?: string | null): string {
  if (!daysStr || daysStr.trim() === '') return 'Mỗi ngày'
  const days = daysStr.split(',').map((d) => d.trim()).filter(Boolean)
  if (days.length === 7) return 'Mỗi ngày'
  const dayMap: Record<string, string> = {
    '1': 'T2',
    '2': 'T3',
    '3': 'T4',
    '4': 'T5',
    '5': 'T6',
    '6': 'T7',
    '7': 'CN',
  }
  return days.map((d) => dayMap[d] ?? d).join(', ')
}

function EventIcon({ type }: { type: string }) {
  switch (type) {
    case 'LID_OPENED':
      return <IconLidOpen size={16} />
    case 'LID_CLOSED':
      return <IconLidClosed size={16} />
    case 'PILL_DISPENSED':
      return <IconPill size={16} />
    case 'DOSE_CONFIRMED':
      return <IconCheck size={16} />
    case 'ALERT_CREATED':
      return <IconAlertTriangle size={16} />
    case 'CLOCK_ADVANCED':
      return <IconFastForward size={16} />
    case 'SIMULATION_RESET':
      return <IconRotateCcw size={16} />
    case 'REMINDER_SENT':
      return <IconBellRing size={16} />
    case 'PILL_REFILLED':
    case 'REFILL':
      return <IconRefresh size={16} />
    default:
      return <IconActivity size={16} />
  }
}

function eventLabel(event: SimulationEvent) {
  if (event.event_type === 'REMINDER_SENT') return Number(event.payload.reminder_level) === 2 ? 'Nhắc lại lần hai' : 'Bắt đầu nhắc thuốc'
  if (event.event_type === 'ALERT_CREATED') return 'Đã tạo cảnh báo quá hạn'
  if (event.event_type === 'CLOCK_ADVANCED') return `Tiến đồng hồ +${event.payload.minutes} phút`
  if (event.event_type === 'SIMULATION_RESET') return 'Đặt lại hộp mô phỏng'
  if (event.event_type === 'PILL_REFILLED' || event.event_type === 'REFILL') {
    const pills = event.payload.count ?? event.payload.pills_added ?? 10
    return `Nạp thêm bịch thuốc (+${pills} bịch)`
  }
  if (event.event_type === 'WEIGHT_READING') {
    const weight = event.payload.weight_g
    return typeof weight === 'number' ? `Cảm biến tải trọng: ${weight.toFixed(1)} g` : 'Cảm biến tải trọng đọc khối lượng'
  }
  if (event.event_type === 'CONFIRM_PRESSED') return 'Nút hộp: Bấm xác nhận uống thuốc'
  if (event.event_type === 'DOSE_CONFIRMED') {
    if (event.payload?.trigger === 'LID_CLOSED' || event.payload?.auto_confirmed) {
      return 'Tự động xác nhận uống thuốc khi đóng nắp'
    }
    return 'Người dùng xác nhận đã uống'
  }
  return {
    LID_OPENED: 'Mở nắp ngăn',
    LID_CLOSED: 'Đóng nắp ngăn',
    PILL_DISPENSED: 'Lấy 1 bịch thuốc mô phỏng',
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
  const [audioEnabled, setAudioEnabled] = useState(true)
  const [, setAudioUnlocked] = useState(isAudioReady())
  const lastReminderEventId = useRef<number | null>(null)
  const modeEnsuredRef = useRef(false)
  const recentEvents = device?.recent_events
  const anyBuzzerActive = Boolean(device?.compartments?.some((c) => c.buzzer_on))

  // Sync audio unlocked status
  useEffect(() => {
    return subscribeAudioUnlock((unlocked) => {
      setAudioUnlocked(unlocked)
    })
  }, [])

  // Poll device state & ensure default mode is REALTIME
  useEffect(() => {
    if (!token) return
    let alive = true
    const refresh = async () => {
      try {
        const result = await request<DeviceState>('/api/simulation/state', token)
        if (alive) {
          setDevice(result)
          setConnectionError('')
          // Ensure default reminder mode is REALTIME
          if (!modeEnsuredRef.current && result.clock_mode !== 'REALTIME') {
            modeEnsuredRef.current = true
            void changeClockMode('REALTIME')
          }
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

  // Continuous sound when buzzer is active on the pillbox
  useEffect(() => {
    if (!audioEnabled || !anyBuzzerActive) return

    // Immediately play alarm chime on trigger
    playBuzzerAlarm()

    // Repeat medical alarm chime every 3.5 seconds while buzzer is buzzing
    const interval = window.setInterval(() => {
      playBuzzerAlarm()
    }, 3500)

    return () => {
      window.clearInterval(interval)
    }
  }, [anyBuzzerActive, audioEnabled])

  // Also play sound when a new reminder event arrives
  useEffect(() => {
    if (!recentEvents) return
    const reminderEvents = recentEvents.filter((event) => event.event_type === 'REMINDER_SENT')
    const newestId = reminderEvents.reduce((latest, event) => Math.max(latest, event.id), 0)
    const previousId = lastReminderEventId.current
    if (previousId === null) {
      lastReminderEventId.current = newestId
      if (newestId > 0 && anyBuzzerActive && audioEnabled) {
        playBuzzerAlarm()
      }
      return
    }
    if (newestId > previousId) {
      lastReminderEventId.current = newestId
      if (audioEnabled) {
        playBuzzerAlarm()
      }
    }
  }, [recentEvents, audioEnabled, anyBuzzerActive])

  async function toggleAudio() {
    await unlockAudio()
    setAudioEnabled((enabled) => !enabled)
    setActionMessage('')
  }

  async function handleTestSound() {
    await unlockAudio()
    setAudioEnabled(true)
    playBuzzerAlarm()
    setActionMessage('Đang phát thử âm thanh còi báo y tế của hộp thuốc...')
    setTimeout(() => setActionMessage(''), 3000)
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginError('')
    void unlockAudio()
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
      modeEnsuredRef.current = false
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
    lastReminderEventId.current = null
    modeEnsuredRef.current = false
  }

  async function sendEvent(slot: number, eventType: EventType, extraPayload: Record<string, unknown> = {}): Promise<DeviceState | null> {
    if (!token) return null
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
      return updated
    } catch (error) {
      if (error instanceof ApiRequestError) setActionMessage(error.message)
      else setConnectionError(error instanceof Error ? error.message : 'Không lưu được thao tác')
      return null
    } finally {
      setBusySlot(null)
    }
  }

  async function takeOnePill(item: Compartment) {
    const nextWeight = Math.max(0, Number((item.weight_grams - 0.5).toFixed(1)))
    await sendEvent(item.slot, 'WEIGHT_READING', { weight_g: nextWeight })
    if (audioEnabled) playConfirmationChime()
  }

  async function refillPills(item: Compartment) {
    await sendEvent(item.slot, 'PILL_REFILLED', { count: 10, pills_added: 10, weight_added_g: 5.0 })
    if (audioEnabled) playConfirmationChime()
  }

  async function injectNoise(item: Compartment) {
    const nextWeight = Math.max(0, Number((item.weight_grams - 0.1).toFixed(1)))
    await sendEvent(item.slot, 'WEIGHT_READING', { weight_g: nextWeight })
  }

  async function confirmDose(item: Compartment) {
    const updated = await sendEvent(
      item.slot,
      'CONFIRM_PRESSED',
      item.current_occurrence_id ? { occurrence_id: item.current_occurrence_id } : {}
    )
    if (updated && audioEnabled) playConfirmationChime()
  }

  async function changeClockMode(mode: 'SIMULATION' | 'REALTIME') {
    if (!token || device?.clock_mode === mode) return
    setBusyControl(true)
    setActionMessage('')
    try {
      const previousReminderId = Math.max(
        0, ...(device?.recent_events ?? [])
          .filter((item) => item.event_type === 'REMINDER_SENT')
          .map((item) => item.id)
      )
      const updated = await request<DeviceState>('/api/simulation/mode', token, {
        method: 'POST',
        body: JSON.stringify({ clock_mode: mode }),
      })
      lastReminderEventId.current = previousReminderId
      setDevice(updated)
      setConnectionError('')
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : 'Không chuyển được chế độ đồng hồ')
    } finally {
      setBusyControl(false)
    }
  }

  async function advanceClock(minutes: number) {
    if (!token || device?.clock_mode === 'REALTIME') return
    setBusyControl(true)
    setActionMessage('')
    try {
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
    if (!token || device?.clock_mode === 'REALTIME' || !window.confirm('Đặt lại hộp sẽ xóa lịch sử thao tác, lần nhắc và cảnh báo của phiên mô phỏng hiện tại. Các tài khoản và lịch thuốc vẫn được giữ; nhật ký sẽ ghi thao tác đặt lại. Tiếp tục?')) return
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

  async function clearHistoryEvents() {
    if (!token || !window.confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử thao tác và sự kiện trên hệ thống không?')) return
    try {
      await request('/api/events', token, { method: 'DELETE' })
      const updated = await request<DeviceState>('/api/simulation/state', token)
      setDevice(updated)
      setActionMessage('Đã làm sạch toàn bộ lịch sử thao tác và sự kiện.')
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : 'Không thể xóa lịch sử sự kiện')
    }
  }

  if (!token) {
    return (
      <main className="login-screen">
        <div className="login-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="art-box">
            <IconPillBox size={64} />
            <span>SIM—001</span>
          </div>
          <div className="art-caption">BA NGĂN THUỐC<br />KẾT NỐI ĐỒNG BỘ</div>
        </div>
        <section className="login-panel">
          <div className="brand-lockup">
            <span className="brand-icon"><IconPillBox size={22} /></span>
            <span>SMART PILL BOX<small>BẢN MÔ PHỎNG / 01</small></span>
          </div>
          <div className="login-copy">
            <p className="eyebrow">BÀN ĐIỀU KHIỂN THIẾT BỊ</p>
            <h1>Một chiếc hộp.<br /><em>Ba ngăn thuốc.</em></h1>
            <p className="muted">Đăng nhập tài khoản điều khiển để thao tác hộp mô phỏng, chạy đồng hồ và xem dữ liệu đã lưu trên máy chủ.</p>
          </div>
          <form className="login-form" onSubmit={login}>
            <label htmlFor="email">Email điều khiển</label>
            <input id="email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <label htmlFor="password">Mật khẩu</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            {loginError && <p className="form-error" role="alert">{loginError}</p>}
            <button className="primary-button login-button" type="submit">
              <span>Đăng nhập</span>
              <IconArrowRight size={16} />
            </button>
            <button
              type="button"
              className="demo-account-hint"
              onClick={() => { setEmail('operator@example.test'); setPassword('Password123!'); void unlockAudio(); }}
              title="Bấm để điền tài khoản người vận hành mặc định"
            >
              <IconKey size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: '6px' }} />
              <span>Điền nhanh: operator@example.test • Password123!</span>
            </button>
          </form>
          <p className="login-footnote">Dữ liệu thử nghiệm · Không dùng hồ sơ bệnh nhân thật</p>
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
          <span>SMART PILL BOX<small>BẢN MÔ PHỎNG / 01</small></span>
        </a>
        <div className="topbar-right">
          <div className={`connection ${connectionError ? 'is-offline' : ''}`}><span className="status-dot" />{connectionError ? 'Mất kết nối' : 'Máy chủ trực tuyến'}</div>
          <button
            className={`audio-toggle ${audioEnabled ? 'audio-on' : ''}`}
            type="button"
            onClick={() => void toggleAudio()}
            aria-pressed={audioEnabled}
            title={audioEnabled ? 'Click để tắt âm thanh còi' : 'Click để bật âm thanh còi'}
          >
            {audioEnabled ? <IconSpeaker size={16} /> : <IconSpeakerMuted size={16} />}
            <span>{audioEnabled ? 'Còi đang bật' : 'Còi đang tắt'}</span>
          </button>
          <button
            className="test-sound-btn"
            type="button"
            onClick={() => void handleTestSound()}
            title="Bấm để phát thử âm thanh chuông báo y tế"
          >
            <IconBellRing size={15} />
            <span>Thử còi</span>
          </button>
          <span className="user-chip">{user?.display_name ?? 'Người vận hành'}</span>
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
            <span className="clock-label">{device?.clock_mode === 'REALTIME' ? 'GIỜ THỰC TẾ · VIỆT NAM (GMT+7)' : 'GIỜ MÔ PHỎNG · GMT+7'}</span>
            <strong>{device ? clockLabel(device.virtual_clock) : '— — : — —'}</strong>
            <span className="clock-date">{device ? dateLabel(device.virtual_clock) : 'Đang tải trạng thái'}</span>
          </div>
        </section>

        {connectionError && (
          <div className="alert-banner" role="status">
            <IconAlertCircle size={20} />
            <div><strong>Không thể đồng bộ với máy chủ</strong><small>{connectionError} · Đang thử kết nối lại mỗi 2 giây.</small></div>
          </div>
        )}
        {actionMessage && (
          <div className="action-banner" role="alert">
            <IconAlertTriangle size={20} />
            <div><strong>Thông báo hệ thống</strong><small>{actionMessage}</small></div>
            <button type="button" onClick={() => setActionMessage('')} aria-label="Đóng thông báo">
              <IconX size={16} />
            </button>
          </div>
        )}
        {loading && !device && <div className="loading-card"><span className="loader" />Đang tải trạng thái từ cơ sở dữ liệu…</div>}

        <section className="simulation-console" aria-label="Điều khiển đồng hồ mô phỏng">
          <div className="console-copy">
            <span className="console-icon">
              {device?.clock_mode === 'REALTIME' ? <IconClockRealtime size={24} /> : <IconClock size={24} />}
            </span>
            <div>
              <p className="eyebrow">CHẾ ĐỘ NHẮC THUỐC</p>
              <strong>{device?.clock_mode === 'REALTIME' ? 'Tự động theo giờ thật (Mặc định)' : 'Đồng hồ mô phỏng'}</strong>
              <small>{device?.clock_mode === 'REALTIME' ? 'Máy chủ tự kiểm tra giờ uống liên tục theo thời gian thực, kể cả khi đóng website. Giữ dịch vụ máy chủ đang chạy.' : 'Tiến phút chủ động để trình diễn nhắc giờ và cảnh báo.'}</small>
            </div>
          </div>
          <div className="clock-mode-toggle" role="group" aria-label="Chế độ thời gian">
            <button type="button" className={device?.clock_mode === 'REALTIME' ? 'mode-active' : ''} disabled={!device || busyControl} onClick={() => void changeClockMode('REALTIME')}>
              Thời gian thực (Mặc định)
            </button>
            <button type="button" className={device?.clock_mode !== 'REALTIME' ? 'mode-active' : ''} disabled={!device || busyControl} onClick={() => void changeClockMode('SIMULATION')}>
              Mô phỏng
            </button>
          </div>
          <div className="clock-buttons">
            {[1, 2, 5].map((minutes) => (
              <button type="button" key={minutes} disabled={!device || busyControl || device.clock_mode === 'REALTIME'} onClick={() => void advanceClock(minutes)}>
                {busyControl ? 'Đang chạy…' : `+${minutes} phút`}
              </button>
            ))}
            <button className="milestone-button" type="button" disabled={!device || busyControl || device.clock_mode === 'REALTIME'} onClick={() => void advanceClock(device?.next_milestone_minutes ?? 1)} title="Nhảy đến mốc nhắc thuốc hoặc quá hạn gần nhất">
              Mốc tiếp theo (+{device?.next_milestone_minutes ?? 1}p)
            </button>
            <button className="reset-button" type="button" disabled={!device || busyControl || device.clock_mode === 'REALTIME'} onClick={() => void resetSimulation()}>
              Đặt lại hộp
            </button>
          </div>
        </section>

        <section className="overview-row">
          <div className="section-heading">
            <div>
              <p className="eyebrow">TRẠNG THÁI THIẾT BỊ</p>
              <h2>Ba ngăn, một lịch trình</h2>
            </div>
            <span className={`live-label ${connectionError ? 'offline-label' : ''}`}>
              <span className="status-dot" />{connectionError ? 'CHỜ KẾT NỐI' : 'CẬP NHẬT 2 GIÂY'}
            </span>
          </div>
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
                      <span className="led-text">{item.led === 'Bật' ? 'ĐÈN BẬT' : 'ĐÈN TẮT'}</span>
                    </div>

                    <div className="pill-well" aria-label={`${item.pill_count} bịch thuốc trong ngăn`}>
                      <div className="pills-scatter">
                        {Array.from({ length: Math.min(item.pill_count, 8) }, (_, pill) => (
                          <div className={`pouch-unit pouch-type-${item.slot}`} key={pill} title="Bịch thuốc phân liều (chứa các viên thuốc của cữ)">
                            <span className="pouch-seal" />
                            <span className="pouch-pill-dots">
                              <span className="dot dot-1" />
                              <span className="dot dot-2" />
                            </span>
                          </div>
                        ))}
                      </div>
                      <div className="pill-counter-tag">
                        <strong>{item.pill_count}</strong>
                        <span>bịch chia sẵn</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="medication-title">
                  <h3>{item.medication_name}</h3>
                  <div className="medication-tags-row">
                    <span className="medication-type-tag">Bịch thuốc chia sẵn</span>
                    {item.schedule_times && item.schedule_times.length > 1 ? (
                      <span className="shared-slot-tag" title="Ngăn này dùng chung cho nhiều cữ trong ngày có cùng loại và cùng số lượng thuốc để tiết kiệm ngăn">
                        Dùng chung · {item.schedule_times.length} cữ: {item.schedule_times.join(' · ')}
                      </span>
                    ) : item.schedule_times && item.schedule_times.length === 1 ? (
                      <span className="single-schedule-tag">
                        Cữ uống: {item.schedule_times[0]}
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="card-metrics">
                  <div className="metric-box scale-metric">
                    <span className="metric-label">CẢM BIẾN TẢI TRỌNG</span>
                    <div className="oled-scale-readout">
                      <span className="oled-tag">CẢM BIẾN TẢI TRỌNG</span>
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
                    {item.buzzer_on ? <IconSpeaker size={18} /> : <IconSpeakerMuted size={18} />}
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
                  <button
                    className={`lid-button ${item.lid_open ? 'secondary-button' : 'primary-button'}`}
                    type="button"
                    disabled={busySlot === item.slot || busyControl}
                    onClick={async () => {
                      const wasBuzzerOn = item.buzzer_on
                      const nextEvent = item.lid_open ? 'LID_CLOSED' : 'LID_OPENED'
                      const updated = await sendEvent(item.slot, nextEvent)
                      if (
                        updated &&
                        nextEvent === 'LID_CLOSED' &&
                        wasBuzzerOn &&
                        !updated.compartments.find((c) => c.slot === item.slot)?.buzzer_on &&
                        audioEnabled
                      ) {
                        playConfirmationChime()
                      }
                    }}
                  >
                    <span className="btn-icon">{item.lid_open ? <IconLidClosed size={16} /> : <IconLidOpen size={16} />}</span>
                    <span>{busySlot === item.slot ? 'Đang gửi…' : item.lid_open ? 'Đóng nắp ngăn' : 'Mở nắp ngăn'}</span>
                  </button>
                  <button
                    className="dispense-button"
                    type="button"
                    disabled={!item.lid_open || item.pill_count <= 0 || busySlot === item.slot || busyControl}
                    onClick={() => void takeOnePill(item)}
                    title={!item.lid_open ? 'Mở nắp ngăn trước' : item.pill_count <= 0 ? 'Ngăn đã hết bịch thuốc chia sẵn' : 'Lấy 1 bịch thuốc chia sẵn'}
                  >
                    <span className="btn-icon"><IconPill size={16} /></span>
                    <span>Lấy 1 bịch thuốc</span>
                    <span className="btn-weight-change">−0,5 g</span>
                  </button>
                  <button
                    className="refill-button"
                    type="button"
                    disabled={!item.lid_open || busySlot === item.slot || busyControl}
                    onClick={() => void refillPills(item)}
                    title={!item.lid_open ? 'Mở nắp ngăn trước khi nạp thêm bịch thuốc' : 'Nạp thêm 10 bịch thuốc chia sẵn (+5.0 g)'}
                  >
                    <span className="btn-icon"><IconRefresh size={15} /></span>
                    <span>Nạp thêm 10 bịch</span>
                    <span className="btn-weight-change">+5,0 g</span>
                  </button>
                  <button
                    className="noise-button"
                    type="button"
                    disabled={!item.lid_open || busySlot === item.slot || busyControl}
                    onClick={() => void injectNoise(item)}
                    title="Thử nhiễu tải trọng 0.1g (kiểm thử rung động, không làm giảm bịch thuốc)"
                  >
                    <span className="btn-icon"><IconVibrate size={15} /></span>
                    <span>Thử nhiễu cân</span>
                    <span className="btn-weight-change">−0,1 g</span>
                  </button>
                  {item.can_confirm && (
                    <button
                      className="confirm-button"
                      type="button"
                      disabled={busySlot === item.slot || busyControl}
                      onClick={() => void confirmDose(item)}
                      title={!item.dose_taken ? 'Lưu ý: Mở nắp và lấy bịch thuốc khỏi ngăn trước khi nhấn xác nhận' : 'Đã lấy bịch thuốc. Nhấn để tắt còi và xác nhận đã uống'}
                    >
                      <span className="confirm-glow" />
                      <span className="btn-icon"><IconCheckCircle size={16} /></span>
                      <span>Nút xác nhận trên hộp</span>
                    </button>
                  )}
                </div>
                <p className="safety-note">Cảm biến chỉ cân tổng tải trọng • Ngăn chứa được nhiều bịch nếu cùng loại và số lượng thuốc • Dùng chung ngăn cho các cữ giống nhau giúp tiết kiệm không gian hộp</p>
              </article>
            ))}

            {!device && !loading && <div className="empty-state">Chưa có trạng thái hộp. Kiểm tra máy chủ và đăng nhập tài khoản điều khiển.</div>}
          </div>
        </section>

        <section className="lower-grid">
          <div className="schedule-panel">
            <div className="section-heading compact">
              <div><p className="eyebrow">ĐỒNG BỘ TỪ CƠ SỞ DỮ LIỆU</p><h2>Lịch đang bật</h2></div>
              <span className="count-pill">{device?.active_schedules.length ?? 0}</span>
            </div>
            {nextSchedule && (
              <div className="next-dose">
                <div className="next-icon"><IconCalendarClock size={20} /></div>
                <div>
                  <span>LỊCH TIẾP THEO</span>
                  <strong>{nextSchedule.medication_name}</strong>
                  <small>Ngăn {nextSchedule.slot} · {nextSchedule.time}</small>
                </div>
                <time>{nextSchedule.time}</time>
              </div>
            )}
            <div className="schedule-list">
              {(device?.active_schedules ?? []).map((schedule) => (
                <div className="schedule-row" key={schedule.id}>
                  <div className="schedule-row-main">
                    <time>{schedule.time}</time>
                    <span className="schedule-slot">Ngăn {schedule.slot}</span>
                    <strong>{schedule.medication_name}</strong>
                  </div>
                  <div className="schedule-row-meta">
                    <span className="recurrence-badge">{formatDaysOfWeek(schedule.days_of_week)}</span>
                    <span className="active-tag">ĐANG BẬT</span>
                  </div>
                </div>
              ))}
              {device && device.active_schedules.length === 0 && <p className="empty-schedules">Chưa có lịch đang bật. Lịch mới từ ứng dụng Flutter sẽ xuất hiện tại đây.</p>}
            </div>
            <p className="sync-note"><span className="sync-arrows"><IconRefresh size={13} /></span> Đồng bộ mỗi 2 giây · lịch dùng chung với ứng dụng Flutter</p>
          </div>

          <aside className="activity-panel">
            <div className="section-heading compact">
              <div><p className="eyebrow">NHẬT KÝ THIẾT BỊ</p><h2>Thao tác gần đây</h2></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  className="text-button"
                  style={{ fontSize: '11px', color: '#dc2626', padding: '2px 8px' }}
                  onClick={() => void clearHistoryEvents()}
                  disabled={events.length === 0}
                  title="Xóa sạch nhật ký sự kiện trên máy chủ"
                >
                  Xóa nhật ký
                </button>
                <span className="count-pill">{events.length}</span>
              </div>
            </div>
            <div className="activity-list">
              {events.map((event) => (
                <div className="activity-row" key={event.id}>
                  <span className={`activity-symbol ${event.event_type === 'ALERT_CREATED' ? 'activity-alert' : event.event_type === 'DOSE_CONFIRMED' ? 'activity-confirmed' : ''}`}>
                    <EventIcon type={event.event_type} />
                  </span>
                  <div className="activity-copy">
                    <strong>{eventLabel(event)}</strong>
                    <small>
                      {event.payload.slot ? `Ngăn ${event.payload.slot}` : 'Hộp mô phỏng'} ·{' '}
                      {event.payload.virtual_time ? clockLabel(String(event.payload.virtual_time)) : new Date(event.created_at).toLocaleTimeString('vi-VN')}
                    </small>
                  </div>
                </div>
              ))}
              {device && events.length === 0 && <p className="empty-activity">Chưa có thao tác trong phiên mô phỏng. Mở nắp hoặc tiến đồng hồ để bắt đầu.</p>}
              {!device && <p className="empty-activity">Nhật ký sẽ xuất hiện sau khi tải trạng thái thiết bị.</p>}
            </div>
            <p className="sync-note"><span className="sync-arrows"><IconRefresh size={13} /></span> Lịch sử sự kiện được lưu trên máy chủ</p>
          </aside>
        </section>

        <footer className="page-footer"><span>SMART PILL BOX <i>·</i> BẢN MÔ PHỎNG</span><span>Dữ liệu giả · Không dùng cho chăm sóc y tế thực tế</span></footer>
      </main>
    </div>
  )
}

export default App
