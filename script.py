import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import matplotlib.pyplot as plt
import numpy as np

# Configuração da página
st.set_page_config(layout="wide", page_title="Análise de Transferências de Futebol")

# Título da aplicação
st.title("Análise de Transferências de Futebol")
st.write("""
Esta aplicação permite visualizar e analisar as transferências de jogadores entre clubes de futebol.
O menu lateral permite configurar a visualização.

**Desenvolvido por:** Igor Marques e João Pedro
""")


# Função para carregar dados
@st.cache_data
def load_data():
    try:
        # Carregar o arquivo CSV
        df = pd.read_csv('transfers_final.csv')  # Assumindo que o arquivo é CSV
        return df
    except Exception as e:
        st.error(f"Não foi possível carregar os dados do arquivo local. Erro: {str(e)}")
        return None


# Sidebar para configurações
with st.sidebar:
    st.header("Configurações")

    # Opções de visualização
    st.subheader("Opções de Visualização")
    node_size = st.selectbox("Tamanho dos nós por:",
                             ["degree", "in_degree", "out_degree", "betweenness", "closeness", "eigenvector"], index=0)

    # Configurações de arestas
    st.subheader("Configurações de Arestas")
    edge_width_enabled = st.checkbox("Largura variável por valor de transferência", True)

    # Configurações de física
    st.subheader("Configurações de Física")
    physics_enabled = st.checkbox("Ativar física da rede", True)

    # Filtros
    st.subheader("Filtros")
    connected_only = st.checkbox("Gerar subgrafo conectado", True)
    min_transfer_fee = st.number_input("Valor mínimo de transferência (em milhões)", min_value=0, value=1)

# Carregar dados
data = load_data()

if data is not None:
    # Criar grafo direcionado
    try:
        G = nx.DiGraph()

        # Filtrar por valor mínimo de transferência
        data = data[data['transfer_fee_amnt'] >= min_transfer_fee * 1e6]

        # Adicionar nós (clubes)
        all_teams = set(data['team_name']).union(set(data['counter_team_name']))
        for team in all_teams:
            G.add_node(team, size=10)

        # Adicionar arestas (transferências)
        transfer_counts = {}
        transfer_values = {}

        for _, row in data.iterrows():
            if row['dir'] == 'in':
                source = row['counter_team_name']
                target = row['team_name']
            else:  # 'left'
                source = row['team_name']
                target = row['counter_team_name']

            key = (source, target)

            # Contar número de transferências entre clubes
            transfer_counts[key] = transfer_counts.get(key, 0) + 1
            # Somar valores de transferência entre clubes
            transfer_values[key] = transfer_values.get(key, 0) + row['transfer_fee_amnt']

        # Adicionar arestas entre clubes
        for (source, target), count in transfer_counts.items():
            total_value = transfer_values[(source, target)]
            avg_value = total_value / count
            G.add_edge(source, target, count=count, transfer_fee_amnt=total_value, avg_transfer_fee=avg_value)

        # Gerar subgrafo conectado se solicitado
        if connected_only:
            # Encontrar o maior componente fracamente conectado
            largest_wcc = max(nx.weakly_connected_components(G), key=len)
            G = G.subgraph(largest_wcc).copy()

        # Calcular métricas
        degree_dict = dict(G.degree())
        in_degree_dict = dict(G.in_degree())
        out_degree_dict = dict(G.out_degree())
        betweenness_dict = nx.betweenness_centrality(G)
        closeness_dict = nx.closeness_centrality(G)
        eigenvector_dict = nx.eigenvector_centrality(G, max_iter=1000)

        # Atualizar atributos dos nós
        nx.set_node_attributes(G, degree_dict, 'degree')
        nx.set_node_attributes(G, in_degree_dict, 'in_degree')
        nx.set_node_attributes(G, out_degree_dict, 'out_degree')
        nx.set_node_attributes(G, betweenness_dict, 'betweenness')
        nx.set_node_attributes(G, closeness_dict, 'closeness')
        nx.set_node_attributes(G, eigenvector_dict, 'eigenvector')

        # Visualização Pyvis
        net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white", notebook=False,
                      directed=True)

        # Configurar opções para esconder labels e mostrar apenas no hover
        options = {
            "nodes": {
                "font": {
                    "size": 0,
                    "face": "arial"
                }
            },
            "edges": {
                "font": {
                    "size": 0
                }
            },
            "interaction": {
                "hover": True,
                "tooltipDelay": 200
            }
        }

        # Configurações de física
        if physics_enabled:
            options["physics"] = {
                "enabled": True,
                "barnesHut": {
                    "gravitationalConstant": -80000,
                    "centralGravity": 0.3,
                    "springLength": 250,
                    "springConstant": 0.001,
                    "damping": 0.09,
                    "avoidOverlap": 0.1
                }
            }
        else:
            options["physics"] = {
                "enabled": False
            }

        # Aplicar as opções
        net.set_options(str(options).replace("'", '"').replace("True", "true").replace("False", "false"))


        # Função para normalizar os valores de tamanho dos nós
        def normalize_size(value, min_val, max_val, min_size=5, max_size=30, physics_enabled=False):
            if max_val == min_val:
                return (max_size + min_size) / 2

            # Ajuste maior quando a física está ativada
            if physics_enabled:
                min_size = 10  # Tamanho mínimo maior
                max_size = 50  # Tamanho máximo maior

            return min_size + (value - min_val) * (max_size - min_size) / (max_val - min_val)


        # Obter valores para o tamanho dos nós
        size_attribute = {
            'degree': 'degree',
            'in_degree': 'in_degree',
            'out_degree': 'out_degree',
            'betweenness': 'betweenness',
            'closeness': 'closeness',
            'eigenvector': 'eigenvector'
        }[node_size]

        size_values = [G.nodes[node].get(size_attribute, 0) for node in G.nodes()]
        min_size_val = min(size_values)
        max_size_val = max(size_values)

        # Adicionar nós ao Pyvis
        for node in G.nodes():
            size_value = G.nodes[node].get(size_attribute, 0)
            normalized_size = normalize_size(size_value, min_size_val, max_size_val,
                                             min_size=5, max_size=30,
                                             physics_enabled=physics_enabled)

            net.add_node(
                node,
                label=node,
                size=normalized_size,
                color='#1f78b4',  # Azul para times
                title=f"""
                Clube: {node}
                Grau total: {G.nodes[node].get('degree', 0)}
                Grau de entrada: {G.nodes[node].get('in_degree', 0)}
                Grau de saída: {G.nodes[node].get('out_degree', 0)}
                Betweenness: {G.nodes[node].get('betweenness', 0):.3f}
                Closeness: {G.nodes[node].get('closeness', 0):.3f}
                Eigenvector: {G.nodes[node].get('eigenvector', 0):.3f}
                """
            )

        # Adicionar arestas ao Pyvis
        for edge in G.edges():
            edge_data = G.edges[edge]

            if edge_width_enabled and 'transfer_fee_amnt' in edge_data:
                value = edge_data['transfer_fee_amnt'] / 1e6  # Converter para milhões
                width = max(1, min(10, value / 10))  # Limitar entre 1 e 10
                title = f"Valor total: €{value:.2f}M\nNúmero de transferências: {edge_data.get('count', 1)}"
            else:
                width = 1
                title = f"Número de transferências: {edge_data.get('count', 1)}"
                if 'transfer_fee_amnt' in edge_data:
                    value = edge_data['transfer_fee_amnt'] / 1e6
                    title += f"\nValor total: €{value:.2f}M"

            net.add_edge(
                edge[0],
                edge[1],
                width=width,
                title=title,
                color='#b3b3b3'
            )

        # Gerar HTML
        net.save_graph("temp.html")
        html_file = open("temp.html", 'r', encoding='utf-8')
        html_content = html_file.read()
        html_file.close()

        # Mostrar grafo
        st.subheader("Visualização Interativa da Rede de Transferências")
        st.components.v1.html(html_content, height=600, scrolling=True)

        # Métricas da rede
        st.subheader("Métricas da Rede")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Número de Clubes", G.number_of_nodes())
            st.metric("Número de Transferências", G.number_of_edges())
            density = nx.density(G)
            st.metric("Densidade", f"{density:.4f}")
            st.caption("Densidade: Razão entre arestas existentes e possíveis (0-1). Redes densas têm mais conexões.")

        with col2:
            scc = nx.number_strongly_connected_components(G)
            wcc = nx.number_weakly_connected_components(G)
            st.metric("Componentes Fortemente Conectados", scc)
            st.caption("Componentes onde todos os nós são mutuamente alcançáveis (direcionado).")
            st.metric("Componentes Fracamente Conectados", wcc)
            st.caption("Componentes conectados se ignorarmos a direção das arestas.")

            if connected_only:
                # Calcular diâmetro para o maior componente fracamente conectado
                undirected_G = G.to_undirected()
                if nx.is_connected(undirected_G):
                    diameter = nx.diameter(undirected_G)
                    st.metric("Diâmetro", diameter)
                    st.caption("Diâmetro: Maior distância entre quaisquer dois nós na rede.")

        with col3:
            try:
                assortativity = nx.degree_assortativity_coefficient(G)
                st.metric("Assortatividade", f"{assortativity:.4f}")
                st.caption(
                    "Assortatividade: Tendência de nós se conectarem a nós similares (positivo) ou diferentes (negativo).")
            except Exception as e:
                st.write(f"Assortatividade: Não calculável ({str(e)})")

            # Estatísticas de transferência
            if 'transfer_fee_amnt' in data.columns:
                total_transfers = data['transfer_fee_amnt'].sum() / 1e6  # Em milhões
                avg_transfer = data['transfer_fee_amnt'].mean() / 1e6
                st.metric("Valor total das transferências (€)", f"{total_transfers:,.2f}M")
                st.metric("Valor médio por transferência (€)", f"{avg_transfer:,.2f}M")

            if connected_only:
                # Calcular periferia para o maior componente fracamente conectado
                undirected_G = G.to_undirected()
                if nx.is_connected(undirected_G):
                    periphery = nx.periphery(undirected_G)
                    st.markdown(f"""
                            **Periferia**  
                            <small>{", ".join(periphery)}</small>
                            """, unsafe_allow_html=True)
                    st.caption("Periferia: Nós com a maior excentricidade (distância máxima a qualquer outro nó).")
                    
        # Distribuição de grau
        st.subheader("Distribuição de Grau")

        degrees = [d for n, d in G.degree()]
        bins = np.arange(min(degrees), max(degrees) + 2) - 0.5

        fig, ax = plt.subplots()
        ax.hist(degrees, bins=bins, edgecolor='black')
        ax.set_xlabel('Grau')
        ax.set_ylabel('Contagem')
        ax.set_title('Distribuição de Grau dos Nós')

        st.pyplot(fig)

        st.caption("Distribuição de grau mostra quantos nós têm cada quantidade de conexões.")

        # Medidas de centralidade
        st.subheader("Medidas de Centralidade")

        # Criar DataFrame apenas com clubes
        centrality_df = pd.DataFrame({
            'Clube': list(G.nodes()),
            'Grau Total': [G.nodes[n].get('degree', 0) for n in G.nodes()],
            'Grau de Entrada': [G.nodes[n].get('in_degree', 0) for n in G.nodes()],
            'Grau de Saída': [G.nodes[n].get('out_degree', 0) for n in G.nodes()],
            'Betweenness': [G.nodes[n].get('betweenness', 0) for n in G.nodes()],
            'Closeness': [G.nodes[n].get('closeness', 0) for n in G.nodes()],
            'Eigenvector': [G.nodes[n].get('eigenvector', 0) for n in G.nodes()]
        })

        # Mostrar tabela com top clubes
        st.write("Top 10 clubes por cada medida de centralidade:")

        tabs = st.tabs(["Grau Total", "Grau de Entrada", "Grau de Saída", "Betweenness", "Closeness", "Eigenvector"])

        with tabs[0]:
            st.dataframe(
                centrality_df.sort_values('Grau Total', ascending=False).head(10),
                hide_index=True
            )
            st.caption("Centralidade de Grau: Clubes com mais conexões totais.")

        with tabs[1]:
            st.dataframe(
                centrality_df.sort_values('Grau de Entrada', ascending=False).head(10),
                hide_index=True
            )
            st.caption("Grau de Entrada: Clubes que mais recebem jogadores.")

        with tabs[2]:
            st.dataframe(
                centrality_df.sort_values('Grau de Saída', ascending=False).head(10),
                hide_index=True
            )
            st.caption("Grau de Saída: Clubes que mais vendem jogadores.")

        with tabs[3]:
            st.dataframe(
                centrality_df.sort_values('Betweenness', ascending=False).head(10),
                hide_index=True
            )
            st.caption("Betweenness: Clubes que atuam como pontes entre diferentes partes da rede.")

        with tabs[4]:
            st.dataframe(
                centrality_df.sort_values('Closeness', ascending=False).head(10),
                hide_index=True
            )
            st.caption("Closeness: Clubes que podem alcançar todos os outros em poucos passos.")

        with tabs[5]:
            st.dataframe(
                centrality_df.sort_values('Eigenvector', ascending=False).head(10),
                hide_index=True
            )
            st.caption("Eigenvector: Clubes conectados a outros clubes importantes.")

        # Matriz de adjacência - mostrando apenas os 20 clubes com maior grau
        st.subheader("Matriz de Adjacência")

        # Ordenar clubes por grau (do maior para o menor)
        clubs_sorted_by_degree = sorted(G.nodes(), key=lambda x: G.degree(x), reverse=True)
        top_20_clubs = clubs_sorted_by_degree[:20]

        # Criar matriz de adjacência apenas para os top 20 clubes
        adjacency_matrix = nx.adjacency_matrix(G, nodelist=top_20_clubs).todense()
        adj_df = pd.DataFrame(adjacency_matrix, index=top_20_clubs, columns=top_20_clubs)

        # Exibir a matriz com destaque para valores não-zero
        st.write("Matriz mostrando as transferências entre os 20 clubes com maior número de conexões:")
        st.dataframe(
            adj_df.style.map(lambda x: 'background-color: #0077b6' if x > 0 else '')
            .format("{:.0f}")  # Mostrar valores inteiros sem casas decimais
        )

        st.caption("""
        Matriz de Adjacência: Representação matricial das conexões entre os 20 clubes com maior grau.
        Cada célula mostra o número de transferências diretas entre os clubes correspondentes.
        """)

    except Exception as e:
        st.error(f"Erro ao processar os dados: {str(e)}")