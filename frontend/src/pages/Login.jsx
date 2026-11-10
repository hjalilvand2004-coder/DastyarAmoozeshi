import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Fingerprint, GraduationCap, Loader2, Lock, LogIn, User } from 'lucide-react'
import api, { errMsg } from '../api'
import { useAuth } from '../auth'
import { faNum } from '../jalali'

export default function Login() {
  const nav = useNavigate()
  const { signIn } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [providers, setProviders] = useState([])
  const [demoIdentity, setDemoIdentity] = useState('student')
  const [ssoBusy, setSsoBusy] = useState('')
  const [showHint, setShowHint] = useState(false)

  useEffect(() => {
    api.get('/auth/sso/providers').then(({ data }) => setProviders(data.providers)).catch(() => {})
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      const { data } = await api.post('/auth/login', { username, password })
      signIn(data.token, data.user)
      nav('/', { replace: true })
    } catch (e2) { setErr(errMsg(e2)) } finally { setBusy(false) }
  }

  const ssoStart = async (p) => {
    setErr(''); setSsoBusy(p.id)
    try {
      if (p.kind === 'demo') {
        const { data } = await api.get(`/auth/sso/${p.id}/start`, { params: { as_: demoIdentity } })
        // جریان واقعی SSO: هدایت به صفحه بازگشت و تبادل تیکت یک‌بار مصرف
        window.location.href = data.redirect
      } else if (p.kind === 'oidc') {
        const { data } = await api.get(`/auth/sso/${p.id}/start`)
        window.location.href = data.redirect
      }
    } catch (e2) { setErr(errMsg(e2)); setSsoBusy('') }
  }

  const demo = providers.find((p) => p.kind === 'demo')
  const oidc = providers.find((p) => p.kind === 'oidc')

  return (
    <div className="min-h-screen flex items-center justify-center p-4" dir="rtl">
      <div className="aurora" />

      <div className="w-full max-w-4xl grid lg:grid-cols-2 gap-0 glass-strong overflow-hidden fade-up">
        {/* پنل برند */}
        <div className="relative hidden lg:flex flex-col justify-between p-10 bg-gradient-to-br from-violet-600/25 via-indigo-600/10 to-cyan-500/20">
          <div>
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-cyan-400 flex items-center justify-center shadow-xl shadow-violet-500/40">
              <GraduationCap size={28} className="text-white" />
            </div>
            <h1 className="mt-6 text-2xl font-bold leading-9 text-slate-100">
              دستیار آموزشی و<br /><span className="grad-text">آیین‌نامه‌ای دانشجو۳۶۰</span>
            </h1>
            <p className="mt-4 text-sm leading-7 text-slate-400">
              پاسخ مستند با ارجاع به متن رسمی آیین‌نامه، ارزیابی قطعی شرایط شما با
              موتور قواعد، یادآور مهلت‌ها و درخواست مستقیم از کارشناس آموزش.
            </p>
          </div>
          <ul className="space-y-2.5 text-sm text-slate-300/90">
            {['پاسخ سه‌لایه: متن رسمی، توضیح ساده، وضعیت شخصی شما',
              'استناد قابل مشاهده: نسخه، ماده و صفحه سند',
              'ورود یکپارچه دانشگاهی (SSO) بدون رمز عبور'].map((t) => (
              <li key={t} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-violet-400 to-cyan-400" />
                {t}
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-amber-300/70">
            داده‌های نمایشی «نمونه و غیررسمی» هستند تا ثبت اسناد رسمی دانشگاه.
          </p>
        </div>

        {/* فرم ورود */}
        <div className="p-8 lg:p-10">
          <div className="lg:hidden flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-400 flex items-center justify-center">
              <GraduationCap size={22} className="text-white" />
            </div>
            <div className="font-bold">دستیار آموزشی دانشجو۳۶۰</div>
          </div>

          <h2 className="text-xl font-bold text-slate-100">ورود به سامانه</h2>
          <p className="text-sm text-slate-500 mt-1 mb-6">با حساب دانشگاهی خود وارد شوید.</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="lbl">نام کاربری</label>
              <div className="relative">
                <User size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input className="input !pr-9" placeholder="مثلاً student" value={username}
                  onChange={(e) => setUsername(e.target.value)} autoFocus />
              </div>
            </div>
            <div>
              <label className="lbl">رمز عبور</label>
              <div className="relative">
                <Lock size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input className="input !pr-9" type="password" placeholder="••••••••" value={password}
                  onChange={(e) => setPassword(e.target.value)} />
              </div>
            </div>
            {err && <div className="text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-xl px-3 py-2">{err}</div>}
            <button className="btn btn-primary w-full !py-2.5" disabled={busy}>
              {busy ? <Loader2 size={16} className="spin" /> : <LogIn size={16} />}
              ورود
            </button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="divider flex-1" />
            <span className="text-xs text-slate-600">یا</span>
            <div className="divider flex-1" />
          </div>

          {/* ورود یکپارچه */}
          <div className="space-y-3">
            {demo && (
              <div className="glass p-3.5">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-200 mb-2.5">
                  <Fingerprint size={16} className="text-cyan-300" /> {demo.name}
                </div>
                <div className="flex gap-2">
                  <select className="select" value={demoIdentity} onChange={(e) => setDemoIdentity(e.target.value)}>
                    {demo.identities.map((i) => <option key={i.id} value={i.id}>{i.label}</option>)}
                  </select>
                  <button className="btn btn-ghost shrink-0" disabled={ssoBusy === 'demo'} onClick={() => ssoStart(demo)}>
                    {ssoBusy === 'demo' ? <Loader2 size={15} className="spin" /> : <Fingerprint size={15} />}
                    ورود بدون رمز
                  </button>
                </div>
              </div>
            )}
            {oidc && (
              <button className="btn btn-ghost w-full" disabled={ssoBusy === 'university'} onClick={() => ssoStart(oidc)}>
                {ssoBusy === 'university' ? <Loader2 size={15} className="spin" /> : <Fingerprint size={15} />}
                ورود یکپارچه دانشگاه (SSO)
              </button>
            )}
            {!oidc && (
              <p className="text-[11px] text-slate-600 leading-5">
                ورود یکپارچه دانشگاهی (Keycloak/OIDC) پس از پیکربندی مدیر سیستم فعال می‌شود.
              </p>
            )}
          </div>

          <div className="mt-6">
            <button className="text-xs text-slate-500 underline underline-offset-4 hover:text-slate-300"
              onClick={() => setShowHint(!showHint)}>
              حساب‌های نمایشی و رمزها
            </button>
            {showHint && (
              <div className="mt-2 glass p-3 text-xs text-slate-400 leading-6 fade-up">
                {['student — Student@123', 'student2 — Student@123 (پروفایل ناقص)',
                  'expert — Expert@123', 'content — Content@123', 'approver — Approver@123',
                  'admin — Admin@123'].map((l, i) => (
                  <div key={l}>{faNum(i + 1)}. <code className="text-violet-300">{l}</code></div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
