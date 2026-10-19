import type { SVGProps } from 'react'

export type IconProps = SVGProps<SVGSVGElement> & {
  size?: number | string
}

const defaultProps = {
  xmlns: 'http://www.w3.org/2000/svg',
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function IconPillBox({ size = 24, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <rect x="2" y="5" width="20" height="15" rx="4" />
      <line x1="8.66" y1="5" x2="8.66" y2="20" />
      <line x1="15.33" y1="5" x2="15.33" y2="20" />
      <circle cx="5.33" cy="9" r="1" fill="currentColor" />
      <circle cx="12" cy="9" r="1" fill="currentColor" />
      <circle cx="18.66" cy="9" r="1" fill="currentColor" />
    </svg>
  )
}

export function IconPill({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z" />
      <path d="m8.5 8.5 7 7" />
    </svg>
  )
}

export function IconLidOpen({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="M4 10v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-9" />
      <path d="M2.5 10h19" />
      <path d="M4 10 7.5 4.5a2 2 0 0 1 1.7-1h5.6a2 2 0 0 1 1.7 1L20 10" strokeDasharray="1 0" />
      <path d="M12 3v5" strokeWidth="2.5" />
      <path d="m9.5 5.5 2.5-2.5 2.5 2.5" />
    </svg>
  )
}

export function IconLidClosed({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <rect x="3" y="10" width="18" height="11" rx="2" />
      <path d="M4 10 7 5.5a2 2 0 0 1 1.7-1h6.6a2 2 0 0 1 1.7 1L20 10" />
      <line x1="10" y1="14" x2="14" y2="14" />
      <circle cx="12" cy="14" r="1" fill="currentColor" />
    </svg>
  )
}

export function IconSpeaker({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  )
}

export function IconSpeakerMuted({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <line x1="2" y1="2" x2="22" y2="22" strokeWidth="2.2" />
      <path d="M18.8 13.8a6.5 6.5 0 0 0-.8-2.8" />
      <polygon points="11 5 6 9 2 9 2 15 6 15 8.2 16.8" />
      <path d="M11 19v-4.5" />
      <line x1="22" y1="9" x2="16" y2="15" />
      <line x1="16" y1="9" x2="22" y2="15" />
    </svg>
  )
}

export function IconBellRing({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      <path d="M4 2C2.8 3.7 2 5.7 2 8" />
      <path d="M22 8c0-2.3-.8-4.3-2-6" />
    </svg>
  )
}

export function IconKey({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="m21 2-2 2m-1.5 1.5L14 9l-2-2-4 4a5 5 0 1 0 7 7l4-4-2-2 2.5-2.5 1.5 1.5 2-2Z" />
      <circle cx="7.5" cy="16.5" r="1.5" fill="currentColor" />
    </svg>
  )
}

export function IconClock({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

export function IconClockRealtime({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 15 15" />
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M18 2a11 11 0 0 1 4 4" stroke="#10b981" />
    </svg>
  )
}

export function IconVibrate({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="m2 8 2 2-2 2 2 2-2 2" />
      <path d="m22 8-2 2 2 2-2 2 2 2" />
      <rect width="8" height="14" x="8" y="5" rx="2" />
      <line x1="12" y1="9" x2="12" y2="15" />
    </svg>
  )
}

export function IconCheck({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

export function IconCheckCircle({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  )
}

export function IconAlertTriangle({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeWidth="3" />
    </svg>
  )
}

export function IconAlertCircle({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" strokeWidth="3" />
    </svg>
  )
}

export function IconRotateCcw({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  )
}

export function IconFastForward({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <polygon points="13 19 22 12 13 5 13 19" />
      <polygon points="2 19 11 12 2 5 2 19" />
    </svg>
  )
}

export function IconRefresh({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
      <path d="M21 21v-5h-5" />
    </svg>
  )
}

export function IconArrowRight({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  )
}

export function IconArrowUpRight({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <line x1="7" y1="17" x2="17" y2="7" />
      <polyline points="7 7 17 7 17 17" />
    </svg>
  )
}

export function IconArrowDownLeft({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <line x1="17" y1="7" x2="7" y2="17" />
      <polyline points="17 17 7 17 7 7" />
    </svg>
  )
}

export function IconX({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

export function IconCalendarClock({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="M21 7.5V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h3.5" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <circle cx="16" cy="16" r="6" />
      <polyline points="16 14 16 16 18 17" />
    </svg>
  )
}

export function IconScale({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
      <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
      <path d="M7 21h10" />
      <path d="M12 3v18" />
      <path d="M3 7h18" />
    </svg>
  )
}

export function IconActivity({ size = 18, ...props }: IconProps) {
  return (
    <svg {...defaultProps} width={size} height={size} viewBox="0 0 24 24" {...props}>
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  )
}
