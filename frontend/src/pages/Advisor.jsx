import { useEffect, useState } from 'react'
import { CheckCircle2, GraduationCap, XCircle } from 'lucide-react'
import api, { errMsg } from '../api'
import { useAuth } from '../auth'
import { Chip, EmptyState, PageHead, RULE_STATE_CHIP, RULE_STATE_FA, Spinner } from '../ui'
import { faNum } from '../jalali'

export default function Advisor() {
  const { can, user } = useAuth()
  const isExpert = can('advisor.student')
  const [students, setStudents] = useState([])
  const [sid, setSid] = useState(user.student_id || '')
  const [courses, setCourses] = useState([])
  const [next, setNext] = useState(null)
  const [grad, setGrad] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (isExpert) api.get('/advisor/students').then(({ data }) => setStudents(data.students)).catch((e) => setErr(errMsg(e)))
  }, [isExpert])

  useEffect(() => {
    if (!sid) return
    setErr('')
    const p = { params: isExpert ? { student_id: sid } : {} }
    Promise.all([
      api.get('/advisor/courses'),
      api.get('/advisor/next-courses', p),
      api.get('/advisor/graduation', p),
    ]).then(([c, n, g]) => { setCourses(c.data.courses); setNext(n.data); setGrad(g.data) })
      .catch((e) => setErr(errMsg(e)))
  }, [sid, isExpert])

  const analyze = async (courseId) => {
    setAnalysis(null)
    try {
      const { data } = await api.get(`/advisor/analyze/${courseId}`, { params: isExpert ? { student_id: sid } : {} })
      setAnalysis(data)
    } catch (e) { setErr(errMsg(e)) }
  }

  return (
    <div>
      <PageHead title="مشاور تحصیلی" sub="پیش‌نیازها، دروس قابل اخذ ترم بعد و ممیزی فارغ‌التحصیلی — همه با موتور قواعد قطعی و بدون حدس." />

      {err && <div className="text-sm text-rose-300 mb-3">{err}</div>}

      {isExpert && (
        <div className="glass p-4 mb-5 max-w-md">
          <label className="lbl">انتخاب دانشجو</label>
          <select className="select" value={sid} onChange={(e) => setSid(e.target.value)}>
            <option value="">— انتخاب کنید —</option>
            {students.map((s) => <option key={s.id} value={s.id}>{s.full_name} — {s.major || '—'}</option>)}
          </select>
        </div>
      )}

      {!sid ? <EmptyState icon={GraduationCap} title="دانشجو انتخاب نشده" sub={isExpert ? 'برای مشاهده، دانشجو را انتخاب کنید.' : 'حساب شما به پروفایل دانشجویی متصل نیست.'} /> : (
        <>
          <div className="grid lg:grid-cols-2 gap-4 mb-5">
            {/* دروس پیشنهادی */}
            <div className="glass p-5 fade-up">
              <h2 className="font-bold mb-3 text-cyan-300">دروس قابل اخذ ترم بعد</h2>
              {!next ? <Spinner /> : next.suggestions?.length ? (
                <ul className="space-y-2">
                  {next.suggestions.map((s) => (
                    <li key={s.code} className="flex items-center gap-2 p-2.5 rounded-xl bg-white/[.03] border border-white/[.06] text-sm">
                      <code className="text-cyan-300 text-xs">{s.code}</code>
                      <span className="flex-1">{s.name}</span>
                      <Chip tone="chip-slate">{faNum(s.credits)} واحد</Chip>
                    </li>
                  ))}
                </ul>
              ) : <EmptyState title="پیشنهادی یافت نشد" sub={next?.note || ''} />}
            </div>

            {/* ممیزی فارغ‌التحصیلی */}
            <div className="glass p-5 fade-up">
              <h2 className="font-bold mb-3 text-violet-300">ممیزی فارغ‌التحصیلی</h2>
              {!grad ? <Spinner /> : (
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                      <span>واحد گذرانده: {faNum(grad.passed_credits ?? '—')}</span>
                      <span>لازم: {faNum(grad.required_credits)}</span>
                    </div>
                    <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400 transition-all duration-700"
                        style={{ width: `${Math.min(100, Math.round(((grad.passed_credits || 0) / (grad.required_credits || 140)) * 100))}%` }} />
                    </div>
                  </div>
                  {grad.missing_prereq_courses?.length > 0 && (
                    <p className="text-xs text-amber-300/80">دروس باقی‌مانده: {grad.missing_prereq_courses.join('، ')}</p>
                  )}
                  <p className={`text-sm font-semibold ${grad.eligible ? 'text-emerald-300' : 'text-amber-300'}`}>
                    {grad.eligible ? '✅ واجد شرایط درخواست فارغ‌التحصیلی (بر اساس قواعد فعلی)' : '⏳ هنوز شرایط کامل نشده است'}
                  </p>
                  <p className="text-[11px] text-slate-500">نتیجه قطعی با تأیید اداره آموزش است.</p>
                </div>
              )}
            </div>
          </div>

          {/* تحلیل درس */}
          <div className="glass p-5 fade-up">
            <h2 className="font-bold mb-3 text-slate-100">تحلیل شرایط یک درس</h2>
            <div className="flex flex-wrap gap-2 mb-4">
              {courses.map((c) => (
                <button key={c.id} className="btn btn-ghost btn-sm" onClick={() => analyze(c.id)}>{c.name}</button>
              ))}
            </div>
            {analysis && (
              <div className="glass !rounded-xl p-4 fade-up">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold">{analysis.course_name}</span>
                  <Chip tone={analysis.eligible ? 'chip-emerald' : 'chip-rose'}>
                    {analysis.eligible ? 'پیش‌نیازها برآورده است' : 'پیش‌نیاز برآورده نشده'}
                  </Chip>
                </div>
                {analysis.missing?.length > 0 && (
                  <p className="text-xs text-rose-300/90 flex items-center gap-1"><XCircle size={13} /> گذرانده نشده: {analysis.missing.join('، ')}</p>
                )}
                {analysis.eligible && <p className="text-xs text-emerald-300/90 flex items-center gap-1"><CheckCircle2 size={13} /> همه پیش‌نیازها گذرانده شده است.</p>}
                {analysis.rule_status && (
                  <div className="mt-2">
                    <Chip tone={RULE_STATE_CHIP[analysis.rule_status.status]}>{analysis.rule_status.status_fa || RULE_STATE_FA[analysis.rule_status.status]}</Chip>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
