import { useEffect, useState } from 'react'
import { Bell, BellOff, CalendarClock, Plus } from 'lucide-react'
import api, { errMsg } from '../api'
import { useAuth } from '../auth'
import { Chip, EmptyState, Modal, PageHead, SampleBanner, Spinner } from '../ui'
import { FA_MONTHS, FA_WEEKDAYS_SHORT, faNum, jalaliMonthLength, jalaliStr, toGregorian, toJalali, weekdayIndexSat0 } from '../jalali'

export default function Deadlines() {
  const { can } = useAuth()
  const [items, setItems] = useState(null)
  const [reminders, setReminders] = useState([])
  const [addOpen, setAddOpen] = useState(false)
  const [err, setErr] = useState('')
  const tj = toJalali(new Date())
  const [month, setMonth] = useState({ jy: tj.jy, jm: tj.jm })

  const load = () => {
    api.get('/deadlines').then(({ data }) => setItems(data.deadlines)).catch((e) => setErr(errMsg(e)))
    api.get('/deadlines/reminders').then(({ data }) => setReminders(data.reminders)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  const ack = async (id) => {
    try { await api.post(`/deadlines/${id}/ack`); setReminders((r) => r.filter((x) => x.id !== id)) } catch (e) { alert(errMsg(e)) }
  }

  const stepMonth = (delta) => {
    setMonth((m) => {
      let jy = m.jy, jm = m.jm + delta
      if (jm > 12) { jm = 1; jy += 1 }
      if (jm < 1) { jm = 12; jy -= 1 }
      return { jy, jm }
    })
  }

  const isoOf = (jy, jm, jd) => {
    const g = toGregorian(jy, jm, jd)
    return `${g.gy}-${String(g.gm).padStart(2, '0')}-${String(g.gd).padStart(2, '0')}`
  }

  const jalOf = (iso) => {
    const [y, m, d] = iso.split('-').map(Number)
    return toJalali(new Date(y, m - 1, d))
  }

  const mlen = jalaliMonthLength(month.jy, month.jm)
  const firstW = weekdayIndexSat0(isoOf(month.jy, month.jm, 1))
  const cells = [...Array(firstW).fill(null), ...Array.from({ length: mlen }, (_, i) => i + 1)]
  const monthItems = (items || []).filter((d) => {
    if (!d.date_iso) return false
    const j = jalOf(d.date_iso)
    return j.jy === month.jy && j.jm === month.jm
  })

  return (
    <div>
      <PageHead title="تقویم آموزشی و مهلت‌ها" sub="تقویم جلالی با رویدادها، یادآور شخصی و تأیید دریافت (ضد تکرار)."
        actions={can('deadlines.manage') && <button className="btn btn-primary" onClick={() => setAddOpen(true)}><Plus size={15} /> ثبت مهلت</button>} />

      <SampleBanner />
      {err && <div className="text-sm text-rose-300 mt-3">{err}</div>}

      {/* یادآورها */}
      {reminders.length > 0 && (
        <div className="glass p-4 mt-5 !border-cyan-400/30 fade-up">
          <div className="flex items-center gap-2 mb-2 text-cyan-300 text-sm font-bold"><Bell size={15} /> یادآورهای اعلام‌نشده شما</div>
          <ul className="space-y-2">
            {reminders.map((r) => (
              <li key={r.id} className="flex items-center gap-2 text-sm">
                <Chip tone="chip-sky">{jalaliStr(r.date_iso)}</Chip>
                <span className="flex-1">{r.title}</span>
                <button className="btn btn-ghost btn-sm" onClick={() => ack(r.id)}><BellOff size={13} /> دیدم</button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* تقویم جلالی */}
      <div className="glass p-5 mt-5 fade-up">
        <div className="flex items-center justify-between mb-4">
          <button className="btn btn-ghost btn-sm" onClick={() => stepMonth(-1)}>‹ ماه قبل</button>
          <h2 className="font-bold text-slate-100">{FA_MONTHS[month.jm - 1]} {faNum(month.jy)}</h2>
          <button className="btn btn-ghost btn-sm" onClick={() => stepMonth(1)}>ماه بعد ›</button>
        </div>
        <div className="grid grid-cols-7 gap-1.5 mb-2 text-center text-[11px] text-slate-500">
          {FA_WEEKDAYS_SHORT.map((w, i) => <div key={w} className={i === 6 ? 'text-rose-300/70' : ''}>{w}</div>)}
        </div>
        <div className="grid grid-cols-7 gap-1.5">
          {cells.map((day, i) => {
            if (day === null) return <div key={`e${i}`} />
            const isFriday = i % 7 === 6
            const isToday = tj.jy === month.jy && tj.jm === month.jm && tj.jd === day
            const evs = monthItems.filter((d) => jalOf(d.date_iso).jd === day)
            return (
              <div key={day} className={`cal-cell ${isToday ? 'today' : ''} ${isFriday ? 'friday' : ''}`}>
                <div className={`text-[11px] mb-1 ${isToday ? 'text-cyan-300 font-bold' : 'text-slate-400'}`}>{faNum(day)}</div>
                {evs.map((e) => (
                  <div key={e.id} className="text-[10px] leading-4 rounded-md bg-violet-500/15 border border-violet-400/25 text-violet-200 px-1 py-0.5 mb-0.5 truncate" title={e.title}>
                    {e.title}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </div>

      {/* فهرست همه مهلت‌ها */}
      <div className="glass p-5 mt-5 fade-up">
        <h2 className="font-bold mb-3 flex items-center gap-2 text-slate-100"><CalendarClock size={16} className="text-cyan-300" /> همه مهلت‌ها</h2>
        {!items ? <Spinner /> : items.length === 0 ? <EmptyState icon={CalendarClock} title="مهلتی ثبت نشده" /> : (
          <ul className="space-y-2">
            {items.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center gap-2 p-3 rounded-xl bg-white/[.03] border border-white/[.06] text-sm">
                <Chip tone="chip-violet">{jalaliStr(d.date_iso)}</Chip>
                <span className="flex-1">{d.title}</span>
                {d.source_document_id && <Chip tone="chip-slate">مستند به سند</Chip>}
                {d.notes?.includes('نمونه') && <Chip tone="chip-amber">نمونه</Chip>}
              </li>
            ))}
          </ul>
        )}
      </div>

      {addOpen && <AddModal onClose={() => { setAddOpen(false); load() }} />}
    </div>
  )
}

function AddModal({ onClose }) {
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try { await api.post('/deadlines', { title, date_iso: date, notes: 'ثبت‌شده از رابط وب' }); onClose() }
    catch (e2) { setErr(errMsg(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal open onClose={onClose} title="ثبت مهلت جدید">
      <form onSubmit={submit} className="space-y-3">
        <div><label className="lbl">عنوان *</label><input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required /></div>
        <div>
          <label className="lbl">تاریخ (میلادی — در تقویم جلالی نمایش داده می‌شود)</label>
          <input type="date" className="input" dir="ltr" value={date} onChange={(e) => setDate(e.target.value)} required />
        </div>
        {err && <div className="text-sm text-rose-300">{err}</div>}
        <button className="btn btn-primary w-full" disabled={busy || !title || !date}>ثبت</button>
      </form>
    </Modal>
  )
}
