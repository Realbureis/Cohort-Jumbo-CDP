import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import re

st.set_page_config(page_title="Jumbo CDP - Gestão de Margem", layout="wide")

st.title("📊 Cohort: Faturamento vs. Investimento em Frete")
st.markdown("Análise de pedidos **'Enviados'** com foco em Margem e Logística.")

uploaded_files = st.file_uploader(
    "Suba as planilhas da Jumbo CDP", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

def limpar_moeda(df, coluna):
    """Garante que a coluna seja numérica, removendo R$, pontos de milhar e tratando vírgulas."""
    # Transforma em string, remove tudo que não é dígito ou vírgula/ponto
    s = df[coluna].astype(str).str.replace(r'[^\d,.-]', '', regex=True)
    # Se houver vírgula como separador decimal, ajusta para ponto
    s = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce').fillna(0)

if uploaded_files:
    dfs_list = []
    for file in uploaded_files:
        try:
            temp_df = pd.read_csv(file, sep=None, engine='python') if file.name.endswith('.csv') else pd.read_excel(file)
            temp_df.columns = [str(c).strip().lower() for c in temp_df.columns]
            dfs_list.append(temp_df)
        except Exception as e:
            st.error(f"Erro ao ler {file.name}: {e}")

    if dfs_list:
        df_full = pd.concat(dfs_list, ignore_index=True)
        
        all_cols = list(df_full.columns)
        st.sidebar.header("Mapeamento de Colunas")
        col_status = st.sidebar.selectbox("Status", all_cols, index=all_cols.index('status') if 'status' in all_cols else 0)
        col_data = st.sidebar.selectbox("Data", all_cols, index=all_cols.index('data') if 'data' in all_cols else 0)
        col_cliente = st.sidebar.selectbox("Cliente", all_cols, index=all_cols.index('codigo cliente') if 'codigo cliente' in all_cols else 0)
        col_total = st.sidebar.selectbox("Valor Total (Produtos)", all_cols, index=all_cols.index('valor total') if 'valor total' in all_cols else 0)
        col_premio = st.sidebar.selectbox("Valor do Premio (Frete Pago)", all_cols, index=all_cols.index('valor do premio') if 'valor do premio' in all_cols else 0)

        # Filtro 'Enviado'
        df = df_full[df_full[col_status].astype(str).str.lower().str.contains('enviado')].copy()

        if not df.empty:
            try:
                # Tratamento de Dados - Conversão forçada para numérico antes da subtração
                df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
                df[col_total] = limpar_moeda(df, col_total)
                df[col_premio] = limpar_moeda(df, col_premio)
                
                # Agora a subtração não dará erro de 'str'
                df['margem_contribuicao'] = df[col_total] - df[col_premio]
                
                df = df.dropna(subset=[col_data])
                
                # Lógica de Cohort
                df['mes_pedido'] = df[col_data].dt.to_period('M')
                df['cohort_group'] = df.groupby(col_cliente)[col_data].transform('min').dt.to_period('M')
                df['cohort_index'] = (df['mes_pedido'].dt.year - df['cohort_group'].dt.year) * 12 + \
                                     (df['mes_pedido'].dt.month - df['cohort_group'].dt.month)

                # --- PROCESSAMENTO ---
                def gear_pivot(df, valor, agg='sum'):
                    res = df.groupby(['cohort_group', 'cohort_index'])[valor].agg(agg).reset_index()
                    pivot = res.pivot(index='cohort_group', columns='cohort_index', values=valor)
                    pivot.index = pivot.index.astype(str)
                    return pivot

                pivot_retencao = gear_pivot(df, col_cliente, 'nunique')
                retention_pct = pivot_retencao.divide(pivot_retencao.iloc[:, 0], axis=0)
                pivot_receita = gear_pivot(df, col_total, 'sum')
                pivot_frete = gear_pivot(df, col_premio, 'sum')

                # --- INTERFACE ---
                tab1, tab2, tab3 = st.tabs(["👥 Retenção (%)", "💰 Faturamento (R$)", "🚚 Custo Frete (Premio)"])

                with tab1:
                    fig1, ax1 = plt.subplots(figsize=(12, 8))
                    sns.heatmap(retention_pct, annot=True, fmt='.0%', cmap='Blues', ax=ax1)
                    st.pyplot(fig1)

                with tab2:
                    fig2, ax2 = plt.subplots(figsize=(12, 8))
                    sns.heatmap(pivot_receita, annot=True, fmt=',.0f', cmap='Greens', ax=ax2)
                    st.pyplot(fig2)

                with tab3:
                    fig3, ax3 = plt.subplots(figsize=(12, 8))
                    sns.heatmap(pivot_frete, annot=True, fmt=',.0f', cmap='Reds', ax=ax3)
                    st.pyplot(fig3)

                st.divider()
                total_rev = df[col_total].sum()
                total_frete = df[col_premio].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Faturamento Total", f"R$ {total_rev:,.2f}")
                c2.metric("Total Gasto em Frete", f"R$ {total_frete:,.2f}")
                c3.metric("% Frete sobre Faturamento", f"{(total_frete/total_rev)*100:.2f}%")

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
                st.write("Dica: Verifique se as colunas de valor contêm apenas números ou formato R$.")
