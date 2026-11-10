import { useEffect, useState } from 'react'
import { FileUp, GitBranch, Search, Sparkles } from 'lucide-react'
import api, { errMsg } from '../api'
import { useAuth } from '../auth'
import { Chip, EmptyState, Modal, PageHead, SampleBanner, Spinner, STATUS_CHIP, STATUS_FA } from '../ui'
import { jalaliStr } from '../jalali'

export default function Regulations() {
  const { can } = useAuth()
  const [docs, setDocs] = useState(null)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('all')
  const [detail, setDetail] = useState(null)
  const [importOpen, setImportOpen] = useState(false)
  const [err, setErr] = useState('')

  const load = () => api.get('/regulations').then(({ data }) => setDocs(data.documents)).catch((e) => setErr(errMsg(e)))
  useEffect(() => { load() }, [])

  const filtered = (docs || []).filter((d) =>
    (status === 'all' || d.status === status) &&
    (!q || (d.title || '').includes(q)))

  const doStatus = async (id, st) => {
    const reason = st === 'retired' ? (window.prompt('دلیل ابطال سند:') || 'ابطال') : ''
    try { await api.post(`/regulations/${id}/status`, { status: st, reason }); load() } catch (e) { alert(errMsg(e)) }
  }
  const doRevise = async (id) => {
    try { const r = await api.post(`/regulations/${id}/revise`); alert(`نسخه جدید پیش‌نویس با شناسه ${r.data.id} ساخته شد.`); load() } catch (e) { alert(errMsg(e)) }
  }

  const canCreate = can('regs.create')
  const canApprove = can('regs.approve_publish')

  return (
    <div>
      <PageHead title="پایگاه دانش آیین‌نامه‌ها" sub="هر سند با نسخه، وضعیت، دامنه اعمال و تاریخ اجرا مدیریت می‌شود. تنها اسناد «منتشرشده» در پاسخ دستیار استناد می‌شوند."
        actions={canCreate && (
          <button className="btn btn-primary" onClick={() => setImportOpen(true)}><FileUp size={15} /> ثبت سند جدید</button>
        )} />

      <SampleBanner />

      <div className="flex flex-wrap items-center gap-2 my-5">
        <div className="relative flex-1 min-w-52">
          <Search size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input className="input !pr-9" placeholder="جست‌وجوی عنوان سند…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        {['all', 'published', 'approved', 'in_review', 'draft', 'retired'].map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            className={`btn btn-sm ${status === s ? 'btn-primary' : 'btn-ghost'}`}>
            {s === 'all' ? 'همه' : STATUS_FA[s]}
          </button>
        ))}
      </div>

      {err && <div className="text-sm text-rose-300 mb-3">{err}</div>}

      {!docs ? <Spinner /> : filtered.length === 0 ? (
        <EmptyState icon={Sparkles} title="سندی یافت نشد" sub="فیلترها را تغییر دهید یا سند جدیدی ثبت کنید." />
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((d) => (
            <button key={d.id} onClick={() => setDetail(d)}
              className="glass card-hover p-5 text-right flex flex-col gap-3 fade-up">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-bold text-slate-100 leading-6">{d.title}</h3>
                <Chip tone={STATUS_CHIP[d.status]}>{STATUS_FA[d.status]}</Chip>
              </div>
              <div className="text-xs text-slate-500 space-y-1 flex-1">
                <div>نسخه: {d.version_no} · نوع: {d.doc_type === 'pdf' ? 'PDF' : d.doc_type === 'docx' ? 'Word' : 'متنی'}</div>
                {(d.scope_level || d.scope_major) && <div>دامنه: {[d.scope_level, d.scope_major].filter(Boolean).join(' - ') || '—'}{d.scope_entry_from ? ` · ورودی ${d.scope_entry_from}${d.scope_entry_to ? ` تا ${d.scope_entry_to}` : ''}` : ''}</div>}
                {d.effective_from && <div>اجرا از: {jalaliStr(d.effective_from)}{d.effective_until ? ` تا ${jalaliStr(d.effective_until)}` : ''}</div>}
                {d.retired_reason && <div className="text-rose-300/70">ابطال: {d.retired_reason}</div>}
              </div>
              <div className="flex items-center justify-between">
                <Chip tone={d.is_official ? 'chip-emerald' : 'chip-amber'}>{d.is_official ? 'رسمی' : 'نمونه و غیررسمی'}</Chip>
                <span className="text-[11px] text-violet-300">مشاهده متن ←</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {detail && <DetailModal doc={detail} onClose={() => { setDetail(null); load() }}
        canApprove={canApprove} canCreate={canCreate} doStatus={doStatus} doRevise={doRevise} />}

      {importOpen && <ImportModal onClose={() => { setImportOpen(false); load() }} />}
    </div>
  )
}

function DetailModal({ doc, onClose, canApprove, canCreate, doStatus, doRevise }) {
  const [chunks, setChunks] = useState(null)
  useEffect(() => {
    api.get(`/regulations/${doc.id}`).then(({ data }) => setChunks(data.chunks)).catch(() => setChunks([]))
  }, [doc.id])

  const nexts = { draft: ['in_review'], in_review: ['approved'], approved: ['published'], published: ['retired'] }[doc.status] || []

  return (
    <Modal open onClose={onClose} title={doc.title} wide>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <Chip tone={STATUS_CHIP[doc.status]}>{STATUS_FA[doc.status]}</Chip>
        <Chip tone="chip-slate">نسخه {doc.version_no}</Chip>
        <Chip tone={doc.is_official ? 'chip-emerald' : 'chip-amber'}>{doc.is_official ? 'رسمی' : 'نمونه و غیررسمی'}</Chip>
        {doc.effective_from && <Chip tone="chip-sky">اجرا از {jalaliStr(doc.effective_from)}</Chip>}
      </div>

      {(canCreate || canApprove) && (
        <div className="flex flex-wrap gap-2 mb-4">
          {canCreate && nexts.includes('in_review') && <button className="btn btn-ghost btn-sm" onClick={() => doStatus(doc.id, 'in_review')}>ارسال برای بررسی</button>}
          {canApprove && nexts.includes('approved') && <button className="btn btn-ghost btn-sm" onClick={() => doStatus(doc.id, 'approved')}>تأیید</button>}
          {canApprove && nexts.includes('published') && <button className="btn btn-primary btn-sm" onClick={() => doStatus(doc.id, 'published')}>انتشار</button>}
          {canApprove && (doc.status === 'published' || doc.status === 'approved') && <button className="btn btn-danger btn-sm" onClick={() => doStatus(doc.id, 'retired')}>ابطال</button>}
          {canCreate && (doc.status === 'published' || doc.status === 'approved') && (
            <button className="btn btn-ghost btn-sm" onClick={() => doRevise(doc.id)}><GitBranch size={13} /> نسخه جدید</button>
          )}
        </div>
      )}

      {!chunks ? <Spinner /> : chunks.length === 0 ? (
        <EmptyState title="متن استخراج‌شده‌ای ثبت نشده" />
      ) : (
        <div className="space-y-2">
          {chunks.map((c) => (
            <details key={c.id} className="acc glass !rounded-xl p-3.5" open={c.idx === 0}>
              <summary className="flex items-center gap-2 text-sm font-semibold text-violet-200">
                <span>{c.clause_ref || `بخش ${c.idx + 1}`}</span>
                {c.flags?.includes('injection_suspect') && <Chip tone="chip-rose">محتوای مشکوک به تزریق</Chip>}
                {c.flags?.includes('ocr_suspect') && <Chip tone="chip-amber">احتمال خطای OCR</Chip>}
              </summary>
              <p className="text-[13px] leading-7 text-slate-300 mt-2 whitespace-pre-wrap">{c.text}</p>
            </details>
          ))}
        </div>
      )}
    </Modal>
  )
}

function ImportModal({ onClose }) {
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [scopeLevel, setScopeLevel] = useState('')
  const [scopeMajor, setScopeMajor] = useState('')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      if (file) {
        const fd = new FormData()
        fd.append('title', title); fd.append('file', file)
        if (scopeLevel) fd.append('scope_level', scopeLevel)
        if (scopeMajor) fd.append('scope_major', scopeMajor)
        await api.post('/regulations/import-file', fd)
      } else {
        await api.post('/regulations/import', { title, text, scope_level: scopeLevel || null, scope_major: scopeMajor || null })
      }
      onClose()
    } catch (e2) { setErr(errMsg(e2)) } finally { setBusy(false) }
  }

  return (
    <Modal open onClose={onClose} title="ثبت سند جدید (پیش‌نویس)">
      <form onSubmit={submit} className="space-y-3">
        <div><label className="lbl">عنوان سند *</label><input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="lbl">مقطع (اختیاری)</label><input className="input" placeholder="مثلاً کارشناسی" value={scopeLevel} onChange={(e) => setScopeLevel(e.target.value)} /></div>
          <div><label className="lbl">رشته (اختیاری)</label><input className="input" placeholder="مثلاً مهندسی کامپیوتر" value={scopeMajor} onChange={(e) => setScopeMajor(e.target.value)} /></div>
        </div>
        <div>
          <label className="lbl">متن سند (ماده‌ها را در خط جدا بنویسید) — یا فایل بگذارید</label>
          <textarea className="textarea" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder={'ماده ۱: …\nماده ۲: …'} />
        </div>
        <div>
          <label className="lbl">فایل (txt / md / pdf / docx)</label>
          <input type="file" accept=".txt,.md,.pdf,.docx" onChange={(e) => setFile(e.target.files?.[0] || null)} className="input !py-2 text-xs" />
          <p className="text-[11px] text-slate-600 mt-1">PDF اسکن‌شده (OCR) در فاز بعد فعال می‌شود.</p>
        </div>
        {err && <div className="text-sm text-rose-300">{err}</div>}
        <button className="btn btn-primary w-full" disabled={busy || !title || (!text && !file)}>
          {busy ? 'در حال ثبت…' : 'ثبت به‌عنوان پیش‌نویس'}
        </button>
        <p className="text-[11px] text-slate-500 leading-5">
          سند جدید با وضعیت «پیش‌نویس» ثبت می‌شود و پس از گذار بررسی ← تأیید ← انتشار، در پاسخ‌های دستیار قابل استناد است.
        </p>
      </form>
    </Modal>
  )
}
