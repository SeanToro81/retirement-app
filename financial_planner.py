import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Financial Planner", page_icon="📈", layout="wide")
st.title("Financial Planning Tool")

tab1, tab2, tab2b, tab3 = st.tabs(["Investment Growth", "My Retirement", "Household Retirement", "Portfolio Comparison"])


# =============================================================================
# Helper: CPP adjustment
# =============================================================================
def calc_cpp(base, start_age):
    months_from_65 = (start_age - 65) * 12
    if months_from_65 < 0:
        return base * (1 + months_from_65 * 0.006)
    else:
        return base * (1 + months_from_65 * 0.007)


def calc_oas(base, start_age):
    months_deferred = (start_age - 65) * 12
    return base * (1 + months_deferred * 0.006)


# =============================================================================
# Helper: Run retirement simulation & render
# =============================================================================
def run_retirement(prefix, include_spouse=False):
    col1, col2 = st.columns([1, 2])

    with col1:
        current_age = st.number_input("Current Age", 18, 80, 30, key=f"{prefix}_age")
        retire_age = st.number_input("Retirement Age", int(current_age) + 1, 90, 65, key=f"{prefix}_retire")
        life_exp = st.number_input("Life Expectancy", int(retire_age) + 1, 110, 90, key=f"{prefix}_life")
        current_savings = st.number_input("Current Savings ($)", 0, 10_000_000, 50_000, 5_000, key=f"{prefix}_savings")
        monthly_savings = st.number_input("Monthly Savings ($)", 0, 50_000, 1_000, 100, key=f"{prefix}_monthly",
                                          help="Stops at retirement age")
        monthly_savings_post = st.number_input("Monthly Savings (After Retirement) ($)", 0, 50_000, 0, 100,
                                               key=f"{prefix}_monthly_post",
                                               help="Only counts after retirement age (e.g. part-time income)")
        annual_extra = st.number_input("Extra Added Money Per Year ($)", 0, 1_000_000, 0, 500, key=f"{prefix}_extra",
                                       help="Stops at retirement age")
        pre_return = st.slider("Pre-Retirement Return (%)", 0.0, 20.0, 7.0, 0.1, key=f"{prefix}_pre")
        post_return = st.slider("Post-Retirement Return (%)", 0.0, 15.0, 4.0, 0.1, key=f"{prefix}_post")
        inflation = st.slider("Annual Inflation (%)", 0.0, 10.0, 3.0, 0.1, key=f"{prefix}_inflation")
        monthly_income_early = st.number_input("Desired Monthly Income — First 10 Years of Retirement (today's $)",
                                                0, 100_000, 6_000, 500, key=f"{prefix}_income_early",
                                                help="Higher spending for travel and active lifestyle")
        monthly_retirement_income = st.number_input("Desired Monthly Income — After First 10 Years (today's $)",
                                                     0, 100_000, 4_000, 500, key=f"{prefix}_income",
                                                     help="Reduced spending in later retirement")
        st.caption("In today's dollars — automatically adjusted for inflation each year.")

        # --- Your CPP & OAS ---
        st.subheader("Your CPP & OAS")
        cpp_base = st.number_input("CPP Monthly Amount at 65 ($)", 0, 5_000, 1_300, 50, key=f"{prefix}_cpp_base")
        cpp_start_age = st.slider("CPP Start Age", 60, 70, 65, key=f"{prefix}_cpp_age")
        cpp_adjusted = calc_cpp(cpp_base, cpp_start_age)
        label = 'early' if cpp_start_age < 65 else ('deferred' if cpp_start_age > 65 else 'standard')
        st.caption(f"Adjusted CPP: **${cpp_adjusted:,.0f}/mo** ({label})")

        oas_base = st.number_input("OAS Monthly Amount at 65 ($)", 0, 2_000, 700, 50, key=f"{prefix}_oas_base")
        oas_start_age = st.slider("OAS Start Age", 65, 70, 65, key=f"{prefix}_oas_age")
        oas_adjusted = calc_oas(oas_base, oas_start_age)
        label = 'deferred' if oas_start_age > 65 else 'standard'
        st.caption(f"Adjusted OAS: **${oas_adjusted:,.0f}/mo** ({label})")

        # --- Spouse (only on household tab) ---
        spouse_pension = 0
        spouse_pension_start_age = retire_age
        spouse_cpp_adjusted = 0
        spouse_cpp_start_age = 65
        spouse_oas_adjusted = 0
        spouse_oas_start_age = 65

        if include_spouse:
            st.divider()
            st.subheader("Spouse")
            spouse_pension = st.number_input("Spouse's Monthly Pension ($)", 0, 50_000, 5_700, 100, key=f"{prefix}_sp_pension")
            spouse_pension_start_age = st.number_input("Spouse's Pension Start Age", 50, 90, int(retire_age), key=f"{prefix}_sp_pension_age")

            sp_cpp_base = st.number_input("Spouse's CPP at 65 ($)", 0, 5_000, 800, 50, key=f"{prefix}_sp_cpp")
            spouse_cpp_start_age = st.slider("Spouse's CPP Start Age", 60, 70, 65, key=f"{prefix}_sp_cpp_age")
            spouse_cpp_adjusted = calc_cpp(sp_cpp_base, spouse_cpp_start_age)
            st.caption(f"Spouse Adjusted CPP: **${spouse_cpp_adjusted:,.0f}/mo**")

            sp_oas_base = st.number_input("Spouse's OAS at 65 ($)", 0, 2_000, 700, 50, key=f"{prefix}_sp_oas")
            spouse_oas_start_age = st.slider("Spouse's OAS Start Age", 65, 70, 65, key=f"{prefix}_sp_oas_age")
            spouse_oas_adjusted = calc_oas(sp_oas_base, spouse_oas_start_age)
            st.caption(f"Spouse Adjusted OAS: **${spouse_oas_adjusted:,.0f}/mo**")

    # --- Accumulation phase ---
    accum_months = (retire_age - current_age) * 12
    pre_monthly = pre_return / 100 / 12
    accum = np.zeros(accum_months + 1)
    accum[0] = current_savings
    for m in range(1, accum_months + 1):
        extra = annual_extra if (m % 12 == 1) else 0
        accum[m] = accum[m - 1] * (1 + pre_monthly) + monthly_savings + extra

    retirement_corpus = accum[-1]

    # --- Drawdown phase ---
    draw_months = (life_exp - retire_age) * 12
    post_monthly = post_return / 100 / 12
    monthly_inflation = inflation / 100 / 12
    drawdown = np.zeros(draw_months + 1)
    drawdown[0] = retirement_corpus
    # Start with early-retirement spending; switch to reduced spending after 10 years
    current_withdrawal = monthly_income_early
    switched_to_later = False
    depleted_month = None

    for m in range(1, draw_months + 1):
        age_at_month = retire_age + m / 12
        # After 10 years of retirement, step down to the "later" income level
        if not switched_to_later and m >= 10 * 12:
            # Scale the later income to today's-dollar equivalent at this point
            years_elapsed = m / 12
            current_withdrawal = monthly_retirement_income * ((1 + inflation / 100) ** years_elapsed)
            switched_to_later = True
        else:
            current_withdrawal *= (1 + monthly_inflation)
        # Your CPP & OAS
        my_cpp = cpp_adjusted if age_at_month >= cpp_start_age else 0
        my_oas = oas_adjusted if age_at_month >= oas_start_age else 0
        # Spouse income
        sp_pen = spouse_pension if (include_spouse and age_at_month >= spouse_pension_start_age) else 0
        sp_cpp = spouse_cpp_adjusted if (include_spouse and age_at_month >= spouse_cpp_start_age) else 0
        sp_oas = spouse_oas_adjusted if (include_spouse and age_at_month >= spouse_oas_start_age) else 0
        total_other_income = my_cpp + my_oas + sp_pen + sp_cpp + sp_oas
        net_withdrawal = max(0, current_withdrawal - total_other_income - monthly_savings_post)
        drawdown[m] = max(0, drawdown[m - 1] * (1 + post_monthly) - net_withdrawal)
        if drawdown[m] == 0 and depleted_month is None:
            depleted_month = m

    # --- Chart ---
    total_balances = np.concatenate([accum, drawdown[1:]])
    ages = np.arange(len(total_balances)) / 12 + current_age

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ages[:accum_months + 1], y=accum, name="Accumulation Phase",
                             line=dict(color="#636EFA"), fill="tozeroy"))
    fig.add_trace(go.Scatter(x=ages[accum_months:], y=drawdown, name="Drawdown (Nominal)",
                             line=dict(color="#EF553B"), fill="tozeroy"))

    # Real values
    real_full = np.zeros(len(total_balances))
    for i in range(len(total_balances)):
        real_full[i] = total_balances[i] / ((1 + inflation / 100) ** (ages[i] - current_age))
    fig.add_trace(go.Scatter(x=ages, y=real_full, name="Real Value (Inflation-Adjusted)",
                             line=dict(color="#AB63FA", dash="dash")))

    fig.add_vline(x=retire_age, line_dash="dot", annotation_text="Retirement", line_color="gray")
    if cpp_start_age >= retire_age:
        fig.add_vline(x=cpp_start_age, line_dash="dash", annotation_text="CPP", line_color="#00CC96")
    if oas_start_age >= retire_age:
        fig.add_vline(x=oas_start_age, line_dash="dash", annotation_text="OAS", line_color="#FFA15A")
    fig.update_layout(title="Retirement Projection", xaxis_title="Age", yaxis_title="Value ($)",
                      yaxis_tickformat="$,.0f", hovermode="x unified", height=500)

    with col2:
        st.plotly_chart(fig, use_container_width=True)

    # --- KPIs ---
    k1, k2, k3 = st.columns(3)
    k1.metric("Retirement Corpus at " + str(retire_age), f"${retirement_corpus:,.0f}")
    if depleted_month is not None:
        depletion_age = retire_age + depleted_month / 12
        k2.metric("Savings Depleted At", f"Age {depletion_age:.1f}")
        k3.metric("Status", "Shortfall", delta=f"Runs out {life_exp - depletion_age:.1f} years early",
                  delta_color="inverse")
    else:
        k2.metric("Remaining at " + str(life_exp), f"${drawdown[-1]:,.0f}")
        k3.metric("Status", "On Track", delta="Savings last through life expectancy")

    # --- Income breakdown ---
    st.divider()
    if not include_spouse:
        # 3 scenarios: pre-65, at 65, at 70
        st.subheader("Monthly Income Scenarios")
        cpp_at_65 = calc_cpp(cpp_base, 65)
        oas_at_65 = calc_oas(oas_base, 65)
        cpp_at_70 = calc_cpp(cpp_base, 70)
        oas_at_70 = calc_oas(oas_base, 70)

        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown("**First 10 Years (before 65)**")
            st.caption("Higher spending, no CPP or OAS yet")
            st.metric("CPP + OAS", "$0/mo")
            st.metric("Drawn from Portfolio", f"${monthly_income_early:,.0f}/mo")
            st.metric("Total Income", f"${monthly_income_early:,.0f}/mo")
        with s2:
            st.markdown("**At 65 (standard)**")
            benefits_65 = cpp_at_65 + oas_at_65
            draw_65 = max(0, monthly_retirement_income - benefits_65)
            st.caption(f"CPP ${cpp_at_65:,.0f} + OAS ${oas_at_65:,.0f}")
            st.metric("CPP + OAS", f"${benefits_65:,.0f}/mo")
            st.metric("Drawn from Portfolio", f"${draw_65:,.0f}/mo")
            st.metric("Total Income", f"${monthly_retirement_income:,.0f}/mo")
        with s3:
            st.markdown("**At 70 (deferred)**")
            benefits_70 = cpp_at_70 + oas_at_70
            draw_70 = max(0, monthly_retirement_income - benefits_70)
            st.caption(f"CPP ${cpp_at_70:,.0f} + OAS ${oas_at_70:,.0f}")
            st.metric("CPP + OAS", f"${benefits_70:,.0f}/mo")
            st.metric("Drawn from Portfolio", f"${draw_70:,.0f}/mo")
            st.metric("Total Income", f"${monthly_retirement_income:,.0f}/mo")
    else:
        st.subheader("Combined Monthly Income in Retirement")
        your_benefits = cpp_adjusted + oas_adjusted
        spouse_total = spouse_pension + spouse_cpp_adjusted + spouse_oas_adjusted
        all_other = your_benefits + spouse_total
        drawn_from_portfolio = max(0, monthly_retirement_income - all_other)
        combined = drawn_from_portfolio + all_other

        c1, c2, c3 = st.columns(3)
        c1.metric("Your CPP + OAS", f"${your_benefits:,.0f}/mo")
        c2.metric("Spouse Pension + CPP + OAS", f"${spouse_total:,.0f}/mo")
        c3.metric("Drawn from Portfolio", f"${drawn_from_portfolio:,.0f}/mo")

        st.metric("Combined Monthly Income (all sources)", f"${combined:,.0f}/mo")


# =============================================================================
# Tab 1 — Investment Growth
# =============================================================================
with tab1:
    st.header("Investment Growth Simulator")

    col1, col2 = st.columns([1, 2])

    with col1:
        initial = st.number_input("Initial Investment ($)", 0, 10_000_000, 10_000, 1_000, key="ig_initial")
        monthly = st.number_input("Monthly Contribution ($)", 0, 100_000, 500, 100, key="ig_monthly")
        annual_return = st.slider("Annual Rate of Return (%)", 0.0, 25.0, 7.0, 0.1, key="ig_return")
        years = st.slider("Time Horizon (years)", 1, 50, 20, key="ig_years")
        ig_annual_extra = st.number_input("Extra Added Money Per Year ($)", 0, 1_000_000, 0, 500, key="ig_extra")
        contrib_increase = st.slider("Annual Contribution Increase (%)", 0.0, 15.0, 0.0, 0.5, key="ig_increase")

    months = years * 12
    monthly_rate = annual_return / 100 / 12
    balances = np.zeros(months + 1)
    contributions = np.zeros(months + 1)
    balances[0] = initial
    contributions[0] = initial
    current_monthly = monthly

    for m in range(1, months + 1):
        if m > 1 and m % 12 == 1:
            current_monthly *= 1 + contrib_increase / 100
        extra = ig_annual_extra if (m % 12 == 1) else 0
        balances[m] = balances[m - 1] * (1 + monthly_rate) + current_monthly + extra
        contributions[m] = contributions[m - 1] + current_monthly + extra

    growth = balances - contributions
    time_axis = np.arange(months + 1) / 12

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=time_axis, y=contributions, name="Total Contributions", fill="tozeroy",
                              line=dict(color="#636EFA")))
    fig1.add_trace(go.Scatter(x=time_axis, y=balances, name="Portfolio Value", fill="tonexty",
                              line=dict(color="#00CC96")))
    fig1.update_layout(title="Portfolio Growth Over Time", xaxis_title="Years", yaxis_title="Value ($)",
                       yaxis_tickformat="$,.0f", hovermode="x unified", height=500)

    with col2:
        st.plotly_chart(fig1, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Final Portfolio Value", f"${balances[-1]:,.0f}")
    m2.metric("Total Contributions", f"${contributions[-1]:,.0f}")
    m3.metric("Investment Growth", f"${growth[-1]:,.0f}")

# =============================================================================
# Tab 2 — My Retirement (solo)
# =============================================================================
with tab2:
    st.header("My Retirement")
    run_retirement("rp", include_spouse=False)

# =============================================================================
# Tab 2b — Household Retirement (with spouse)
# =============================================================================
with tab2b:
    st.header("Household Retirement")
    run_retirement("hh", include_spouse=True)

# =============================================================================
# Tab 3 — Portfolio Comparison
# =============================================================================
with tab3:
    st.header("Portfolio Comparison")

    col_params, col_chart = st.columns([1, 2])

    with col_params:
        pc_initial = st.number_input("Initial Investment ($)", 0, 10_000_000, 100_000, 5_000, key="pc_initial")
        pc_years = st.slider("Time Horizon (years)", 1, 50, 20, key="pc_years")
        num_portfolios = st.slider("Number of Portfolios", 2, 4, 3, key="pc_num")

        st.subheader("Asset Class Returns & Volatility")
        st.caption("Set expected annual return and standard deviation for each asset class.")
        ac1, ac2 = st.columns(2)
        with ac1:
            stock_return = st.number_input("Stocks Return (%)", -10.0, 30.0, 10.0, 0.5, key="ac_sr")
            bond_return = st.number_input("Bonds Return (%)", -5.0, 15.0, 4.0, 0.5, key="ac_br")
        with ac2:
            cash_return = st.number_input("Cash Return (%)", 0.0, 10.0, 2.0, 0.5, key="ac_cr")
            re_return = st.number_input("Real Estate Return (%)", -5.0, 25.0, 7.0, 0.5, key="ac_rr")

        stock_vol = st.number_input("Stocks Volatility (%)", 0.0, 50.0, 16.0, 0.5, key="ac_sv")
        bond_vol = st.number_input("Bonds Volatility (%)", 0.0, 30.0, 5.0, 0.5, key="ac_bv")
        cash_vol = st.number_input("Cash Volatility (%)", 0.0, 10.0, 1.0, 0.5, key="ac_cv")
        re_vol = st.number_input("Real Estate Volatility (%)", 0.0, 40.0, 12.0, 0.5, key="ac_rv")

    asset_returns = np.array([stock_return, bond_return, cash_return, re_return]) / 100
    asset_vols = np.array([stock_vol, bond_vol, cash_vol, re_vol]) / 100

    default_allocations = [
        ("Aggressive", 80, 10, 5, 5),
        ("Balanced", 50, 30, 10, 10),
        ("Conservative", 20, 50, 20, 10),
        ("All Equity", 100, 0, 0, 0),
    ]

    portfolios = []
    for i in range(num_portfolios):
        defaults = default_allocations[i]
        with st.expander(f"Portfolio {i + 1}", expanded=(i == 0)):
            name = st.text_input("Name", defaults[0], key=f"pn_{i}")
            s = st.slider("Stocks %", 0, 100, defaults[1], 5, key=f"ps_{i}")
            b = st.slider("Bonds %", 0, 100, defaults[2], 5, key=f"pb_{i}")
            c = st.slider("Cash %", 0, 100, defaults[3], 5, key=f"pc_{i}")
            r = st.slider("Real Estate %", 0, 100, defaults[4], 5, key=f"pr_{i}")
            total = s + b + c + r
            if total != 100:
                st.warning(f"Allocations sum to {total}%. Should be 100%.")
            alloc = np.array([s, b, c, r]) / 100
            portfolios.append((name, alloc))

    # Compute portfolio metrics and growth curves
    fig3 = go.Figure()
    colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
    results = []

    for idx, (name, alloc) in enumerate(portfolios):
        port_return = np.dot(alloc, asset_returns)
        port_vol = np.sqrt(np.dot(alloc ** 2, asset_vols ** 2))  # simplified (no correlation)
        sharpe = (port_return - cash_return / 100) / port_vol if port_vol > 0 else 0

        months = pc_years * 12
        monthly_r = port_return / 12
        values = np.zeros(months + 1)
        values[0] = pc_initial
        for m in range(1, months + 1):
            values[m] = values[m - 1] * (1 + monthly_r)

        time_ax = np.arange(months + 1) / 12
        fig3.add_trace(go.Scatter(x=time_ax, y=values, name=name, line=dict(color=colors[idx % len(colors)])))
        results.append({
            "Portfolio": name,
            "Expected Return": f"{port_return * 100:.1f}%",
            "Volatility": f"{port_vol * 100:.1f}%",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Final Value": f"${values[-1]:,.0f}",
        })

    fig3.update_layout(title="Portfolio Growth Comparison", xaxis_title="Years", yaxis_title="Value ($)",
                       yaxis_tickformat="$,.0f", hovermode="x unified", height=500)

    with col_chart:
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Comparison Table")
    st.table(results)
