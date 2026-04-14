import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Jumbo CDP - Cohort", layout="wide")
st.title("📊 Análise de Cohort - Pedidos Enviados")

uploaded_files = st.file_uploader(
    "Selecione as planilhas (CSV ou Excel)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

if uploaded_files:
    dfs_list = []
    
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                temp_df = pd.read_csv(file, sep=None, engine='python')
            else:
                temp_df = pd.read_excel(file)
            
            # --- PADRONIZAÇÃO DAS COLUNAS ---
            # Remove espaços e coloca tudo em minúsculo para facilitar a busca
            temp_df.columns = [str(c).strip().lower() for c in temp_df.columns]
            dfs_list.append(temp_df)
            st.sidebar.success(f"✅ {file.name} carregado")
        except Exception as e:
            st.sidebar.error(f"❌ Erro ao ler {file.name}: {e}")

    if dfs_list:
        df_full = pd.concat(dfs_list, ignore_index=True)
        
        # Mapeamento flexível das colunas (mesmo que mude o case, ele encontra)
        # Procuramos pelos termos equivalentes ao que você usa
        try:
            # Filtro de status
            df = df_full[df_full['status'].astype(str).str.lower() == 'enviados'].copy()
            
            # Tratamento de data
            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            df = df.dropna(subset=['data'])
            
            # Coluna Codigo Cliente (padronizada para minúsculo pelo código acima)
            col_cliente = 'codigo cliente' 
            
            # Lógica de Cohort
            df['mes_pedido'] = df['data'].dt.to_period('M')
            df['cohort_group'] = df.groupby(col_cliente)['data'].transform('min').dt.to_period('M')
            
            df['cohort_index'] = (df['mes_pedido'].dt.year - df['cohort_group'].dt.year) * 12 + \
                                 (df['mes_pedido'].dt.month - df['cohort_group'].dt.month)

            # Matriz
            cohort_data = df.groupby(['cohort_group', 'cohort_index'])[col_cliente].nunique().reset_index()
            cohort_pivot = cohort_data.pivot(index='cohort_group', columns='cohort_index', values=col_cliente)

            # Retenção
            cohort_size = cohort_pivot.iloc[:, 0]
            retention = cohort_pivot.divide(cohort_size, axis=0)
            retention.index = retention.index.astype(str)

            # Plot
            st.subheader("Mapa de Calor de Retenção")
            fig, ax = plt.subplots(figsize=(14, 10))
            sns.heatmap(retention, annot=True, fmt='.0%', cmap='YlGnBu', ax=ax)
            plt.xlabel('Meses após a 1ª compra')
            plt.ylabel('Mês de Aquisição')
            st.pyplot(fig)

        except KeyError:
            st.error("❌ Erro de Colunas!")
            st.write("As colunas detectadas no seu arquivo foram:")
            st.write(list(df_full.columns))
            st.info("Verifique se as colunas na sua planilha se chamam exatamente: 'status', 'data' e 'Codigo Cliente'.")
    else:
        st.warning("Aguardando upload.")
