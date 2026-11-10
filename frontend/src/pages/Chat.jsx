import { useEffect, useRef, useState } from 'react'
import { EyeOff, LifeBuoy, MessageSquareText, Plus, Send, ShieldQuestion } from 'lucide-react'
import { Link } from 'react-router-dom'
import api, { errMsg } from '../api'
import { Chip, EmptyState, RULE_STATE_CHIP, RULE_STATE_FA, Spinner } from '../ui'

const SUGGESTIONS = ['شرایط ثبت‌نام کارورزی چیست؟', 'سقف واحد دانشجوی مشروط چقدر است؟',
  'حذف و اضافه چگونه انجام می‌شود؟', 'شرایط انتقالی چیست؟']

export default function Chat() {
  const [sessions, setSessions] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [includeRetired, setIncludeRetired] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const endRef = useRef(null)

  useEffect(() => {
    api.get('/chat/sessions').then(({ data }) => setSessions(data.sessions)).catch(() => {})
      .finally(() => setLoadingHistory(false))
  }, [])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  const newSession = () => { setSessionId(null); setMessages([]) }

  const openSession = async (id) => {
    setSessionId(id); setErr('')
    const { data } = await api.get(`/chat/sessions/${id}/messages`)
    setMessages(data.messages.map((m) => ({
      role: m.role, content: m.content,
      answer: m.role === 'assistant' ? { sources: m.meta?.sources || [], warnings: m.meta?.warnings || [], status_rows: m.meta?.status_rows || [] } : null,
    })))
  }

  const send = async (q) => {
    const question = (q ?? input).trim()
    if (!question || busy) return
    setInput(''); setErr(''); setBusy(true)
    setMessages((m) => [...m, { role: 'user', content: question }])
    try {
      const { data } = await api.post('/chat/ask', { question, session_id: sessionId, include_retired: includeRetired })
      const ans = data.answer
      setSessionId(ans.session_id)
      setMessages((m) => [...m, { role: 'assistant', content: ans.short || ans.note || '—', answer: ans }])
      api.get('/chat/sessions').then(({ data: s }) => setSessions(s.sessions)).catch(() => {})
    } catch (e) {
      setErr(errMsg(e))
      setMessages((m) => m.slice(0, -1))
    } finally { setBusy(false) }
  }

  return (
    <div className="fade-up">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-100">دستیار مستند آیین‌نامه</h1>
          <p className="text-sm text-slate-500 mt-1">پاسخ سه‌لایه: متن رسمی سند ← توضیح ساده ← وضعیت شخصی شما. همه پاسخ‌ها استناد واقعی دارند.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none">
            <input type="checkbox" checked={includeRetired} onChange={(e) => setIncludeRetired(e.target.checked)}
              className="accent-violet-500 w-3.5 h-3.5" />
            نمایش نسخه‌های ملغی (فقط برای مقایسه)
          </label>
          <button className="btn btn-ghost btn-sm" onClick={newSession}><Plus size={14} /> گفت‌وگوی جدید</button>
        </div>
      </div>

      {/* تاریخچه گفت‌وگوها */}
      {sessions.length > 0 && (
        <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
          {sessions.slice(0, 8).map((s) => (
            <button key={s.id} onClick={() => openSession(s.id)}
              className={`btn btn-sm shrink-0 ${sessionId === s.id ? 'btn-primary' : 'btn-ghost'}`}>
              <MessageSquareText size={13} /> {s.title?.slice(0, 26) || `گفت‌وگوی ${s.id}`}
            </button>
          ))}
        </div>
      )}

      <div className="glass overflow-hidden flex flex-col" style={{ minHeight: '58vh' }}>
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {loadingHistory ? <Spinner /> : messages.length === 0 ? (
            <div className="pt-6">
              <EmptyState icon={ShieldQuestion} title="چه چیزی می‌خواهید بدانید؟"
                sub="پرسش خود را بنویسید. اگر مطلب مرتبطی در اسناد نباشد، صادقانه اعلام می‌شود و ساختگی پاسخ نمی‌دهیم." />
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="btn btn-ghost btn-sm" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => m.role === 'user'
              ? <UserMsg key={i} text={m.content} />
              : <AssistantMsg key={i} answer={m.answer} content={m.content} />)
          )}
          {busy && (
            <div className="flex items-center gap-1.5 px-2">
              <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
            </div>
          )}
          <div ref={endRef} />
        </div>

        {err && <div className="mx-4 mb-2 text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-xl px-3 py-2">{err}</div>}

        <div className="p-3 md:p-4 border-t border-white/[.07]">
          <div className="flex gap-2">
            <textarea className="textarea resize-none" rows={1} placeholder="پرسش خود را بنویسید…"
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
            <button className="btn btn-primary shrink-0" disabled={busy || !input.trim()} onClick={() => send()}>
              <Send size={16} /> ارسال
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function UserMsg({ text }) {
  return (
    <div className="flex justify-start msg-in">
      <div className="max-w-[80%] bg-gradient-to-bl from-violet-600/35 to-indigo-600/20 border border-violet-500/30 rounded-2xl rounded-tr-md px-4 py-2.5 text-sm leading-6">
        {text}
      </div>
    </div>
  )
}

function AssistantMsg({ answer, content }) {
  if (!answer) return null
  return (
    <div className="flex justify-end msg-in">
      <div className="w-full max-w-[95%] md:max-w-[88%]">
        {answer.warnings?.map((w, i) => (
          <div key={i} className="mb-2 rounded-xl border border-amber-400/30 bg-amber-400/[.07] px-3.5 py-2.5 text-xs leading-6 text-amber-200/90">
            ⚠️ {w}
          </div>
        ))}

        {answer.no_result ? (
          <div className="glass p-4">
            <p className="text-sm leading-7 text-slate-300">{answer.note || 'موردی یافت نشد.'}</p>
            <Link to="/tickets" className="btn btn-ghost btn-sm mt-3"><LifeBuoy size={14} /> پرسش از کارشناس آموزش</Link>
          </div>
        ) : (
          <div className="glass p-4 md:p-5">
            {/* لایه ۱: متن رسمی */}
            {answer.sources?.length > 0 && (
              <div className="layer layer-official">
                <div className="layer-title text-emerald-300"><EyeOff size={0} className="hidden" />📜 لایه ۱ — متن رسمی سند (عیناً)</div>
                {answer.sources.map((s) => (
                  <div key={s.ref} className="bg-black/20 rounded-xl p-3 mb-2 last:mb-0">
                    <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                      <Chip tone="chip-violet">{s.ref}</Chip>
                      <span className="text-xs font-bold text-slate-200">{s.doc_title}</span>
                      <Chip tone="chip-slate">نسخه {s.version_no}</Chip>
                      {s.clause_ref && <Chip tone="chip-sky">{s.clause_ref}</Chip>}
                      {s.page_no && <Chip tone="chip-slate">صفحه {s.page_no}</Chip>}
                      <Chip tone={s.official ? 'chip-emerald' : 'chip-amber'}>{s.official ? 'رسمی' : 'نمونه و غیررسمی'}</Chip>
                      <Chip tone={STATUS_CHIP2[s.status]}>{STATUS_FA2[s.status]}</Chip>
                    </div>
                    <p className="text-[13px] leading-7 text-slate-200 whitespace-pre-wrap">{s.excerpt}</p>
                    {s.url && <a href={s.url} target="_blank" rel="noreferrer" className="text-[11px] text-cyan-300 hover:underline mt-1 inline-block">{s.url}</a>}
                  </div>
                ))}
              </div>
            )}

            {/* لایه ۲: توضیح ساده */}
            <div className="layer layer-explain">
              <div className="layer-title text-slate-300">💡 لایه ۲ — توضیح ساده</div>
              <p className="text-sm leading-7 text-slate-200">{content}</p>
              {answer.conditions?.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {answer.conditions.map((c, i) => (
                    <li key={i} className="text-[13px] leading-6 text-slate-300 flex gap-1.5">
                      <span className="text-violet-300 mt-1">▸</span><span>{c}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* لایه ۳: وضعیت شخصی + اقدام */}
            {answer.status_rows?.length > 0 && (
              <div className="layer layer-action">
                <div className="layer-title text-violet-300">🎯 لایه ۳ — وضعیت شخصی شما (ارزیابی قطعی)</div>
                <ul className="space-y-1.5">
                  {answer.status_rows.map((r, i) => (
                    <li key={i} className="flex flex-wrap items-center gap-2 text-[13px]">
                      <span className="font-semibold text-slate-200">{r.title}:</span>
                      <Chip tone={RULE_STATE_CHIP[r.state]}>{r.state_fa}</Chip>
                      {r.missing?.length > 0 && <span className="text-[11px] text-amber-300/80">ناقص: {r.missing.join('، ')}</span>}
                      {r.detail && <span className="text-slate-400 w-full leading-6">{r.detail}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {answer.next_steps?.length > 0 && (
              <div className="layer layer-explain">
                <div className="layer-title text-cyan-300">🚀 اقدام بعدی پیشنهادی</div>
                <ol className="space-y-1">
                  {answer.next_steps.map((s, i) => (
                    <li key={i} className="text-[13px] leading-6 text-slate-300">{i + 1}. {s}</li>
                  ))}
                </ol>
              </div>
            )}

            {answer.confirmations?.length > 0 && (
              <div className="mt-3 rounded-xl border border-amber-400/25 bg-amber-400/[.05] p-3">
                <div className="text-xs font-bold text-amber-200 mb-1.5">موارد نیازمند تأیید کارشناس آموزش:</div>
                <ul className="space-y-1">
                  {answer.confirmations.map((c, i) => <li key={i} className="text-[12px] leading-6 text-amber-100/80">• {c}</li>)}
                </ul>
                <Link to="/tickets" className="btn btn-ghost btn-sm mt-2"><LifeBuoy size={13} /> ثبت درخواست</Link>
              </div>
            )}

            <p className="text-[11px] text-slate-500 mt-3 leading-5">
              موتور تولید پاسخ: {answer.provider_name} · این پاسخ راهنمای خودکار است و جایگزین حکم رسمی دانشگاه نیست.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

const STATUS_FA2 = { draft: 'پیش‌نویس', in_review: 'در حال بررسی', approved: 'تأییدشده', published: 'منتشرشده (معتبر)', retired: 'ملغی‌شده' }
const STATUS_CHIP2 = { draft: 'chip-slate', in_review: 'chip-sky', approved: 'chip-violet', published: 'chip-emerald', retired: 'chip-rose' }
