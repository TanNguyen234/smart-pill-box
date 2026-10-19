/**
 * Web Audio API synthesizer for Smart Pill Box SIM-001 hardware simulator.
 * Automatically unlocks on user interaction and plays authentic medical reminder chimes.
 */

let audioContext: AudioContext | null = null
let isUnlocked = false
const unlockListeners: Array<(unlocked: boolean) => void> = []

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (!audioContext) {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (AudioCtx) {
      audioContext = new AudioCtx()
    }
  }
  return audioContext
}

export async function unlockAudio(): Promise<boolean> {
  const ctx = getAudioContext()
  if (!ctx) return false
  try {
    if (ctx.state === 'suspended') {
      await ctx.resume()
    }
    if (ctx.state === 'running') {
      if (!isUnlocked) {
        isUnlocked = true
        unlockListeners.forEach((fn) => fn(true))
      }
      return true
    }
  } catch (err) {
    console.warn('[Audio] Failed to resume AudioContext:', err)
  }
  return false
}

// Global auto-unlock on any user gesture anywhere in the browser window
if (typeof window !== 'undefined') {
  const autoUnlock = () => {
    void unlockAudio()
  }
  window.addEventListener('pointerdown', autoUnlock, { capture: true, once: false })
  window.addEventListener('keydown', autoUnlock, { capture: true, once: false })
  window.addEventListener('click', autoUnlock, { capture: true, once: false })
}

export function subscribeAudioUnlock(callback: (unlocked: boolean) => void): () => void {
  unlockListeners.push(callback)
  callback(isUnlocked || audioContext?.state === 'running')
  return () => {
    const index = unlockListeners.indexOf(callback)
    if (index >= 0) unlockListeners.splice(index, 1)
  }
}

export function isAudioReady(): boolean {
  return isUnlocked || audioContext?.state === 'running'
}

/**
 * Plays an authentic medical alarm alert chime:
 * 2 dual-tone melodic beeps (880Hz -> 1175Hz, then 880Hz -> 1318Hz).
 */
export function playBuzzerAlarm(volume = 0.32): void {
  const ctx = getAudioContext()
  if (!ctx) return

  if (ctx.state === 'suspended') {
    void ctx.resume().then(() => {
      if (ctx.state === 'running') playBuzzerAlarm(volume)
    })
    return
  }

  const now = ctx.currentTime

  const notes = [
    { freq: 880, start: now + 0.00, dur: 0.12 },
    { freq: 1175, start: now + 0.16, dur: 0.18 },
    { freq: 880, start: now + 0.44, dur: 0.12 },
    { freq: 1318, start: now + 0.60, dur: 0.24 },
  ]

  notes.forEach(({ freq, start, dur }) => {
    try {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, start)

      gain.gain.setValueAtTime(0.0001, start)
      gain.gain.exponentialRampToValueAtTime(volume, start + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, start + dur)

      osc.connect(gain)
      gain.connect(ctx.destination)

      osc.start(start)
      osc.stop(start + dur + 0.05)
    } catch (e) {
      console.warn('[Audio] Note schedule error:', e)
    }
  })
}

/**
 * Plays a soft positive confirmation chime when medication is taken or confirmed.
 */
export function playConfirmationChime(volume = 0.25): void {
  const ctx = getAudioContext()
  if (!ctx || ctx.state !== 'running') return

  const now = ctx.currentTime
  const notes = [
    { freq: 587.33, start: now + 0.00, dur: 0.10 }, // D5
    { freq: 880.00, start: now + 0.12, dur: 0.14 }, // A5
    { freq: 1174.66, start: now + 0.28, dur: 0.22 }, // D6
  ]

  notes.forEach(({ freq, start, dur }) => {
    try {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = 'triangle'
      osc.frequency.setValueAtTime(freq, start)

      gain.gain.setValueAtTime(0.0001, start)
      gain.gain.exponentialRampToValueAtTime(volume, start + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, start + dur)

      osc.connect(gain)
      gain.connect(ctx.destination)

      osc.start(start)
      osc.stop(start + dur + 0.05)
    } catch {
      // Ignored
    }
  })
}
