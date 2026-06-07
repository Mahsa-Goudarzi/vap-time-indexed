import streamlit as st
import pulp
import pandas as pd

st.set_page_config(
    page_title="VAP Optimizer - Base Model",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stButton > button {
    background: #0ea5e9 !important; color: #000 !important;
    border: none !important; font-weight: 600 !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.4rem !important; transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: #38bdf8 !important; transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(14,165,233,0.3) !important;
}
.stButton > button:disabled {
    background: #2a2f3e !important; color: #555 !important;
    transform: none !important; box-shadow: none !important;
}

.stTabs [data-baseweb="tab"] {
    font-size: 0.82rem !important;
    font-weight: 500 !important; letter-spacing: 0.04em !important;
    padding: 0.6rem 1.2rem !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #0ea5e9 !important;
    border-bottom: 2px solid #0ea5e9 !important;
    background: transparent !important;
}

.section-label {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.14em;
    color: #0ea5e9;
    margin-bottom: 0.3rem;
    margin-top: 1rem;
}
.info-box {
    border: 1px solid #38bdf8;
    border-left: 3px solid #38bdf8; border-radius: 6px;
    padding: 0.6rem 1rem; font-size: 0.82rem;
    opacity: 0.9;
}
.warn-box {
    border: 1px solid #facc15;
    border-left: 3px solid #facc15; border-radius: 6px;
    padding: 0.6rem 1rem; font-size: 0.82rem;
    margin-bottom: 0.8rem;
    opacity: 0.9;
}
.badge-E { background:#14532d; color:#86efac; padding:2px 7px; border-radius:4px; font-size:0.75rem; font-weight:600; }
.badge-D { background:#78350f; color:#fed7aa; padding:2px 7px; border-radius:4px; font-size:0.75rem; font-weight:600; }
.badge-single {
    background: #1e3a5f; color: #93c5fd;
    padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;
}
.badge-combined {
    background: #3b0764; color: #d8b4fe;
    padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;
}

/* assignment html table */
.asgn-table { width:100%; border-collapse:collapse; font-size:0.84rem; }
.asgn-table th {
    padding: 8px 12px; text-align:left;
    font-size:0.68rem; font-weight:600;
    letter-spacing:0.1em; text-transform:uppercase;
    color:#0ea5e9; border-bottom:2px solid #0ea5e9;
}
.asgn-table td { padding: 7px 12px; border-bottom: 1px solid rgba(128,128,128,0.15); }

hr { border-color: #2a2f3e !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# BASE SCENARIO DEFAULT DATA  (from notebook)
# ═══════════════════════════════════════════════════════════════════════════

BASE = {
    "n_carriers": 2,
    "n_trips": 5,
    "trips_per_carrier": [2, 3],
    "vehs_per_carrier":  [3, 3],
    "is_electric": [False, False, True, True, True, False],
    "alpha": 1.0, "beta": 0.8, "mu": 80.0, "c_E": 0.2,
    "T_drive": 8.0, "T_charge": 8.0, "income": 1.8,
    "d":     [150, 100, 80, 120, 130],
    "delta": [20,  20,  10, 10,  10],
    "p":     [25,  25,  25, 25,  25],
    "Cap":   [40,  40,  40, 40,  40,  40],
    "E_empty":[0.3,0.2, 0.3,0.3, 0.3, 0.3],
    "E_full": [0.3,0.4, 0.3,0.3, 0.4, 0.3],
    "op_cost": [
        [0.8, 0.8, 0.7, 1000, 1000, 1000],
        [1000,1000,1000,0.7,  0.7,  0.8 ],
    ],
    "d_origin": [
        [0,   0,   0,   50,  50,  50 ],
        [0,   0,   0,   50,  50,  50 ],
        [100, 100, 100, 80,  80,  80 ],
        [50,  50,  50,  0,   0,   0  ],
        [50,  50,  50,  0,   0,   0  ],
    ],
    "d_dest": [
        [150, 150, 150, 200, 200, 200],
        [100, 100, 100, 150, 150, 150],
        [50,  50,  50,  0,   0,   0  ],
        [170, 170, 170, 120, 120, 120],
        [180, 180, 180, 130, 130, 130],
    ],
    "eps": [
        [0,   150, 60,  140, 140],
        [150, 0,   0,   80,  80 ],
        [50,  50,  0,   0,   0  ],
        [170, 200, 200, 0,   120],
        [180, 180, 140, 130, 0  ],
    ],
    "O": [
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [1, 1, 0, 1, 1],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════

def init():
    if "initialized" not in st.session_state:
        for k, v in BASE.items():
            st.session_state[k] = v
        st.session_state.initialized = True
        st.session_state.solved = False

init()


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_structure():
    nc  = int(st.session_state.n_carriers)
    nt  = int(st.session_state.n_trips)
    tpc = st.session_state.trips_per_carrier[:nc]
    vpc = st.session_state.vehs_per_carrier[:nc]
    carriers = list(range(nc))
    trips    = list(range(nt))
    trips_of_carrier    = {}
    vehicles_of_carrier = {}
    tid = 0; vid = 0
    for r in carriers:
        trips_of_carrier[r]    = list(range(tid, tid + tpc[r]))
        vehicles_of_carrier[r] = list(range(vid, vid + vpc[r]))
        tid += tpc[r]; vid += vpc[r]
    all_vehicles = list(range(vid))
    return carriers, trips, trips_of_carrier, vehicles_of_carrier, all_vehicles

def tl(trips):    return [f"T{n}" for n in trips]
def vl(vehicles): return [f"V{v}" for v in vehicles]
def cl(carriers): return [f"C{r}" for r in carriers]

def df_1row(vals, cols):
    return pd.DataFrame([vals[:len(cols)] + [0.0]*(len(cols)-len(vals))], columns=cols)

def df_matrix(data, row_labels, col_labels, row_col_name):
    nr = len(row_labels); nc_ = len(col_labels)
    rows = []
    for i, rl in enumerate(row_labels):
        row = [rl]
        for j in range(nc_):
            try:    row.append(float(data[i][j]))
            except: row.append(0.0)
        rows.append(row)
    return pd.DataFrame(rows, columns=[row_col_name] + col_labels)


# ═══════════════════════════════════════════════════════════════════════════
# SOLVER
# ═══════════════════════════════════════════════════════════════════════════

def TOA_single(v, n, d_origin, d, d_dest):
    return d_origin[(n,v)] + d[n] + d_dest[(n,v)]

def TOA_combined(v, n, k, d_origin, d, eps, d_dest):
    return d_origin[(n,v)] + d[n] + eps[(n,k)] + d[k] + d_dest[(k,v)]

def emission_single(v, n, is_electric, d_origin, d, d_dest, E_empty, E_full, p, Cap):
    if is_electric[v]: return 0.0
    toa = TOA_single(v, n, d_origin, d, d_dest)
    return toa*E_empty[v] + (E_full[v]-E_empty[v])*d[n]*p[n]/Cap[v]

def emission_combined(v, n, k, is_electric, d_origin, d, eps, d_dest, E_empty, E_full, p, Cap):
    if is_electric[v]: return 0.0
    toa = TOA_combined(v, n, k, d_origin, d, eps, d_dest)
    return toa*E_empty[v] + (E_full[v]-E_empty[v])*(d[n]*p[n]+d[k]*p[k])/Cap[v]

def solve(params):
    carriers = params["carriers"]; trips = params["trips"]
    trips_of_carrier = params["trips_of_carrier"]
    vehicles_of_carrier = params["vehicles_of_carrier"]
    is_electric = params["is_electric"]
    alpha=params["alpha"]; beta=params["beta"]
    mu=params["mu"]; c_E=params["c_E"]
    T_avail=params["T_avail"]
    d=params["d"]; delta=params["delta"]
    p=params["p"]; Cap=params["Cap"]
    E_empty=params["E_empty"]; E_full=params["E_full"]
    I=params["I"]; z=params["z"]
    d_origin=params["d_origin"]; d_dest=params["d_dest"]
    eps=params["eps"]; O=params["O"]
    op_cost=params["op_cost"]; op_cost_full=params["op_cost_full"]

    # ── P1 ────────────────────────────────────────────────────────────────
    S0 = {}
    for r in carriers:
        pr = pulp.LpProblem(f"P1_{r}", pulp.LpMaximize)
        mt = trips_of_carrier[r]; mv = vehicles_of_carrier[r]
        chi = pulp.LpVariable.dicts("chi",
            [(n,v) for n in mt for v in mv], cat="Binary")
        pr += pulp.lpSum(
            (alpha*d[n]*I[r]
             - TOA_single(v,n,d_origin,d,d_dest)*op_cost[r][v]
             - c_E*emission_single(v,n,is_electric,d_origin,d,d_dest,E_empty,E_full,p,Cap)
            ) * chi[(n,v)]
            for n in mt for v in mv)
        for n in mt:
            pr += pulp.lpSum(chi[(n,v)] for v in mv) == 1
        pr += pulp.lpSum(chi[(n,v)] for n in mt for v in mv) <= len(mv)
        for v in mv:
            pr += pulp.lpSum(chi[(n,v)] for n in mt) <= 1
        for n in mt:
            for v in mv:
                if is_electric[v]:
                    pr += chi[(n,v)]*TOA_single(v,n,d_origin,d,d_dest) <= T_avail[v]*mu
        pr.solve(pulp.PULP_CBC_CMD(msg=0))
        S0[r] = pulp.value(pr.objective) if pr.status==1 else 0.0

    # ── P2 ────────────────────────────────────────────────────────────────
    prob = pulp.LpProblem("P2", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("x",
        [(r,v,n) for r in carriers
         for v in vehicles_of_carrier[r] for n in trips], cat="Binary")
    y = pulp.LpVariable.dicts("y",
        [(r,v,n,k) for r in carriers
         for v in vehicles_of_carrier[r]
         for n in trips for k in trips if k!=n], cat="Binary")

    def S1(r):
        terms = []
        for n in trips:
            for v in vehicles_of_carrier[r]:
                rev  = alpha*d[n]*I[r]
                opc  = TOA_single(v,n,d_origin,d,d_dest)*op_cost_full[(r,v)]
                emc  = beta*c_E*emission_single(v,n,is_electric,d_origin,d,d_dest,E_empty,E_full,p,Cap)
                terms.append((rev-opc-emc)*x[(r,v,n)])
        return pulp.lpSum(terms)

    def S2(r):
        terms = []
        for n in trips:
            for k in trips:
                if k==n: continue
                for v in vehicles_of_carrier[r]:
                    rev  = alpha*(d[n]+d[k])*I[r]
                    opc  = TOA_combined(v,n,k,d_origin,d,eps,d_dest)*op_cost_full[(r,v)]
                    emc  = beta*c_E*emission_combined(v,n,k,is_electric,d_origin,d,eps,d_dest,E_empty,E_full,p,Cap)
                    terms.append((rev-opc-emc)*y[(r,v,n,k)])
        return pulp.lpSum(terms)

    def S3(r):
        terms = []
        for n in trips:
            for rp in carriers:
                if rp==r: continue
                for v in vehicles_of_carrier[rp]:
                    terms.append(+delta[n]*z[(r,n)]*x[(rp,v,n)])
                for v in vehicles_of_carrier[r]:
                    terms.append(-delta[n]*z[(rp,n)]*x[(r,v,n)])
        for n in trips:
            for k in trips:
                if k==n: continue
                for rp in carriers:
                    if rp==r: continue
                    for v in vehicles_of_carrier[rp]:
                        terms.append(+delta[n]*z[(r,n)]*y[(rp,v,n,k)])
                        terms.append(+delta[k]*z[(r,k)]*y[(rp,v,n,k)])
                    for v in vehicles_of_carrier[r]:
                        terms.append(-delta[n]*z[(rp,n)]*y[(r,v,n,k)])
                        terms.append(-delta[k]*z[(rp,k)]*y[(r,v,n,k)])
        return pulp.lpSum(terms)

    prob += pulp.lpSum(S1(r)+S2(r)+S3(r) for r in carriers)

    for r in carriers:
        prob += S1(r)+S2(r)+S3(r) >= S0[r]
    for n in trips:
        prob += (
            pulp.lpSum(x[(r,v,n)] for r in carriers for v in vehicles_of_carrier[r])
            + pulp.lpSum(y[(r,v,n,k)]+y[(r,v,k,n)]
                         for r in carriers for v in vehicles_of_carrier[r]
                         for k in trips if k!=n)
            == 1)
    for r in carriers:
        prob += (
            pulp.lpSum(x[(r,v,n)] for v in vehicles_of_carrier[r] for n in trips)
            + pulp.lpSum(y[(r,v,n,k)] for v in vehicles_of_carrier[r]
                         for n in trips for k in trips if k!=n)
            <= len(vehicles_of_carrier[r]))
    for r in carriers:
        for v in vehicles_of_carrier[r]:
            prob += (
                pulp.lpSum(x[(r,v,n)] for n in trips)
                + pulp.lpSum(y[(r,v,n,k)] for n in trips for k in trips if k!=n)
                <= 1)
    for r in carriers:
        for v in vehicles_of_carrier[r]:
            if is_electric[v]:
                for n in trips:
                    prob += x[(r,v,n)]*TOA_single(v,n,d_origin,d,d_dest) <= T_avail[v]*mu
                for n in trips:
                    for k in trips:
                        if k!=n:
                            prob += y[(r,v,n,k)]*TOA_combined(v,n,k,d_origin,d,eps,d_dest) <= T_avail[v]*mu
    for r in carriers:
        for v in vehicles_of_carrier[r]:
            for n in trips:
                for k in trips:
                    if k!=n:
                        prob += y[(r,v,n,k)] <= O[(n,k)]

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[prob.status]
    total  = pulp.value(prob.objective) if prob.status==1 else None

    # results
    profit_rows = []
    for r in carriers:
        s1v=pulp.value(S1(r)); s2v=pulp.value(S2(r)); s3v=pulp.value(S3(r))
        profit_rows.append({
            "Carrier":            f"C{r}",
            "Initial S0 (€)":     round(S0[r],2),
            "Single S1 (€)":      round(s1v,2),
            "Combined S2 (€)":    round(s2v,2),
            "Compensation S3 (€)":round(s3v,2),
            "Final Total (€)":    round(s1v+s2v+s3v,2),
            "Gain vs S0 (€)":     round((s1v+s2v+s3v)-S0[r],2),
        })

    assign_rows = []
    is_elec = params["is_electric"]
    for r in carriers:
        for v in vehicles_of_carrier[r]:
            vtype = "E" if is_elec[v] else "D"
            for n in trips:
                val = pulp.value(x[(r,v,n)])
                if val and val > 0.5:
                    assign_rows.append({
                        "type": "Single", "trips": f"T{n}",
                        "carrier": f"C{r}", "vehicle": f"V{v}",
                        "vtype": vtype,
                    })
            for n in trips:
                for k in trips:
                    if k==n: continue
                    val = pulp.value(y[(r,v,n,k)])
                    if val and val > 0.5:
                        assign_rows.append({
                            "type": "Combined", "trips": f"T{n} + T{k}",
                            "carrier": f"C{r}", "vehicle": f"V{v}",
                            "vtype": vtype,
                        })

    return status, total, pd.DataFrame(profit_rows), assign_rows, S0


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("# 🚛 VAP Optimizer")
    st.markdown("*Cooperative Trip Planning - Base Model*")

    st.markdown("---")
    st.markdown("### Dimensions")

    nc = st.number_input("Carriers", 1, 8, int(st.session_state.n_carriers),
                          key="n_carriers")
    nt = st.number_input("Total Trips", 1, 20, int(st.session_state.n_trips),
                          key="n_trips")

    st.markdown("### Trips per Carrier")
    tpc = []
    for r in range(int(nc)):
        prev = (st.session_state.trips_per_carrier[r]
                if r < len(st.session_state.trips_per_carrier)
                else max(1, int(nt)//int(nc)))
        v = st.number_input(f"C{r} trips", 1, int(nt), int(prev), key=f"tpc_{r}")
        tpc.append(int(v))
    st.session_state.trips_per_carrier = tpc

    tpc_sum = sum(tpc)
    if tpc_sum != int(nt):
        st.warning(f"Trip sum ({tpc_sum}) ≠ {int(nt)}")

    st.markdown("### Vehicles per Carrier")
    vpc = []
    for r in range(int(nc)):
        prev = (st.session_state.vehs_per_carrier[r]
                if r < len(st.session_state.vehs_per_carrier) else 3)
        v = st.number_input(f"C{r} vehicles", 1, 15, int(prev), key=f"vpc_{r}")
        vpc.append(int(v))
    st.session_state.vehs_per_carrier = vpc

    total_v = sum(vpc)
    st.markdown(f"<small style='color:#7dd3fc'>Total vehicles: **{total_v}**</small>",
                unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Model Scalars")
    alpha    = st.number_input("α (revenue scale)",      0.1, 5.0,  1.0, 0.1)
    beta     = st.number_input("β (emission share)",     0.0, 1.0,  0.8, 0.05)
    mu       = st.number_input("μ speed (km/h)",        10.0,150.0, 80.0, 5.0)
    c_E      = st.number_input("c_E (€/g CO₂)",         0.0, 2.0,  0.2, 0.05)
    T_drive  = st.number_input("T_drive (h)",            1.0, 24.0,  8.0, 0.5)
    T_charge = st.number_input("T_charge (h)",           1.0, 24.0,  8.0, 0.5)
    income   = st.number_input("Income (€/km)",          0.1, 10.0,  1.8, 0.1)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

carriers, trips, trips_of_carrier, vehicles_of_carrier, all_vehicles = get_structure()
n_t = len(trips); n_v = len(all_vehicles); n_c = len(carriers)
t_labels = tl(trips); v_labels = vl(all_vehicles); c_labels = cl(carriers)

valid = (sum(tpc) == int(nt))

if not valid:
    st.markdown(
        f'<div class="warn-box">⚠ Trip distribution ({sum(tpc)}) ≠ total trips ({int(nt)}). '
        f'Fix in the sidebar before solving.</div>', unsafe_allow_html=True)
else:
    st.markdown(
        f'<div class="info-box">📐 {n_c} carriers · {n_t} trips · {n_v} vehicles '
        f'— all tables adapt automatically when you change dimensions.</div>',
        unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "🚛  Fleet & Costs",
    "📐  Distance Matrices",
    "▶  Run & Results",
])


# ── Tab 1: Fleet & Costs ──────────────────────────────────────────────────
with tab1:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<p class="section-label">Vehicle Types</p>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Rows follow vehicle order V0, V1, … Check Electric? for EV.</div>',
                    unsafe_allow_html=True)

        ev_rows = []
        for r in carriers:
            for v in vehicles_of_carrier[r]:
                prev = (st.session_state.is_electric[v]
                        if v < len(st.session_state.is_electric) else False)
                ev_rows.append({"Vehicle": f"V{v}  (C{r})", "Electric?": bool(prev)})

        ev_df = st.data_editor(
            pd.DataFrame(ev_rows), use_container_width=True, hide_index=True,
            column_config={
                "Vehicle":   st.column_config.TextColumn(disabled=True),
                "Electric?": st.column_config.CheckboxColumn(),
            },
            key=f"ev_{n_c}_{n_v}",
        )
        is_electric = {v: bool(ev_df.iloc[i]["Electric?"])
                       for i, v in enumerate(all_vehicles)}
        T_avail = {v: min(T_drive, T_charge) if is_electric[v] else T_drive
                   for v in all_vehicles}

        ev_count = sum(is_electric.values())
        st.markdown(
            f"<small style='color:#7dd3fc'>⚡ {ev_count} electric · "
            f"🛢 {n_v - ev_count} diesel</small>", unsafe_allow_html=True)

        st.markdown('<p class="section-label">Cargo Weight  p (kg)</p>',
                    unsafe_allow_html=True)
        p_df = st.data_editor(
            df_1row(BASE["p"], t_labels),
            use_container_width=True, hide_index=True,
            key=f"p_{n_t}",
        )

        st.markdown('<p class="section-label">Compensation Cost  δ (€)</p>',
                    unsafe_allow_html=True)
        delta_df = st.data_editor(
            df_1row(BASE["delta"], t_labels),
            use_container_width=True, hide_index=True,
            key=f"delta_{n_t}",
        )

    with col_b:
        st.markdown('<p class="section-label">Operating Cost  op_cost (€/km)</p>',
                    unsafe_allow_html=True)
        st.markdown('<div class="info-box">Row = Carrier, Column = Vehicle. '
                    'Use <strong>1000</strong> for vehicles not owned by that carrier.</div>',
                    unsafe_allow_html=True)

        op_default = []
        for i, r in enumerate(carriers):
            row = [c_labels[i]]
            for j, v in enumerate(all_vehicles):
                try: row.append(float(BASE["op_cost"][i][j]))
                except: row.append(0.7 if v in vehicles_of_carrier[r] else 1000.0)
            op_default.append(row)
        op_df = st.data_editor(
            pd.DataFrame(op_default, columns=["Carrier ↓ / Vehicle →"] + v_labels),
            use_container_width=True, hide_index=True,
            key=f"op_{n_c}_{n_v}",
        )

        st.markdown('<p class="section-label">Vehicle Capacity  Cap (kg)</p>',
                    unsafe_allow_html=True)
        cap_df = st.data_editor(
            df_1row(BASE["Cap"], v_labels),
            use_container_width=True, hide_index=True,
            key=f"cap_{n_v}",
        )

        st.markdown('<p class="section-label">Emissions (g/km)</p>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.caption("E_empty: vehicle empty")
            ee_df = st.data_editor(
                df_1row(BASE["E_empty"], v_labels),
                use_container_width=True, hide_index=True,
                key=f"ee_{n_v}",
            )
        with c2:
            st.caption("E_full: vehicle fully loaded")
            ef_df = st.data_editor(
                df_1row(BASE["E_full"], v_labels),
                use_container_width=True, hide_index=True,
                key=f"ef_{n_v}",
            )


# ── Tab 2: Distance Matrices ──────────────────────────────────────────────
with tab2:
    st.markdown('<div class="info-box">All values in <strong>km</strong>. '
                'Tables resize automatically when you change dimensions.</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-label">d: Trip Distance (km)</p>',
                    unsafe_allow_html=True)
        d_df = st.data_editor(
            df_1row(BASE["d"], t_labels),
            use_container_width=True, hide_index=True,
            key=f"d_{n_t}",
        )

        st.markdown('<p class="section-label">d_origin: Depot → Trip Origin (km)</p>',
                    unsafe_allow_html=True)
        st.caption("Row = Trip, Column = Vehicle")
        dor_df = st.data_editor(
            df_matrix(BASE["d_origin"], t_labels, v_labels, "Trip ↓ / Vehicle →"),
            use_container_width=True, hide_index=True,
            key=f"dor_{n_t}_{n_v}",
        )

        st.markdown('<p class="section-label">d_dest: Trip Destination → Depot (km)</p>',
                    unsafe_allow_html=True)
        st.caption("Row = Trip, Column = Vehicle")
        dd_df = st.data_editor(
            df_matrix(BASE["d_dest"], t_labels, v_labels, "Trip ↓ / Vehicle →"),
            use_container_width=True, hide_index=True,
            key=f"dd_{n_t}_{n_v}",
        )

    with col2:
        st.markdown('<p class="section-label">ε: Repositioning Distance (km)</p>',
                    unsafe_allow_html=True)
        st.caption("Row = Trip n, Column = Trip k. Diagonal = 0.")
        eps_df = st.data_editor(
            df_matrix(BASE["eps"], t_labels, t_labels, "T_n \\ T_k"),
            use_container_width=True, hide_index=True,
            key=f"eps_{n_t}",
        )

        st.markdown('<p class="section-label">O: Combinability (0 / 1)</p>',
                    unsafe_allow_html=True)
        st.caption("1 = may be combined. Diagonal must be 0.")
        O_df = st.data_editor(
            df_matrix(BASE["O"], t_labels, t_labels, "T_n \\ T_k"),
            use_container_width=True, hide_index=True,
            key=f"O_{n_t}",
        )


# ── Tab 3: Run & Results ──────────────────────────────────────────────────
with tab3:
    solve_btn = st.button("▶  Solve Optimization",
                          disabled=not valid,
                          use_container_width=False)

    if solve_btn and valid:
        with st.spinner("Solving... please wait..."):
            try:
                # parse inputs
                z = {(r,n): (1 if n in trips_of_carrier[r] else 0)
                     for r in carriers for n in trips}
                I_d = {r: income for r in carriers}

                d_d     = {n: float(d_df.iloc[0, n])     for n in trips}
                delta_d = {n: float(delta_df.iloc[0, n]) for n in trips}
                p_d     = {n: float(p_df.iloc[0, n])     for n in trips}
                Cap_d   = {v: float(cap_df.iloc[0, i])   for i, v in enumerate(all_vehicles)}
                E_empty_d = {v: float(ee_df.iloc[0, i])  for i, v in enumerate(all_vehicles)}
                E_full_d  = {v: float(ef_df.iloc[0, i])  for i, v in enumerate(all_vehicles)}

                op_cost_d = {r: {} for r in carriers}
                op_cost_full_d = {}
                for i, r in enumerate(carriers):
                    for j, v in enumerate(all_vehicles):
                        val = float(op_df.iloc[i, j+1])
                        op_cost_full_d[(r,v)] = val
                        if v in vehicles_of_carrier[r]:
                            op_cost_d[r][v] = val

                d_origin_d = {(n,v): float(dor_df.iloc[n, j+1])
                              for n in trips for j,v in enumerate(all_vehicles)}
                d_dest_d   = {(n,v): float(dd_df.iloc[n, j+1])
                              for n in trips for j,v in enumerate(all_vehicles)}
                eps_d      = {(n,k): float(eps_df.iloc[n, k+1])
                              for n in trips for k in trips}
                O_d        = {(n,k): int(O_df.iloc[n, k+1])
                              for n in trips for k in trips}

                params = dict(
                    carriers=carriers, trips=trips,
                    trips_of_carrier=trips_of_carrier,
                    vehicles_of_carrier=vehicles_of_carrier,
                    is_electric=is_electric, T_avail=T_avail,
                    alpha=alpha, beta=beta, mu=mu, c_E=c_E,
                    I=I_d, z=z,
                    d=d_d, delta=delta_d, p=p_d, Cap=Cap_d,
                    E_empty=E_empty_d, E_full=E_full_d,
                    op_cost=op_cost_d, op_cost_full=op_cost_full_d,
                    d_origin=d_origin_d, d_dest=d_dest_d,
                    eps=eps_d, O=O_d,
                )

                status, total, profit_df, assign_rows, S0 = solve(params)
                st.session_state.solved = True
                st.session_state.last = (status, total, profit_df, assign_rows, S0)

            except Exception as e:
                import traceback
                st.error(f"Solver error:\n\n{traceback.format_exc()}")

    if st.session_state.get("solved") and "last" in st.session_state:
        status, total, profit_df, assign_rows, S0 = st.session_state.last

        st.markdown("---")

        # ── metrics ───────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Solver Status", status)
        with m2:
            st.metric("Total Profit", f"€ {total:.2f}" if total else "—")
        with m3:
            total_gain = float(profit_df["Gain vs S0 (€)"].sum())
            st.metric("Cooperation Gain", f"€ {total_gain:.2f}",
                      delta=f"+€{total_gain:.2f}" if total_gain > 0 else None)
        with m4:
            n_combined = sum(1 for r in assign_rows if r["type"]=="Combined")
            n_single   = sum(1 for r in assign_rows if r["type"]=="Single")
            st.metric("Combined / Single Trips", f"{n_combined} / {n_single}")

        st.markdown("---")

        # ── profit table ──────────────────────────────────────────────────
        st.markdown('<p class="section-label">Profit Breakdown per Carrier</p>',
                    unsafe_allow_html=True)
        st.dataframe(profit_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── assignments ───────────────────────────────────────────────────
        st.markdown('<p class="section-label">Trip Assignments</p>',
                    unsafe_allow_html=True)

        if assign_rows:
            html_rows = []
            for row in assign_rows:
                type_badge = (
                    f'<span class="badge-single">Single</span>'
                    if row["type"] == "Single"
                    else f'<span class="badge-combined">Combined</span>'
                )
                veh_badge = (
                    f'<span class="badge-E">⚡ {row["vehicle"]}</span>'
                    if row["vtype"] == "E"
                    else f'<span class="badge-D">🛢 {row["vehicle"]}</span>'
                )
                html_rows.append(
                    f"<tr>"
                    f"<td>{type_badge}</td>"
                    f"<td style='font-family:DM Mono,monospace'>{row['trips']}</td>"
                    f"<td>{row['carrier']}</td>"
                    f"<td>{veh_badge}</td>"
                    f"</tr>"
                )

            table_html = f"""
<table class="asgn-table">
  <thead>
    <tr>
      <th>Type</th>
      <th>Trip(s)</th>
      <th>Carrier</th>
      <th>Vehicle</th>
    </tr>
  </thead>
  <tbody>
    {"".join(f'<tr>{r[4:-5]}</tr>' for r in html_rows)}
  </tbody>
</table>
"""
            st.write(table_html, unsafe_allow_html=True)

            # quick summary
            st.markdown("---")
            sa, sb, sc = st.columns(3)
            ev_trips = sum(1 for r in assign_rows if r["vtype"]=="E")
            with sa: st.metric("Electric Vehicle Trips", ev_trips)
            with sb: st.metric("Diesel Vehicle Trips",   len(assign_rows)-ev_trips)
            with sc: st.metric("Total Assignments",      len(assign_rows))
        else:
            st.info("No assignments found in the solution.")
