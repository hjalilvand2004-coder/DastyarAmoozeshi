import { useEffect, useState } from 'react'
import { LifeBuoy, Plus, Send } from 'lucide-react'
import api, { errMsg } from '../api'
import { Chip, EmptyState, Modal, PageHead, Spinner, TICKET_CHIP, TICKET_FA } from '../ui'

const STEPS = ['submitted', 'under_review', 'answered', 'closed']

export default function Tickets() {
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [err, setErr] = useState('')

  const load = () => api.get('/tickets').then(({ data }) => setData(data)).catch((e) => setErr(errMsg(e)))
  useEffect(() => { load() }, [])

  return (
    <div>
      <PageHead title="درخواست از کارشناس آموزش" sub="اگر پاسخ مستند پیدا نشد یا تصمیم نهایی لازم است، موضوع را به کارت کارشناس بفرستید؛ وضعیت در هر مرحله مشخص است."
        actions={<button className="btn btn-primary" onClick={() => setCreateOpen(true)}><Plus size={15} /> درخواست جدید</button>} />

      {err && <div className="text-sm text-rose-300 mb-3">{err}</div>}
      {!data ? <Spinner /> : data.tickets.length === 0 ? (
        <EmptyState icon={LifeBuoy} title="درخواستی ثبت نشده" sub="با دکمه «درخواست جدید» موضوع خود را مطرح کنید." />
      ) : (
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="space-y-2">
            {data.tickets.map((t) => (
              <button key={t.id} onClick={() => setSelected(t.id)}
                className={`w-full text-right glass card-hover p-4 ${selected === t.id ? '!border-violet-400/50' : ''}`}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-semibold text-sm truncate">{t.subject}</span>
                  <Chip tone={TICKET_CHIP[t.status]}>{t.status_fa}</Chip>
                </div>
                <div className="text-[11px] text-slate-500">
                  {t.requester ? `درخواست‌کننده: ${t.requester} · ` : ''}شناسه {t.id}
                </div>
              </button>
            ))}
          </div>
          <div className="lg:col-span-2">
            {selected ? <Thread id={selected} isStaff={data.is_staff} reload={load} /> : (
              <div className="glass p-6 h-full flex items-center justify-center text-slate-500 text-sm">یک درخواست را انتخاب کنید.</div>
            )}
          </div>
        </div>
      )}

      {createOpen && <CreateModal onClose={() => { setCreateOpen(false); load() }} />}
    </div>
  )
}

function Thread({ id, isStaff, reload }) {
  const [thread, setThread] = useState(null)
  const [body, setBody] = useState('')
  const [err, setErr] = useState('')

  const load = () => api.get(`/tickets/${id}`).then(({ data }) => setThread(data)).catch((e) => setErr(errMsg(e)))
  useEffect(() => { setThread(null); load() }, [id])

  const send = async () => {
    if (!body.trim()) return
    try { await api.post(`/tickets/${id}/messages`, { body }); setBody(''); load() } catch (e) { setErr(errMsg(e)) }
  }
  const transition = async (st) => {
    try { await api.post(`/tickets/${id}/status`, { status: st }); load(); reload() } catch (e) { alert(errMsg(e)) }
  }

  if (!thread) return <Spinner />
  const t = thread.ticket
  const stepIdx = STEPS.indexOf(t.status === 'needs_info' ? 'under_review' : t.status)

  return (
    <div className="glass p-5 fade-up">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h2 className="font-bold">{t.subject}</h2>
        <Chip tone={TICKET_CHIP[t.status]}>{t.status_fa}</Chip>
      </div>

      {/* نوار وضعیت */}
      <div className="flex items-center gap-1 mb-5">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center flex-1 last:flex-none">
            <div className={`flex items-center gap-1.5 text-[11px] ${i <= stepIdx ? 'text-violet-300' : 'text-slate-600'}`}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center border text-[10px] ${i <= stepIdx ? 'bg-violet-500/25 border-violet-400/50' : 'border-white/10'}`}>{i + 1}</span>
              {TICKET_FA[s]}
            </div>
            {i < STEPS.length - 1 && <div className={`h-px flex-1 mx-2 ${i < stepIdx ? 'bg-violet-400/50' : 'bg-white/10'}`} />}
          </div>
        ))}
      </div>

      {/* پیام‌ها */}
      <div className="space-y-3 max-h-96 overflow-y-auto pl-1 mb-4">
        {thread.messages.map((m) => (
          <div key={m.id} className={`flex ${m.is_staff ? 'justify-start' : 'justify-end'}`}>
            <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-6 border ${m.is_staff
              ? 'bg-cyan-500/10 border-cyan-400/25 rounded-tl-md'
              : 'bg-violet-600/15 border-violet-400/25 rounded-tr-md'}`}>
              <div className="text-[10px] text-slate-400 mb-0.5">{m.author} {m.is_staff ? '· کارشناس' : ''}</div>
              {m.body}
            </div>
          </div>
        ))}
      </div>

      {err && <div className="text-sm text-rose-300 mb-2">{err}</div>}

      {t.status !== 'closed' ? (
        <div className="flex gap-2">
          <textarea className="textarea resize-none" rows={2} placeholder="پیام خود را بنویسید…"
            value={body} onChange={(e) => setBody(e.target.value)} />
          <button className="btn btn-primary shrink-0 self-end" onClick={send} disabled={!body.trim()}><Send size={15} /></button>
        </div>
      ) : (
        <p className="text-xs text-slate-500">این درخواست بسته شده است.</p>
      )}

      {isStaff && t.allowed_transitions?.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-white/[.07]">
          <span className="text-xs text-slate-500 self-center">گذار وضعیت:</span>
          {t.allowed_transitions.map((s) => (
            <button key={s} className="btn btn-ghost btn-sm" onClick={() => transition(s)}>{TICKET_FA[s] || s}</button>
          ))}
        </div>
      )}
    </div>
  )
}

function CreateModal({ onClose }) {
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try { await api.post('/tickets', { subject, body }); onClose() } catch (e2) { setErr(errMsg(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal open onClose={onClose} title="درخواست جدید از کارشناس">
      <form onSubmit={submit} className="space-y-3">
        <div><label className="lbl">موضوع *</label><input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} required /></div>
        <div><label className="lbl">توضیح</label><textarea className="textarea" rows={4} value={body} onChange={(e) => setBody(e.target.value)} /></div>
        {err && <div className="text-sm text-rose-300">{err}</div>}
        <button className="btn btn-primary w-full" disabled={busy || !subject.trim()}>ثبت درخواست</button>
      </form>
    </Modal>
  )
}
