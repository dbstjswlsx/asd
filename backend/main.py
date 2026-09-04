import os
import sqlite3
import json
import urllib.parse
import urllib.request
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
DB_PATH = "/workspace/data/app.db"
def load_local_env():
    env_path = '/workspace/.env'
    if not os.path.exists(env_path): return
    with open(env_path, encoding='utf-8') as env_file:
        for line in env_file:
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
load_local_env()
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def rows(items):
    return [dict(x) for x in items]
def init_db():
    with get_db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, bio TEXT DEFAULT '', points INTEGER NOT NULL DEFAULT 0, avatar TEXT DEFAULT '✦');
        CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, intro TEXT NOT NULL, category TEXT NOT NULL, creator_id INTEGER NOT NULL, price INTEGER NOT NULL DEFAULT 0, published INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS places (id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, name TEXT NOT NULL, address TEXT DEFAULT '', lat REAL NOT NULL, lng REAL NOT NULL, memo TEXT DEFAULT '', position INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS course_likes (user_id INTEGER NOT NULL, course_id INTEGER NOT NULL, PRIMARY KEY(user_id, course_id));
        CREATE TABLE IF NOT EXISTS follows (follower_id INTEGER NOT NULL, creator_id INTEGER NOT NULL, PRIMARY KEY(follower_id, creator_id));
        CREATE TABLE IF NOT EXISTS purchases (buyer_id INTEGER NOT NULL, course_id INTEGER NOT NULL, amount INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(buyer_id, course_id));
        CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount INTEGER NOT NULL, type TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS map_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, text TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, password TEXT NOT NULL, user_id INTEGER NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS saved_pins (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, note TEXT DEFAULT '', lat REAL NOT NULL, lng REAL NOT NULL, color TEXT NOT NULL DEFAULT '#6c55d9', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS stamp_shops (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, area TEXT NOT NULL, category TEXT NOT NULL, description TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS user_stamps (user_id INTEGER NOT NULL, shop_id INTEGER NOT NULL, stamped_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, shop_id));
        CREATE TABLE IF NOT EXISTS stamp_rewards (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, stamp_count INTEGER NOT NULL DEFAULT 10, amount INTEGER NOT NULL DEFAULT 3000, redeemed_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS stamp_redemptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, stamp_count INTEGER NOT NULL, amount INTEGER NOT NULL, redeemed_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS stamp_applications (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_name TEXT NOT NULL, shop_name TEXT NOT NULL, area TEXT NOT NULL, contact TEXT NOT NULL, message TEXT DEFAULT '', status TEXT NOT NULL DEFAULT '접수됨', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS friend_events (user_id INTEGER NOT NULL, event_code TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, event_code));
        CREATE TABLE IF NOT EXISTS group_maps (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', leader_id INTEGER NOT NULL, price INTEGER NOT NULL DEFAULT 990, invite_code TEXT NOT NULL UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS group_members (map_id INTEGER NOT NULL, user_id INTEGER NOT NULL, joined_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(map_id, user_id));
        CREATE TABLE IF NOT EXISTS group_pins (id INTEGER PRIMARY KEY AUTOINCREMENT, map_id INTEGER NOT NULL, user_id INTEGER NOT NULL, name TEXT NOT NULL, note TEXT DEFAULT '', lat REAL NOT NULL, lng REAL NOT NULL, color TEXT NOT NULL DEFAULT '#c9343d', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS external_data (resultCode TEXT, resultMsg TEXT, numOfRows TEXT, pageNo TEXT, totalCount TEXT, UC_SEQ TEXT, MAIN_TITLE TEXT, GUGUN_NM TEXT, LAT TEXT, LNG TEXT, PLACE TEXT, TITLE TEXT, SUBTITLE TEXT, ADDR1 TEXT, ADDR2 TEXT, CNTCT_TEL TEXT, HOMEPAGE_URL TEXT, USAGE_DAY_WEEK_AND_TIME TEXT, RPRSNTV_MENU TEXT, MAIN_IMG_NORMAL TEXT, MAIN_IMG_THUMB TEXT, ITEMCNTNTS TEXT);
        ''')
        if conn.execute('SELECT count(*) FROM users').fetchone()[0] == 0:
            conn.executemany('INSERT INTO users(id,nickname,bio,points,avatar) VALUES(?,?,?,?,?)', [
                (1,'여행하는 민지','낯선 골목에서 가장 좋아하는 장면을 찾아요.',3200,'🌷'),
                (2,'유진의 주말','서울의 느린 하루를 모아요.',1850,'☀️'),
                (3,'카페 수집가','작업하기 좋은 자리를 기록합니다.',2450,'☕'),
                (4,'도윤 산책','걷고 먹고 사진 찍는 코스.',900,'🌿')])
            seed=[
                ('연남동, 혼자 걷기 좋은 오후','조용한 책방과 커피, 작은 공원을 따라 걷는 나만의 오후 코스예요.','혼자 가기 좋은 곳',2,500,[(37.5619,126.9237,'어쩌다 책방','마포구 연희로','첫 장소는 천천히 둘러보기'),(37.5628,126.9258,'낙타 커피','마포구 동교로','창가 자리를 추천해요'),(37.5639,126.9271,'연남동 산책길','마포구 연남동','해 질 무렵 걷기 좋아요')]),
                ('성수동 데이트, 빛나는 하루','전시와 디저트, 서울숲까지 자연스럽게 이어지는 데이트 동선.','데이트 코스',4,1000,[(37.5446,127.0557,'성수 전시 공간','성동구 성수이로','전시 예약을 확인해요'),(37.5457,127.0574,'버터룸','성동구 연무장길','디저트는 나눠 먹기'),(37.5438,127.0538,'서울숲','성동구 뚝섬로','노을 시간 추천')]),
                ('서촌에서 일하는 날','집중과 휴식의 균형을 찾는 서촌 카페 루트.','작업하기 좋은 카페',3,0,[(37.5795,126.9692,'서촌 작업실','종로구 자하문로','콘센트 있는 긴 테이블'),(37.5807,126.9710,'고요한 커피','종로구 필운대로','오전에는 특히 조용해요'),(37.5820,126.9698,'통인시장','종로구 자하문로','작업 후 간단한 간식')]),
                ('망원 한강 피크닉 지도','장보기부터 노을까지, 친구들과 가볍게 즐기는 주말 코스.','인기 코스',2,500,[(37.5562,126.9018,'망원시장','마포구 포은로','간식은 여기서 준비'),(37.5548,126.9060,'망원한강공원','마포구 마포나루길','돗자리 펴기 좋은 잔디'),(37.5524,126.9084,'한강 노을 포인트','마포구','해 지기 30분 전 도착')])]
            for title,intro,cat,creator,price,spots in seed:
                cur=conn.execute('INSERT INTO courses(title,intro,category,creator_id,price) VALUES(?,?,?,?,?)',(title,intro,cat,creator,price))
                for n,(lat,lng,name,address,memo) in enumerate(spots,1):
                    conn.execute('INSERT INTO places(course_id,name,address,lat,lng,memo,position) VALUES(?,?,?,?,?,?,?)',(cur.lastrowid,name,address,lat,lng,memo,n))
            conn.executemany('INSERT INTO course_likes(user_id,course_id) VALUES(?,?)',[(1,1),(1,3),(2,1),(3,1),(4,2),(3,4)])
            conn.executemany('INSERT INTO follows(follower_id,creator_id) VALUES(?,?)',[(1,2),(1,3),(2,3),(4,2)])
        if conn.execute('SELECT count(*) FROM stamp_shops').fetchone()[0] == 0:
            shops=[('낙타 커피','연남','카페','창가에서 쉬기 좋은 연남의 참여 카페'),('어쩌다 책방','연남','서점','여행의 영감을 채우는 독립서점'),('버터룸','성수','디저트','달콤한 디저트를 만나는 참여 매장'),('고요한 커피','서촌','카페','차분히 머물기 좋은 작업 카페'),('망원시장','망원','시장','피크닉 간식을 고르는 지역 상점')]
            conn.executemany('INSERT INTO stamp_shops(name,area,category,description) VALUES(?,?,?,?)',shops)
            conn.executemany('INSERT INTO user_stamps(user_id,shop_id) VALUES(?,?)',[(1,1),(1,2),(1,3)])
        if conn.execute('SELECT count(*) FROM external_data').fetchone()[0] == 0:
            restaurants=[
                ('1001','초량밀면','동구','35.1158','129.0403','초량','부산 동구 중앙대로 225','부산식 밀면과 만두를 함께 즐기는 식당','매일 10:30~20:30','밀면, 만두'),
                ('1002','전포 카페거리 브런치','부산진구','35.1576','129.0642','전포','부산 부산진구 전포대로 199','전포 카페거리에서 가볍게 즐기는 브런치','매일 10:00~21:00','브런치, 커피'),
                ('1003','광안리 바다국수','수영구','35.1532','129.1186','광안','부산 수영구 광안해변로 245','바다를 바라보며 먹는 따뜻한 국수','매일 11:00~22:00','해물국수'),
                ('1004','남포동 돼지국밥','중구','35.0997','129.0302','남포','부산 중구 광복로 46','오래된 골목의 든든한 한 끼','매일 08:00~21:00','돼지국밥'),
                ('1005','해운대 달빛횟집','해운대구','35.1588','129.1603','해운대','부산 해운대구 해운대해변로 286','제철 회와 해운대 밤바다를 즐기는 곳','매일 12:00~23:00','모둠회'),
                ('1006','송정 로스터리','해운대구','35.1807','129.1993','송정','부산 해운대구 송정해변로 18','파도 소리와 함께 쉬어 가는 로스터리','매일 09:00~20:00','드립커피'),
                ('1007','흰여울 골목식당','영도구','35.0786','129.0444','영도','부산 영도구 흰여울문화마을길 75','절벽 골목 산책 뒤 들르기 좋은 식당','화~일 11:00~19:00','생선구이'),
                ('1008','온천장 소금빵','동래구','35.2204','129.0851','온천장','부산 동래구 온천장로 107','갓 구운 빵을 만나는 작은 베이커리','매일 09:00~19:00','소금빵'),
                ('1009','다대포 노을카페','사하구','35.0476','128.9677','다대포','부산 사하구 다대낙조2길 17','노을 시간에 들르기 좋은 바다 카페','매일 11:00~21:00','라테, 케이크'),
                ('1010','기장 해녀의 밥상','기장군','35.2442','129.2151','기장','부산 기장군 기장해안로 101','해산물로 차린 정갈한 한 상','매일 10:30~20:00','전복솥밥'),
                ('1011','부평 깡통시장 분식','중구','35.1024','129.0263','부평','부산 중구 부평1길 48','시장 안에서 즐기는 부산식 분식','매일 11:00~22:00','떡볶이, 튀김'),
                ('1012','청사포 조개구이','해운대구','35.1609','129.1912','청사포','부산 해운대구 청사포로 139','바다 바람과 함께 즐기는 조개구이','매일 12:00~22:00','조개구이'),
                ('1013','서면 비건키친','부산진구','35.1570','129.0595','서면','부산 부산진구 서전로 35','가볍고 든든한 식물성 한 끼','매일 11:30~20:30','비건볼'),
                ('1014','감천 골목다방','사하구','35.0975','129.0100','감천','부산 사하구 감내2로 203','알록달록 마을을 걷다 쉬는 다방','수~월 10:00~18:00','핸드드립'),
                ('1015','명지 수제버거','강서구','35.0952','128.9057','명지','부산 강서구 명지국제8로 252','두툼한 패티가 인상적인 수제버거','매일 11:00~21:00','치즈버거'),
            ]
            conn.executemany('''INSERT INTO external_data(resultCode,resultMsg,numOfRows,pageNo,totalCount,UC_SEQ,MAIN_TITLE,GUGUN_NM,LAT,LNG,PLACE,TITLE,SUBTITLE,ADDR1,ADDR2,CNTCT_TEL,HOMEPAGE_URL,USAGE_DAY_WEEK_AND_TIME,RPRSNTV_MENU,MAIN_IMG_NORMAL,MAIN_IMG_THUMB,ITEMCNTNTS) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', [('0000','정상','15','1','15',seq,title,area,lat,lng,place,title,'부산 맛집 정보',addr,'','','',hours,menu,'','',desc) for seq,title,area,lat,lng,place,addr,desc,hours,menu in restaurants])
app=FastAPI()
init_db()
class Toggle(BaseModel): user_id:int=1
class Purchase(BaseModel): buyer_id:int=1
class PlaceIn(BaseModel): name:str; address:str=''; lat:float; lng:float; memo:str=''; position:int
class CourseIn(BaseModel): title:str; intro:str; category:str; price:int=0; creator_id:int=1; places:list[PlaceIn]
class MapNoteIn(BaseModel): text:str; lat:float; lng:float; user_id:int=1
class AccountIn(BaseModel): email:str; password:str; nickname:str=''
class LoginIn(BaseModel): email:str; password:str
class PinIn(BaseModel): name:str; note:str=''; lat:float; lng:float; color:str='#6c55d9'; user_id:int=1
class NearbyPlaceIn(BaseModel): lat:float; lng:float
class StampIn(BaseModel): user_id:int=1
class StampExchangeIn(BaseModel): user_id:int=1; stamp_count:int=5
class StampApplicationIn(BaseModel): owner_name:str; shop_name:str; area:str; contact:str; message:str=''
KAKAO_REST_API_KEY = os.environ.get('KAKAO_REST_API_KEY', '')
def kakao_keyword_search(query: str):
    if not KAKAO_REST_API_KEY:
        raise HTTPException(503, '장소 검색 키가 아직 연결되지 않았어요.')
    url = 'https://dapi.kakao.com/v2/local/search/keyword.json?' + urllib.parse.urlencode({'query': query, 'size': 8})
    request = urllib.request.Request(url, headers={'Authorization': f'KakaoAK {KAKAO_REST_API_KEY}'})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception:
        raise HTTPException(502, '장소 검색 서비스에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.')
    return [{
        'id': item.get('id', ''),
        'name': item.get('place_name', ''),
        'address': item.get('road_address_name') or item.get('address_name') or '',
        'category': item.get('category_name', ''),
        'phone': item.get('phone', ''),
        'lat': float(item['y']),
        'lng': float(item['x']),
    } for item in payload.get('documents', []) if item.get('x') and item.get('y')]
def kakao_building_search(lat: float, lng: float):
    if not KAKAO_REST_API_KEY: return []
    query = f'{lat:.6f},{lng:.6f}'
    url = 'https://dapi.kakao.com/v2/local/geo/coord2address.json?' + urllib.parse.urlencode({'x':lng, 'y':lat})
    request = urllib.request.Request(url, headers={'Authorization': f'KakaoAK {KAKAO_REST_API_KEY}'})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            addresses = json.loads(response.read().decode('utf-8')).get('documents', [])
    except Exception:
        return []
    road = next((item.get('road_address', {}).get('address_name', '') for item in addresses if item.get('road_address')), '')
    if not road: return []
    search_url = 'https://dapi.kakao.com/v2/local/search/keyword.json?' + urllib.parse.urlencode({'query':road, 'size':15})
    search_request = urllib.request.Request(search_url, headers={'Authorization': f'KakaoAK {KAKAO_REST_API_KEY}'})
    try:
        with urllib.request.urlopen(search_request, timeout=5) as response:
            places = json.loads(response.read().decode('utf-8')).get('documents', [])
    except Exception:
        return []
    return [{
        'name': item.get('place_name', ''),
        'address': item.get('road_address_name') or item.get('address_name') or road,
        'distance': 0,
        'category': item.get('category_name', '').split(' > ')[-1] or '장소',
    } for item in places if (item.get('road_address_name') or item.get('address_name') or '') == road]
def profile_data(conn, user_id, viewer=1):
    u=conn.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
    if not u: raise HTTPException(404,'사용자를 찾을 수 없어요.')
    d=dict(u)
    d['followers']=conn.execute('SELECT count(*) FROM follows WHERE creator_id=?',(user_id,)).fetchone()[0]
    d['following']=conn.execute('SELECT count(*) FROM follows WHERE follower_id=?',(user_id,)).fetchone()[0]
    d['followed']=bool(conn.execute('SELECT 1 FROM follows WHERE follower_id=? AND creator_id=?',(viewer,user_id)).fetchone()) if user_id!=viewer else False
    d['courses']=[course_data(conn,c,viewer) for c in conn.execute('SELECT * FROM courses WHERE creator_id=?',(user_id,)).fetchall()]
    d['library']=[course_data(conn,c,viewer) for c in conn.execute('SELECT c.* FROM courses c JOIN purchases p ON p.course_id=c.id WHERE p.buyer_id=?',(user_id,)).fetchall()]
    return d
def course_data(conn, course, viewer=1, detail=False):
    d=dict(course); cid=d['id']
    d['creator']=dict(conn.execute('SELECT id,nickname,bio,avatar FROM users WHERE id=?',(d['creator_id'],)).fetchone())
    d['like_count']=conn.execute('SELECT count(*) FROM course_likes WHERE course_id=?',(cid,)).fetchone()[0]
    d['purchase_count']=conn.execute('SELECT count(*) FROM purchases WHERE course_id=?',(cid,)).fetchone()[0]
    d['liked']=bool(conn.execute('SELECT 1 FROM course_likes WHERE user_id=? AND course_id=?',(viewer,cid)).fetchone())
    d['owned']=d['price']==0 or d['creator_id']==viewer or bool(conn.execute('SELECT 1 FROM purchases WHERE buyer_id=? AND course_id=?',(viewer,cid)).fetchone())
    d['places']=rows(conn.execute('SELECT * FROM places WHERE course_id=? ORDER BY position',(cid,)).fetchall())
    if detail and not d['owned']: d['places']=d['places'][:1]
    return d
@app.get('/api/health')
def health(): return {'ok':True}
@app.post('/api/auth/signup')
def signup(body:AccountIn):
    if '@' not in body.email or len(body.password) < 4 or not body.nickname.strip():
        raise HTTPException(400,'이메일, 4자 이상 비밀번호, 닉네임을 입력해 주세요.')
    with get_db() as conn:
        if conn.execute('SELECT 1 FROM accounts WHERE email=?',(body.email.lower().strip(),)).fetchone(): raise HTTPException(400,'이미 가입된 이메일이에요.')
        cur=conn.execute('INSERT INTO users(nickname,bio,points,avatar) VALUES(?,?,?,?)',(body.nickname.strip(),'나만의 순간을 지도에 모으고 있어요.',1500,'📍'))
        conn.execute('INSERT INTO accounts(email,password,user_id) VALUES(?,?,?)',(body.email.lower().strip(),body.password,cur.lastrowid))
        return {'user':profile_data(conn,cur.lastrowid,cur.lastrowid)}
@app.post('/api/auth/login')
def login(body:LoginIn):
    with get_db() as conn:
        account=conn.execute('SELECT user_id FROM accounts WHERE email=? AND password=?',(body.email.lower().strip(),body.password)).fetchone()
        if not account: raise HTTPException(400,'이메일 또는 비밀번호를 확인해 주세요.')
        return {'user':profile_data(conn,account['user_id'],account['user_id'])}
@app.get('/api/me')
def me(user_id:int=1):
    with get_db() as conn: return profile_data(conn,user_id,user_id)
@app.get('/api/courses')
def courses(category:Optional[str]=None, user_id:int=1):
    with get_db() as conn:
        q='SELECT * FROM courses WHERE published=1'; args=[]
        if category and category!='전체': q+=' AND category=?'; args.append(category)
        return [course_data(conn,c,user_id) for c in conn.execute(q+' ORDER BY id DESC',args).fetchall()]
@app.get('/api/courses/{course_id}')
def course(course_id:int, user_id:int=1):
    with get_db() as conn:
        c=conn.execute('SELECT * FROM courses WHERE id=?',(course_id,)).fetchone()
        if not c: raise HTTPException(404,'코스를 찾을 수 없어요.')
        return course_data(conn,c,user_id,detail=True)
@app.post('/api/courses/{course_id}/like')
def like(course_id:int, body:Toggle):
    with get_db() as conn:
        exists=conn.execute('SELECT 1 FROM course_likes WHERE user_id=? AND course_id=?',(body.user_id,course_id)).fetchone()
        if exists: conn.execute('DELETE FROM course_likes WHERE user_id=? AND course_id=?',(body.user_id,course_id)); state=False
        else: conn.execute('INSERT INTO course_likes VALUES(?,?)',(body.user_id,course_id)); state=True
        return {'liked':state,'count':conn.execute('SELECT count(*) FROM course_likes WHERE course_id=?',(course_id,)).fetchone()[0]}
@app.post('/api/courses/{course_id}/purchase')
def purchase(course_id:int, body:Purchase):
    with get_db() as conn:
        c=conn.execute('SELECT * FROM courses WHERE id=?',(course_id,)).fetchone()
        if not c: raise HTTPException(404,'코스를 찾을 수 없어요.')
        if c['creator_id']==body.buyer_id or c['price']==0: return {'ok':True,'message':'바로 열람할 수 있는 코스예요.'}
        if conn.execute('SELECT 1 FROM purchases WHERE buyer_id=? AND course_id=?',(body.buyer_id,course_id)).fetchone(): raise HTTPException(400,'이미 보관함에 있는 코스예요.')
        buyer=conn.execute('SELECT points FROM users WHERE id=?',(body.buyer_id,)).fetchone()
        if buyer['points']<c['price']: raise HTTPException(400,'포인트가 부족해요.')
        conn.execute('UPDATE users SET points=points-? WHERE id=?',(c['price'],body.buyer_id)); conn.execute('UPDATE users SET points=points+? WHERE id=?',(c['price'],c['creator_id']))
        conn.execute('INSERT INTO purchases(buyer_id,course_id,amount) VALUES(?,?,?)',(body.buyer_id,course_id,c['price']))
        conn.execute('INSERT INTO transactions(user_id,amount,type,note) VALUES(?,?,?,?)',(body.buyer_id,-c['price'],'구매',c['title']))
        conn.execute('INSERT INTO transactions(user_id,amount,type,note) VALUES(?,?,?,?)',(c['creator_id'],c['price'],'판매',c['title']))
        return {'ok':True,'points':buyer['points']-c['price']}
@app.post('/api/courses')
def create_course(body:CourseIn):
    if not body.title.strip() or not body.intro.strip() or len(body.places)<2: raise HTTPException(400,'제목, 소개, 두 곳 이상의 장소가 필요해요.')
    with get_db() as conn:
        cur=conn.execute('INSERT INTO courses(title,intro,category,creator_id,price) VALUES(?,?,?,?,?)',(body.title,body.intro,body.category,body.creator_id,body.price))
        for p in body.places: conn.execute('INSERT INTO places(course_id,name,address,lat,lng,memo,position) VALUES(?,?,?,?,?,?,?)',(cur.lastrowid,p.name,p.address,p.lat,p.lng,p.memo,p.position))
        return {'id':cur.lastrowid}
@app.get('/api/profile/{user_id}')
def profile(user_id:int, viewer_id:int=1):
    with get_db() as conn: return profile_data(conn,user_id,viewer_id)
@app.post('/api/profile/{user_id}/follow')
def follow(user_id:int, body:Toggle):
    if user_id==body.user_id: raise HTTPException(400,'나 자신은 팔로우할 수 없어요.')
    with get_db() as conn:
        e=conn.execute('SELECT 1 FROM follows WHERE follower_id=? AND creator_id=?',(body.user_id,user_id)).fetchone()
        if e: conn.execute('DELETE FROM follows WHERE follower_id=? AND creator_id=?',(body.user_id,user_id)); state=False
        else: conn.execute('INSERT INTO follows VALUES(?,?)',(body.user_id,user_id)); state=True
        return {'followed':state,'count':conn.execute('SELECT count(*) FROM follows WHERE creator_id=?',(user_id,)).fetchone()[0]}
@app.get('/api/rankings')
def rankings(user_id:int=1):
    with get_db() as conn:
        cs=[course_data(conn,c,user_id) for c in conn.execute('SELECT * FROM courses WHERE published=1').fetchall()]
        cs.sort(key=lambda x:x['like_count']*2+x['purchase_count']*3,reverse=True)
        us=rows(conn.execute('SELECT u.*,count(f.follower_id) followers FROM users u LEFT JOIN follows f ON f.creator_id=u.id GROUP BY u.id ORDER BY followers DESC LIMIT 20').fetchall())
        return {'courses':cs[:20],'creators':us}
@app.get('/api/recommendations')
def recommendations(user_id:int=1):
    with get_db() as conn:
        liked=rows(conn.execute('SELECT c.category FROM courses c JOIN course_likes l ON l.course_id=c.id WHERE l.user_id=?',(user_id,)).fetchall())
        cats=[x['category'] for x in liked]; q='SELECT * FROM courses WHERE published=1'; args=[]
        if cats: q+=' AND category IN ('+','.join('?' for _ in cats)+')'; args=cats
        q+=' ORDER BY id DESC'
        return [course_data(conn,c,user_id) for c in conn.execute(q,args).fetchall()][:6]
@app.get('/api/busan-restaurants')
def busan_restaurants(limit:int=6, offset:int=0):
    safe_limit=max(1,min(limit,20)); safe_offset=max(0,offset)
    with get_db() as conn:
        items=rows(conn.execute('SELECT * FROM external_data ORDER BY CAST(UC_SEQ AS INTEGER) LIMIT ? OFFSET ?',(safe_limit,safe_offset)).fetchall())
        total=conn.execute('SELECT count(*) FROM external_data').fetchone()[0]
        return {'items':items,'total':total,'limit':safe_limit,'offset':safe_offset}
@app.get('/api/place-search')
def place_search(query:str=''):
    if len(query.strip()) < 2: raise HTTPException(400,'두 글자 이상 입력해 주세요.')
    return kakao_keyword_search(query.strip())
@app.post('/api/nearby-places')
def nearby_places(body:NearbyPlaceIn):
    candidates=kakao_building_search(body.lat, body.lng)
    with get_db() as conn:
        if not candidates:
            for item in conn.execute('SELECT name,address,lat,lng FROM places').fetchall():
                distance=(((float(item['lat'])-body.lat)**2+(float(item['lng'])-body.lng)**2)**.5)*111000
                if distance<=12:
                    candidates.append({'name':item['name'],'address':item['address'],'distance':0,'category':'핀플 코스 장소'})
        unique=[]; seen=set()
        for item in candidates:
            if item['name'] not in seen:
                unique.append(item); seen.add(item['name'])
        return {'items':unique[:15],'building_only':True}
@app.get('/api/map-notes')
def map_notes(user_id:int=1):
    with get_db() as conn: return rows(conn.execute('SELECT * FROM map_notes WHERE user_id=? ORDER BY id DESC',(user_id,)).fetchall())
@app.post('/api/map-notes')
def add_map_note(body:MapNoteIn):
    if not body.text.strip(): raise HTTPException(400,'메모 내용을 입력해 주세요.')
    with get_db() as conn:
        cur=conn.execute('INSERT INTO map_notes(user_id,text,lat,lng) VALUES(?,?,?,?)',(body.user_id,body.text.strip(),body.lat,body.lng))
        return dict(conn.execute('SELECT * FROM map_notes WHERE id=?',(cur.lastrowid,)).fetchone())
@app.get('/api/pins')
def pins(user_id:int=1):
    with get_db() as conn: return rows(conn.execute('SELECT * FROM saved_pins WHERE user_id=? ORDER BY id DESC',(user_id,)).fetchall())
@app.post('/api/pins')
def add_pin(body:PinIn):
    if not body.name.strip(): raise HTTPException(400,'핀 이름을 입력해 주세요.')
    with get_db() as conn:
        cur=conn.execute('INSERT INTO saved_pins(user_id,name,note,lat,lng,color) VALUES(?,?,?,?,?,?)',(body.user_id,body.name.strip(),body.note.strip(),body.lat,body.lng,body.color))
        return dict(conn.execute('SELECT * FROM saved_pins WHERE id=?',(cur.lastrowid,)).fetchone())
@app.get('/api/pin-recommendations')
def pin_recommendations(user_id:int=1):
    with get_db() as conn:
        saved=rows(conn.execute('SELECT * FROM saved_pins WHERE user_id=? ORDER BY id DESC',(user_id,)).fetchall())
        groups=[]
        for color in list(dict.fromkeys(pin['color'] for pin in saved)):
            color_pins=[pin for pin in saved if pin['color']==color]
            candidates=[]
            for course in conn.execute('SELECT * FROM courses WHERE published=1').fetchall():
                places=rows(conn.execute('SELECT * FROM places WHERE course_id=? ORDER BY position',(course['id'],)).fetchall())
                if not places: continue
                nearest=min((pin['lat']-place['lat'])**2+(pin['lng']-place['lng'])**2 for pin in color_pins for place in places)
                data=course_data(conn,course,user_id)
                data['match_score']=round(1/(1+nearest*15000)*100)
                candidates.append((nearest,-data['like_count'],-data['purchase_count'],data))
            candidates.sort(key=lambda item:(item[0],item[1],item[2]))
            groups.append({'color':color,'pin_count':len(color_pins),'pins':color_pins[:3],'courses':[item[3] for item in candidates[:4]]})
        return {'groups':groups}
@app.delete('/api/pins/{pin_id}')
def remove_pin(pin_id:int):
    with get_db() as conn:
        conn.execute('DELETE FROM saved_pins WHERE id=? AND user_id=1',(pin_id,))
        return {'ok':True}
@app.get('/api/stamps')
def stamps(user_id:int=1):
    with get_db() as conn:
        shops=rows(conn.execute('''SELECT s.*, CASE WHEN us.shop_id IS NULL THEN 0 ELSE 1 END stamped
            FROM stamp_shops s LEFT JOIN user_stamps us ON us.shop_id=s.id AND us.user_id=? ORDER BY s.id''',(user_id,)).fetchall())
        count=conn.execute('SELECT count(*) FROM user_stamps WHERE user_id=?',(user_id,)).fetchone()[0]
        redeemed=conn.execute('SELECT COALESCE(sum(stamp_count),0) FROM stamp_redemptions WHERE user_id=?',(user_id,)).fetchone()[0]
        available=count-redeemed
        rewards=conn.execute('SELECT count(*) FROM stamp_redemptions WHERE user_id=?',(user_id,)).fetchone()[0]
        return {'shops':shops,'stamp_count':count,'available_stamps':available,'redeemed_stamps':redeemed,'rewards':rewards,'next_reward':max(0,5-available),'next_major_reward':max(0,10-available)}
@app.post('/api/stamps/{shop_id}')
def collect_stamp(shop_id:int, body:StampIn):
    with get_db() as conn:
        shop=conn.execute('SELECT name FROM stamp_shops WHERE id=?',(shop_id,)).fetchone()
        if not shop: raise HTTPException(404,'참여 가게를 찾을 수 없어요.')
        if conn.execute('SELECT 1 FROM user_stamps WHERE user_id=? AND shop_id=?',(body.user_id,shop_id)).fetchone(): raise HTTPException(400,'이미 받은 스탬프예요.')
        conn.execute('INSERT INTO user_stamps(user_id,shop_id) VALUES(?,?)',(body.user_id,shop_id))
        count=conn.execute('SELECT count(*) FROM user_stamps WHERE user_id=?',(body.user_id,)).fetchone()[0]
        redeemed=conn.execute('SELECT COALESCE(sum(stamp_count),0) FROM stamp_redemptions WHERE user_id=?',(body.user_id,)).fetchone()[0]
        points=conn.execute('SELECT points FROM users WHERE id=?',(body.user_id,)).fetchone()[0]
        return {'ok':True,'shop_name':shop['name'],'stamp_count':count,'available_stamps':count-redeemed,'points':points,'rewarded':False}
@app.post('/api/stamp-exchange')
def stamp_exchange(body:StampExchangeIn):
    if body.stamp_count not in (5, 10): raise HTTPException(400,'5개 또는 10개 단위로 교환할 수 있어요.')
    amount = 1000 if body.stamp_count == 5 else 3000
    with get_db() as conn:
        total=conn.execute('SELECT count(*) FROM user_stamps WHERE user_id=?',(body.user_id,)).fetchone()[0]
        used=conn.execute('SELECT COALESCE(sum(stamp_count),0) FROM stamp_redemptions WHERE user_id=?',(body.user_id,)).fetchone()[0]
        available=total-used
        if available < body.stamp_count: raise HTTPException(400,f'교환 가능한 스탬프가 {body.stamp_count}개 이상 필요해요.')
        conn.execute('INSERT INTO stamp_redemptions(user_id,stamp_count,amount) VALUES(?,?,?)',(body.user_id,body.stamp_count,amount))
        conn.execute('INSERT INTO stamp_rewards(user_id,stamp_count,amount) VALUES(?,?,?)',(body.user_id,body.stamp_count,amount))
        conn.execute('UPDATE users SET points=points+? WHERE id=?',(amount,body.user_id))
        conn.execute('INSERT INTO transactions(user_id,amount,type,note) VALUES(?,?,?,?)',(body.user_id,amount,'스탬프 교환',f'스탬프 {body.stamp_count}개 교환'))
        points=conn.execute('SELECT points FROM users WHERE id=?',(body.user_id,)).fetchone()[0]
        return {'ok':True,'stamp_count':body.stamp_count,'amount':amount,'available_stamps':available-body.stamp_count,'points':points}
@app.post('/api/stamp-applications')
def stamp_application(body:StampApplicationIn):
    if not all([body.owner_name.strip(), body.shop_name.strip(), body.area.strip(), body.contact.strip()]):
        raise HTTPException(400,'이름, 가게명, 지역, 연락처를 모두 입력해 주세요.')
    with get_db() as conn:
        cur=conn.execute('INSERT INTO stamp_applications(owner_name,shop_name,area,contact,message) VALUES(?,?,?,?,?)',(body.owner_name.strip(),body.shop_name.strip(),body.area.strip(),body.contact.strip(),body.message.strip()))
        return {'ok':True,'id':cur.lastrowid,'message':'참여 요청이 접수됐어요. 검토 후 안내드릴게요.'}
class FriendEventIn(BaseModel): event_code:str='friend-join'; user_id:int=1
class GroupMapIn(BaseModel): title:str; description:str=''; user_id:int=1
class JoinGroupIn(BaseModel): invite_code:str; user_id:int=1
class GroupPinIn(BaseModel): name:str; note:str=''; lat:float; lng:float; color:str='#c9343d'; user_id:int=1
def group_map_data(conn, item, viewer=1):
    data=dict(item)
    data['member_count']=conn.execute('SELECT count(*) FROM group_members WHERE map_id=?',(data['id'],)).fetchone()[0]
    data['joined']=bool(conn.execute('SELECT 1 FROM group_members WHERE map_id=? AND user_id=?',(data['id'],viewer)).fetchone())
    leader=conn.execute('SELECT nickname,avatar FROM users WHERE id=?',(data['leader_id'],)).fetchone()
    data['leader']=dict(leader) if leader else {'nickname':'팀장','avatar':'📍'}
    data['pins']=rows(conn.execute('''SELECT p.*, u.nickname, u.avatar FROM group_pins p
        JOIN users u ON u.id=p.user_id WHERE p.map_id=? ORDER BY p.id DESC''',(data['id'],)).fetchall())
    return data
@app.post('/api/friend-event')
def friend_event(body:FriendEventIn):
    with get_db() as conn:
        if conn.execute('SELECT 1 FROM friend_events WHERE user_id=? AND event_code=?',(body.user_id,body.event_code)).fetchone():
            raise HTTPException(400,'이미 참여한 친구 추가 이벤트예요.')
        conn.execute('INSERT INTO friend_events(user_id,event_code) VALUES(?,?)',(body.user_id,body.event_code))
        conn.execute('UPDATE users SET points=points+500 WHERE id=?',(body.user_id,))
        conn.execute('INSERT INTO transactions(user_id,amount,type,note) VALUES(?,?,?,?)',(body.user_id,500,'친구 추가 이벤트','친구와 함께 시작 보상'))
        return {'ok':True,'points':conn.execute('SELECT points FROM users WHERE id=?',(body.user_id,)).fetchone()[0], 'amount':500}
@app.get('/api/group-maps')
def group_maps(user_id:int=1):
    with get_db() as conn:
        items=conn.execute('''SELECT gm.* FROM group_maps gm JOIN group_members m ON m.map_id=gm.id
            WHERE m.user_id=? ORDER BY gm.id DESC''',(user_id,)).fetchall()
        return [group_map_data(conn, item, user_id) for item in items]
@app.post('/api/group-maps')
def create_group_map(body:GroupMapIn):
    if not body.title.strip(): raise HTTPException(400,'모임 지도 이름을 입력해 주세요.')
    with get_db() as conn:
        leader=conn.execute('SELECT points FROM users WHERE id=?',(body.user_id,)).fetchone()
        if not leader: raise HTTPException(404,'팀장 정보를 찾을 수 없어요.')
        if leader['points'] < 990: raise HTTPException(400,'모임 지도를 만들 포인트가 부족해요. 990포인트가 필요해요.')
        code='PIN'+str(abs(hash(body.title.strip()+str(conn.execute('SELECT count(*) FROM group_maps').fetchone()[0])))%900000+100000)
        while conn.execute('SELECT 1 FROM group_maps WHERE invite_code=?',(code,)).fetchone(): code='PIN'+str(int(code[3:])+1)
        conn.execute('UPDATE users SET points=points-990 WHERE id=?',(body.user_id,))
        cur=conn.execute('INSERT INTO group_maps(title,description,leader_id,price,invite_code) VALUES(?,?,?,?,?)',(body.title.strip(),body.description.strip(),body.user_id,990,code))
        conn.execute('INSERT INTO group_members(map_id,user_id) VALUES(?,?)',(cur.lastrowid,body.user_id))
        conn.execute('INSERT INTO transactions(user_id,amount,type,note) VALUES(?,?,?,?)',(body.user_id,-990,'모임 지도 생성',body.title.strip()))
        data=group_map_data(conn,conn.execute('SELECT * FROM group_maps WHERE id=?',(cur.lastrowid,)).fetchone(),body.user_id)
        data['points']=leader['points']-990
        return data
@app.post('/api/group-maps/join')
def join_group_map(body:JoinGroupIn):
    with get_db() as conn:
        item=conn.execute('SELECT * FROM group_maps WHERE invite_code=?',(body.invite_code.strip().upper(),)).fetchone()
        if not item: raise HTTPException(404,'초대 코드를 찾을 수 없어요.')
        if not conn.execute('SELECT 1 FROM users WHERE id=?',(body.user_id,)).fetchone(): raise HTTPException(404,'팀원 정보를 찾을 수 없어요.')
        existing=conn.execute('SELECT 1 FROM group_members WHERE map_id=? AND user_id=?',(item['id'],body.user_id)).fetchone()
        if not existing:
            count=conn.execute('SELECT count(*) FROM group_members WHERE map_id=?',(item['id'],)).fetchone()[0]
            if count>=10: raise HTTPException(400,'이 모임 지도는 이미 10명이 참여 중이에요.')
            conn.execute('INSERT INTO group_members(map_id,user_id) VALUES(?,?)',(item['id'],body.user_id))
        return group_map_data(conn,item,body.user_id)
@app.post('/api/group-maps/{map_id}/pins')
def add_group_pin(map_id:int, body:GroupPinIn):
    if not body.name.strip(): raise HTTPException(400,'핀 이름을 입력해 주세요.')
    with get_db() as conn:
        if not conn.execute('SELECT 1 FROM group_members WHERE map_id=? AND user_id=?',(map_id,body.user_id)).fetchone(): raise HTTPException(403,'참여한 모임 지도에서만 핀을 남길 수 있어요.')
        cur=conn.execute('INSERT INTO group_pins(map_id,user_id,name,note,lat,lng,color) VALUES(?,?,?,?,?,?,?)',(map_id,body.user_id,body.name.strip(),body.note.strip(),body.lat,body.lng,body.color))
        return dict(conn.execute('SELECT * FROM group_pins WHERE id=?',(cur.lastrowid,)).fetchone())
