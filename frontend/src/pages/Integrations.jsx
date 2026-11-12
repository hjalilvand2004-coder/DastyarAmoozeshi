import { useEffect, useState } from 'react'
import { Activity, Blocks, Code2, Copy, Eye, EyeOff, KeyRound, Plus, ScrollText, Power } from 'lucide-react'
import api, { errMsg } from '../api'
import { Chip, Modal, PageHead, Spinner, EmptyState } from '../ui'
import { jalaliStr } from '../jalali'

// پشتیبانی از پیش‌نمایش گیت‌وی (پارامتر XTransformPort) — در استقرار واقعی خالی است
const GATEWAY = (() => { try { return new URLSearchParams(window.location.search).get('XTransformPort') } catch { return null } })()
const ORIGIN = window.location.origin

const WIDGET_SNIPPET = (key, base) =>
  `<script src="${base}/api/v1/integration/widget.js"\n        data-key="${key}"\n        data-url="${base}"\n        data-title="دستیار آیین‌نامه‌ای"\n        data-position="left"></script>`

export default function Integrations() {
  const [systems, setSystems] = useState(null)
  const [scopes, setScopes] = useState([])
  const [err, setErr] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [newKey, setNewKey] = useState(null)
  const [logsFor, setLogsFor] = useState(null)
  const [snippetFor, setSnippetFor] = useState(null)

  const load = () => api.get('/integrations').then(({ data }) => setSystems(data.systems)).catch((e) => setErr(errMsg(e)))
  useEffect(() => {
    load()
    api.get('/integrations/scopes').then(({ data }) => setScopes(data.scopes)).catch(() => {})
  }, [])

  const toggle = async (s) => {
    try { await api.post(`/integrations/${s.id}/active`, { active: !s.active }); load() } catch (e) { alert(errMsg(e)) }
  }
  const rotate = async (s) => {
    if (!window.confirm(`کلید «${s.name}» عوض شود؟ کلید قبلی بلافاصله باطل می‌شود.`)) return
    try {
      const { data } = await api.post(`/integrations/${s.id}/rotate`)
      setNewKey({ key: data.api_key, name: s.name }); load()
    } catch (e) { alert(errMsg(e)) }
  }

  return (
    <div>
      <PageHead
        title="سامانه‌های متصل"
        sub="هر سامانه دیگر (پژوهشیار، برنامه‌ریز، پرتال، اپ موبایل، ...) با کلید API از سرویس‌های این دستیار استفاده می‌کند یا چت‌بات آن را با یک خط کد نصب می‌کند."
        actions={<button className="btn btn-primary btn-sm" onClick={() => setAddOpen(true)}><Plus size={14} /> سامانه متصل جدید</button>}
      />

      <div className="glass p-4 mb-5 flex items-start gap-3 !border-violet-400/25 !bg-violet-400/[.05] text-sm fade-up">
        <Blocks size={18} className="text-violet-300 shrink-0 mt-0.5" />
        <div className="text-slate-300 leading-6">
          <b className="text-violet-200">سه راه استفاده از این دستیار در سامانه‌های دیگر:</b>
          <span className="block mt-1 text-slate-400 text-[13px] leading-6">
            ۱) <b className="text-slate-200">پرسش مستند</b> — سامانه میزبان با <code className="text-cyan-300">X-API-Key</code> به <code className="text-cyan-300">POST /api/v1/integration/v1/ask</code> پرسش می‌فرستد و پاسخ سه‌لایه با استناد می‌گیرد.
            ۲) <b className="text-slate-200">خدمات منفرد</b> — جست‌وجوی آیین‌نامه، ارزیابی قاعده، مهلت‌ها، فرایندها و ثبت تیکت (هرکدام با اسکوپ جداگانه).
            ۳) <b className="text-slate-200">چت‌بات نصب‌شدنی</b> — یک تگ <code className="text-cyan-300">&lt;script&gt;</code> در صفحه میزبان، دستیار را با ظاهر شیشه‌ای و پاسخ‌های مستند در همان صفحه حاضر می‌کند.
          </span>
        </div>
      </div>

      {err && <div className="text-sm text-rose-300 mb-3">{err}</div>}
      {!systems ? <Spinner /> : systems.length === 0 ? (
        <EmptyState icon={Blocks} title="هنوز سامانه‌ای متصل نشده" sub="با دکمه بالا اولین سامانه متصل را بسازید." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {systems.map((s) => <SystemCard key={s.id} s={s} onToggle={() => toggle(s)} onRotate={() => rotate(s)}
            onLogs={() => setLogsFor(s)} onSnippet={() => setSnippetFor(s)} />)}
        </div>
      )}

      {addOpen && <AddSystemModal scopes={scopes} onClose={() => { setAddOpen(false); load() }} onCreated={setNewKey} />}
      {newKey && <KeyModal item={newKey} onClose={() => setNewKey(null)} />}
      {logsFor && <LogsModal system={logsFor} onClose={() => setLogsFor(null)} />}
      {snippetFor && <SnippetModal system={snippetFor} onClose={() => setSnippetFor(null)} />}
    </div>
  )
}

function SystemCard({ s, onToggle, onRotate, onLogs, onSnippet }) {
  const [showKey, setShowKey] = useState(false)
  return (
    <div className="glass card-hover p-5 flex flex-col gap-3 fade-up">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-bold text-slate-100 truncate">{s.name}</div>
          <code className="text-[11px] text-cyan-300" dir="ltr">{s.code}</code>
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <Chip tone={s.active ? 'chip-emerald' : 'chip-rose'}>{s.active ? 'فعال' : 'غیرفعال'}</Chip>
          {s.is_widget && <Chip tone="chip-sky">ویجت</Chip>}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {s.scopes.map((sc) => <Chip key={sc} tone="chip-violet">{sc}</Chip>)}
      </div>

      <div className="text-[11.5px] text-slate-400 space-y-1 leading-5">
        <div className="flex justify-between"><span>فراخوانی‌ها</span><span className="text-slate-200 font-semibold">{s.call_count?.toLocaleString?.() || 0}</span></div>
        <div className="flex justify-between"><span>سقف در ساعت</span><span className="text-slate-200">{s.rate_limit_per_hour}</span></div>
        <div className="flex justify-between"><span>آخرین فراخوانی</span><span className="text-slate-200">{s.last_used_at ? jalaliStr(s.last_used_at.slice(0, 10)) : '—'}</span></div>
      </div>

      <div className="divider" />

      <div className="flex items-center gap-2">
        <code className="text-[11px] text-slate-400 flex-1 truncate" dir="ltr">{showKey ? s.api_key : s.api_key_masked}</code>
        <button className="btn btn-ghost btn-sm !px-2" title={showKey ? 'پنهان' : 'نمایش کلید'} onClick={() => setShowKey(!showKey)}>
          {showKey ? <EyeOff size={13} /> : <Eye size={13} />}
        </button>
        <button className="btn btn-ghost btn-sm !px-2" title="کپی کلید"
          onClick={() => { navigator.clipboard.writeText(s.api_key); alert('کلید کپی شد.') }}>
          <Copy size={13} />
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <button className="btn btn-ghost btn-sm" onClick={onSnippet}><Code2 size={13} /> کد نصب ویجت</button>
        <button className="btn btn-ghost btn-sm" onClick={onLogs}><ScrollText size={13} /> لاگ</button>
        <button className="btn btn-ghost btn-sm" onClick={onRotate} title="چرخش کلید"><KeyRound size={13} /></button>
        <button className={`btn btn-sm ${s.active ? 'btn-danger' : 'btn-ghost'}`} onClick={onToggle}>
          <Power size={13} /> {s.active ? 'غیرفعال' : 'فعال'}
        </button>
      </div>
    </div>
  )
}

function AddSystemModal({ scopes, onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', code: '', rate_limit_per_hour: 120, is_widget: false, contact: '' })
  const [picked, setPicked] = useState(['ask', 'regulations.read', 'deadlines.read', 'processes.read'])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try {
      const { data } = await api.post('/integrations', { ...form, scopes: picked })
      onCreated({ key: data.api_key, name: form.name })
      onClose()
    } catch (e2) { setErr(errMsg(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal open onClose={onClose} title="سامانه متصل جدید">
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="lbl">نام سامانه *</label><input className="input" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="مثلاً سامانه پژوهشیار" required /></div>
          <div><label className="lbl">شناسه (لاتین) *</label><input className="input" dir="ltr" value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))} placeholder="pajooheshyar" required /></div>
        </div>
        <div>
          <label className="lbl">اسکوپ‌ها (خدمات مجاز)</label>
          <div className="grid sm:grid-cols-2 gap-1.5">
            {scopes.map((s) => (
              <label key={s.scope} className="flex items-start gap-2 glass !rounded-xl p-2.5 cursor-pointer text-xs leading-5">
                <input type="checkbox" className="mt-1 accent-violet-500" checked={picked.includes(s.scope)}
                  onChange={(e) => setPicked((p) => e.target.checked ? [...p, s.scope] : p.filter((x) => x !== s.scope))} />
                <span><b className="text-cyan-300" dir="ltr">{s.scope}</b><br /><span className="text-slate-400">{s.description}</span></span>
              </label>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="lbl">سقف فراخوانی در ساعت</label><input className="input" dir="ltr" type="number" min="1" value={form.rate_limit_per_hour} onChange={(e) => setForm((f) => ({ ...f, rate_limit_per_hour: Number(e.target.value) }))} /></div>
          <div><label className="lbl">نوع</label>
            <select className="select" value={form.is_widget ? 'widget' : 'service'} onChange={(e) => setForm((f) => ({ ...f, is_widget: e.target.value === 'widget' }))}>
              <option value="service">سرویس سرور-به-سرور</option>
              <option value="widget">ویجت چت‌بات (صفحه میزبان)</option>
            </select>
          </div>
        </div>
        <div><label className="lbl">راه تماس (اختیاری)</label><input className="input" value={form.contact} onChange={(e) => setForm((f) => ({ ...f, contact: e.target.value }))} /></div>
        {err && <div className="text-sm text-rose-300">{err}</div>}
        <button className="btn btn-primary w-full" disabled={busy}>ایجاد و دریافت کلید</button>
      </form>
    </Modal>
  )
}

function KeyModal({ item, onClose }) {
  const [copied, setCopied] = useState(false)
  return (
    <Modal open onClose={onClose} title={`کلید «${item.name}»`}>
      <div className="space-y-3">
        <p className="text-xs text-amber-200 leading-6 bg-amber-400/[.07] border border-amber-400/30 rounded-xl p-3">
          این کلید فقط همین یک بار کامل نمایش داده می‌شود. آن را همین حالا کپی و نزد سامانه میزبان ذخیره کنید.
        </p>
        <div className="flex gap-2">
          <input className="input text-cyan-300" dir="ltr" readOnly value={item.key} onFocus={(e) => e.target.select()} />
          <button className="btn btn-primary shrink-0" onClick={() => { navigator.clipboard.writeText(item.key); setCopied(true) }}>
            <Copy size={14} /> {copied ? 'کپی شد' : 'کپی'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

function LogsModal({ system, onClose }) {
  const [logs, setLogs] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.get(`/integrations/${system.id}/logs`, { params: { limit: 100 } })
      .then(({ data }) => setLogs(data.logs)).catch((e) => setErr(errMsg(e)))
  }, [system.id])
  return (
    <Modal open onClose={onClose} title={`فراخوانی‌های «${system.name}»`} wide>
      {err && <div className="text-sm text-rose-300">{err}</div>}
      {!logs ? <Spinner /> : logs.length === 0 ? (
        <EmptyState icon={Activity} title="هنوز فراخوانی ثبت نشده" sub="با اولین استفاده سامانه میزبان، اینجا لاگ می‌بینید." />
      ) : (
        <div className="glass overflow-x-auto p-1 max-h-[55vh] overflow-y-auto">
          <table className="tbl">
            <thead><tr><th>زمان</th><th>مسیر</th><th>وضعیت</th><th>طول کشیدن</th><th>IP</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="text-xs text-slate-500 whitespace-nowrap" dir="ltr">{l.created_at?.slice(0, 19)}</td>
                  <td className="text-[11px] text-cyan-300" dir="ltr">{l.endpoint}</td>
                  <td><Chip tone={l.status_code < 400 ? 'chip-emerald' : l.status_code < 500 ? 'chip-amber' : 'chip-rose'}>{l.status_code}</Chip></td>
                  <td className="text-xs text-slate-400">{l.duration_ms}ms</td>
                  <td className="text-xs text-slate-500" dir="ltr">{l.ip || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  )
}

function SnippetModal({ system, onClose }) {
  const base = ORIGIN
  const snippet = WIDGET_SNIPPET(system.api_key, base)
  const demoUrl = `${base}/integration-demo?key=${encodeURIComponent(system.api_key)}${GATEWAY ? `&XTransformPort=${GATEWAY}` : ''}`
  return (
    <Modal open onClose={onClose} title={`نصب دستیار در «${system.name}»`} wide>
      <div className="space-y-4">
        <p className="text-xs text-slate-400 leading-6">
          این تگ را در انتهای <code className="text-cyan-300">&lt;body&gt;</code> صفحات سامانه میزبان بگذارید؛
          دکمه شناور و گفت‌وگوی مستند با همان قالب شیشه‌ای سامانه شما ظاهر می‌شود.
          اگر سامانه میزبان اطلاعات دانشجو را دارد، با متغیر <code className="text-cyan-300">window.DastyarStudent</code> (شیء JSON) پاسخ‌ها شخصی‌سازی می‌شود.
        </p>
        <pre className="glass p-4 text-[11.5px] leading-6 text-cyan-200 overflow-x-auto" dir="ltr">{snippet}</pre>
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-primary btn-sm" onClick={() => { navigator.clipboard.writeText(snippet); alert('کد کپی شد.') }}>
            <Copy size={13} /> کپی کد نصب
          </button>
          <a className="btn btn-ghost btn-sm" href={demoUrl} target="_blank" rel="noreferrer">
            <Activity size={13} /> بازکردن صفحه آزمایش (شبیه میزبانی در سامانه دیگر)
          </a>
        </div>
        <p className="text-[11px] text-slate-500 leading-6">
          نکته امنیتی: کلید ویجت در صفحه میزبان دیده می‌شود؛ برای ویجت‌ها سقف نرخ جداگانه بگذارید و اسکوپ را فقط «ask» نگه دارید. در محیط عملیاتی، فیلتر دامنه (Referer) در فاز بعد فعال می‌شود (docs/10-integration.md).
        </p>
      </div>
    </Modal>
  )
}
