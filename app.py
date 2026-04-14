import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Configuração da página
st.set_page_config(page_title="Jumbo CDP - Cohort Consolidado", layout="wide")

st.title("📊 Análise de Cohort - Pedidos Enviados")
st.markdown("Consolidação de múltiplas planilhas para visualização de retenção.")

# 1. Upload de Múltiplos Arquivos
uploaded_files = st.file_uploader(
    "Selecione as 3 planilhas (CSV ou Excel)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

if uploaded_files:
    dfs_list = []
    
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                # sep=None com engine python detecta automaticamente se é , ou ;
                temp_df = pd.read_csv(file, sep=None, engine='python')
            else:
                temp_df = pd.read_excel(file)
            
            # Limpeza rápida: remove espaços extras dos nomes das colunas
            temp_df.columns = [c.strip() for c in temp_df.columns]
            dfs_list.append(temp_df)
            st.sidebar.success(f"✅ {file.name} carregado")
        except Exception as e:
            st.sidebar.error(f"❌ Erro ao ler {file.name}: {e}")

    if dfs_list:
        # Consolida tudo em um único DataFrame
        df_full = pd.concat(dfs_list, ignore_index=True)
        
        try:
            # 2. Filtro de Status
            # Filtra apenas os pedidos com status 'enviados' (independente de maiúsculas/minúsculas)
            df = df_full[df_full['status'].astype(str).str.lower() == 'enviados'].copy()
            
            # 3. Tratamento de Datas
            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            df = df.dropna(subset=['data'])
            
            # 4. Lógica de Cohort
            # Nome da coluna ajustado para [Codigo Cliente]
            col_cliente = 'Codigo Cliente'
            
            # Período do pedido (Mês/Ano)
            df['mes_pedido'] = df['data'].dt.to_period('M')
            
            # Mês da primeira compra do cliente (considerando o histórico total das 3 planilhas)
            df['cohort_group'] = df.groupby(col_cliente)['data'].transform('min').dt.to_period('M')
            
            # Cálculo do Índice (Mês 0, Mês 1, Mês 2...)
            df['cohort_index'] = (df['mes_pedido'].dt.year - df['cohort_group'].dt.year) * 12 + \
                                 (df['mes_pedido'].dt.month - df['cohort_group'].dt.month)

            # 5. Criação da Matriz de Retenção
            cohort_data = df.groupby(['cohort_group', 'cohort_index'])[col_cliente].nunique().reset_index()
            cohort_pivot = cohort_data.pivot(index='cohort_group', columns='cohort_index', values=col_cliente)

            # Cálculo em porcentagem
            cohort_size = cohort_pivot.iloc[:, 0]
            retention = cohort_pivot.divide(cohort_size, axis=0)
            retention.index = retention.index.astype(str)

            # 6. Visualização
            st.subheader("Mapa de Calor: Retenção por Safra de Clientes")
            
            fig, ax = plt.subplots(figsize=(14, 10))
            sns.heatmap(retention, 
                        annot=True, 
                        fmt='.0%', 
                        cmap='YlGnBu', 
                        ax=ax)
            
            plt.title('Taxa de Retenção (%) - Base Jumbo CDP')
            plt.xlabel('Meses após a primeira compra')
            plt.ylabel('Mês de Aquisição (Cohort)')
            st.pyplot(fig)

            # Métricas rápidas no rodapé
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Clientes Únicos (Enviados)", df[col_cliente].nunique())
            m2.metric("Total de Pedidos Processados", len(df))
            m3.metric("Período Analisado", f"{df['data'].min().strftime('%m/%Y')} até {df['data'].max().strftime('%m/%Y')}")

        except KeyError as e:
            st.error(f"Erro: Não encontrei a coluna {e}. Verifique se o nome na planilha é exatamente 'status', 'data' ou 'Codigo Cliente'.")
    else:
        st.warning("Aguardando o upload das planilhas.")
else:
    st.info("Suba as 3 planilhas de 6 meses para consolidar os dados e gerar o gráfico.")
