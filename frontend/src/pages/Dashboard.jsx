import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, BookOpenText, CalendarClock, FlaskConical, LifeBuoy,
  MessageSquareText, Sparkles,
} from 'lucide-react'
import api from '../api'
import { useAuth } from '../auth'
import { Chip, EmptyState, SampleBanner, Spinner } from '../ui'
import { daysUntil, faNum, jalaliStr } from '../jalali'

export default function Dashboard() {
  const { user, refresh } = useAuth()
  const [data, setData] = useState(null)
  const [me, setMe] = useState(null)

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    Promise.all([
      api.get('/deadlines/reminders', { params: { window_days: 45 } }),
      api.get('/deadlines'),
      api.get('/regulations'),
      api.get('/tickets').catch(() => ({ data: { tickets: [] } })),
      api.get('/auth/me'),
    ]).then(([rem, dl, regs, tix, me]) => {
      setMe(me.data)
      setData({
        reminders: rem.data.reminders,
        deadlines: dl.data.deadlines,
        published: regs.data.documents.filter((d) => d.status === 'published').length,
        tickets: tix.data.tickets,
      })
    }).catch(() => setData({ reminders: [], deadlines: [], published: 0, tickets: [] }))
  }, [])

  if (!data) return <Spinner />

  const openTickets = data.tickets.filter((t) => t.status !== 'closed')
  const soon = [...data.deadlines].filter((d) => daysUntil(d.date_iso) >= 0)
    .sort((a, b) => daysUntil(a.date_iso) - daysUntil(b.date_iso)).slice(0, 4)
  const student = me?.student

  const stats = [
    { icon: BookOpenText, label: 'اسناد منتشرشده', value: data.published, to: '/regulations', tone: 'from-violet-500/25 to-violet-500/5 text-violet-300' },
    { icon: CalendarClock, label: 'یادآور فعال', value: data.reminders.length, to: '/deadlines', tone: 'from-cyan-500/25 to-cyan-500/5 text-cyan-300' },
    { icon: LifeBuoy, label: 'درخواست‌های باز', value: openTickets.length, to: '/tickets', tone: 'from-emerald-500/25 to-emerald-500/5 text-emerald-300' },
  ]

  return (
    <div className="space-y-6">
      {/* خوش‌آمد */}
      <div className="relative glass p-6 md:p-8 overflow-hidden fade-up">
        <div className="absolute -left-16 -top-16 w-56 h-56 rounded-full bg-violet-600/20 blur-3xl" />
        <div className="absolute -right-10 -bottom-20 w-56 h-56 rounded-full bg-cyan-500/15 blur-3xl" />
        <div className="relative">
          <div className="flex items-center gap-2 text-violet-300 text-sm mb-2">
            <Sparkles size={15} /> زیرسیستم دستیار آموزشی دانشجو۳۶۰
          </div>
          <h1 className="text-2xl md:text-3xl font-bold">
            {user.full_name || user.username} عزیز، <span className="grad-text">خوش آمدید</span>
          </h1>
          <p className="text-slate-400 mt-2 text-sm leading-6 max-w-2xl">
            هر پرسشی درباره آیین‌نامه‌ها دارید، اول از «دستیار مستند» بپرسید؛ پاسخ با متن رسمی سند و
            ارجاع دقیق ارائه می‌شود و شرایط شخصی شما با موتور قواعد قطعی ارزیابی می‌گردد.
          </p>
          <div className="flex flex-wrap gap-2 mt-5">
            <Link to="/chat" className="btn btn-primary"><MessageSquareText size={15} /> پرسش از دستیار مستند</Link>
            <Link to="/deadlines" className="btn btn-ghost"><CalendarClock size={15} /> مهلت‌های من</Link>
            <Link to="/tickets" className="btn btn-ghost"><LifeBuoy size={15} /> درخواست از کارشناس</Link>
          </div>
        </div>
      </div>

      <SampleBanner />

      {/* آمار */}
      <div className="grid sm:grid-cols-3 gap-4">
        {stats.map((s) => (
          <Link key={s.label} to={s.to} className={`glass card-hover p-5 flex items-center gap-4 bg-gradient-to-bl ${s.tone}`}>
            <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
              <s.icon size={22} />
            </div>
            <div>
              <div className="text-2xl font-bold">{faNum(s.value)}</div>
              <div className="text-xs text-slate-400">{s.label}</div>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* مهلت‌های پیش‌رو */}
        <div className="glass p-5 fade-up">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-100 flex items-center gap-2"><CalendarClock size={17} className="text-cyan-300" /> مهلت‌های پیش‌رو</h2>
            <Link to="/deadlines" className="text-xs text-violet-300 hover:underline flex items-center gap-1">همه <ArrowLeft size={13} /></Link>
          </div>
          {soon.length === 0 ? (
            <EmptyState icon={CalendarClock} title="مهلتی در پیش نیست" sub="وقتی مهلت جدیدی ثبت شود، همین‌جا می‌بینید." />
          ) : (
            <ul className="space-y-2.5">
              {soon.map((d) => {
                const days = daysUntil(d.date_iso)
                return (
                  <li key={d.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[.03] border border-white/[.06]">
                    <div className={`w-11 text-center py-1.5 rounded-xl text-xs font-bold border ${days <= 7 ? 'border-rose-400/40 text-rose-300 bg-rose-500/10' : 'border-cyan-400/30 text-cyan-300 bg-cyan-500/10'}`}>
                      {faNum(days)}<br /><span className="text-[9px] font-normal">روز</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium truncate">{d.title}</div>
                      <div className="text-[11px] text-slate-500">{jalaliStr(d.date_iso)}</div>
                    </div>
                    {d.notes?.includes('نمونه') && <Chip tone="chip-amber">نمونه</Chip>}
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* وضعیت من */}
        <div className="glass p-5 fade-up">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-100 flex items-center gap-2"><FlaskConical size={17} className="text-violet-300" /> وضعیت ارزیابی من</h2>
            <Link to="/rules" className="text-xs text-violet-300 hover:underline flex items-center gap-1">جزئیات <ArrowLeft size={13} /></Link>
          </div>
          {!student ? (
            <EmptyState icon={FlaskConical} title="پروفایل دانشجویی متصل نیست"
              sub="این حساب به پروفایل دانشجویی متصل نیست؛ برای بررسی، از کارشناس آموزش درخواست کنید." />
          ) : (
            <MyRules />
          )}
        </div>
      </div>
    </div>
  )
}

function MyRules() {
  const [res, setRes] = useState(null)
  useEffect(() => {
    api.get('/rules/my').then(({ data }) => setRes(data)).catch(() => setRes({ results: [] }))
  }, [])
  if (!res) return <div className="skeleton h-24" />
  if (!res.results.length) return <EmptyState icon={FlaskConical} title="قاعده تأییدشده‌ای وجود ندارد" />
  return (
    <ul className="space-y-2.5">
      {res.results.slice(0, 4).map((r) => (
        <li key={r.rule_id} className="p-3 rounded-xl bg-white/[.03] border border-white/[.06]">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium">{r.title}</span>
            <Chip tone={r.status === 'satisfied' ? 'chip-emerald' : r.status === 'not_satisfied' ? 'chip-rose' : r.status === 'needs_review' ? 'chip-sky' : 'chip-amber'}>
              {r.status_fa}
            </Chip>
          </div>
          {r.detail && <p className="text-xs text-slate-500 mt-1 leading-5">{r.detail}</p>}
        </li>
      ))}
    </ul>
  )
}
