const API_BASE_URL = 'https://vibe.aitestbed.kr/preview/289ffc01-898a-4ab0-a019-2b9e8ae08983/api'

export const api = (path: string, init?: RequestInit) =>
  fetch(`${API_BASE_URL}/${path.replace(/^\/+/, '')}`, init)
