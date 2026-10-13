def _one(revenue, net_debt, shares, growth, fcf_margin, wacc, terminal_growth, years):
    if revenue <= 0 or shares <= 0: raise ValueError("revenue and shares must be positive")
    if wacc <= terminal_growth: raise ValueError("wacc must exceed terminal growth")
    pv = 0.0;
    rev = revenue;
    rows = []
    for y in range(1, years + 1):
        rev *= 1 + growth;
        fcf = rev * fcf_margin;
        pv += fcf / (1 + wacc) ** y
        rows.append({"year": y, "revenue": rev, "fcf": fcf, "pv_fcf": fcf / (1 + wacc) ** y})
    terminal = rev * (1 + terminal_growth) * fcf_margin / (wacc - terminal_growth)
    pv_terminal = terminal / (1 + wacc) ** years;
    ev = pv + pv_terminal;
    eq = ev - net_debt
    return {"enterprise_value": ev, "equity_value": eq, "value_per_share": eq / shares, "pv_explicit": pv,
            "terminal_value": terminal, "pv_terminal": pv_terminal, "forecast": rows}


def scenario_dcf(
        revenue,
        net_debt,
        shares,
        growth,
        fcf_margin,
        wacc,
        terminal_growth,
        years=5
):
    cases = {
        "bear": {
            "growth": growth - 0.04,
            "margin": fcf_margin - 0.02,
            "wacc": wacc + 0.015,
            "terminal_growth": max(0, terminal_growth - 0.005)
        },
        "base": {
            "growth": growth,
            "margin": fcf_margin,
            "wacc": wacc,
            "terminal_growth": terminal_growth
        },
        "bull": {
            "growth": growth + 0.04,
            "margin": fcf_margin + 0.02,
            "wacc": max(
                wacc - 0.015,
                terminal_growth + 0.01
            ),
            "terminal_growth": terminal_growth + 0.005
        }
    }

    return {
        name: {
            **cfg,
            **_one(
                revenue,
                net_debt,
                shares,
                cfg["growth"],
                cfg["margin"],
                cfg["wacc"],
                cfg["terminal_growth"],
                years
            )
        }
        for name, cfg in cases.items()
    }


def sensitivity(revenue, net_debt, shares, growth, fcf_margin, wacc, terminal_growth, years=5, wacc_steps=None,
                growth_steps=None):
    wacc_steps = wacc_steps or [-.02, -.01, 0, .01, .02];
    growth_steps = growth_steps or [-.01, -.005, 0, .005, .01]
    return [{"wacc": wacc + dw, "terminal_growth": terminal_growth + dg, "value_per_share":
        _one(revenue, net_debt, shares, growth, fcf_margin, wacc + dw, terminal_growth + dg, years)["value_per_share"]}
            for dw in wacc_steps for dg in growth_steps]
