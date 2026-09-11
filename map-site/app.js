const STORAGE_KEY = 'my-map-places'
const START = { lat: 37.5665, lng: 126.978, zoom: 13 } // 서울시청

// ── 지도 & 레이어 ─────────────────────────────
const map = L.map('map', { zoomControl: false }).setView([START.lat, START.lng], START.zoom)

const baseLayers = {
  '일반 지도': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }),
  '밝은 지도': L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 20,
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  }),
  '위성 사진': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri',
  }),
}
baseLayers['일반 지도'].addTo(map)
L.control.layers(baseLayers, null, { position: 'topright' }).addTo(map)
L.control.zoom({ position: 'bottomright' }).addTo(map)
L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map)

const pinIcon = (extra = '') => L.divIcon({
  className: 'pin-wrap',
  html: `<div class="pin ${extra}"></div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -26],
})

// ── 유틸 ─────────────────────────────────────
const $ = (id) => document.getElementById(id)
const fmt = (n) => n.toFixed(5)
let toastTimer
function toast(text) {
  const el = $('toast')
  el.textContent = text
  el.hidden = false
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { el.hidden = true }, 2200)
}
function el(tag, props = {}, children = []) {
  const node = Object.assign(document.createElement(tag), props)
  node.append(...children)
  return node
}

// ── 저장한 장소 (localStorage) ─────────────────
let places = []
try { places = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] } catch { places = [] }
const markers = new Map()
const savedLayer = L.layerGroup().addTo(map)

function persist() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(places)) } catch {}
}

function addPlace(name, lat, lng) {
  const place = { id: Date.now(), name: name.trim() || '이름 없는 장소', lat, lng }
  places.unshift(place)
  persist()
  render()
  markers.get(place.id)?.openPopup()
  toast(`"${place.name}" 저장했어요`)
}

function removePlace(id) {
  places = places.filter((p) => p.id !== id)
  persist()
  render()
}

function focusPlace(place) {
  map.flyTo([place.lat, place.lng], Math.max(map.getZoom(), 16), { duration: 0.6 })
  map.once('moveend', () => markers.get(place.id)?.openPopup())
}

function savedPopup(place) {
  return el('div', { className: 'popup-form' }, [
    el('b', { textContent: place.name }),
    el('small', { textContent: `${fmt(place.lat)}, ${fmt(place.lng)}` }),
    el('button', { className: 'ghost', textContent: '삭제', onclick: () => removePlace(place.id) }),
  ])
}

function render() {
  savedLayer.clearLayers()
  markers.clear()
  places.forEach((p) => {
    const m = L.marker([p.lat, p.lng], { icon: pinIcon() })
      .bindTooltip(p.name, { direction: 'top', offset: [0, -26] })
      .bindPopup(() => savedPopup(p))
    savedLayer.addLayer(m)
    markers.set(p.id, m)
  })

  $('saved-count').textContent = places.length
  const list = $('saved-list')
  list.replaceChildren(...places.map((p) => el('li', {}, [
    el('button', { onclick: () => focusPlace(p) }, [
      el('b', { textContent: p.name }),
      el('small', { textContent: `${fmt(p.lat)}, ${fmt(p.lng)}` }),
    ]),
    el('button', { className: 'del', textContent: '×', ariaLabel: '삭제', onclick: () => removePlace(p.id) }),
  ])))
}

// 이름을 입력해 저장하는 팝업 폼
function savePrompt(lat, lng, defaultName = '') {
  const input = el('input', { value: defaultName, placeholder: '장소 이름' })
  const form = el('form', { className: 'popup-form' }, [
    el('b', { textContent: '이 위치 저장하기' }),
    el('small', { textContent: `${fmt(lat)}, ${fmt(lng)}` }),
    input,
    el('button', { type: 'submit', textContent: '저장' }),
  ])
  form.onsubmit = (e) => {
    e.preventDefault()
    map.closePopup()
    addPlace(input.value, lat, lng)
  }
  setTimeout(() => input.focus(), 50)
  return form
}

// ── 지도 클릭 → 저장 ──────────────────────────
map.on('click', (e) => {
  L.popup().setLatLng(e.latlng).setContent(savePrompt(e.latlng.lat, e.latlng.lng)).openOn(map)
})
map.on('mousemove', (e) => { $('coords').textContent = `${fmt(e.latlng.lat)}, ${fmt(e.latlng.lng)}` })

// ── 장소 검색 (OpenStreetMap Nominatim) ───────
const searchLayer = L.layerGroup().addTo(map)

$('search-form').addEventListener('submit', async (e) => {
  e.preventDefault()
  const q = $('search-input').value.trim()
  const results = $('results')
  if (q.length < 2) return toast('두 글자 이상 입력해 주세요')

  results.replaceChildren(el('li', { className: 'empty', textContent: '찾는 중…' }))
  try {
    const url = 'https://nominatim.openstreetmap.org/search?' + new URLSearchParams({
      q, format: 'jsonv2', limit: '6', 'accept-language': 'ko',
    })
    const res = await fetch(url)
    if (!res.ok) throw new Error()
    const items = await res.json()
    if (!items.length) {
      results.replaceChildren(el('li', { className: 'empty', textContent: '검색 결과가 없어요.' }))
      return
    }
    results.replaceChildren(...items.map((item) => {
      const name = item.name || item.display_name.split(',')[0]
      return el('li', {}, [el('button', { onclick: () => showResult(name, +item.lat, +item.lon) }, [
        el('b', { textContent: name }),
        el('small', { textContent: item.display_name }),
      ])])
    }))
  } catch {
    results.replaceChildren(el('li', { className: 'empty', textContent: '검색에 실패했어요. 잠시 후 다시 시도해 주세요.' }))
  }
})

function showResult(name, lat, lng) {
  searchLayer.clearLayers()
  const m = L.marker([lat, lng], { icon: pinIcon('search-pin') }).addTo(searchLayer)
  m.bindPopup(() => savePrompt(lat, lng, name))
  map.flyTo([lat, lng], 16, { duration: 0.8 })
  map.once('moveend', () => m.openPopup())
  $('results').replaceChildren()
}

// ── 내 위치 ──────────────────────────────────
const locateLayer = L.layerGroup().addTo(map)
$('locate-btn').addEventListener('click', () => {
  if (!navigator.geolocation) return toast('이 브라우저는 위치 기능을 지원하지 않아요')
  toast('현재 위치를 찾는 중…')
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      const ll = [coords.latitude, coords.longitude]
      locateLayer.clearLayers()
      L.circle(ll, { radius: coords.accuracy, color: '#3b6fd8', weight: 1, fillOpacity: 0.12 }).addTo(locateLayer)
      L.circleMarker(ll, { radius: 7, color: '#fff', weight: 3, fillColor: '#3b6fd8', fillOpacity: 1 })
        .bindPopup(() => savePrompt(ll[0], ll[1], '내 위치'))
        .addTo(locateLayer)
      map.flyTo(ll, 16, { duration: 0.8 })
    },
    () => toast('위치 권한을 허용해 주세요'),
    { enableHighAccuracy: true, timeout: 10000 },
  )
})

// ── 모두 보기 / 패널 접기 ─────────────────────
$('fit-btn').addEventListener('click', () => {
  if (!places.length) return toast('아직 저장한 장소가 없어요')
  if (places.length === 1) return focusPlace(places[0])
  map.flyToBounds(places.map((p) => [p.lat, p.lng]), { padding: [60, 60], duration: 0.8 })
})
$('toggle-panel').addEventListener('click', () => $('panel').classList.toggle('collapsed'))

render()
