import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('d360_token')
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !location.pathname.startsWith('/login') && !location.pathname.startsWith('/sso')) {
      localStorage.removeItem('d360_token')
      localStorage.removeItem('d360_user')
      location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export const errMsg = (e) =>
  e?.response?.data?.detail || e?.message || 'خطای ناشناخته رخ داد'

export default api
