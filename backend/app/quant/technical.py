import numpy as np
import pandas as pd

def indicators(df):
    x=df.copy().sort_index(); c=x.close.astype(float); h=x.high.astype(float); l=x.low.astype(float)
    v=x.volume.astype(float) if "volume" in x else pd.Series(index=x.index,dtype=float)
    for n in (20,50,200): x[f"sma{n}"]=c.rolling(n).mean()
    d=c.diff(); gain=d.clip(lower=0).rolling(14).mean(); loss=(-d.clip(upper=0)).rolling(14).mean(); rs=gain/loss.replace(0,np.nan)
    x["rsi14"]=100-(100/(1+rs)); e12=c.ewm(span=12,adjust=False).mean(); e26=c.ewm(span=26,adjust=False).mean()
    x["macd"]=e12-e26; x["macd_signal"]=x.macd.ewm(span=9,adjust=False).mean()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); x["atr14"]=tr.rolling(14).mean(); x["atr_pct"]=x.atr14/c
    x["return_1d"]=c.pct_change(); x["return_20d"]=c.pct_change(20); x["return_60d"]=c.pct_change(60)
    x["volatility_20d"]=x.return_1d.rolling(20).std()*np.sqrt(252); x["volume_sma20"]=v.rolling(20).mean(); x["volume_ratio"]=v/x.volume_sma20
    x["ema20"]=c.ewm(span=20,adjust=False).mean(); x["ema50"]=c.ewm(span=50,adjust=False).mean()
    return x

def risk(df, benchmark=None):
    c=df.close.astype(float); r=c.pct_change().dropna(); peak=c.cummax(); dd=c/peak-1
    out={"latest_price":float(c.iloc[-1]),"annualized_volatility":float(r.std()*np.sqrt(252)) if len(r)>1 else None,"sharpe_approx":float(r.mean()/r.std()*np.sqrt(252)) if len(r)>1 and r.std() else None,"max_drawdown":float(dd.min())}
    if benchmark is not None and len(benchmark):
        b=benchmark.reindex(df.index).close.astype(float).pct_change(); joined=pd.concat([r,b],axis=1).dropna();
        if len(joined)>1 and joined.iloc[:,1].var()>0: out["beta_vs_benchmark"]=float(joined.iloc[:,0].cov(joined.iloc[:,1])/joined.iloc[:,1].var())
    return out

def factor_snapshot(df):
    r=df.iloc[-1]; scores={
        "trend": np.clip((r.sma20/r.close-1)*-100 + (r.sma50/r.close-1)*-50, -100,100) if pd.notna(r.sma20) and pd.notna(r.sma50) else 0,
        "momentum": np.clip((r.return_20d or 0)*500, -100,100),
        "rsi": np.clip((r.rsi14-50)*2, -100,100) if pd.notna(r.rsi14) else 0,
        "macd": np.clip((r.macd-r.macd_signal)/max(abs(r.close),1)*10000,-100,100) if pd.notna(r.macd_signal) else 0,
    }
    return {k:float(v) for k,v in scores.items()}
