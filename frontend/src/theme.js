// تم شب/روز «Aurora Premium» — ذخیره در localStorage + کلاس light-theme روی <html>
const KEY = 'theme'

export function currentTheme() {
  try { return localStorage.getItem(KEY) === 'light' ? 'light' : 'dark' } catch { return 'dark' }
}

export function applyTheme(t) {
  const light = t === 'light'
  document.documentElement.classList.toggle('light-theme', light)
  try { localStorage.setItem(KEY, light ? 'light' : 'dark') } catch { /* ignore */ }
}

export function toggleTheme() {
  const next = currentTheme() === 'light' ? 'dark' : 'light'
  applyTheme(next)
  return next
}
