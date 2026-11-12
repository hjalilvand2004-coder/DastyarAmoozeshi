import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  BookOpenText, CalendarClock, ClipboardList, FlaskConical, GraduationCap,
  LayoutDashboard, LifeBuoy, LogOut, Map, MessageSquareText, Settings2, ShieldAlert, Blocks,
} from 'lucide-react'
import { useAuth } from '../auth'
import { Chip } from '../ui'

const NAV = [
  { to: '/', label: 'میزکار', icon: LayoutDashboard, perm: null },
  { to: '/chat', label: 'دستیار مستند', icon: MessageSquareText, perm: 'chat' },
  { to: '/regulations', label: 'آیین‌نامه‌ها', icon: BookOpenText, perm: 'regs.read' },
  { to: '/advisor', label: 'مشاور تحصیلی', icon: GraduationCap, perm: 'advisor.self' },
  { to: '/rules', label: 'قواعد ارزیابی', icon: FlaskConical, perm: 'rules.evaluate' },
  { to: '/processes', label: 'راهنمای فرایندها', icon: Map, perm: 'regs.read' },
  { to: '/deadlines', label: 'تقویم و مهلت‌ها', icon: CalendarClock, perm: 'deadlines.read' },
  { to: '/tickets', label: 'درخواست از کارشناس', icon: LifeBuoy, perm: 'tickets.own' },
  { to: '/admin', label: 'مدیریت سیستم', icon: Settings2, perm: 'users.manage' },
  { to: '/integrations', label: 'سامانه‌های متصل', icon: Blocks, perm: 'users.manage' },
]

export default function Layout() {
  const { user, signOut, can } = useAuth()
  const nav = useNavigate()
  const [menu, setMenu] = useState(false)
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000)
    return () => clearInterval(t)
  }, [])

  const items = NAV.filter((n) => !n.perm || can(n.perm))
  const greeting = now.getHours() < 12 ? 'صبح بخیر' : now.getHours() < 18 ? 'وقت بخیر' : 'شب بخیر'

  return (
    <div className="min-h-screen flex" dir="rtl">
      <div className="aurora" />

      {/* نوار کناری */}
      <aside className="hidden lg:flex w-64 shrink-0 flex-col gap-1 p-4 sticky top-0 h-screen">
        <div className="glass p-4 mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-violet-500/30">
              <GraduationCap size={20} className="text-white" />
            </div>
            <div>
              <div className="font-bold text-sm text-slate-100">دستیار آموزشی</div>
              <div className="text-[11px] text-slate-500">زیرسیستم دانشجو۳۶۰</div>
            </div>
          </div>
        </div>
        {items.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'}
            className={({ isActive }) => `side-item ${isActive ? 'active' : ''}`}>
            <n.icon size={17} />
            {n.label}
          </NavLink>
        ))}
        <div className="mt-auto glass p-3 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-violet-500/60 to-cyan-500/60 flex items-center justify-center text-sm font-bold">
            {(user.full_name || user.username).charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold truncate">{user.full_name || user.username}</div>
            <div className="text-[11px] text-violet-300/80">{user.role_fa}</div>
          </div>
          <button onClick={() => { signOut(); nav('/login') }} title="خروج"
            className="btn btn-ghost btn-sm !px-2 text-slate-400 hover:!text-rose-300">
            <LogOut size={15} />
          </button>
        </div>
      </aside>

      {/* محتوا */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-30 px-4 lg:px-8 py-3 flex items-center gap-3 glass-strong !rounded-none !border-x-0 !border-t-0">
          <button className="lg:hidden btn btn-ghost btn-sm" onClick={() => setMenu(!menu)}>
            <ClipboardList size={16} />
          </button>
          <div className="hidden sm:block text-sm text-slate-400">{greeting}، <span className="text-slate-200 font-semibold">{user.full_name || user.username}</span></div>
          <div className="flex-1" />
          <Chip tone="chip-amber"><ShieldAlert size={12} /> داده نمونه — غیررسمی</Chip>
          <button className="lg:hidden btn btn-ghost btn-sm" onClick={() => { signOut(); nav('/login') }}><LogOut size={15} /></button>
        </header>

        {menu && (
          <div className="lg:hidden p-3 grid grid-cols-2 gap-2 fade-up">
            {items.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === '/'} onClick={() => setMenu(false)}
                className={({ isActive }) => `side-item ${isActive ? 'active' : ''} glass !rounded-xl`}>
                <n.icon size={16} /> {n.label}
              </NavLink>
            ))}
          </div>
        )}

        <main className="flex-1 px-4 lg:px-8 py-6 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>

        <footer className="px-8 py-4 text-center text-xs text-slate-600 mt-auto">
          دستیار آموزشی و آیین‌نامه‌ای — بخشی از زیرسیستم دانشجو۳۶۰ · پاسخ‌ها راهنمای خودکارند و جایگزین حکم رسمی دانشگاه نیستند
        </footer>
      </div>
    </div>
  )
}
