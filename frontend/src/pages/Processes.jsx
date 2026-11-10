import { useEffect, useState } from 'react'
import { FileText, Map } from 'lucide-react'
import api, { errMsg } from '../api'
import { Chip, EmptyState, PageHead, Spinner } from '../ui'

export default function Processes() {
  const [procs, setProcs] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/processes').then(({ data }) => setProcs(data.processes)).catch((e) => setErr(errMsg(e)))
  }, [])

  if (err) return <div className="text-sm text-rose-300">{err}</div>
  if (!procs) return <Spinner />

  return (
    <div>
      <PageHead title="راهنمای گام‌به‌گام فرایندها" sub="مراحل دقیق، مدارک لازم و سیستم مقصد برای هر فرایند اداری — ثبت نهایی همیشه فقط در سیستم رسمی انجام می‌شود." />
      {procs.length === 0 ? (
        <EmptyState icon={Map} title="فرایندی ثبت نشده" />
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {procs.map((p) => (
            <div key={p.id} className="glass card-hover p-5 fade-up">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500/30 to-cyan-500/20 border border-white/10 flex items-center justify-center text-violet-200">
                  <Map size={16} />
                </div>
                <h3 className="font-bold text-slate-100">{p.title}</h3>
              </div>
              <ol className="space-y-2 mb-4">
                {p.steps.map((s, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
                    <span className="w-5 h-5 shrink-0 rounded-full bg-violet-500/20 border border-violet-400/40 text-[11px] flex items-center justify-center text-violet-200 mt-0.5">{i + 1}</span>
                    <span className="leading-6">{s}</span>
                  </li>
                ))}
              </ol>
              {p.required_docs?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {p.required_docs.map((d) => <Chip key={d} tone="chip-sky"><FileText size={11} /> {d}</Chip>)}
                </div>
              )}
              {p.target_system && (
                <p className="text-xs text-slate-400 leading-5">
                  ثبت نهایی در: <b className="text-slate-200">{p.target_system}</b>
                  {p.target_url && <> · <a href={p.target_url} target="_blank" rel="noreferrer" className="text-cyan-300 hover:underline">لینک سیستم مقصد</a></>}
                </p>
              )}
              {p.notes?.includes('نمونه') && <div className="mt-2"><Chip tone="chip-amber">نمونه و غیررسمی</Chip></div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
