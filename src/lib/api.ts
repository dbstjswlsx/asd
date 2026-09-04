const API_BASE_URL = 'https://vibe.aitestbed.kr/preview/1a450a3d-c9c5-4f6c-abed-da6ebdba5c27/api'

export const api = (path: string, init?: RequestInit) =>
  fetch(`${API_BASE_URL}/${path.replace(/^\/+/, '')}`, init)
