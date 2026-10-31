import os, sqlite3, warnings
warnings.filterwarnings("ignore")
os.environ["TZ"]="Asia/Kolkata"
os.environ["RESET_KEY"]="testkey"
import time; time.tzset()
from datetime import datetime, timedelta
import app as A
from werkzeug.security import generate_password_hash
A.app.config['TESTING']=True
res=[]
def chk(name,cond,info=""):
    res.append((name,bool(cond),info)); print(("PASS " if cond else "FAIL ")+name+(f"  [{info}]" if info and not cond else ""))
def cl(): return A.app.test_client()
def login(c,n,r,pw="demo123"): return c.post('/login',data={'name':n,'password':pw,'role':r})
def sql(q,a=()):
    d=sqlite3.connect('food_rescue.db');d.row_factory=sqlite3.Row;r=d.execute(q,a).fetchall();d.commit();d.close();return r
boot=cl(); boot.get('/reset-demo?confirm=true&key=testkey')
users={r['name']:(r['id'],r['role']) for r in sql('select id,name,role from users')}
print("users:",users)
now=datetime.now(); f=lambda d:d.strftime('%Y-%m-%dT%H:%M')

print("\n--- ANON ACCESS ---")
a=cl()
for p in ['/donate','/ngo/offers','/volunteer/tasks','/api/ngo/offers','/api/volunteer/tasks']:
    r=a.get(p); chk(f"anon GET {p} blocked", r.status_code in (301,302,401,403), r.status_code)
for p in ['/accept/1','/decline/1','/pickup/1','/deliver/1']:
    r=a.post(p,data={'otp':'4821'}); chk(f"anon POST {p} blocked", r.status_code in (301,302,401,403), r.status_code)
r=a.get('/reset-demo'); chk("anon /reset-demo without key is blocked", r.status_code in(401,403), r.status_code)
n0=sql('select count(*) c from donations')[0]['c']
r=a.get('/reset-demo?confirm=true&key=wrong'); n1=sql('select count(*) c from donations')[0]['c']
chk("anon /reset-demo?confirm=true must NOT wipe data", n0==n1 or r.status_code in (401,403), f"donations {n0}->{n1} status {r.status_code}")
chk("anon /dashboard public ok", a.get('/dashboard').status_code==200)
chk("anon /api/stats ok", a.get('/api/stats').status_code==200)

print("\n--- LOGIN ---")
chk("correct pw ok", login(cl(),'Green Valley Hostel','donor').status_code==302)
c=cl(); r=login(c,'Green Valley Hostel','donor','wrongpw'); 
chk("wrong pw rejected (no session)", 'user_id' not in dict(c.session_transaction().__enter__()), r.status_code)
# bypass: account with CUSTOM password logged in with demo123
sql("insert into users(name,role,phone,lat,lng,password,approved) values('Real Donor','donor','1',31.3,75.5,?,1)",(generate_password_hash('S3cretPass!'),))
c=cl(); login(c,'Real Donor','donor','demo123')
with c.session_transaction() as s: chk("custom-pw account NOT loginable with 'demo123'", 'user_id' not in s, dict(s))
c=cl(); login(c,'Real Donor','donor','S3cretPass!')
with c.session_transaction() as s: chk("custom-pw account loginable with real pw", 'user_id' in s)
c=cl(); login(c,'Real Donor','','demo123')
with c.session_transaction() as s: chk("role-omitted login w/ demo pw blocked for custom-pw acct", 'user_id' not in s, dict(s))
c=cl(); login(c,'Green Valley Hostel','ngo')  # wrong role for donor
with c.session_transaction() as s: chk("wrong role for user rejected", s.get('role')!='ngo', dict(s))

print("\n--- E2E LIFECYCLE ---")
donor=cl(); login(donor,'Green Valley Hostel','donor')
ngo=cl();   login(ngo,'Robin Hood Army','ngo')
vol=cl();   login(vol,'Aman Sharma','volunteer')
sql("delete from events"); sql("delete from donations")
r=donor.post('/donate',data={'food_type':'Cooked Meals (Rice & Dal)','quantity_kg':'25','cooked_at':f(now-timedelta(minutes=20)),'pickup_from':f(now+timedelta(minutes=20)),'pickup_to':f(now+timedelta(hours=2)),'lat':'31.3125','lng':'75.5804'},follow_redirects=True)
d=sql('select * from donations')
chk("donation created", len(d)==1, r.status_code)
if d:
    did=d[0]['id']; print("status after post:",d[0]['status'],"ngo_id",d[0]['ngo_id'])
    chk("auto-matched to NGO", d[0]['status']=='matched' and d[0]['ngo_id'], d[0]['status'])
    m=donor.get(f'/matches/{did}').get_json(); chk("/matches returns NGOs", m and m.get('matches'), m)
    offers=ngo.get('/api/ngo/offers').get_json(); chk("NGO sees offer via API", any(o['id']==did for o in offers), offers)
    # NGO accept
    r=ngo.post(f'/accept/{did}',follow_redirects=True)
    row=sql('select * from donations where id=?',(did,))[0]; print("after accept:",row['status'],row['otp'],row['volunteer_id'])
    chk("accept -> OTP generated", row['otp'] and len(row['otp'])==4, dict(row))
    chk("accept -> status accepted/assigned", row['status'] in('accepted','assigned'), row['status'])
    # OTP visibility
    s_d=donor.get(f'/api/status/{did}').get_json()
    chk("donor owner sees OTP", s_d.get('otp')==row['otp'], s_d)
    for nm,cc in [('anon',cl()),('ngo',ngo),('volunteer',vol)]:
        s=cc.get(f'/api/status/{did}').get_json(); chk(f"{nm} does NOT see OTP", s.get('otp') in (None,''), s)
    other=cl(); login(other,'Real Donor','donor','S3cretPass!')
    s=other.get(f'/api/status/{did}').get_json(); chk("other donor does NOT see OTP", s.get('otp') in (None,''), s)
    # volunteer sees task
    tasks=vol.get('/api/volunteer/tasks').get_json(); chk("volunteer sees task", any(t['id']==did for t in tasks), tasks)
    ovt=cl(); login(ovt,'Priya Singh','volunteer','vol123')
    chk("non-assigned volunteer does NOT see the task", not any(x['id']==did for x in (ovt.get('/api/volunteer/tasks').get_json() or [])))
    # deliver before pickup
    vol.post(f'/deliver/{did}'); st=sql('select status from donations where id=?',(did,))[0]['status']
    chk("cannot deliver before pickup", st!='delivered', st)
    # wrong otp
    r=vol.post(f'/pickup/{did}',data={'otp':'0000' if row['otp']!='0000' else '1111'})
    st=sql('select status from donations where id=?',(did,))[0]['status']; chk("wrong OTP rejected", st!='picked_up', st)
    # donor/ngo cannot pickup
    donor.post(f'/pickup/{did}',data={'otp':row['otp']}); st=sql('select status from donations where id=?',(did,))[0]['status']
    chk("donor cannot pickup", st!='picked_up', st)
    # volunteer pickup right OTP
    vol.post(f'/pickup/{did}',data={'otp':row['otp']}); st=sql('select status from donations where id=?',(did,))[0]['status']
    chk("correct OTP -> picked_up", st=='picked_up', st)
    vol.post(f'/deliver/{did}'); st=sql('select status from donations where id=?',(did,))[0]['status']
    chk("deliver -> delivered", st=='delivered', st)
    ev=[e['status'] for e in sql('select status from events where donation_id=? order by id',(did,))]; print("events:",ev)
    stats=cl().get('/api/stats').get_json(); chk("stats meals_saved updated", stats.get('meals_saved',0)>0, stats)

print("\n--- AUTHZ / IDOR ---")
sql("insert into users(name,role,lat,lng,password,capacity_kg,open_from,open_to,approved) values('Other NGO','ngo',31.32,75.57,?,100,'00:00','23:59',1)",(generate_password_hash('x'),))
sql("insert into users(name,role,lat,lng,password,approved) values('Other Vol','volunteer',31.33,75.58,?,1)",(generate_password_hash('x'),))
oid=sql("select id from users where name='Other NGO'")[0]['id']
sql("insert into donations(donor_id,food_type,quantity_kg,cooked_at,safe_until,pickup_from,pickup_to,lat,lng,status,ngo_id,created_at) values(?,?,?,?,?,?,?,?,?,?,?,?)",
    (users['Green Valley Hostel'][0],'Dal',10,f(now),f(now+timedelta(hours=5)).replace('T',' '),f(now).replace('T',' '),f(now+timedelta(hours=2)).replace('T',' '),31.31,75.58,'matched',users['Robin Hood Army'][0],now.strftime('%Y-%m-%d %H:%M')))
did2=sql('select max(id) m from donations')[0]['m']
onx=cl(); login(onx,'Other NGO','ngo','x')
onx.post(f'/accept/{did2}'); row=sql('select status,ngo_id from donations where id=?',(did2,))[0]
chk("NGO B cannot accept offer matched to NGO A", row['ngo_id']==users['Robin Hood Army'][0], dict(row))
onx.post(f'/decline/{did2}'); row=sql('select status,ngo_id from donations where id=?',(did2,))[0]
chk("NGO B cannot decline offer matched to NGO A", row['status']=='matched' and row['ngo_id']==users['Robin Hood Army'][0], dict(row))
ngo.post(f'/accept/{did2}'); row=sql('select * from donations where id=?',(did2,))[0]
ov=cl(); login(ov,'Other Vol','volunteer','x')
if row['volunteer_id'] and row['volunteer_id']!=sql("select id from users where name='Other Vol'")[0]['id']:
    ov.post(f'/pickup/{did2}',data={'otp':row['otp']}); st=sql('select status from donations where id=?',(did2,))[0]['status']
    chk("Volunteer B cannot pick up task assigned to Volunteer A", st!='picked_up', st)
else: print("SKIP volunteer IDOR (assignment differs)", dict(row))

print("\n--- SAFETY INPUT ---")
def post(**kw):
    base={'food_type':'Dal','quantity_kg':'5','cooked_at':f(now-timedelta(minutes=10)),'pickup_from':f(now+timedelta(minutes=10)),'pickup_to':f(now+timedelta(hours=1)),'lat':'31.3','lng':'75.5'}; base.update(kw)
    n=sql('select count(*) c from donations')[0]['c']; donor.post('/donate',data=base); return sql('select count(*) c from donations')[0]['c']-n
chk("raw meat blocked", post(food_type='Raw Meat')==0)
chk("expired food blocked", post(cooked_at=f(now-timedelta(hours=9)))==0)
chk("negative qty blocked", post(quantity_kg='-5')==0)
chk("zero qty blocked", post(quantity_kg='0')==0)
chk("past pickup window blocked", post(pickup_from=f(now-timedelta(hours=3)),pickup_to=f(now-timedelta(hours=2)))==0)
chk("end<start blocked", post(pickup_from=f(now+timedelta(hours=2)),pickup_to=f(now+timedelta(hours=1)))==0)
chk("future cooked_at blocked", post(cooked_at=f(now+timedelta(hours=3)))==0)
chk("valid donation accepted", post()==1)
chk("garbage qty no 500", donor.post('/donate',data={'food_type':'Dal','quantity_kg':'abc','cooked_at':'x','pickup_from':'x','pickup_to':'x'}).status_code<500)

print("\n=== SUMMARY ===")
bad=[r for r in res if not r[1]]; print(f"{len(res)-len(bad)}/{len(res)} passed")
for n,_,i in bad: print("FAILED:",n,"|",i)
