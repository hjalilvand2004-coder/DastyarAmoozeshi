// ویجت داشیار «دانشگاه هوشمند من» — بارگذاری یک‌باره + پل وضعیت دانشجو
// منبع ویجت: هسته عامل داشیار (کپی رسمی در بک‌اند این سامانه سرو می‌شود)
import api from './api'

let booted = false

/** به‌روزرسانی «آخرین وضعیت» کاربر/دانشجو برای هسته داشیار (قبل از هر ارسال پیام خوانده می‌شود) */
export function updateMsuContext(user, student) {
  try {
    window.MSUHostContext = {
      origin: 'amoozeshyar360',
      system: 'آموزش‌یار۳۶۰',
      system_url: 'http://188.212.96.235:8091',
      page: location.pathname,
      ts: new Date().toISOString(),
      user: user ? {
        username: user.username, full_name: user.full_name,
        role: user.role, role_fa: user.role_fa,
      } : null,
      student: student ? {
        full_name: student.full_name, level: student.level, major: student.major,
        entry_year: student.entry_year, gpa: student.gpa,
        passed_credits: student.passed_credits,
        profile_extra: student.profile_extra || {},
      } : null,
    }
  } catch { /* ignore */ }
}

/** بارگذاری یک‌بارهٔ ویجت داشیار در پایین‌چپ صفحه (تنظیم‌پذیر از مدیریت سیستم) */
export async function bootMsuAgent() {
  if (booted) return
  booted = true
  try {
    const { data } = await api.get('/integrations/msu/config')
    if (!data?.enabled) return
    const s = document.createElement('script')
    s.src = '/api/v1/integration/msu-agent.js'
    s.async = true
    s.setAttribute('data-agent-url', data.url || 'http://188.212.96.235:8096')
    s.setAttribute('data-origin', data.origin || 'amoozeshyar360')
    s.setAttribute('data-position', 'bl') // پایین‌چپ طبق استاندارد پرتال دانشجویار۳۶۰
    s.setAttribute('data-accent', '#7c3aed')
    s.setAttribute('data-accent2', '#a78bfa')
    s.setAttribute('data-title', 'دانشیار دانشگاه هوشمند من')
    s.setAttribute('data-subtitle', 'دستیار هوشمند دانشجو — هماهنگ با آموزش‌یار۳۶۰')
    s.setAttribute('data-greeting',
      'سلام! من «دانشیار» دانشگاه هوشمند من هستم؛ از همهٔ سامانه‌های دانشجویی وضعیت شما را دریافت می‌کنم و در هماهنگی با آموزش‌یار۳۶۰، متناسب با آخرین وضعیتتان راهنمایی می‌کنم. بپرسید یا یکی از پیشنهادها را انتخاب کنید.')
    document.body.appendChild(s)
  } catch { /* هسته در دسترس نیست؛ ویجت بی‌صدا حذف می‌شود */ }
}
