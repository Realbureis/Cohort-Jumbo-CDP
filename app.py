import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Configuração da página para aproveitar o espaço lateral
st.set_page_config(page_title="Jumbo CDP - Análise de Cohort", layout="wide")

st.title("📊 Consilidação de Cohort - Pedidos Enviados")
st.markdown("""
Arraste as **3 planilhas** (ou mais) abaixo. O sistema irá unificar os dados, filtrar apenas os pedidos 
com status **'enviados'** e calcular a retenção baseada no **'código do cliente'**.
""")

# 1. Upload de múltiplos arquivos
uploaded_files = st.file_uploader(
    "Selecione seus arquivos CSV ou Excel", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

if uploaded_files:
    dfs_list = []
    
    # Processando cada arquivo subido
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                # Caso o CSV use ponto e vírgula como separador (comum em exportações brasileiras)
                # tentei adicionar um tratamento básico aqui
                temp_df = pd.read_csv(file, sep=None, engine='python')
            else:
                temp_df = pd.read_excel(file)
            
            # Padronizando nomes de colunas (removendo espaços e deixando minusculo)
            # Isso ajuda se uma planilha tiver "Status" e outra "status"
            temp_df.columns = [c.strip().lower() for c in temp_df.columns]
            dfs_list.append(temp_df)
            st.sidebar.success(f"✅ {file.name} carregado")
        except Exception as e:
            st.sidebar.error(f"❌ Erro ao ler {file.name}: {e}")

    if len(dfs_list) > 0:
        # 2. Concatenando tudo
        df_raw = pd.concat(dfs_list, ignore_index=True)
        
        try:
            # Conferindo nomes exatos após normalização
            # Esperamos: 'status', 'código do cliente', 'data'
            
            # 3. Filtragem e Conversão
            df = df_raw[df_raw['status'].astype(str).str.lower() == 'enviados'].copy()
            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            df = df.dropna(subset=['data']) # Remove linhas com data inválida
            
            # 4. Cálculo do Cohort
            # Mês da transação
            df['mes_pedido'] = df['data'].dt.to_period('M')
            
            # Mês da primeira compra do cliente (considerando todo o histórico consolidado)
            df['cohort_group'] = df.groupby('Codigo Cliente')['data'].transform('min').dt.to_period('M')
            
            # Índice de meses (0, 1, 2...)
            df['cohort_index'] = (df['mes_pedido'].dt.year - df['cohort_group'].dt.year) * 12 + \
                                 (df['mes_pedido'].dt.month - df['cohort_group'].dt.month)

            # 5. Criação da Matriz
            cohort_counts = df.groupby(['cohort_group', 'cohort_index'])['Codigo Cliente'].nunique().reset_index()
            cohort_pivot = cohort_counts.pivot(index='cohort_group', columns='cohort_index', values='Codigo Cliente')

            # 6. Cálculo da Retenção em %
            cohort_size = cohort_pivot.iloc[:, 0]
            retention = cohort_pivot.divide(cohort_size, axis=0)
            retention.index = retention.index.astype(str)

            # --- Visualização ---
            col1, col2 = st.columns([3, 1])

            with col1:
                st.subheader("Mapa de Calor de Retenção")
                fig, ax = plt.subplots(figsize=(12, 8))
                sns.heatmap(retention, annot=True, fmt='.0%', cmap='YlGnBu', ax=ax)
                plt.title('Retenção de Clientes (%)')
                plt.xlabel('Meses após a 1ª compra')
                plt.ylabel('Mês de Aquisição')
                st.pyplot(fig)

            with col2:
                st.subheader("Métricas Gerais")
                st.metric("Total de Pedidos Enviados", len(df))
                st.metric("Clientes Únicos", df['Codigo Cliente'].nunique())
                st.metric("Arquivos Processados", len(uploaded_files))

            # Opção de baixar os dados processados
            st.divider()
            if st.checkbox("Ver matriz numérica bruta"):
                st.dataframe(cohort_pivot)

        except KeyError as e:
            st.error(f"Erro: Não encontrei a coluna {e}. Verifique se os nomes na planilha estão corretos.")
    else:
        st.warning("Nenhum dado válido foi extraído dos arquivos.")
else:
    st.info("Aguardando o upload das 3 planilhas para gerar a inteligência de dados.")
