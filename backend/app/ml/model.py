import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score,roc_auc_score,precision_score,recall_score,confusion_matrix,brier_score_loss
FEATURES=["return_1d","return_20d","return_60d","rsi14","macd","macd_signal","volatility_20d","volume_sma20","volume_ratio","atr_pct"]

def make_target(df,horizon=20):
    future=df.close.shift(-horizon)/df.close-1
    return future.where(future.notna()).gt(0).astype(float).where(future.notna())

def _metrics(y,p):
    pred=(p>=.5).astype(int); m={"accuracy":float(accuracy_score(y,pred)),"precision":float(precision_score(y,pred,zero_division=0)),"recall":float(recall_score(y,pred,zero_division=0)),"brier_score":float(brier_score_loss(y,p))}
    if len(np.unique(y))==2:m["roc_auc"]=float(roc_auc_score(y,p))
    m["confusion_matrix"]=confusion_matrix(y,pred).tolist(); return m

def train(df,horizon=20):
    x=df.copy(); x["target"]=make_target(x,horizon); x=x.dropna(subset=FEATURES+["target"])
    if len(x)<160: raise ValueError("Need at least 160 usable observations for the V0.3 baseline")
    split=int(len(x)*.8); tr=x.iloc[:split]; te=x.iloc[split:]
    models={"logistic":Pipeline([("imputer",SimpleImputer(strategy="median")),("clf",LogisticRegression(max_iter=1000))]),"hist_gradient_boosting":Pipeline([("imputer",SimpleImputer(strategy="median")),("clf",HistGradientBoostingClassifier(max_iter=250,learning_rate=.05,random_state=42))]),"random_forest":Pipeline([("imputer",SimpleImputer(strategy="median")),("clf",RandomForestClassifier(n_estimators=300,min_samples_leaf=5,random_state=42,n_jobs=-1,class_weight="balanced"))])}
    results={}; fitted={}
    for name,model in models.items():
        model.fit(tr[FEATURES],tr.target.astype(int)); p=model.predict_proba(te[FEATURES])[:,1]; results[name]=_metrics(te.target.astype(int).values,p); fitted[name]=model
    best=max(results,key=lambda n: results[n].get("roc_auc",results[n]["accuracy"]))
    return fitted[best],{"selected_model":best,"models":results,"train_rows":len(tr),"test_rows":len(te),"horizon_days":horizon,"accuracy":results[best]["accuracy"],"roc_auc":results[best].get("roc_auc") }

def predict(model,df):
    row=df.dropna(subset=FEATURES).iloc[[-1]]; p=float(model.predict_proba(row[FEATURES])[:,1][0]); return {"p_up":p,"p_down":1-p,"signal":"up_bias" if p>=.55 else "down_bias" if p<=.45 else "neutral"}

def tensorflow_available():
    try: import tensorflow; return True
    except ImportError:return False
