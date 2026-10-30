import { IconInfo } from './Icons.jsx'

export const DISCLAIMER =
  'Informational only, not medical advice. Always read the physical label and consult a doctor or dietitian for medical decisions.'

export default function Disclaimer({ compact = false }) {
  return (
    <p className={`flex items-start gap-2 text-muted ${compact ? 'text-[11px]' : 'text-xs'}`}>
      <IconInfo width={14} height={14} className="mt-px shrink-0" />
      <span>{DISCLAIMER}</span>
    </p>
  )
}
