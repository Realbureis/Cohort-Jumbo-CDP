import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(page_title="Jumbo CDP - Cohort", layout="wide")
st.title("📊 Análise de Cohort - Status: [Enviado]")

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
            
            # Padroniza nomes de colunas: tudo minúsculo e sem espaços nas pontas
            temp_df.columns = [str(c).strip().lower() for c in temp_df.columns]
            dfs_list.append(temp_df)
        except Exception as e:
            st.error(f"Erro ao ler {file.name}: {e}")

    if dfs_list:
        df_full = pd.concat(dfs_list, ignore_index=True)
        
        # Mapeamento das colunas baseado no seu padrão
        # O código agora procura pelos nomes em minúsculo devido à padronização acima
        col_status = 'status'
        col_data = 'data'
        col_cliente = 'codigo cliente'

        if col_status in df_full.columns:
            # FILTRO INTELIGENTE: Aceita 'Enviado', 'enviado', 'Enviados', etc.
            df = df_full[df_full[col_status].astype(str).str.lower().str.contains('enviado')].copy()
            
            if not df.empty:
                try:
                    df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
                    df = df.dropna(subset=[col_data])
                    
                    # Lógica de Cohort
                    df['mes_pedido'] = df[col_data].dt.to_period('M')
                    df['cohort_group'] = df.groupby(col_cliente)[col_data].transform('min').dt.to_period('M')
                    
                    df['cohort_index'] = (df['mes_pedido'].dt.year - df['cohort_group'].dt.year) * 12 + \
                                         (df['mes_pedido'].dt.month - df['cohort_group'].dt.month)

                    # Matriz de Clientes Únicos
                    cohort_data = df.groupby(['cohort_group', 'cohort_index'])[col_cliente].nunique().reset_index()
                    cohort_pivot = cohort_data.pivot(index='cohort_group', columns='cohort_index', values=col_cliente)

                    # Cálculo da Retenção
                    cohort_size = cohort_pivot.iloc[:, 0]
                    retention = cohort_pivot.divide(cohort_size, axis=0)
                    retention.index = retention.index.astype(str)

                    # Gráfico
                    st.subheader(f"Retenção de Clientes - Total de {len(df)} pedidos 'Enviados'")
                    fig, ax = plt.subplots(figsize=(14, 10))
                    sns.heatmap(retention, annot=True, fmt='.0%', cmap='Blues', ax=ax)
                    plt.xlabel('Meses após a 1ª compra')
                    plt.ylabel('Mês de Aquisição')
                    st.pyplot(fig)
                    
                except Exception as e:
                    st.error(f"Erro ao processar dados: {e}")
            else:
                st.warning("Atenção: A coluna 'status' foi encontrada, mas não existe nenhum valor contendo 'enviado'.")
                st.write("Valores reais encontrados na sua coluna status:", df_full[col_status].unique())
        else:
            st.error(f"Coluna '{col_status}' não encontrada. Colunas disponíveis: {list(df_full.columns)}")
