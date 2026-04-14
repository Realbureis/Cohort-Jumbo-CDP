import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Jumbo CDP - Gestão Estratégica", layout="wide")

st.title("📊 Inteligência de Dados Jumbo CDP")
st.markdown("Interface adaptável: analise desde uma planilha isolada até o histórico completo.")

# --- FUNÇÕES DE LIMPEZA ---
def limpar_moeda(df, coluna):
    """Limpa strings de moeda (R$) e trata formatos brasileiros para numérico."""
    if df[coluna].dtype == 'object':
        # Remove símbolos, pontos de milhar e ajusta a vírgula decimal
        s = df[coluna].astype(str).str.replace(r'[^\d,.-]', '', regex=True)
        s = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        return pd.to_numeric(s, errors='coerce').fillna(0)
    return df[coluna].fillna(0)

# --- UPLOAD FLEXÍVEL ---
# O segredo está aqui: ele aceita qualquer quantidade de arquivos.
uploaded_files = st.file_uploader(
    "Selecione uma ou mais planilhas (Arraste os arquivos de 6 meses aqui)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

if uploaded_files:
    dfs_list = []
    
    # Feedback visual da quantidade de arquivos selecionados
    st.sidebar.info(f"📁 {len(uploaded_files)} arquivo(s) selecionado(s)")
    
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                temp_df = pd.read_csv(file, sep=None, engine='python')
            else:
                temp_df = pd.read_excel(file)
            
            # Padroniza nomes de colunas (minúsculo e sem espaços)
            temp_df.columns = [str(c).strip().lower() for c in temp_df.columns]
            dfs_list.append(temp_df)
            st.sidebar.write(f"✅ {file.name}")
        except Exception as e:
            st.sidebar.error(f"❌ Erve ao ler {file.name}: {e}")

    if dfs_list:
        # CONSOLIDAÇÃO: Junta tudo o que foi carregado (1, 2, 3 ou mais)
        df_full = pd.concat(dfs_list, ignore_index=True)
        
        # --- MAPEAMENTO DE COLUNAS ---
        all_cols = list(df_full.columns)
        st.sidebar.header("Configuração de Colunas")
        col_status = st.sidebar.selectbox("Coluna de Status", all_cols, index=all_cols.index('status') if 'status' in all_cols else 0)
        col_data = st.sidebar.selectbox("Coluna de Data", all_cols, index=all_cols.index('data') if 'data' in all_cols else 0)
        col_cliente = st.sidebar.selectbox("Código Cliente", all_cols, index=all_cols.index('codigo cliente') if 'codigo cliente' in all_cols else 0)
        col_total = st.sidebar.selectbox("Valor Total", all_cols, index=all_cols.index('valor total') if 'valor total' in all_cols else 0)
        col_premio = st.sidebar.selectbox("Valor do Premio", all_cols, index=all_cols.index('valor do premio') if 'valor do premio' in all_cols else 0)

        # Filtro de pedidos 'Enviado'
        df = df_full[df_full[col_status].astype(str).str.lower().str.contains('enviado')].copy()

        if not df.empty:
            try:
                # 1. Tratamento de Dados
                df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
                df[col_total] = limpar_moeda(df, col_total)
                df[col_premio] = limpar_moeda(df, col_premio)
                df = df.dropna(subset=[col_data])
                
                # 2. Lógica de Recorrência (Baseada em todo o conjunto carregado)
                df['primeira_compra'] = df.groupby(col_cliente)[col_data].transform('min')
                df['tipo_cliente'] = df.apply(lambda x: 'Novo Cliente' if x[col_data] == x['primeira_compra'] else 'Retido (Recorrência)', axis=1)

                # 3. Lógica de Cohort
                df['mes_pedido_p'] = df[col_data].dt.to_period('M')
                df['cohort_group'] = df['primeira_compra'].dt.to_period('M')
                df['cohort_index'] = (df['mes_pedido_p'].dt.year - df['cohort_group'].dt.year) * 12 + \
                                     (df['mes_pedido_p'].dt.month - df['cohort_group'].dt.month)

                # --- INTERFACE POR ABAS (MANTIDA) ---
                tab1, tab2, tab3 = st.tabs(["📊 Composição de Receita", "📅 Matriz de Retenção", "🚚 Eficiência Logística"])

                with tab1:
                    st.subheader("Faturamento: Clientes Novos vs. Recorrência")
                    df_resumo = df.groupby([df[col_data].dt.strftime('%Y-%m'), 'tipo_cliente'])[col_total].sum().unstack().fillna(0)
                    st.bar_chart(df_resumo)
                    
                    m1, m2 = st.columns(2)
                    total_novo = df[df['tipo_cliente'] == 'Novo Cliente'][col_total].sum()
                    total_retido = df[df['tipo_cliente'] == 'Retido (Recorrência)'][col_total].sum()
                    m1.metric("Faturamento de Novos", f"R$ {total_novo:,.2f}")
                    m2.metric("Faturamento de Recorrência", f"R$ {total_retido:,.2f}")

                with tab2:
                    st.subheader("Matriz de Cohort (%)")
                    cohort_counts = df.groupby(['cohort_group', 'cohort_index'])[col_cliente].nunique().reset_index()
                    pivot_counts = cohort_counts.pivot(index='cohort_group', columns='cohort_index', values=col_cliente)
                    retention = pivot_counts.divide(pivot_counts.iloc[:, 0], axis=0)
                    retention.index = retention.index.astype(str)

                    fig, ax = plt.subplots(figsize=(12, 8))
                    sns.heatmap(retention, annot=True, fmt='.0%', cmap='YlGnBu', ax=ax)
                    st.pyplot(fig)

                with tab3:
                    st.subheader("Peso do Frete (Prêmio) no Faturamento")
                    total_f = df[col_total].sum()
                    total_p = df[col_premio].sum()
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Faturamento Total", f"R$ {total_f:,.2f}")
                    c2.metric("Custo de Frete (Premio)", f"R$ {total_p:,.2f}")
                    c3.metric("% Frete sobre Receita", f"{(total_p/total_f)*100:.2f}%")
                    
                    st.line_chart(df.groupby(df[col_data].dt.strftime('%Y-%m'))[col_premio].sum())

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
        else:
            st.warning("Nenhum pedido 'Enviado' encontrado nos arquivos selecionados.")
else:
    st.info("💡 Pronto para analisar. Selecione a quantidade de planilhas que desejar acima.")
