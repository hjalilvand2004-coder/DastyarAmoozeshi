import { X } from 'lucide-react'

export const STATUS_FA = {
  draft: 'پیش‌نویس', in_review: 'در حال بررسی', approved: 'تأییدشده',
  published: 'منتشرشده (معتبر)', retired: 'ملغی‌شده',
}
export const STATUS_CHIP = {
  draft: 'chip-slate', in_review: 'chip-sky', approved: 'chip-violet',
  published: 'chip-emerald', retired: 'chip-rose',
}
export const RULE_STATE_FA = {
  satisfied: 'برقرار است', not_satisfied: 'برقرار نیست',
  insufficient_info: 'اطلاعات ناکافی', needs_review: 'نیازمند بررسی کارشناس',
}
export const RULE_STATE_CHIP = {
  satisfied: 'chip-emerald', not_satisfied: 'chip-rose',
  insufficient_info: 'chip-amber', needs_review: 'chip-sky',
}
export const TICKET_FA = {
  submitted: 'ثبت‌شده', under_review: 'در حال بررسی', needs_info: 'نیازمند اطلاعات',
  answered: 'پاسخ داده شد', closed: 'بسته‌شده',
}
export const TICKET_CHIP = {
  submitted: 'chip-slate', under_review: 'chip-sky', needs_info: 'chip-amber',
  answered: 'chip-emerald', closed: 'chip-slate',
}

export function Chip({ tone = 'chip-slate', children, title }) {
  return <span className={`chip ${tone}`} title={title}>{children}</span>
}

export function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" dir="rtl">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className={`glass-strong relative w-full ${wide ? 'max-w-3xl' : 'max-w-lg'} max-h-[88vh] overflow-y-auto p-6 fade-up`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-100">{title}</h3>
          <button onClick={onClose} className="btn btn-ghost btn-sm !px-2" aria-label="بستن"><X size={16} /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Spinner({ label = 'در حال بارگذاری…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 gap-3 text-slate-400">
      <div className="w-8 h-8 rounded-full border-2 border-violet-500/30 border-t-violet-400 spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function EmptyState({ icon: Icon, title, sub }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center gap-2">
      {Icon && <div className="w-12 h-12 rounded-2xl glass flex items-center justify-center text-violet-300"><Icon size={22} /></div>}
      <div className="font-semibold text-slate-200">{title}</div>
      {sub && <div className="text-sm text-slate-500 max-w-md">{sub}</div>}
    </div>
  )
}

export function PageHead({ title, sub, actions }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 mb-6 fade-up">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-100">{title}</h1>
        {sub && <p className="text-sm text-slate-500 mt-1">{sub}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function SampleBanner() {
  return (
    <div className="glass p-3.5 flex items-start gap-3 !border-amber-400/30 !bg-amber-400/[.06] text-sm fade-up">
      <span className="chip chip-amber shrink-0 mt-0.5">نمونه و غیررسمی</span>
      <p className="text-amber-200/90 leading-6">
        داده‌های فعلی سامانه <b>نمونه و غیررسمی</b> هستند. تا زمانی که مدیر محتوا اسناد رسمی دانشگاه را ثبت کند،
        هیچ موردی به‌عنوان قانون واقعی دانشگاه ارائه نمی‌شود.
      </p>
    </div>
  )
}
