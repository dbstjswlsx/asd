import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { useEffect } from 'react'
import type { Course, Place, SavedPin } from '../types'
import 'leaflet/dist/leaflet.css'
const icon = (label:string, active=false, note=false, color='') => L.divIcon({
  className:'pin-wrap',
  html:`<span class="pin ${active?'active':''} ${note?'note-pin':''}" ${color?`style="background:${color}"`:''}>${label}</span>`,
  iconSize:[34,34], iconAnchor:[17,17]
})
function Clicker({onPick}:{onPick?:(lat:number,lng:number)=>void}) {
  useMapEvents({click:e=>onPick?.(e.latlng.lat,e.latlng.lng)})
  return null
}
function Fit({points}:{points:Place[]}) {
  const map=useMap()
  useEffect(()=>{if(points.length>1) map.fitBounds(points.map(p=>[p.lat,p.lng]),{padding:[35,35]})},[points,map])
  return null
}
function MoveTo({place}:{place?:{lat:number;lng:number}}) {
  const map=useMap()
  useEffect(()=>{if(place) map.flyTo([place.lat,place.lng],16,{duration:.55})},[map,place])
  return null
}
type Note={id:number;text:string;lat:number;lng:number}
export default function CourseMap({courses=[],selected,onSelect,editable=[],onPick,onPinSelect,notes=[],pins=[],searchPlace}:{courses?:Course[];selected?:Course;onSelect?:(c:Course)=>void;editable?:Place[];onPick?:(lat:number,lng:number)=>void;onPinSelect?:(lat:number,lng:number)=>void;notes?:Note[];pins?:SavedPin[];searchPlace?:{lat:number;lng:number}}) {
 const focus=selected?.places || editable
 const center:[number,number]=focus?.[0]?[focus[0].lat,focus[0].lng]:[37.558,126.95]
 return <MapContainer center={center} zoom={13} className="map-view" zoomControl={false}>
  <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://tiles.osm.kr/hot/{z}/{x}/{y}.png" />
  <MoveTo place={searchPlace}/>
  <Clicker onPick={onPick}/>
  {focus.length>1&&<><Polyline positions={focus.map(p=>[p.lat,p.lng])} pathOptions={{color:'#c9343d',weight:4,opacity:.8}}/><Fit points={focus}/></>}
  {editable.map(p=><Marker key={'p'+p.position} position={[p.lat,p.lng]} icon={icon(String(p.position),true)}><Tooltip direction="top">{p.name}</Tooltip></Marker>)}
  {!editable.length&&courses.flatMap(c=>c.places.slice(0,1).map(p=><Marker key={c.id} position={[p.lat,p.lng]} icon={icon(c.id===selected?.id?'♥':'✦',c.id===selected?.id)} eventHandlers={{click:()=>{onSelect?.(c);onPinSelect?.(p.lat,p.lng)}}}><Tooltip direction="top">{c.title}</Tooltip></Marker>))}
  {notes.map(n=><Marker key={'n'+n.id} position={[n.lat,n.lng]} icon={icon('✎',false,true)} eventHandlers={{click:()=>onPinSelect?.(n.lat,n.lng)}}><Tooltip direction="top">{n.text}</Tooltip></Marker>)}
  {pins.map(p=><Marker key={'pin'+p.id} position={[p.lat,p.lng]} icon={icon('●',false,false,p.color)} eventHandlers={{click:()=>onPinSelect?.(p.lat,p.lng)}}><Tooltip direction="top"><b>{p.name}</b><br/>{p.note||'내가 저장한 핀'}</Tooltip></Marker>)}
 </MapContainer>
}
