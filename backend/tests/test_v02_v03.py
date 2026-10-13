import pandas as pd, numpy as np
from app.quant.technical import indicators, factor_snapshot
from app.valuation.dcf import scenario_dcf, sensitivity
from app.valuation.multiples import valuation_snapshot
from app.ml.model import make_target

def sample(n=420):
    idx=pd.date_range('2020-01-01',periods=n,freq='B'); close=100*np.exp(np.cumsum(np.random.default_rng(42).normal(.0005,.015,n))); return pd.DataFrame({'open':close,'high':close*1.01,'low':close*.99,'close':close,'volume':100000},index=idx)

def test_indicators():
    df=indicators(sample()); assert 'rsi14' in df and df.sma200.notna().sum()>0; assert set(factor_snapshot(df))=={'trend','momentum','rsi','macd'}

def test_dcf_scenarios():
    r=scenario_dcf(1000,100,100,0.08,0.15,0.09,0.025); assert set(r)=={'bear','base','bull'}; assert r['bull']['value_per_share']>r['bear']['value_per_share']
    assert len(sensitivity(1000,100,100,.08,.15,.09,.025))==25

def test_multiples():
    r=valuation_snapshot(100,5,20,4,.05); assert r['current_pe']==20

def test_target_tail_is_nan():
    t=make_target(sample(100),20); assert t.tail(20).isna().all()
