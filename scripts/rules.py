import numpy as np

def orderkeys(*keys):return np.lexsort(tuple(keys[::-1]),axis=-1)

def rank_field(wins,ap,pts,pot,credits,opp,conf,div):
 # All inputs have leading simulation dimension, including a single deterministic forecast.
 s=len(wins);rr=np.arange(s);dw=np.zeros((s,32),bool)
 for ix in div:
  tied=np.round(wins[:,ix],10)==np.round(wins[:,ix].max(1,keepdims=True),10)
  mini=np.full((s,len(ix)),-np.inf)
  for j,t in enumerate(ix):
   opponents=opp[:,t];num=np.zeros(s);den=np.zeros(s)
   for k,o in enumerate(opponents):
    match=np.flatnonzero(ix==o)
    if len(match):
     include=tied[:,match[0]]&tied[:,j];num+=include*credits[:,k,t];den+=include
   np.divide(num,den,out=mini[:,j],where=den>0)
  o=orderkeys(-np.round(wins[:,ix],10),-mini,-ap[:,ix],-pts[:,ix],-pot[:,ix])
  dw[rr,ix[o[:,0]]]=True
 q=dw.copy();seed=np.zeros((s,32),int)
 for ix in conf:
  o=orderkeys(np.where(dw[:,ix],np.inf,-np.round(wins[:,ix],10)),-ap[:,ix],-pts[:,ix],-pot[:,ix])
  q[rr[:,None],ix[o[:,:3]]]=True
  o=orderkeys(-ap[:,ix],-pts[:,ix],-pot[:,ix]);sq=np.take_along_axis(q[:,ix],o,axis=1)
  ranked=np.where(sq,np.cumsum(sq,1),7+np.cumsum(~sq,1));seed[rr[:,None],ix[o]]=ranked
 assert (q.sum(1)==14).all() and (dw.sum(1)==8).all()
 return q,dw,seed


def fafl_outcomes(scores,potweek,opp,conf,div):
 ap=((scores[:,:,:,None]>scores[:,:,None,:]).sum(-1)+.5*((scores[:,:,:,None]==scores[:,:,None,:]).sum(-1)-1))
 other=np.take_along_axis(scores,np.broadcast_to(opp,scores.shape),axis=2)
 credits=(scores>other)+.5*(scores==other);wins=credits.sum(1);pts=scores.sum(1);aps=ap.sum(1)
 for a,b in [(0,3),(3,6),(6,9),(9,12),(0,12)]:
  if b>scores.shape[1]:continue
  order=orderkeys(-ap[:,a:b].sum(1),-scores[:,a:b].sum(1),-potweek[:,a:b].sum(1))
  bonus=np.zeros_like(wins);rr=np.arange(len(wins))[:,None]
  bonus[rr,order[:,:15]]=1;bonus[rr,order[:,15:17]]=.5;wins+=bonus
 q,dw,seed=rank_field(wins,aps,pts,potweek.sum(1),credits,opp,conf,div)
 return q,dw,seed,wins,aps,credits

