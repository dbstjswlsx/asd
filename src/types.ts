export type Place = { id?:number; name:string; address:string; lat:number; lng:number; memo:string; position:number }
export type Creator = { id:number; nickname:string; bio:string; avatar:string }
export type Course = { id:number; title:string; intro:string; category:string; creator_id:number; creator:Creator; price:number; like_count:number; purchase_count:number; liked:boolean; owned:boolean; places:Place[] }
export type Profile = Creator & { points:number; followers:number; following:number; followed:boolean; courses:Course[]; library:Course[] }
export type SavedPin = { id:number; user_id:number; name:string; note:string; lat:number; lng:number; color:string; created_at:string }
export type StampShop = { id:number; name:string; area:string; category:string; description:string; stamped:boolean }
export type StampData = { shops:StampShop[]; stamp_count:number; available_stamps:number; redeemed_stamps:number; rewards:number; next_reward:number; next_major_reward:number }
