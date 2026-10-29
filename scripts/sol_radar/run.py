#!/usr/bin/env python3
"""GitHub Actions data producer. Only public token data; no Site credentials."""
import json,os,sys,time,math,urllib.parse,concurrent.futures
from pathlib import Path
import collect as base
WINDOW=108000000
PERIOD=1800000

def ts(v):
 try:
  n=float(v);return int(n*1000 if n<1e12 else n) if math.isfinite(n) and n>0 else 0
 except (ValueError,TypeError):return 0

def peak(r):return max(float(r.get('price') or 0),float((r.get('historyCheck') or {}).get('high') or 0),float(r.get('_peak') or 0))
def excluded(r):
 try:return (r.get('holders') is not None and float(r['holders'])<50) or (r.get('price') is not None and float(r['price'])<.000003) or peak(r)>=.0008
 except (TypeError,ValueError):return True

def ready(r):
 h=r.get('historyCheck') or {}
 return not excluded(r) and r.get('price') is not None and r.get('holders') is not None and h.get('complete') and ts(h.get('through'))>=ts(r.get('snapshotAt'))-60000

def fast_collect(targets):
 now=int(time.time()*1000);ranges=[]
 for r in targets:
  age=(now-ts(r.get('migrateTime')))/60000
  if 0<=age<1800:ranges.append((max(0,int(age)-2),min(1800,int(age)+3)))
 windows=[]
 for lo,hi in sorted(ranges):
  if windows and lo<=windows[-1][1]:windows[-1]=(windows[-1][0],max(hi,windows[-1][1]))
  else:windows.append((lo,hi))
 wanted={r['contractAddress'] for r in targets};rows={};errors=[];requests=0;saturated=0
 def get(window):
  lo,hi=window
  try:
   d=base.request_json(base.API,{'chainId':'CT_501','rankType':30,'protocol':[1001],'limit':100,'tokenAgeMin':lo,'tokenAgeMax':hi})
   if d.get('code')!='000000' or not isinstance(d.get('data'),list):raise ValueError('invalid upstream response')
   return window,d['data'],None
  except Exception as e:return window,[],str(e)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  while windows and requests<24:
   batch=windows[:min(4,24-requests)];del windows[:len(batch)];requests+=len(batch)
   for (lo,hi),data,err in ex.map(get,batch):
    if err:errors.append(f'{lo}-{hi}m: {err}');continue
    for r in data:
     if r.get('contractAddress') in wanted and r.get('chainId')=='CT_501' and r.get('protocol')==1001 and r.get('migrateStatus')==1:
      rows[r['contractAddress']]={**{k:r[k] for k in base.FIELDS if k in r},'snapshotAt':int(time.time()*1000)}
    missing=[r for r in targets if r['contractAddress'] not in rows and lo<=(now-ts(r['migrateTime']))/60000<=hi]
    if len(data)>=100 and missing:
     if hi-lo>1:mid=(lo+hi)//2;windows.extend([(lo,mid),(mid,hi)])
     else:saturated+=1
 if requests and requests==len(errors):raise RuntimeError('All priority snapshot requests failed; previous data preserved')
 missing=wanted-rows.keys()
 if missing:errors.append(f'{len(missing)} priority snapshots missing; old snapshots remain stale')
 return {'rows':list(rows.values()),'requests':requests,'saturated':saturated+len(windows),'rejected':0,'errors':errors[:5],'collectedAt':int(time.time()*1000),'source':'Binance Meme Rush'}

def incremental_history(row,old):
 previous=old.get('historyCheck') or {};now=int(time.time()*1000);migrated=ts(row['migrateTime'])
 if not previous.get('complete') or ts(previous.get('from'))>migrated:return base.history_check(row)
 # Re-read the previously open interval. Never use a stale checkpoint as current proof.
 start=(ts(previous.get('through'))//300000)*300000
 limit=max(4,math.ceil((now-start)/300000)+2)
 if limit>=500:return base.history_check(row)
 query=urllib.parse.urlencode({'platform':'solana','address':row['contractAddress'],'interval':'5min','limit':limit,'to':now,'pm':'p'})
 d=base.request_json('https://dquery.sintral.io/u-kline/v1/k-line/candles?'+query)
 if str(d.get('status',{}).get('error_code'))!='0' or not isinstance(d.get('data'),list):raise ValueError('incremental history unavailable')
 bars=[]
 for raw in d['data']:
  if not isinstance(raw,list) or len(raw)<7:continue
  try:v=[float(x) for x in raw[:7]]
  except (ValueError,TypeError):continue
  if all(math.isfinite(x) for x in v) and v[0]>0 and v[2]>0 and v[1]>=max(v[0],v[3]) and v[2]<=min(v[0],v[3]) and start<=v[5]<=now:bars.append(v)
 bars=sorted({r[5]:r for r in bars}.values(),key=lambda x:x[5]);last_closed=(now//300000-1)*300000
 complete=bool(bars) and bars[0][5]<=start and bars[-1][5]>=last_closed and all(bars[i][5]-bars[i-1][5]==300000 for i in range(1,len(bars)))
 high=max([peak(old),float(row.get('price') or 0)]+[r[1] for r in bars])
 return {'source':'Binance USD OHLCV' if complete else 'Binance USD OHLCV partial','high':high,'from':migrated if complete else None,'through':now,'bars':len(bars),'complete':complete,'incremental':True}

def produce(previous,force=False):
 now=int(time.time()*1000);old={r['contractAddress']:r for r in previous.get('rows',[]) if 0<=now-ts(r.get('migrateTime'))<WINDOW}
 discover=force or not previous.get('lastDiscoveryAt') or now-previous['lastDiscoveryAt']>=PERIOD
 targets=[r for r in old.values() if r.get('_track') and not excluded(r)]
 data=base.collect() if discover else fast_collect(targets)
 for r in data['rows']:r.setdefault('snapshotAt',data['collectedAt'])
 todo=[r for r in data['rows'] if not excluded(r)]
 todo.sort(key=lambda r:(not old.get(r['contractAddress'],{}).get('_track',False),ts((old.get(r['contractAddress'],{}).get('historyCheck') or {}).get('attemptedAt')),-float(r.get('liquidity') or 0)))
 budget=max(40,len(targets)) if discover else len(targets);history_errors=[];count=0;started=time.time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  for i in range(0,min(len(todo),budget,100),4):
   if time.time()-started>120:break
   batch=todo[i:i+4];futures={ex.submit(incremental_history,r,old.get(r['contractAddress'],{})):r for r in batch}
   for f,r in futures.items():
    count+=1
    try:r['historyCheck']={**f.result(),'attemptedAt':int(time.time()*1000)}
    except Exception as e:
     r['historyCheck']={'high':peak(old.get(r['contractAddress'],{})),'attemptedAt':int(time.time()*1000),'complete':False};history_errors.append(r['contractAddress']+': '+str(e))
 for r in data['rows']:
  prior=old.get(r['contractAddress'],{});r['_peak']=max(peak(prior),peak(r));r['historyCheck']={**(r.get('historyCheck') or {}),'high':r['_peak']};r['_track']=not excluded(r) and (prior.get('_track',False) or ready(r));old[r['contractAddress']]=r
 data.update({'rows':list(old.values()),'schemaVersion':1,'mode':'discovery' if discover else 'priority','lastDiscoveryAt':data['collectedAt'] if discover else previous.get('lastDiscoveryAt'),'historyRequests':count,'historyErrors':history_errors[:5],'errors':(data['errors']+(['历史价格核验部分失败，相关代币保持待核验'] if history_errors else []))[:6],'focusMints':[r['contractAddress'] for r in old.values() if r.get('_track') and not excluded(r)]})
 return data

def main():
 path=Path(os.environ.get('SOL_RADAR_DATA','data/sol-radar/latest.json'));previous=json.loads(path.read_text()) if path.exists() else {}
 data=produce(previous,os.environ.get('SOL_RADAR_FORCE_DISCOVERY')=='true');path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n');temp.replace(path)
 summary={'mode':data['mode'],'snapshots':len(data['rows']),'focus':len(data['focusMints']),'listRequests':data['requests'],'historyRequests':data['historyRequests'],'partial':bool(data['errors'] or data['saturated']),'errors':data['errors'],'historyErrors':data['historyErrors']};print(json.dumps(summary,ensure_ascii=False))
 if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('### SOL 外盘雷达采集\n```json\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n```\n')
 if os.environ.get('GITHUB_OUTPUT'):
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('partial='+str(summary['partial']).lower()+'\n')
if __name__=='__main__':
 try:main()
 except Exception as e:print('Collection failed; previous snapshot preserved: '+str(e),file=sys.stderr);sys.exit(1)
