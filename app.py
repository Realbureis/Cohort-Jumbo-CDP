import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Jumbo CDP - Dashboard Estratégico", layout="wide")

st.title("🚀 Jumbo CDP: Inteligência de Dados e Retenção")
st.markdown("Análise consolidada de faturamento, logística e comportamento de clientes.")

# --- FUNÇÕES DE AUXÍLIO ---
def limpar_moeda(df, coluna):
    """Limpa strings de moeda e converte para float."""
    s = df[coluna].astype(str).str.replace(r'[^\d,.-]', '', regex=True)
    s = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce').fillna(0)

# --- UPLOAD ---
uploaded_files = st.file_uploader(
    "Arraste as planilhas aqui (CSV ou Excel)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

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
        
        # Mapeamento de colunas (Sidebar)
        all_cols = list(df_full.columns)
        st.sidebar.header("Mapeamento")
        col_status = st.sidebar.selectbox("Status", all_cols, index=all_cols.index('status') if 'status' in all_cols else 0)
        col_data = st.sidebar.selectbox("Data", all_cols, index=all_cols.index('data') if 'data' in all_cols else 0)
        col_data_cad = st.sidebar.selectbox("Data do Cadastro", all_cols, index=all_cols.index('data do cadastro') if 'data do cadastro' in all_cols else 0)
        col_cliente = st.sidebar.selectbox("Código Cliente", all_cols, index=all_cols.index('codigo cliente') if 'codigo cliente' in all_cols else 0)
        col_total = st.sidebar.selectbox("Valor Total", all_cols, index=all_cols.index('valor total') if 'valor total' in all_cols else 0)
        col_premio = st.sidebar.selectbox("Valor do Premio", all_cols, index=all_cols.index('valor do premio') if 'valor do premio' in all_cols else 0)

        # Filtro de pedidos 'Enviados'
        df = df_full[df_full[col_status].astype(str).str.lower().str.contains('enviado')].copy()

        if not df.empty:
            try:
                # Tratamento de Dados
                df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
                df[col_data_cad] = pd.to_datetime(df[col_data_cad], errors='coerce')
                df[col_total] = limpar_moeda(df, col_total)
                df[col_premio] = limpar_moeda(df, col_premio)
                df = df.dropna(subset=[col_data, col_data_cad])
                
                # Identificação de Novo vs Retido baseada na DATA DE CADASTRO
                # Se o mês/ano do pedido for o mesmo do cadastro = Novo Cliente
                df['mes_pedido_idx'] = df[col_data].dt.to_period('M')
                df['mes_cadastro_idx'] = df[col_data_cad].dt.to_period('M')
                
                df['tipo_cliente'] = 'Retido (Recorrência)'
                df.loc[df['mes_pedido_idx'] == df['mes_cadastro_idx'], 'tipo_cliente'] = 'Novo Cliente'

                # Lógica de Cohort para a Matriz (Usando a data de cadastro como origem)
                df['cohort_group'] = df['mes_cadastro_idx']
                df['cohort_index'] = (df['mes_pedido_idx'].dt.year - df['cohort_group'].dt.year) * 12 + \
                                     (df['mes_pedido_idx'].dt.month - df['cohort_group'].dt.month)

                # --- TELA PRINCIPAL: ABAS ---
                tab_resumo, tab_cohort, tab_logistica = st.tabs(["📊 Visão Geral", "📅 Cohort", "🚚 Logística"])

                with tab_resumo:
                    st.subheader("Composição do Faturamento Mensal")
                    df_resumo = df.groupby([df[col_data].dt.strftime('%Y-%m'), 'tipo_cliente'])[col_total].sum().unstack().fillna(0)
                    
                    fig_bar, ax_bar = plt.subplots(figsize=(12, 6))
                    df_resumo.plot(kind='bar', stacked=True, color=['#2ecc71', '#3498db'], ax=ax_bar)
                    plt.title("Novos Clientes vs. Recorrência (Baseado no Cadastro)")
                    plt.ylabel("Faturamento (R$)")
                    plt.xlabel("Mês")
                    plt.xticks(rotation=45)
                    st.pyplot(fig_bar)
                    
                    st.info("💡 Como ler: A parte azul mostra o faturamento de clientes que já estavam cadastrados em meses anteriores.")

                with tab_cohort:
                    st.subheader("Matriz de Retenção por Data de Cadastro (%)")
                    cohort_counts = df.groupby(['cohort_group', 'cohort_index'])[col_cliente].nunique().reset_index()
                    pivot_counts = cohort_counts.pivot(index='cohort_group', columns='cohort_index', values=col_cliente)
                    
                    # Cálculo de retenção (Mês 0 é a base de cadastrados que compraram)
                    retention = pivot_counts.divide(pivot_counts.iloc[:, 0], axis=0)
                    retention.index = retention.index.astype(str)

                    fig_coh, ax_coh = plt.subplots(figsize=(12, 8))
                    sns.heatmap(retention, annot=True, fmt='.0%', cmap='YlGnBu', ax=ax_coh)
                    plt.title("Fidelidade após o Mês de Cadastro")
                    st.pyplot(fig_coh)

                with tab_logistica:
                    st.subheader("Eficiência de Frete (Prêmio)")
                    total_faturamento = df[col_total].sum()
                    total_frete = df[col_premio].sum()
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Faturamento Acumulado", f"R$ {total_faturamento:,.2f}")
                    c2.metric("Total Investido em Frete", f"R$ {total_frete:,.2f}", 
                              delta=f"{(total_frete/total_faturamento)*100:.2f}% da receita")
                    
                    df_frete_mes = df.groupby(df[col_data].dt.strftime('%Y-%m'))[col_premio].sum()
                    st.line_chart(df_frete_mes)

            except Exception as e:
                st.error(f"Erro no processamento dos dados: {e}")
        else:
            st.warning("Nenhum pedido com status 'Enviado' foi encontrado nas planilhas.")
else:
    st.info("Aguardando upload das planilhas para gerar o Dashboard Jumbo 2026.")
