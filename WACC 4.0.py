import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import base64

st.set_page_config(page_title="Simulador de WACC", layout="centered")
def get_base64_image(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

logo_base64 = get_base64_image("logo.png.png")

st.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="data:image/png;base64,{logo_base64}" alt="Logo" width="150">
        <h1 style="margin: 0;">Simulador de WACC com Monte Carlo</h1>
    </div>
    """,
    unsafe_allow_html=True)

st.markdown("### Qual percentil usar e quando?")

# Tabela simples com markdown puro do Streamlit
st.markdown("""
| Situação                                                                 | Percentil recomendado  |
|--------------------------------------------------------------------------|------------------------|
| Ambiente regulatório **estável e maduro** (baixo risco)                 | **50%**                 |
| Concessões **brownfield** (ativos já existentes, com risco menor)       | **50% a 69%**           |
| Concessões **greenfield** (ativos novos, com mais risco)                | **69% ou até 84%**      |
| Ambiente **regulatório instável** ou de **alta volatilidade econômica** | **84%**                 |
| Projetos de **altíssimo CAPEX** (portos, aeroportos grandes etc.)       | **69% a 84%**           |
""")            
#file_path = os.path.expanduser(r'~\\OneDrive - Eagle Consultoria Econômica e de Engenharia\\Projetos\\ECP04 - Gestão do conhecimento\\2. Economia\\WACC\\inputs wacc 3.0.xlsx')
file_path = 'inputs wacc 3.0.xlsx'

# Input
try:
    fixos_df = pd.read_excel(file_path, sheet_name='fixos')
    anuais_df = pd.read_excel(file_path, sheet_name='anuais')
    setoriais_df = pd.read_excel(file_path, sheet_name='setoriais')
except Exception as e:
    st.error(f"❌ Arquivo não encontrado: {e}")
    st.stop()

# Lista de setores
sector_list = setoriais_df['setor'].dropna().tolist()
chosen_sector = st.selectbox("Selecione o setor desejado:", sector_list)

# Escolha do percentil
percentil_desejado = st.slider(
    "Percentil desejado",
    min_value=50,
    max_value=99,
    value=69,
    step=1
)

n_simulations = st.number_input("🔁 Número de simulações", min_value=1000, value=30000, step=1000)

# Botão de cálculo
if st.button("Calcular WACC"):
    try:
        # Dados do setor escolhido
        setor = setoriais_df[setoriais_df['setor'] == chosen_sector].iloc[0]
        beta = setor['beta']
        equity_weight = setor['equity_weight']
        debt_weight = setor['debt_weight']

        # x e s
        country_risk_premium = anuais_df['country_risk_premium'].mean()
        risk_free_rate_avg = anuais_df['risk_free_rate'].mean()
        market_risk_premium_avg = anuais_df['market_risk_premium'].mean()
        market_risk_premium_std = anuais_df['market_risk_premium'].std()
        cost_of_debt_nominal_avg = anuais_df['cost_of_debt_nominal'].mean()
        cost_of_debt_nominal_std = anuais_df['cost_of_debt_nominal'].std()
        inflation_avg = anuais_df['inflation_us'].mean()
        tax_rate = fixos_df.loc[0, 'tax_rate']
        unlevered_beta = beta * (1 + (1 - tax_rate) * (debt_weight / equity_weight))

        mrp_samples = np.random.normal(market_risk_premium_avg, market_risk_premium_std, n_simulations)
        cost_of_debt_nominal_samples = np.random.normal(cost_of_debt_nominal_avg, cost_of_debt_nominal_std, n_simulations)

        ke_nominal = risk_free_rate_avg + unlevered_beta * mrp_samples + country_risk_premium

        ke_real = ((1 + ke_nominal) / (1 + inflation_avg)) - 1
        kd_real = ((1 + cost_of_debt_nominal_samples) / (1 + inflation_avg)) - 1

        wacc_real = equity_weight * ke_real + debt_weight * kd_real * (1 - tax_rate)
        wacc_nominal = equity_weight * ke_nominal + debt_weight * cost_of_debt_nominal_samples * (1 - tax_rate)

        media = np.mean(wacc_real)
        mediana = np.median(wacc_real)
        percentil_valor = np.percentile(wacc_real, percentil_desejado)
        
        # Resultados principais
        st.success(f"📌 Média do WACC Real: {media*100:.2f}%")
        st.success(f"📌 Média do WACC Nominal: {np.mean(wacc_nominal)*100:.2f}%")
        st.info(f"📌 Mediana do WACC Real: {mediana*100:.2f}%")
        st.warning(f"📌 WACC Real no percentil {percentil_desejado}%: {percentil_valor*100:.2f}%")

        plt.style.use('default')
        sns.set_style("dark", {"axes.facecolor": "#2c2c2e"})  # cinza escuro para fundo dos eixos
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#2c2c2e')  # fundo da figura

        # Histograma
        sns.histplot(
            wacc_real,
            bins=50,
            stat="density",
            color="deepskyblue",
            edgecolor="white",
            ax=ax
        )

        sns.kdeplot(
            wacc_real,
            color="cyan",
            linewidth=2.5,
            ax=ax
        )
        ax.axvline(media, color='red', linestyle='--', linewidth=2, label=f"Média: {media*100:.2f}%")
        ax.axvline(mediana, color='limegreen', linestyle='--', linewidth=2, label=f"Mediana: {mediana*100:.2f}%")
        ax.axvline(percentil_valor, color='gold', linestyle='--', linewidth=2, label=f"Percentil {percentil_desejado}%: {percentil_valor*100:.2f}%")

        #ax.axvline(media, color='red', linestyle='--', linewidth=2, label=f"Média: {media:.4f}")
        #ax.axvline(mediana, color='limegreen', linestyle='--', linewidth=2, label=f"Mediana: {mediana:.4f}")
        #ax.axvline(percentil_valor, color='gold', linestyle='--', linewidth=2, label=f"Percentil {percentil_desejado}%: {percentil_valor:.4f}")

        ax.set_title(f"Distribuição Simulada do WACC Real – {chosen_sector}", fontsize=14, weight='bold', color='white')
        ax.set_xlabel("WACC Real", fontsize=12, color='white')
        ax.set_ylabel("Densidade", fontsize=12, color='white')
        ax.tick_params(colors='white')

        legend = ax.legend(loc='upper right', fontsize=10, facecolor='#1e1e1e', edgecolor='white')
        for text in legend.get_texts():
            text.set_color('white')

        ax.grid(True, linestyle='--', alpha=0.2)

        st.pyplot(fig)

        # Checar valores das variáveis
        #st.write("Média Ke_nominal:", np.mean(ke_nominal))
        #st.write("Média Ke_real:", np.mean(ke_real))
        #st.write("Média Kd_nominal:", np.mean(cost_of_debt_nominal_samples))
        #st.write("Média Kd_real:", np.mean(kd_real))
        #st.write("Inflação média:", inflation_avg)
        #st.write("Peso do capital próprio (E):", equity_weight)
        #st.write("Peso da dívida (D):", debt_weight)
        #st.write("Taxa de imposto:", tax_rate)
        #st.write("risk_free_rate_avg:", risk_free_rate_avg)
        #st.write("beta:", beta)
        #st.write("country_risk_premium", country_risk_premium)
        #st.write("market_risk_premium_avg", market_risk_premium_avg)
        #st.write("unlevered_beta", unlevered_beta)

    except Exception as e:
        st.error(f"❌ Erro ao calcular o WACC: {e}")

