import numpy as np,pandas as pd
from app.quant.dcf import dcf_value
from app.quant.technical import indicators,risk
from app.ml.model import train,predict
from app.rag.retriever import Retriever,Document
def data(n=320):
 r=np.random.default_rng(42).normal(.001,.02,n); c=100*np.exp(np.cumsum(r)); return pd.DataFrame({'open':c,'high':c*1.01,'low':c*.99,'close':c,'volume':np.random.default_rng(2).integers(1000,10000,n)},index=pd.date_range('2020-01-01',periods=n))
def test_dcf(): assert dcf_value(1000,100,100,.08,.15,.10,.03)['value_per_share']>0
def test_quant_ml():
 d=indicators(data()); assert 'rsi14' in d; assert risk(d)['latest_price']>0; m,metrics=train(d); p=predict(m,d); assert 0<=p['p_up']<=1 and 'accuracy' in metrics
def test_rag():
 r=Retriever(); r.add(Document('1','Margins','operating margin expanded with revenue','x')); r.add(Document('2','Debt','net debt declined','x')); assert r.search('operating margin')[0]['id']=='1'
