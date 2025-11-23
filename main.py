import re
import os
import copy
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import numpy as np

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
            # Ordena por nota (crescente). O primeiro é o menor nota.
            projeto.alunos_alocados.sort(key=lambda x: x.nota)
            pior_atual = projeto.alunos_alocados[0]

            if aluno.nota > pior_atual.nota:
                # Troca
                projeto.alunos_alocados.pop(0)
                pior_atual.projeto_alocado = None
                
                # Remove conexão antiga do estado visual
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

# --- Visualização Radial (Circular) ---
def gerar_visualizacoes(projetos, alunos, snapshots):
    if not os.path.exists('graficos'):
        os.makedirs('graficos')

    print("Gerando visualizações com layout Radial (Circular)...")

    # --- Configuração do Layout Radial ---
    G = nx.Graph()
    lista_alunos = list(alunos.keys())
    lista_projetos = list(projetos.keys())
    G.add_nodes_from(lista_alunos)
    G.add_nodes_from(lista_projetos)

    pos = {}
    
    # Círculo de Projetos (Interno - Raio 10)
    raio_proj = 10
    for i, p in enumerate(lista_projetos):
        angulo = (2 * np.pi * i) / len(lista_projetos)
        pos[p] = (raio_proj * np.cos(angulo), raio_proj * np.sin(angulo))
        
    # Círculo de Alunos (Externo - Raio 25)
    raio_aluno = 25
    for i, a in enumerate(lista_alunos):
        angulo = (2 * np.pi * i) / len(lista_alunos)
        pos[a] = (raio_aluno * np.cos(angulo), raio_aluno * np.sin(angulo))

    # --- Seleção de Snapshots ---
    total_snaps = len(snapshots)
    indices = np.linspace(0, total_snaps - 1, 10, dtype=int)

    for idx_img, idx_snap in enumerate(indices):
        snap = snapshots[idx_snap]
        
        # Aumentei um pouco a figura para caber os nomes
        plt.figure(figsize=(18, 18)) 
        
        # Título Informativo
        acao_txt = "ACEITO" if snap['resultado'] == 'aceito' else "REJEITADO"
        cor_titulo = 'green' if snap['resultado'] == 'aceito' else 'red'
        plt.suptitle(f"Iteração {snap['iteracao']}: {snap['aluno']} tenta {snap['projeto']} -> {acao_txt}", 
                     fontsize=16, color=cor_titulo, fontweight='bold')
        
        # 1. Desenha Nós
        # Alunos (Azul claro) - Aumentei um pouco o node_size para caber o texto
        nx.draw_networkx_nodes(G, pos, nodelist=lista_alunos, node_size=150, node_color='#87CEFA', label='Alunos')
        # Projetos (Verde claro)
        nx.draw_networkx_nodes(G, pos, nodelist=lista_projetos, node_size=400, node_color='#90EE90', label='Projetos')
        
        # --- RÓTULOS (LABELS) ---
        # Labels dos Projetos (Fonte maior)
        nx.draw_networkx_labels(G, pos, labels={p: p for p in lista_projetos}, font_size=9, font_weight='bold')
        
        # Labels dos Alunos (NOVO: Fonte menor para caber todo mundo)
        nx.draw_networkx_labels(G, pos, labels={a: a for a in lista_alunos}, font_size=6)
        
        # 2. Desenha Arestas (Emparelhamentos Estáveis) - COR VERDE
        conexoes = snap['conexoes_final']
        edges_verdes = list(conexoes.keys())
        
        # Remove a aresta atual da lista de verdes para desenhá-la com destaque
        aresta_atual = (snap['aluno'], snap['projeto'])
        if aresta_atual in edges_verdes and snap['resultado'] == 'aceito':
            edges_verdes.remove(aresta_atual)
            
        nx.draw_networkx_edges(G, pos, edgelist=edges_verdes, edge_color='green', alpha=0.3, width=1)
        
        # 3. Desenha Ação Atual
        if snap['resultado'] == 'aceito':
            # Proposta Aceita (Azul forte)
            nx.draw_networkx_edges(G, pos, edgelist=[aresta_atual], edge_color='blue', width=3)
        else:
            # Proposta Rejeitada (Vermelho tracejado)
            nx.draw_networkx_edges(G, pos, edgelist=[aresta_atual], edge_color='red', width=3, style='dashed')

        # Legenda
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='green', lw=2, label='Emparelhado (Estável)'),
            Line2D([0], [0], color='blue', lw=2, label='Proposta Aceita (Ativa)'),
            Line2D([0], [0], color='red', lw=2, linestyle='--', label='Proposta Rejeitada'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#87CEFA', markersize=10, label='Alunos (Externo)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#90EE90', markersize=10, label='Projetos (Interno)')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.axis('off')
        plt.savefig(f"graficos/snapshot_{idx_img+1}.png")
        plt.close()

    print("Snapshots radiais salvos na pasta 'graficos'.")
    
    # --- 2. Matriz de Satisfação e Tabela Final (Continua igual) ---
    dados_finais = []
    rank_satisfacao = {'1ª Opção': 0, '2ª Opção': 0, '3ª Opção': 0, 'Não Alocado': 0}

    for a in alunos.values():
        if a.projeto_alocado:
            proj = a.projeto_alocado
            try:
                rank = a.preferencias_originais.index(proj.codigo) + 1
                rank_str = f"{rank}ª"
                if rank == 1: rank_satisfacao['1ª Opção'] += 1
                elif rank == 2: rank_satisfacao['2ª Opção'] += 1
                elif rank == 3: rank_satisfacao['3ª Opção'] += 1
            except ValueError:
                rank_str = "N/A"
            
            dados_finais.append([a.codigo, proj.codigo, a.nota, rank_str])
        else:
            dados_finais.append([a.codigo, "-", a.nota, "Não Alocado"])
            rank_satisfacao['Não Alocado'] += 1
            
    df_final = pd.DataFrame(dados_finais, columns=['Aluno', 'Projeto', 'Nota Aluno', 'Rank Escolha'])
    df_final.to_excel("graficos/resultado_final.xlsx", index=False)
    
    # --- 3. Gráfico de Satisfação ---
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