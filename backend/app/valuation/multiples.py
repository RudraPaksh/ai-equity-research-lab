def implied_price_from_pe(eps, pe): return eps * pe
def implied_price_from_fcf(fcf_per_share, fcf_yield):
    if fcf_yield<=0: raise ValueError("fcf_yield must be positive")
    return fcf_per_share/fcf_yield

def valuation_snapshot(price, eps=None, pe=None, fcf_per_share=None, fcf_yield=None, revenue_per_share=None, ps=None):
    out={"price":price}
    if eps is not None and eps!=0: out["current_pe"]=price/eps
    if fcf_per_share is not None and fcf_per_share!=0: out["fcf_yield"]=fcf_per_share/price
    if revenue_per_share is not None and revenue_per_share!=0: out["current_ps"]=price/revenue_per_share
    if pe is not None and eps is not None: out["implied_price_pe"]=implied_price_from_pe(eps,pe)
    if fcf_yield is not None and fcf_per_share is not None: out["implied_price_fcf"]=implied_price_from_fcf(fcf_per_share,fcf_yield)
    if ps is not None and revenue_per_share is not None: out["implied_price_ps"]=revenue_per_share*ps
    return out
