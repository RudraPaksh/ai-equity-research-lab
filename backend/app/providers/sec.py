from ..config import settings
from .http import get_json
BASE="https://data.sec.gov"

async def ticker_map():
    data,_=await get_json("https://www.sec.gov/files/company_tickers.json",provider="sec",ttl=86400,headers={"User-Agent":settings.sec_user_agent})
    return {v["ticker"].upper():int(v["cik_str"]) for v in data.values()}

async def company_facts_by_cik(cik:int):
    data,_=await get_json(f"{BASE}/api/xbrl/companyfacts/CIK{cik:010d}.json",provider="sec",ttl=86400,headers={"User-Agent":settings.sec_user_agent})
    return data

async def company_facts(symbol:str):
    mapping=await ticker_map(); cik=mapping.get(symbol.upper())
    if not cik: raise RuntimeError(f"SEC CIK not found for {symbol}")
    return await company_facts_by_cik(cik)
