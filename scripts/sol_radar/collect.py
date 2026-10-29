#!/usr/bin/env python3
"""Collect public indexed pump.fun migrations and write to a private Site.
Input via hidden stdin: {"url": SITE_ORIGIN, "token": CURRENT_SITE_SERVICE_TOKEN}.
No secrets are stored. Run with standard Python3; urllib uses runtime proxies.
"""
import sys,json,time,urllib.request,urllib.error,concurrent.futures
API='https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list/ai'
FIELDS='chainId contractAddress symbol name icon protocol migrateStatus migrateTime createTime price marketCap liquidity volume priceChange holders count countBuy countSell holdersTop10Percent holdersDevPercent holdersSniperPercent holdersInsiderPercent bundlerHoldingPercent netBuy smartMoneyHolders smartMoneyHoldingPercent devSellPercent devPosition twitterHandle twitterInfo tagDevWashTrading tagInsiderWashTrading pumpfunSubType narrativeText socials'.split()
def request_json(url,body=None,headers=None):
    h={'Accept':'application/json',**(headers or {})}
    if body is not None:h['Content-Type']='application/json'
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers=h)
    with urllib.request.urlopen(req,timeout=18) as r:return json.load(r)
def collect():
    queue=[(0,30),(30,240),(240,720),(720,1800)]
    rows={};errors=[];requests=0;saturated=0;rejected=0;started=time.time()
    def get(window):
        lo,hi=window
        try:
            d=request_json(API,{'chainId':'CT_501','rankType':30,'protocol':[1001],'limit':100,'holdersMin':50,'tokenAgeMin':lo,'tokenAgeMax':hi})
            if d.get('code')!='000000' or not isinstance(d.get('data'),list):raise ValueError('upstream returned invalid data')
            return window,d['data'],None
        except Exception as e:return window,[],str(e)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        while queue and requests<40 and time.time()-started<180:
            batch=queue[:min(4,40-requests)];del queue[:len(batch)];requests+=len(batch)
            for (lo,hi),data,error in ex.map(get,batch):
                if error:errors.append(f'{lo}-{hi}m: {error}');continue
                now=int(time.time()*1000)
                for r in data:
                    try:
                        mt=float(r.get('migrateTime') or 0);mt=mt*1000 if mt<1e12 else mt
                        if r.get('chainId')!='CT_501' or r.get('protocol')!=1001 or r.get('migrateStatus')!=1 or not 0<=now-mt<108000000:rejected+=1;continue
                        rows[r['contractAddress']]={k:r[k] for k in FIELDS if k in r}
                    except (ValueError,TypeError,KeyError):rejected+=1
                if len(data)>=100:
                    if hi-lo>1:mid=(lo+hi)//2;queue.extend([(lo,mid),(mid,hi)])
                    else:saturated+=1
    if requests==len(errors):raise RuntimeError('All source requests failed; previous Site data was preserved. '+ '; '.join(errors[:2]))
    return {'rows':list(rows.values()),'requests':requests,'saturated':saturated+len(queue),'rejected':rejected,'errors':errors[:5],'collectedAt':int(time.time()*1000),'source':'Binance Meme Rush'}
def history_check(row):
    import math,urllib.parse
    migrated=float(row['migrateTime']);now=int(time.time()*1000)
    query=urllib.parse.urlencode({'platform':'solana','address':row['contractAddress'],'interval':'5min','limit':500,'to':now,'pm':'p'})
    d=request_json('https://dquery.sintral.io/u-kline/v1/k-line/candles?'+query)
    if str(d.get('status',{}).get('error_code'))!='0' or not isinstance(d.get('data'),list):raise ValueError('Historical USD candles unavailable')
    bars=[]
    for r in d['data']:
        if not isinstance(r,list) or len(r)<7:continue
        vals=[float(x) for x in r[:7]]
        if not all(math.isfinite(x) for x in vals) or vals[0]<=0 or vals[1]<max(vals[0],vals[3]) or vals[2]>min(vals[0],vals[3]) or vals[2]<=0:continue
        if vals[5]+300000>migrated and vals[5]<=now:bars.append(vals)
    bars=sorted({r[5]:r for r in bars}.values(),key=lambda r:r[5])
    if not bars:raise ValueError('No post-migration historical candles')
    full=[r for r in bars if r[5]>=migrated]
    high=max([float(row.get('price') or 0)]+[r[1] for r in full])
    post_migration_high=high
    boundary=[r for r in bars if r[5]<migrated]
    ambiguous=any(r[1]>=.0008 for r in boundary)
    if not ambiguous:high=max([high]+[r[1] for r in boundary])
    start=(int(migrated)//300000)*300000
    complete=(bars[0][5]<=start and bars[-1][5]>=((now//300000)-1)*300000 and len(d['data'])<500 and all(bars[i][5]-bars[i-1][5]==300000 for i in range(1,len(bars))) and not ambiguous)
    return {'source':'Binance USD OHLCV' if complete else 'Binance USD OHLCV partial','high':high,'from':migrated if complete else None,'through':int(time.time()*1000),'bars':len(bars),'complete':complete,'postMigrationHigh':post_migration_high,'points':[[int(r[5]+300000),r[3]] for r in bars if r[5]+300000<=now]}
def enrich_history(data,state):
    known={x['mint']:x for x in state.get('tokens',[])};todo=[]
    for r in data['rows']:
        price=r.get('price');holders=r.get('holders');old=known.get(r['contractAddress'],{})
        if (old.get('peak') or 0)>=.0008:r['historyCheck']={'source':'Stored observation','high':old['peak']};continue
        if price is None or holders is None or float(holders)<50 or not .000003<=float(price)<.0008:continue
        todo.append(r)
    todo.sort(key=lambda r:(known.get(r['contractAddress'],{}).get('attemptedAt') or 0,-float(r.get('liquidity') or 0)))
    errors=[];started=time.time();checked=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for i in range(0,min(len(todo),40),4):
            if time.time()-started>120:break
            batch=todo[i:i+4]
            future={ex.submit(history_check,r):r for r in batch}
            for f,r in future.items():
                checked+=1
                try:r['historyCheck']={**f.result(),'attemptedAt':int(time.time()*1000)}
                except Exception as e:
                    r['historyCheck']={'attemptedAt':int(time.time()*1000)};errors.append(r['contractAddress']+': '+str(e))
    data['historyRequests']=checked;data['historyPending']=len(todo)-sum(bool(r.get('historyCheck',{}).get('complete')) for r in todo);data['historyErrors']=errors[:5]
    return data

def main():
    if sys.stdin.isatty():
        import termios
        attrs=termios.tcgetattr(sys.stdin);new=list(attrs);new[3]&=~termios.ECHO;termios.tcsetattr(sys.stdin,termios.TCSADRAIN,new)
    cfg=json.loads(sys.stdin.readline())
    origin=cfg['url'].rstrip('/');headers={'OAI-Sites-Authorization':'Bearer '+cfg['token']}
    state=request_json(origin+'/api/collection-state',headers=headers)
    data=enrich_history(collect(),state)
    saved=request_json(origin+'/api/ingest',data,headers)
    readback=request_json(origin+'/api/tokens',headers=headers)
    tokens=readback.get('tokens',[])
    print(json.dumps({'saved':saved,'readbackCount':len(tokens),'focusCounts':readback.get('counts'),'historyRequests':data.get('historyRequests'),'historyPending':data.get('historyPending'),'ageRangeHours':[min((time.time()*1000-t['migratedAt'])/3600000 for t in tokens),max((time.time()*1000-t['migratedAt'])/3600000 for t in tokens)] if tokens else None,'sample':[{'symbol':t['symbol'],'liquidity':t['liquidity']} for t in tokens[:3]],'sync':readback.get('sync')},ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'error':str(e)},ensure_ascii=False));sys.exit(1)
