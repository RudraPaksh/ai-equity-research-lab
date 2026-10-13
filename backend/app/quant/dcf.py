def dcf_value(revenue, net_debt, shares, growth, fcf_margin, wacc, terminal_growth, years=5):
    if revenue <= 0 or shares <= 0: raise ValueError("revenue and shares must be positive")
    if wacc <= terminal_growth: raise ValueError("wacc must exceed terminal growth")
    pv = 0;
    rev = revenue
    for y in range(1, years + 1):
        rev *= 1 + growth;
        fcf = rev * fcf_margin;
        pv += fcf / (1 + wacc) ** y
    terminal = rev * (1 + terminal_growth) * fcf_margin / (wacc - terminal_growth)
    ev = pv + terminal / (1 + wacc) ** years;
    eq = ev - net_debt
    return {"enterprise_value": ev, "equity_value": eq, "value_per_share": eq / shares}
