import { useEffect, useState } from 'react'
import { FlaskConical, Plus, ShieldCheck } from 'lucide-react'
import api, { errMsg } from '../api'
import { useAuth } from '../auth'
import { Chip, EmptyState, Modal, PageHead, RULE_STATE_CHIP, RULE_STATE_FA, Spinner } from '../ui'

const RULE_STATUS_FA = { draft: 'پیش‌نویس', approved: 'تأییدشده (فعال)', disabled: 'غیرفعال' }
const RULE_STATUS_CHIP = { draft: 'chip-slate', approved: 'chip-emerald', disabled: 'chip-rose' }

export default function Rules() {
  const { can } = useAuth()
  const isExpert = can('rules.evaluate')
  const [rules, setRules] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [evalRule, setEvalRule] = useState(null)
  const [err, setErr] = useState('')

  const load = () => api.get('/rules').then(({ data }) => setRules(data.rules)).catch((e) => setErr(errMsg(e)))
  useEffect(() => { load() }, [])

  return (
    <div>
      <PageHead title="قواعد ارزیابی قطعی" sub="قواعد قابل‌محاسبه (معدل، واحدها، سال ورود و …) جدا از مدل زبانی و فقط پس از تأیید انسانی فعال می‌شوند. خروجی هر ارزیابی چهار حالته است."
        actions={can('regs.create') && (
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}><Plus size={15} /> قاعده جدید</button>
        )} />

      {err && <div className="text-sm text-rose-300 mb-3">{err}</div>}
      {!rules ? <Spinner /> : rules.length === 0 ? (
        <EmptyState icon={FlaskConical} title="قاعده‌ای ثبت نشده" />
      ) : (
        <div className="glass overflow-x-auto p-1">
          <table className="tbl">
            <thead><tr><th>عنوان قاعده</th><th>منبع</th><th>شرط</th><th>وضعیت</th><th>اقدام</th></tr></thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td className="font-medium">{r.title}</td>
                  <td className="text-xs text-slate-500">{r.source_clause || '—'}</td>
                  <td><code dir="ltr" className="text-[11px] text-cyan-300/90">{r.cond_json}</code></td>
                  <td><Chip tone={RULE_STATUS_CHIP[r.status]}>{RULE_STATUS_FA[r.status] || r.status}</Chip></td>
                  <td>
                    <div className="flex gap-1.5">
                      {isExpert && r.status === 'approved' && (
                        <button className="btn btn-ghost btn-sm" onClick={() => setEvalRule(r)}>ارزیابی</button>
                      )}
                      {can('rules.approve') && r.status === 'draft' && (
                        <button className="btn btn-primary btn-sm" onClick={async () => {
                          try { await api.post(`/rules/${r.id}/approve`); load() } catch (e) { alert(errMsg(e)) }
                        }}><ShieldCheck size={13} /> تأیید</button>
                      )}
                      {can('rules.approve') && r.status === 'approved' && (
                        <button className="btn btn-danger btn-sm" onClick={async () => {
                          try { await api.post(`/rules/${r.id}/status`, { status: 'disabled' }); load() } catch (e) { alert(errMsg(e)) }
                        }}>غیرفعال</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createOpen && <CreateModal onClose={() => { setCreateOpen(false); load() }} />}
      {evalRule && <EvalModal rule={evalRule} onClose={() => setEvalRule(null)} />}
    </div>
  )
}

function CreateModal({ onClose }) {
  const [title, setTitle] = useState('')
  const [field, setField] = useState('gpa')
  const [op, setOp] = useState('>=')
  const [value, setValue] = useState('')
  const [sourceDoc, setSourceDoc] = useState('')
  const [sourceClause, setSourceClause] = useState('')
  const [docs, setDocs] = useState([])
  const [reviewFields, setReviewFields] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { api.get('/regulations').then(({ data }) => setDocs(data.documents)).catch(() => {}) }, [])

  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try {
      await api.post('/rules', {
        title,
        cond: { attr: field, op, value: isNaN(Number(value)) ? value : Number(value) },
        source_document_id: sourceDoc ? Number(sourceDoc) : null,
        source_clause: sourceClause,
        review_fields: reviewFields ? reviewFields.split(',').map((s) => s.trim()).filter(Boolean) : [],
      })
      onClose()
    } catch (e2) { setErr(errMsg(e2)) } finally { setBusy(false) }
  }

  return (
    <Modal open onClose={onClose} title="تعریف قاعده جدید">
      <form onSubmit={submit} className="space-y-3">
        <div><label className="lbl">عنوان *</label><input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required /></div>
        <div className="grid grid-cols-3 gap-2">
          <div><label className="lbl">فیلد</label>
            <select className="select" value={field} onChange={(e) => setField(e.target.value)}>
              {['gpa', 'entry_year', 'passed_credits', 'level', 'major', 'on_probation'].map((f) => <option key={f}>{f}</option>)}
            </select>
          </div>
          <div><label className="lbl">عملگر</label>
            <select className="select" value={op} onChange={(e) => setOp(e.target.value)}>
              {['>=', '<=', '>', '<', '==', '!=', 'in', 'not_in'].map((o) => <option key={o} dir="ltr">{o}</option>)}
            </select>
          </div>
          <div><label className="lbl">مقدار</label><input className="input" dir="ltr" value={value} onChange={(e) => setValue(e.target.value)} required /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="lbl">سند منبع</label>
            <select className="select" value={sourceDoc} onChange={(e) => setSourceDoc(e.target.value)}>
              <option value="">— بدون سند —</option>
              {docs.map((d) => <option key={d.id} value={d.id}>{d.title} (v{d.version_no})</option>)}
            </select>
          </div>
          <div><label className="lbl">ماده/بند منبع</label><input className="input" value={sourceClause} onChange={(e) => setSourceClause(e.target.value)} placeholder="مثلاً ماده ۱۲" /></div>
        </div>
        <div><label className="lbl">فیلدهای نیازمند تأیید رسمی (اختیاری، با کاما)</label>
          <input className="input" value={reviewFields} onChange={(e) => setReviewFields(e.target.value)} placeholder="مثلاً transcript_verified" />
        </div>
        {err && <div className="text-sm text-rose-300">{err}</div>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? 'در حال ثبت…' : 'ثبت قاعده (پیش‌نویس)'}</button>
        <p className="text-[11px] text-slate-500 leading-5">قاعده جدید «پیش‌نویس» است و تا تأیید تصویب‌کننده هیچ‌گاه در ارزیابی‌ها به‌کار نمی‌رود.</p>
      </form>
    </Modal>
  )
}

function EvalModal({ rule, onClose }) {
  const [students, setStudents] = useState([])
  const [sid, setSid] = useState('')
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/advisor/students').then(({ data }) => setStudents(data.students)).catch((e) => setErr(errMsg(e)))
  }, [])

  const run = async () => {
    setErr(''); setResult(null)
    try {
      const { data } = await api.post(`/rules/${rule.id}/evaluate/${sid}`)
      setResult(data)
    } catch (e) { setErr(errMsg(e)) }
  }

  return (
    <Modal open onClose={onClose} title={`ارزیابی: ${rule.title}`}>
      <div className="space-y-3">
        <div><label className="lbl">دانشجو</label>
          <select className="select" value={sid} onChange={(e) => setSid(e.target.value)}>
            <option value="">— انتخاب کنید —</option>
            {students.map((s) => <option key={s.id} value={s.id}>{s.full_name} — {s.major || '—'}</option>)}
          </select>
        </div>
        <button className="btn btn-primary w-full" disabled={!sid} onClick={run}>ارزیابی قطعی</button>
        {err && <div className="text-sm text-rose-300">{err}</div>}
        {result && (
          <div className="glass p-4 fade-up">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-slate-200">{result.title || rule.title}</span>
              <Chip tone={RULE_STATE_CHIP[result.status]}>{result.status_fa || RULE_STATE_FA[result.status]}</Chip>
            </div>
            {result.missing?.length > 0 && <p className="text-xs text-amber-300/80">اطلاعات ناقص: {result.missing.join('، ')}</p>}
            {result.details?.map((d, i) => <p key={i} className="text-xs text-slate-400 mt-1">{d}</p>)}
          </div>
        )}
      </div>
    </Modal>
  )
}
