import axios from 'axios'

// حالت پیش‌نمایش گیت‌وی: اگر صفحه پشت درگاه (پارامتر XTransformPort) اجرا شود،
// همان پارامتر به همه درخواست‌های API اضافه می‌شود. در استقرار مستقل اثری ندارد.
export const GATEWAY_PORT = (() => {
  try { return new URLSearchParams(window.location.search).get('XTransformPort') } catch { return null }
})()

// افزودن پارامتر درگاه به یک URL داخلی (برای ریدایرکت‌های کامل صفحه)
export const withGateway = (url) =>
  GATEWAY_PORT ? `${url}${url.includes('?') ? '&' : '?'}XTransformPort=${GATEWAY_PORT}` : url

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('d360_token')
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  if (GATEWAY_PORT) cfg.params = { ...(cfg.params || {}), XTransformPort: GATEWAY_PORT }
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !location.pathname.startsWith('/login') && !location.pathname.startsWith('/sso')) {
      localStorage.removeItem('d360_token')
      localStorage.removeItem('d360_user')
      location.href = withGateway('/login')
    }
    return Promise.reject(err)
  },
)

export const errMsg = (e) =>
  e?.response?.data?.detail || e?.message || 'خطای ناشناخته رخ داد'

export default api
