import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Simulator Investiții: ETF vs. Unit Linked",
    layout="wide"
)

def fmt_lei(valoare: float) -> str:
    return f"{valoare:,.0f} lei".replace(",", ".")

def simuleaza_acumulare(
    suma_initiala: float,
    contributie_lunara: float,
    indexare_anuala_pct: float,
    randament_brut_pct: float,
    ani: int,
    ter_pct: float,
    comision_intrare_pct: float,
    aplica_impozit: bool,
    impozit_pct: float,
    retragere_activa: bool = False,
    an_retragere: int = 10,
    suma_retragere: float = 0.0
) -> pd.DataFrame:
    randament_net_anual = (randament_brut_pct - ter_pct) / 100.0
    rata_lunara = (1 + randament_net_anual) ** (1 / 12) - 1 if randament_net_anual > -1 else -1
    factor_intrare = 1 - (comision_intrare_pct / 100.0)

    sold_brut = suma_initiala * factor_intrare
    baza_cost = suma_initiala
    total_depus = suma_initiala

    date = [{
        "An": 0,
        "Contribuție lunară": contributie_lunara,
        "Total depus": total_depus,
        "Valoare brută": sold_brut,
        "Impozit estimat": 0.0,
        "Valoare netă": sold_brut
    }]

    for an in range(1, ani + 1):
        # Indexarea contribuției lunare în fiecare an (începând cu anul 2)
        contrib_curenta = contributie_lunara * ((1 + indexare_anuala_pct / 100.0) ** (an - 1))

        for _ in range(12):
            sold_brut = sold_brut * (1 + rata_lunara) + (contrib_curenta * factor_intrare)
            total_depus += contrib_curenta
            baza_cost += contrib_curenta

        # Retragere parțială la finalul anului selectat
        if retragere_activa and an == an_retragere and suma_retragere > 0 and sold_brut > 0:
            retragere_efectiva = min(suma_retragere, sold_brut)
            procent_retras = retragere_efectiva / sold_brut
            sold_brut -= retragere_efectiva
            baza_cost *= (1 - procent_retras)

        profit_brut = max(0.0, sold_brut - baza_cost)
        impozit = profit_brut * (impozit_pct / 100.0) if aplica_impozit else 0.0
        valoare_neta = sold_brut - impozit

        date.append({
            "An": an,
            "Contribuție lunară": round(contrib_curenta, 2),
            "Total depus": round(total_depus, 2),
            "Valoare brută": round(sold_brut, 2),
            "Impozit estimat": round(impozit, 2),
            "Valoare netă": round(valoare_neta, 2)
        })

    return pd.DataFrame(date)


def simuleaza_venit_pasiv(
    capital_initial: float,
    retragere_lunara: float,
    randament_brut_pct: float,
    ter_pct: float,
    indexare_retragere_pct: float = 0.0,
    ani_max: int = 50
) -> tuple[pd.DataFrame, int, bool]:
    randament_net_anual = (randament_brut_pct - ter_pct) / 100.0
    rata_lunara = (1 + randament_net_anual) ** (1 / 12) - 1 if randament_net_anual > -1 else -1

    sold = capital_initial
    total_retras = 0.0
    luni_sustinute = 0
    epuizat = False

    date = [{
        "An retragere": 0,
        "Retragere lunară": retragere_lunara,
        "Sold rămas": sold,
        "Total retras cumulat": 0.0
    }]

    for an in range(1, ani_max + 1):
        retragere_curenta = retragere_lunara * ((1 + indexare_retragere_pct / 100.0) ** (an - 1))
        for _ in range(12):
            if sold <= 0:
                epuizat = True
                break
            sold = sold * (1 + rata_lunara)
            if sold >= retragere_curenta:
                sold -= retragere_curenta
                total_retras += retragere_curenta
                luni_sustinute += 1
            else:
                total_retras += sold
                sold = 0.0
                epuizat = True
                break

        date.append({
            "An retragere": an,
            "Retragere lunară": round(retragere_curenta, 2),
            "Sold rămas": round(sold, 2),
            "Total retras cumulat": round(total_retras, 2)
        })

        if epuizat:
            break

    return pd.DataFrame(date), luni_sustinute, epuizat


# --- HEADER ---
st.title("Simulator Investiții & Venit Pasiv: ETF vs. Unit Linked")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Parametri Acumulare")
    suma_initiala = st.number_input("Sumă inițială (lei)", min_value=0, max_value=2_000_000, value=0, step=5000)
    contributie_lunara = st.slider("Contribuție lunară inițială (lei)", min_value=100, max_value=15000, value=2000, step=50)
    indexare_anuala = st.slider("Indexare anuală contribuție (%)", min_value=0.0, max_value=15.0, value=0.0, step=0.5, help="Cu cât crește contribuția lunară în fiecare an (ex. pentru a acoperi inflația).")
    randament_brut = st.slider("Randament anual brut (%)", min_value=1.0, max_value=18.0, value=10.0, step=0.5)
    ani = st.slider("Orizont acumulare (ani)", min_value=1, max_value=40, value=20, step=1)

    st.divider()
    st.header("2. Retragere Parțială")
    retragere_activa = st.toggle("Simulează o retragere parțială", value=False)
    an_retragere = st.slider("Anul retragerii", min_value=1, max_value=max(1, ani), value=min(10, ani), disabled=not retragere_activa)
    suma_retragere = st.number_input("Suma retrasă (lei)", min_value=0, max_value=2_000_000, value=50000, step=5000, disabled=not retragere_activa)

    st.divider()
    st.header("3. Faza de Venit Pasiv")
    venit_tinta = st.number_input("Venit pasiv dorit / lună (lei)", min_value=500, max_value=50000, value=5000, step=500)
    randament_retragere = st.slider("Randament anual în faza de retragere (%)", min_value=1.0, max_value=15.0, value=7.0, step=0.5)
    indexare_retragere = st.slider("Indexare anuală retragere / inflație (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.5)

    st.divider()
    mod_comparatie = st.toggle("Compară 2 instrumente (ETF vs. Unit Linked)", value=True)

# --- CONFIGURARE INSTRUMENTE ---
col_cfg1, col_cfg2 = st.columns(2) if mod_comparatie else (st.container(), None)

with col_cfg1:
    with st.expander("Setări Scenariu 1 (ex: ETF)", expanded=True):
        nume_1 = st.text_input("Denumire Scenariu 1", value="ETF (S&P 500 / VWCE)")
        c1, c2 = st.columns(2)
        ter_1 = c1.number_input("TER / Comision anual (%)", min_value=0.0, max_value=10.0, value=0.20, step=0.05, key="ter1")
        intrare_1 = c2.number_input("Comision intrare (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.1, key="in1")
        c3, c4 = st.columns(2)
        tax_on_1 = c3.checkbox("Aplică impozit pe profit", value=True, key="taxon1")
        tax_1 = c4.number_input("Impozit profit (%)", min_value=0.0, max_value=30.0, value=1.0, step=0.5, disabled=not tax_on_1, key="tax1")

df1 = simuleaza_acumulare(
    suma_initiala, contributie_lunara, indexare_anuala, randament_brut, ani,
    ter_1, intrare_1, tax_on_1, tax_1, retragere_activa, an_retragere, suma_retragere
)

df2 = None
if mod_comparatie and col_cfg2 is not None:
    with col_cfg2:
        with st.expander("Setări Scenariu 2 (ex: Unit Linked)", expanded=True):
            nume_2 = st.text_input("Denumire Scenariu 2", value="Unit Linked")
            c1, c2 = st.columns(2)
            ter_2 = c1.number_input("TER / Comision anual (%)", min_value=0.0, max_value=10.0, value=2.00, step=0.10, key="ter2")
            intrare_2 = c2.number_input("Comision alocare/intrare (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.5, key="in2")
            c3, c4 = st.columns(2)
            tax_on_2 = c3.checkbox("Aplică impozit pe profit", value=False, key="taxon2")
            tax_2 = c4.number_input("Impozit profit (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.5, disabled=not tax_on_2, key="tax2")

    df2 = simuleaza_acumulare(
        suma_initiala, contributie_lunara, indexare_anuala, randament_brut, ani,
        ter_2, intrare_2, tax_on_2, tax_2, retragere_activa, an_retragere, suma_retragere
    )

# --- TAB-URI ---
tab1, tab2, tab3 = st.tabs([
    "1. Acumulare & Retragere Parțială",
    "2. Perioada Venitului Pasiv",
    "3. Scenarii de Randament (%)"
])

# ==========================================
# TAB 1: ACUMULARE & RETRAGERE PARȚIALĂ
# ==========================================
with tab1:
    final_1 = df1.iloc[-1]
    capital_tinta_4pct = (venit_tinta * 12) / 0.04

    if mod_comparatie and df2 is not None:
        final_2 = df2.iloc[-1]
        diferenta = final_1["Valoare netă"] - final_2["Valoare netă"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total bani depuși", fmt_lei(final_1["Total depus"]), f"Ultima lună: {fmt_lei(final_1['Contribuție lunară'])}")
        m2.metric(f"Net final — {nume_1}", fmt_lei(final_1["Valoare netă"]))
        m3.metric(f"Net final — {nume_2}", fmt_lei(final_2["Valoare netă"]))
        m4.metric("Diferență netă", fmt_lei(abs(diferenta)), f"În favoarea: {nume_1 if diferenta >= 0 else nume_2}")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total bani depuși", fmt_lei(final_1["Total depus"]), f"Ultima lună: {fmt_lei(final_1['Contribuție lunară'])}")
        m2.metric("Valoare brută", fmt_lei(final_1["Valoare brută"]))
        m3.metric("Impozit estimat", fmt_lei(final_1["Impozit estimat"]))
        m4.metric("Valoare netă finală", fmt_lei(final_1["Valoare netă"]))

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df1["An"], y=df1["Total depus"], mode="lines", name="Total bani depuși",
        line=dict(color="#94a3b8", width=2, dash="dot")
    ))
    fig1.add_trace(go.Scatter(
        x=df1["An"], y=df1["Valoare netă"], mode="lines+markers", name=f"{nume_1} (Net)",
        line=dict(color="#2563eb", width=3)
    ))
    if mod_comparatie and df2 is not None:
        fig1.add_trace(go.Scatter(
            x=df2["An"], y=df2["Valoare netă"], mode="lines+markers", name=f"{nume_2} (Net)",
            line=dict(color="#10b981", width=3)
        ))

    # Marcaj pentru retragerea parțială
    if retragere_activa and suma_retragere > 0:
        fig1.add_vline(
            x=an_retragere, line_dash="dash", line_color="#f59e0b",
            annotation_text=f"Retragere -{fmt_lei(suma_retragere)}",
            annotation_position="top right"
        )

    fig1.add_hline(
        y=capital_tinta_4pct, line_dash="dash", line_color="#ef4444",
        annotation_text=f"Prag Regula 4% ({fmt_lei(capital_tinta_4pct)})",
        annotation_position="top left"
    )

    fig1.update_layout(
        title="Evoluția portofoliului în faza de acumulare",
        xaxis_title="Ani", yaxis_title="Valoare (lei)",
        hovermode="x unified", height=480, yaxis=dict(tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig1, use_container_width=True)

    with st.expander("Vezi tabelul detaliat de acumulare (an cu an)"):
        st.dataframe(df1.style.format("{:,.0f}"), use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: PERIOADA VENITULUI PASIV
# ==========================================
with tab2:
    st.subheader(f"Cât timp poți retrage {fmt_lei(venit_tinta)} / lună din capitalul acumulat?")

    df_pasiv_1, luni_1, epuizat_1 = simuleaza_venit_pasiv(
        final_1["Valoare netă"], venit_tinta, randament_retragere, ter_1, indexare_retragere
    )

    txt_durata_1 = f"{luni_1 // 12} ani și {luni_1 % 12} luni" if epuizat_1 else "50+ ani (Sustenabil)"

    if mod_comparatie and df2 is not None:
        df_pasiv_2, luni_2, epuizat_2 = simuleaza_venit_pasiv(
            df2.iloc[-1]["Valoare netă"], venit_tinta, randament_retragere, ter_2, indexare_retragere
        )
        txt_durata_2 = f"{luni_2 // 12} ani și {luni_2 % 12} luni" if epuizat_2 else "50+ ani (Sustenabil)"

        c1, c2 = st.columns(2)
        c1.metric(f"Durată venit pasiv — {nume_1}", txt_durata_1, f"Capital start: {fmt_lei(final_1['Valoare netă'])}")
        c2.metric(f"Durată venit pasiv — {nume_2}", txt_durata_2, f"Capital start: {fmt_lei(df2.iloc[-1]['Valoare netă'])}")
    else:
        st.metric(f"Durată venit pasiv — {nume_1}", txt_durata_1, f"Capital start: {fmt_lei(final_1['Valoare netă'])}")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df_pasiv_1["An retragere"], y=df_pasiv_1["Sold rămas"],
        mode="lines+markers", name=f"Sold {nume_1}",
        line=dict(color="#2563eb", width=3), fill="tozeroy" if not mod_comparatie else None
    ))
    if mod_comparatie and df2 is not None:
        fig2.add_trace(go.Scatter(
            x=df_pasiv_2["An retragere"], y=df_pasiv_2["Sold rămas"],
            mode="lines+markers", name=f"Sold {nume_2}",
            line=dict(color="#10b981", width=3)
        ))

    fig2.update_layout(
        title=f"Evoluția capitalului în timpul retragerilor ({fmt_lei(venit_tinta)}/lună, randament {randament_retragere}%)",
        xaxis_title="Ani de venit pasiv", yaxis_title="Sold rămas (lei)",
        hovermode="x unified", height=460, yaxis=dict(tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig2, use_container_width=True)

# ==========================================
# TAB 3: SCENARII DE RANDAMENT (%)
# ==========================================
with tab3:
    st.subheader(f"Comparație scenarii de randament pentru {nume_1}")
    s1, s2, s3 = st.columns(3)
    pct_conservator = s1.number_input("Scenariu Conservator (%)", min_value=1.0, max_value=20.0, value=7.0, step=0.5)
    pct_realist = s2.number_input("Scenariu Realist (%)", min_value=1.0, max_value=20.0, value=10.0, step=0.5)
    pct_optimist = s3.number_input("Scenariu Optimist (%)", min_value=1.0, max_value=20.0, value=12.0, step=0.5)

    scenarii = [
        ("Conservator", pct_conservator, "#f59e0b"),
        ("Realist", pct_realist, "#2563eb"),
        ("Optimist", pct_optimist, "#10b981")
    ]

    fig3 = go.Figure()
    rezumat_scenarii = []

    for label, pct, culoare in scenarii:
        df_s = simuleaza_acumulare(
            suma_initiala, contributie_lunara, indexare_anuala, pct, ani,
            ter_1, intrare_1, tax_on_1, tax_1, retragere_activa, an_retragere, suma_retragere
        )
        net_final = df_s.iloc[-1]["Valoare netă"]
        _, luni_s, epuizat_s = simuleaza_venit_pasiv(
            net_final, venit_tinta, randament_retragere, ter_1, indexare_retragere
        )
        durata_txt = f"{luni_s // 12} ani, {luni_s % 12} luni" if epuizat_s else "50+ ani (Sustenabil)"

        fig3.add_trace(go.Scatter(
            x=df_s["An"], y=df_s["Valoare netă"],
            mode="lines+markers", name=f"{label} ({pct}%)",
            line=dict(color=culoare, width=3)
        ))

        rezumat_scenarii.append({
            "Scenariu": f"{label} ({pct}%)",
            "Total depus": fmt_lei(df_s.iloc[-1]["Total depus"]),
            "Capital net final": fmt_lei(net_final),
            "Venit lunar (Regula 4%)": fmt_lei((net_final * 0.04) / 12),
            f"Durată la {fmt_lei(venit_tinta)}/lună": durata_txt
        })

    fig3.update_layout(
        title="Comparație evoluție portofoliu pe scenarii de randament",
        xaxis_title="Ani", yaxis_title="Valoare netă (lei)",
        hovermode="x unified", height=450, yaxis=dict(tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.table(pd.DataFrame(rezumat_scenarii))