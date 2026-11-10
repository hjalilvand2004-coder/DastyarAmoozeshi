import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertTriangle, Loader2 } from 'lucide-react'
import api, { errMsg } from '../api'
import { useAuth } from '../auth'

export default function SsoCallback() {
  const [params] = useSearchParams()
  const nav = useNavigate()
  const { signIn, refresh } = useAuth()
  const [err, setErr] = useState('')
  const done = useRef(false)

  useEffect(() => {
    if (done.current) return
    done.current = true

    const token = params.get('token')
    if (token) {
      // بازگشت مستقیم از IdP واقعی (توکن برنامه در URL است)
      finish(token, null)
      return
    }
    const ticket = params.get('ticket')
    if (ticket) {
      api.post('/auth/sso/demo/exchange', { ticket })
        .then(({ data }) => finish(data.token, data.user))
        .catch((e) => setErr(errMsg(e)))
      return
    }
    setErr('پارامترهای بازگشت SSO ناقص است.')
  }, [])

  const finish = async (token, user) => {
    signIn(token, user) // ذخیره توکن + به‌روزرسانی فوری context
    await refresh()     // دریافت پروفایل کامل کاربر قبل از هدایت
    nav('/', { replace: true })
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" dir="rtl">
      <div className="aurora" />
      <div className="glass-strong p-8 text-center max-w-sm w-full fade-up">
        {err ? (
          <>
            <AlertTriangle className="mx-auto text-amber-300 mb-3" size={28} />
            <div className="font-bold text-slate-100 mb-1">ورود یکپارچه ناموفق بود</div>
            <p className="text-sm text-slate-400 mb-4">{err}</p>
            <button className="btn btn-primary" onClick={() => nav('/login')}>بازگشت به ورود</button>
          </>
        ) : (
          <>
            <Loader2 className="mx-auto text-violet-300 mb-3 spin" size={30} />
            <div className="font-semibold text-slate-200">در حال تکمیل ورود یکپارچه…</div>
            <p className="text-xs text-slate-500 mt-2">چند لحظه صبر کنید.</p>
          </>
        )}
      </div>
    </div>
  )
}
