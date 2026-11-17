import { useEffect, useState } from 'react'
import { KeyRound, ScrollText, Settings2, UserPlus, Users } from 'lucide-react'
import api, { errMsg } from '../api'
import { Chip, Modal, PageHead, Spinner } from '../ui'
import { jalaliStr } from '../jalali'

const TABS = [
  { id: 'users', label: 'کاربران', icon: Users },
  { id: 'settings', label: 'تنظیمات', icon: Settings2 },
  { id: 'audit', label: 'حسابرسی', icon: ScrollText },
]

const ROLES = [
  { id: 'student', label: 'دانشجو' },
  { id: 'expert', label: 'کارشناس آموزش' },
  { id: 'content_admin', label: 'مدیر محتوای آیین‌نامه' },
  { id: 'approver', label: 'تأییدکننده' },
  { id: 'system_admin', label: 'مدیر سیستم' },
]

export default function Admin() {
  const [tab, setTab] = useState('users')
  return (
    <div>
      <PageHead title="مدیریت سیستم" sub="کاربران، تنظیمات (مدل زبانی و ورود یکپارچه) و گزارش حسابرسی." />
      <div className="flex gap-2 mb-5">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`btn btn-sm ${tab === t.id ? 'btn-primary' : 'btn-ghost'}`}>
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>
      {tab === 'users' && <UsersTab />}
      {tab === 'settings' && <SettingsTab />}
      {tab === 'audit' && <AuditTab />}
    </div>
  )
}

function UsersTab() {
  const [users, setUsers] = useState(null)
  const [err, setErr] = useState('')
  const [addOpen, setAddOpen] = useState(false)

  const load = () => api.get('/admin/users').then(({ data }) => setUsers(data.users)).catch((e) => setErr(errMsg(e)))
  useEffect(() => { load() }, [])

  const toggle = async (u) => {
    try { await api.post(`/admin/users/${u.id}/active`, { active: !u.active }); load() } catch (e) { alert(errMsg(e)) }
  }
  const resetPwd = async (u) => {
    const p = window.prompt(`رمز جدید برای «${u.username}» (حداقل ۶ کاراکتر):`)
    if (!p) return
    try { await api.post(`/admin/users/${u.id}/password`, { password: p }); alert('رمز به‌روزرسانی شد.') } catch (e) { alert(errMsg(e)) }
  }

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button className="btn btn-primary btn-sm" onClick={() => setAddOpen(true)}><UserPlus size={14} /> کاربر جدید</button>
      </div>
      {err && <div className="text-sm text-rose-300">{err}</div>}
      {!users ? <Spinner /> : (
        <div className="glass overflow-x-auto p-1">
          <table className="tbl">
            <thead><tr><th>نام</th><th>نام کاربری</th><th>نقش</th><th>وضعیت</th><th>اقدام</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="font-medium">{u.full_name || '—'}</td>
                  <td><code className="text-xs text-cyan-300">{u.username}</code></td>
                  <td className="text-xs">{u.role_fa || u.role}</td>
                  <td><Chip tone={u.active ? 'chip-emerald' : 'chip-rose'}>{u.active ? 'فعال' : 'غیرفعال'}</Chip></td>
                  <td>
                    <div className="flex gap-1.5">
                      <button className="btn btn-ghost btn-sm" onClick={() => toggle(u)}>{u.active ? 'غیرفعال' : 'فعال'}</button>
                      <button className="btn btn-ghost btn-sm" onClick={() => resetPwd(u)}><KeyRound size={12} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {addOpen && <AddUserModal onClose={() => { setAddOpen(false); load() }} />}
    </div>
  )
}

function AddUserModal({ onClose }) {
  const [form, setForm] = useState({ username: '', password: '', full_name: '', role: 'student', student_id: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try {
      await api.post('/admin/users', { ...form, student_id: form.student_id ? Number(form.student_id) : null })
      onClose()
    } catch (e2) { setErr(errMsg(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal open onClose={onClose} title="ایجاد کاربر">
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="lbl">نام کاربری *</label><input className="input" dir="ltr" value={form.username} onChange={set('username')} required /></div>
          <div><label className="lbl">رمز عبور *</label><input className="input" dir="ltr" type="password" value={form.password} onChange={set('password')} required /></div>
        </div>
        <div><label className="lbl">نام کامل</label><input className="input" value={form.full_name} onChange={set('full_name')} /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="lbl">نقش</label>
            <select className="select" value={form.role} onChange={set('role')}>
              {ROLES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>
          </div>
          <div><label className="lbl">شناسه دانشجو (اختیاری)</label><input className="input" dir="ltr" value={form.student_id} onChange={set('student_id')} /></div>
        </div>
        {err && <div className="text-sm text-rose-300">{err}</div>}
        <button className="btn btn-primary w-full" disabled={busy}>ایجاد</button>
      </form>
    </Modal>
  )
}

function SettingsTab() {
  const [st, setSt] = useState(null)
  const [draft, setDraft] = useState({})
  const [saved, setSaved] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/admin/settings').then(({ data }) => setSt(data.settings)).catch((e) => setErr(errMsg(e)))
  }, [])

  const save = async (key) => {
    const value = draft[key]
    if (value === undefined) return
    try {
      await api.post('/admin/settings', { key, value })
      setSaved(key); setDraft((d) => { const n = { ...d }; delete n[key]; return n })
      const { data } = await api.get('/admin/settings'); setSt(data.settings)
      setTimeout(() => setSaved(''), 2000)
    } catch (e) { alert(errMsg(e)) }
  }

  if (err) return <div className="text-sm text-rose-300">{err}</div>
  if (!st) return <Spinner />

  const LABELS = {
    llm_provider: 'ارائه‌دهنده مدل زبانی (auto/template)',
    llm_base_url: 'آدرس سرویس مدل زبانی (سازگار با OpenAI)',
    llm_api_key: 'کلید مدل زبانی (مخفی)',
    llm_model: 'نام مدل',
    rate_limit_chat_per_hour: 'حد پرسش در ساعت (هر کاربر)',
    search_max_chunks: 'حداکثر تکه‌های استنادی هر پاسخ',
    grad_required_credits: 'واحد لازم برای فارغ‌التحصیلی',
    public_base_url: 'آدرس عمومی سامانه (مبنای ورود یکپارچه) — مثل http://188.212.96.235:8091',
    sso_oidc_issuer: 'آدرس پرتال SSO سازمان (مثل http://188.212.96.235:8086)',
    sso_oidc_client_id: 'شناسه سرویس‌گیرنده در پرتال SSO (مثل amoozeshyar360)',
    sso_oidc_client_secret: 'رمز سرویس‌گیرنده SSO (مخفی — کلاینت عمومی خالی بماند)',
    sso_oidc_scope: 'اسکوپ‌های SSO (پیش‌فرض: openid profile)',
    sso_app_key: 'کلید سامانه در پرتال SSO (مبنای نگاشت نقش‌ها مثل amoozeshyar.admin)',
    sso_hub_secret: 'رمز مشترک توکن HS256 پرتال (اختیاری، مخفی)',
  }
  const SECRET = ['llm_api_key', 'sso_oidc_client_secret', 'sso_hub_secret']
  const entryUrl = (st.public_base_url || '').replace(/\/+$/, '') + '/api/v1/auth/sso/university/entry'

  return (
    <div className="space-y-3 max-w-3xl">
      {st.public_base_url && st.sso_oidc_issuer && (
        <div className="glass p-4 border border-violet-500/30">
          <div className="text-sm font-bold text-violet-200 mb-1.5">آدرس ورود برای ثبت در پرتال SSO سازمانی</div>
          <code dir="ltr" className="block text-xs bg-black/30 rounded-lg px-3 py-2 text-cyan-300 break-all">{entryUrl}</code>
          <p className="text-[11px] text-slate-400 leading-6 mt-2">
            این آدرس را در «مدیریت سامانه‌ها» پرتال SSO در فیلد «آدرس ورود (نقطه ورود OIDC)» سامانه
            آموزش‌یار۳۶۰ ثبت کنید؛ Client ID باید با «شناسه سرویس‌گیرنده» بالا یکی باشد.
          </p>
        </div>
      )}
      {Object.entries(LABELS).map(([k, label]) => (
        <div key={k} className="glass p-4">
          <label className="lbl">{label}</label>
          <div className="flex gap-2">
            <input className="input" dir="ltr" value={draft[k] ?? st[k] ?? ''}
              onChange={(e) => setDraft((d) => ({ ...d, [k]: e.target.value }))} />
            <button className="btn btn-ghost shrink-0" onClick={() => save(k)} disabled={draft[k] === undefined}>
              {saved === k ? '✓' : 'ذخیره'}
            </button>
          </div>
        </div>
      ))}
      <p className="text-xs text-slate-500 leading-6">
        پس از ثبت «آدرس پرتال SSO سازمان»، گزینه «ورود یکپارچه سازمانی (SSO)» در صفحه ورود فعال می‌شود؛
        اگر کاربر در پرتال SSO نشست فعال داشته باشد، ورود بدون رمز انجام می‌گیرد.
        کلیدها فقط با نقش مدیر سیستم قابل ویرایش‌اند و مقادیر مخفی با «•••» نمایش داده می‌شوند.
      </p>
    </div>
  )
}

function AuditTab() {
  const [events, setEvents] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.get('/admin/audit', { params: { limit: 300 } }).then(({ data }) => setEvents(data.events)).catch((e) => setErr(errMsg(e)))
  }, [])
  if (err) return <div className="text-sm text-rose-300">{err}</div>
  if (!events) return <Spinner />
  return (
    <div className="glass overflow-x-auto p-1 max-h-[70vh] overflow-y-auto">
      <table className="tbl">
        <thead><tr><th>زمان</th><th>کاربر</th><th>رخداد</th><th>جزئیات</th></tr></thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id}>
              <td className="text-xs text-slate-500 whitespace-nowrap">{e.created_at?.slice(0, 16)}</td>
              <td className="text-xs">{e.username || '—'}</td>
              <td><Chip tone="chip-violet">{e.action}</Chip></td>
              <td className="text-xs text-slate-400">{e.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
