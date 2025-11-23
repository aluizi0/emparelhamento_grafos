import re
import os
import copy
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

# --- Estruturas de Dados ---
class Projeto:
    def __init__(self, codigo, vagas, nota_minima):
        self.codigo = codigo
        self.vagas = int(vagas)
        self.nota_minima = int(nota_minima)
        self.alunos_alocados = [] # Lista de objetos Aluno

    def __repr__(self):
        return f"[{self.codigo}: Vagas={self.vagas}, Min={self.nota_minima}]"

class Aluno:
    def __init__(self, codigo, preferencias_raw, nota):
        self.codigo = codigo
        # Limpa espaços e cria lista
        self.preferencias = [p.strip() for p in preferencias_raw.split(',') if p.strip()]
        # Guarda uma cópia das preferencias originais para calcular satisfação depois
        self.preferencias_originais = list(self.preferencias) 
        self.nota = int(nota)
        self.projeto_alocado = None

    def __repr__(self):
        return f"[{self.codigo}: Nota={self.nota}]"

# --- Funções de Leitura e Processamento ---
def carregar_dados(caminho_arquivo):
    projetos = {}
    alunos = {}

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Regex para Projetos: (P1, 2, 5)
    matches_proj = re.findall(r'\((P\d+),\s*(\d+),\s*(\d+)\)', conteudo)
    for p_code, vagas, nota_min in matches_proj:
        projetos[p_code] = Projeto(p_code, vagas, nota_min)

    # Regex para Alunos: (A1):(P1, P30, P50) (5)
    matches_aluno = re.findall(r'\((A\d+)\):\((.*?)\)\s*\((\d)\)', conteudo)
    for a_code, prefs_str, nota in matches_aluno:
        alunos[a_code] = Aluno(a_code, prefs_str, nota)

    return projetos, alunos

def filtrar_preferencias(projetos, alunos):
    remocoes = 0
    for aluno in alunos.values():
        validas = []
        for p_code in aluno.preferencias:
            proj = projetos.get(p_code)
            if proj and aluno.nota >= proj.nota_minima:
                validas.append(p_code)
            else:
                remocoes += 1
        aluno.preferencias = validas
    print(f"Filtragem: {remocoes} preferências removidas por requisitos não atendidos.")

# --- Algoritmo Gale-Shapley ---
def executar_gale_shapley(projetos, alunos):
    # Fila apenas com alunos que têm preferências válidas
    fila = [a.codigo for a in alunos.values() if a.preferencias]
    
    snapshots = []
    iteracao = 0
    
    # Dicionário para rastrear o estado atual das conexões para o gráfico
    estado_conexoes = {} # Chave: (aluno, projeto), Valor: 'aceito'

    while fila:
        iteracao += 1
        a_code = fila.pop(0)
        aluno = alunos[a_code]

        if not aluno.preferencias:
            continue

        p_code = aluno.preferencias.pop(0)
        projeto = projetos[p_code]

        # -- Registro do Snapshot (Proposta) --
        snapshots.append({
            'iteracao': iteracao,
            'acao': 'proposta',
            'aluno': a_code,
            'projeto': p_code,
            'conexoes': estado_conexoes.copy() # Copia o estado atual
        })

        aceito = False
        
        # 1. Vaga Livre
        if len(projeto.alunos_alocados) < projeto.vagas:
            projeto.alunos_alocados.append(aluno)
            aluno.projeto_alocado = projeto
            aceito = True
            estado_conexoes[(a_code, p_code)] = 'aceito'
            
        # 2. Cheio -> Competição por Nota
        else:
            projeto.alunos_alocados.sort(key=lambda x: x.nota)
            pior_atual = projeto.alunos_alocados[0]

            if aluno.nota > pior_atual.nota:
                # Troca
                projeto.alunos_alocados.pop(0)
                pior_atual.projeto_alocado = None
                
                # Remove conexão antiga do estado
                if (pior_atual.codigo, p_code) in estado_conexoes:
                    del estado_conexoes[(pior_atual.codigo, p_code)]
                
                fila.append(pior_atual.codigo) # O removido volta pra fila

                projeto.alunos_alocados.append(aluno)
                aluno.projeto_alocado = projeto
                aceito = True
                estado_conexoes[(a_code, p_code)] = 'aceito'
            else:
                # Rejeitado
                fila.append(a_code)
        
        # Registra o resultado desta iteração para visualização
        snapshots[-1]['resultado'] = 'aceito' if aceito else 'rejeitado'
        snapshots[-1]['conexoes_final'] = estado_conexoes.copy()

    return snapshots

# --- Visualização ---
def gerar_visualizacoes(projetos, alunos, snapshots):
    if not os.path.exists('graficos'):
        os.makedirs('graficos')

    # 1. Gerar Snapshots (Vamos pegar 10 momentos distribuídos)
    total_snaps = len(snapshots)
    indices_para_plotar = [int(i * total_snaps / 9) for i in range(10)] # 10 índices
    indices_para_plotar[-1] = total_snaps - 1 # Garante o último
    
    # Layout do Grafo Bipartido
    G = nx.Graph()
    top_nodes = list(alunos.keys())
    bottom_nodes = list(projetos.keys())
    G.add_nodes_from(top_nodes, bipartite=0)
    G.add_nodes_from(bottom_nodes, bipartite=1)
    
    # Posicionamento fixo para não pular na tela
    pos = {}
    for i, node in enumerate(top_nodes):
        pos[node] = (i * 2, 1) # Alunos em cima
    for i, node in enumerate(bottom_nodes):
        pos[node] = (i * 8, 0) # Projetos embaixo (mais espaçados pois são menos)

    print("Gerando imagens dos snapshots...")
    for idx, i in enumerate(indices_para_plotar):
        snap = snapshots[i]
        
        plt.figure(figsize=(20, 10))
        plt.title(f"Iteração {snap['iteracao']}: Aluno {snap['aluno']} -> Projeto {snap['projeto']} ({snap['resultado'].upper()})")
        
        # Desenha nós
        nx.draw_networkx_nodes(G, pos, nodelist=top_nodes, node_color='skyblue', node_size=300, label='Alunos')
        nx.draw_networkx_nodes(G, pos, nodelist=bottom_nodes, node_color='lightgreen', node_size=500, node_shape='s', label='Projetos')
        
        # Arestas Estáveis (Já aceitas)
        conexoes = snap['conexoes_final']
        edges_aceitas = [edge for edge in conexoes.keys()]
        nx.draw_networkx_edges(G, pos, edgelist=edges_aceitas, edge_color='green', width=2)
        
        # Aresta da Ação Atual (destaque)
        cor_acao = 'blue' if snap['resultado'] == 'aceito' else 'red'
        estilo = 'solid' if snap['resultado'] == 'aceito' else 'dashed'
        nx.draw_networkx_edges(G, pos, edgelist=[(snap['aluno'], snap['projeto'])], edge_color=cor_acao, width=3, style=estilo)

        # Labels (apenas alguns para não poluir se for muito grande)
        # Se for muito denso, pode comentar isso
        # nx.draw_networkx_labels(G, pos, font_size=8)

        plt.legend(['Alunos', 'Projetos'])
        plt.axis('off')
        plt.savefig(f"graficos/snapshot_{idx+1}.png")
        plt.close()

    print("Snapshots salvos na pasta 'graficos'.")

    # 2. Matriz de Satisfação e Tabela Final
    dados_finais = []
    rank_satisfacao = {'1ª Opção': 0, '2ª Opção': 0, '3ª Opção': 0, 'Não Alocado': 0}

    for a in alunos.values():
        if a.projeto_alocado:
            proj = a.projeto_alocado
            # Em qual posição da lista ORIGINAL estava esse projeto?
            try:
                rank = a.preferencias_originais.index(proj.codigo) + 1
                rank_str = f"{rank}ª"
                if rank == 1: rank_satisfacao['1ª Opção'] += 1
                elif rank == 2: rank_satisfacao['2ª Opção'] += 1
                elif rank == 3: rank_satisfacao['3ª Opção'] += 1
            except ValueError:
                rank_str = "N/A" # Não deveria acontecer se a lógica estiver certa
            
            dados_finais.append([a.codigo, proj.codigo, a.nota, rank_str])
        else:
            dados_finais.append([a.codigo, "-", a.nota, "Não Alocado"])
            rank_satisfacao['Não Alocado'] += 1
            
    df_final = pd.DataFrame(dados_finais, columns=['Aluno', 'Projeto', 'Nota Aluno', 'Rank Escolha'])
    df_final.to_excel("graficos/resultado_final.xlsx", index=False)
    
    # 3. Gráfico de Satisfação
    plt.figure(figsize=(8, 6))
    plt.bar(rank_satisfacao.keys(), rank_satisfacao.values(), color=['gold', 'silver', 'brown', 'gray'])
    plt.title("Índice de Satisfação dos Alunos")
    plt.xlabel("Classificação da Escolha Obtida")
    plt.ylabel("Quantidade de Alunos")
    for i, v in enumerate(rank_satisfacao.values()):
        plt.text(i, v + 1, str(v), ha='center')
    plt.savefig("graficos/indice_satisfacao.png")
    plt.close()
    
    print("Gráfico de satisfação e tabela Excel salvos.")

# --- Execução Principal ---
if __name__ == "__main__":
    arquivo_entrada = 'entradaProj2.txt'
    
    if not os.path.exists(arquivo_entrada):
        print(f"ERRO: Crie o arquivo '{arquivo_entrada}' com os dados primeiro!")
    else:
        print("--- 1. Carregando ---")
        projs, alus = carregar_dados(arquivo_entrada)
        
        print("--- 2. Filtrando ---")
        filtrar_preferencias(projs, alus)
        
        print("--- 3. Executando Gale-Shapley ---")
        historico = executar_gale_shapley(projs, alus)
        print(f"Total de iterações: {len(historico)}")
        
        print("--- 4. Gerando Visualizações ---")
        gerar_visualizacoes(projs, alus, historico)
        
        print("\n--- Concluído! Verifique a pasta 'graficos'. ---")