import re
import os
import copy
import sys

# Configurações
MAX_PREFERENCES = 3  # limite máximo de preferências por aluno conforme enunciado
GANHO_THRESHOLD = 3  # considera 'Ganho' se aluno obteve uma das top N opções

try:
    import matplotlib.pyplot as plt
    import networkx as nx
    import pandas as pd
    import numpy as np
    import imageio.v2 as imageio
except ModuleNotFoundError as e:
    print(f"ERRO: Módulo não encontrado: {e.name}")
    print("Instale as dependências executando (PowerShell):")
    print("  python -m pip install -r requirements.txt")
    sys.exit(1)

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
        todas_prefs = [p.strip() for p in preferencias_raw.split(',') if p.strip()]

        # Limita o número de preferências ao máximo permitido pelo projeto
        if len(todas_prefs) > MAX_PREFERENCES:
            print(f"Aviso: Aluno {codigo} indicou {len(todas_prefs)} preferências; truncando para {MAX_PREFERENCES}.")
        self.preferencias = todas_prefs[:MAX_PREFERENCES]

        # Guarda uma cópia das preferencias (após truncamento) para calcular satisfação depois
        self.preferencias_originais = list(self.preferencias)
        # Guarda também as preferências válidas após filtragem por requisitos (preenchido depois)
        self.preferencias_filtradas = []
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
        # Salva preferências filtradas separadamente antes que a execução de Gale-Shapley as modifique
        aluno.preferencias_filtradas = list(validas)
        aluno.preferencias = list(validas)
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

# --- Verificação de Estabilidade (Corrigida) ---
def verificar_estabilidade(projetos, alunos):
    blocking_pairs = []
    
    for aluno in alunos.values():
        # Usamos as preferências FILTRADAS, pois o aluno só pode bloquear
        # com projetos para os quais ele foi considerado elegível.
        prefs_lista = getattr(aluno, 'preferencias_filtradas', [])

        for pref_proj_code in prefs_lista:
            proj = projetos.get(pref_proj_code)
            if not proj: continue

            # REGRA DE OURO: Se o aluno não tem nota, ignora (não é bloqueio)
            if aluno.nota < proj.nota_minima:
                continue
            
            # Se chegamos no projeto atual do aluno, paramos de verificar (pois as próximas são piores)
            if aluno.projeto_alocado and aluno.projeto_alocado.codigo == pref_proj_code:
                break

            # --- Verificação de Bloqueio ---
            # 1. Projeto tem vaga livre?
            if len(proj.alunos_alocados) < proj.vagas:
                blocking_pairs.append((aluno.codigo, pref_proj_code))
                # print(f"Bloqueio: {aluno.codigo} quer {pref_proj_code} (Vaga Livre)")
            
            # 2. Projeto está cheio, mas tem alguém pior que eu?
            else:
                pior = min(proj.alunos_alocados, key=lambda x: x.nota)
                if aluno.nota > pior.nota:
                    blocking_pairs.append((aluno.codigo, pref_proj_code))
                    # print(f"Bloqueio: {aluno.codigo} (Nota {aluno.nota}) ganharia de {pior.codigo} (Nota {pior.nota}) em {pref_proj_code}")

    return len(blocking_pairs) == 0, blocking_pairs

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

    # --- Seleção de Snapshots (até 10) ---
    total_snaps = len(snapshots)
    if total_snaps == 0:
        print("Nenhum snapshot gerado; pulando visualizações.")
    else:
        n_images = min(10, total_snaps)
        indices = np.linspace(0, total_snaps - 1, n_images, dtype=int)
        indices = sorted(set(int(i) for i in indices))

        for idx_img, idx_snap in enumerate(indices):
            snap = snapshots[idx_snap]
        
        # Ajuste dinâmico de figura e tamanhos para reduzir sobreposição
        n_alunos = max(1, len(lista_alunos))
        n_projetos = max(1, len(lista_projetos))
        figsize = (12, 12) if (n_alunos + n_projetos) < 200 else (18, 18)
        plt.figure(figsize=figsize, dpi=150)

        # Título Informativo
        acao_txt = "ACEITO" if snap['resultado'] == 'aceito' else "REJEITADO"
        cor_titulo = 'green' if snap['resultado'] == 'aceito' else 'red'
        plt.suptitle(f"Iteração {snap['iteracao']}: {snap['aluno']} tenta {snap['projeto']} -> {acao_txt}", 
                     fontsize=14, color=cor_titulo, fontweight='bold')

        # Node sizes e fontes adaptativas
        aluno_node_size = int(max(30, 4000 / n_alunos))
        proj_node_size = int(max(200, 6000 / n_projetos))
        aluno_font = 6 if n_alunos > 60 else 8
        proj_font = 9 if n_projetos < 50 else 8

        # Cria posições levemente deslocadas para labels para reduzir sobreposição
        label_pos = {}
        for node, (x, y) in pos.items():
            if node in lista_alunos:
                # desloca labels um pouco para fora
                label_pos[node] = (x * 1.06, y * 1.06)
            else:
                # desloca labels um pouco para dentro
                label_pos[node] = (x * 0.92, y * 0.92)

        # Desenha nós com cores distintas
        nx.draw_networkx_nodes(G, pos, nodelist=lista_alunos, node_size=aluno_node_size, node_color='#6fa8dc', label='Alunos', alpha=0.9)
        nx.draw_networkx_nodes(G, pos, nodelist=lista_projetos, node_size=proj_node_size, node_color='#93c47d', label='Projetos', alpha=0.95)

        # Rótulos usando posições ajustadas
        nx.draw_networkx_labels(G, label_pos, labels={p: p for p in lista_projetos}, font_size=proj_font, font_weight='bold')
        nx.draw_networkx_labels(G, label_pos, labels={a: a for a in lista_alunos}, font_size=aluno_font)

        # 2. Desenha Arestas (Emparelhamentos Estáveis) - COR VERDE
        conexoes = snap['conexoes_final']
        edges_verdes = list(conexoes.keys())

        # Remove a aresta atual da lista de verdes para desenhá-la com destaque
        aresta_atual = (snap['aluno'], snap['projeto'])
        if aresta_atual in edges_verdes and snap['resultado'] == 'aceito':
            edges_verdes.remove(aresta_atual)

        # Desenha arestas estáveis com largura fina e baixa opacidade
        if edges_verdes:
            nx.draw_networkx_edges(G, pos, edgelist=edges_verdes, edge_color='#2e8b57', alpha=0.35, width=1)

        # 3. Desenha Ação Atual com destaque
        if snap['resultado'] == 'aceito':
            nx.draw_networkx_edges(G, pos, edgelist=[aresta_atual], edge_color='#1f4e79', width=3)
        else:
            nx.draw_networkx_edges(G, pos, edgelist=[aresta_atual], edge_color='#b22222', width=3, style='dashed')

        # Legenda melhorada
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='#2e8b57', lw=2, label='Emparelhado (Estável)'),
            Line2D([0], [0], color='#1f4e79', lw=2, label='Proposta Aceita (Ativa)'),
            Line2D([0], [0], color='#b22222', lw=2, linestyle='--', label='Proposta Rejeitada'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#6fa8dc', markersize=8, label='Alunos (Externo)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#93c47d', markersize=10, label='Projetos (Interno)')
        ]
        plt.legend(handles=legend_elements, loc='upper right', fontsize=9)

        plt.axis('off')
        plt.tight_layout()
        plt.savefig(f"graficos/snapshot_{idx_img+1}.png", dpi=150)
        plt.close()

    print("Snapshots radiais salvos na pasta 'graficos'.")
    
    # --- Gerar GIF a partir dos snapshots (se houver) ---
    try:
        snapshot_files = sorted([f for f in os.listdir('graficos') if f.startswith('snapshot_') and f.endswith('.png')],
                                key=lambda x: int(x.split('_')[1].split('.')[0]))
        if snapshot_files:
            from PIL import Image
            images = []
            for fname in snapshot_files:
                img = Image.open(os.path.join('graficos', fname))
                images.append(img)
            
            # Salva como GIF (PIL trata redimensionamento automaticamente)
            if images:
                images[0].save(os.path.join('graficos', 'emparelhamento_animacao.gif'), 
                              save_all=True, append_images=images[1:], duration=800, loop=0)
                print("GIF de animação salvo em 'graficos/emparelhamento_animacao.gif'.")
    except Exception as e:
        print(f"Aviso: não foi possível gerar GIF de animação: {e}")

    # --- Gerar Matriz de Emparelhamento (Proje x Aluno) ---
    alunos_list = sorted(alunos.keys())
    projetos_list = sorted(projetos.keys())
    matriz = pd.DataFrame('', index=projetos_list, columns=alunos_list)
    for a in alunos.values():
        if a.projeto_alocado:
            matriz.at[a.projeto_alocado.codigo, a.codigo] = 'Alocado'

    matriz.to_excel('graficos/matriz_emparelhamento.xlsx')
    print("Matriz de emparelhamento salva em 'graficos/matriz_emparelhamento.xlsx'.")

    # --- 2. Matriz de Satisfação e Tabela Final (com Rank no Projeto) ---
    # Primeiro, constrói ranking por projeto (lista de candidatos que tinham o projeto nas preferências filtradas)
    ranking_projetos = {}
    for p_code, proj in projetos.items():
        candidatos = [a for a in alunos.values() if p_code in getattr(a, 'preferencias_filtradas', [])]
        # Ordena por nota decrescente (maior nota = preferência maior do projeto)
        candidatos.sort(key=lambda x: x.nota, reverse=True)
        ranking_projetos[p_code] = [c.codigo for c in candidatos]

    dados_finais = []
    rank_satisfacao = {'1ª Opção': 0, '2ª Opção': 0, '3ª Opção': 0, 'Não Alocado': 0}

    for a in alunos.values():
        if a.projeto_alocado:
            proj = a.projeto_alocado
            # Rank do projeto na lista do aluno (posição da escolha do aluno)
            try:
                rank_aluno_escolha = a.preferencias_originais.index(proj.codigo) + 1
                rank_aluno_escolha_str = f"{rank_aluno_escolha}ª"
                if rank_aluno_escolha == 1: rank_satisfacao['1ª Opção'] += 1
                elif rank_aluno_escolha == 2: rank_satisfacao['2ª Opção'] += 1
                elif rank_aluno_escolha == 3: rank_satisfacao['3ª Opção'] += 1
            except ValueError:
                rank_aluno_escolha = None
                rank_aluno_escolha_str = "N/A"

            # Rank do aluno na lista do projeto
            try:
                lista_proj = ranking_projetos.get(proj.codigo, [])
                rank_aluno_no_projeto = lista_proj.index(a.codigo) + 1
                rank_aluno_no_projeto_str = f"{rank_aluno_no_projeto}ª"
            except ValueError:
                rank_aluno_no_projeto = None
                rank_aluno_no_projeto_str = "N/A"

            # Nova regra Ganho/Perda: comparar posições relativas normalizadas
            # Calculamos scores normalizados entre 0 e 1 para aluno e projeto
            def normalized_score(rank, total_list_length):
                try:
                    if total_list_length <= 1:
                        return 1.0
                    return 1.0 - ((rank - 1) / (total_list_length - 1))
                except Exception:
                    return None

            # total possível para aluno = número de preferências originais (se >0)
            total_aluno = len(a.preferencias_originais) if a.preferencias_originais else 1
            total_proj = len(ranking_projetos.get(proj.codigo, [])) if ranking_projetos.get(proj.codigo) else 1

            aluno_score = normalized_score(rank_aluno_escolha, total_aluno) if rank_aluno_escolha is not None else None
            proj_score = normalized_score(rank_aluno_no_projeto, total_proj) if rank_aluno_no_projeto is not None else None

            # Regra: se aluno_score >= proj_score => 'Ganho', caso contrário 'Perda'
            if aluno_score is None or proj_score is None:
                ganho_perda = 'N/A'
            else:
                ganho_perda = 'Ganho' if aluno_score >= proj_score else 'Perda'

            dados_finais.append([a.codigo, proj.codigo, a.nota, rank_aluno_escolha_str, rank_aluno_no_projeto_str, ganho_perda])
        else:
            dados_finais.append([a.codigo, "-", a.nota, "Não Alocado", "N/A", 'Perda'])
            rank_satisfacao['Não Alocado'] += 1
            
    df_final = pd.DataFrame(dados_finais, columns=['Aluno', 'Projeto', 'Nota Aluno', 'Rank Escolha', 'Rank no Projeto', 'Ganho/Perda'])
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
    
    # --- 4. Gráfico de Ganho/Perda por Projeto ---
    ganho_perda_proj = {}
    for p_code in projetos.keys():
        ganho_perda_proj[p_code] = {'Ganho': 0, 'Perda': 0}
    
    for row in dados_finais:
        aluno_cod, proj_cod, nota, rank_esc, rank_proj, ganho_perda = row
        if proj_cod != "-" and ganho_perda in ['Ganho', 'Perda']:
            ganho_perda_proj[proj_cod][ganho_perda] += 1
    
    # Filtra projetos com alocações
    proj_com_alocacao = {p: gp for p, gp in ganho_perda_proj.items() if gp['Ganho'] + gp['Perda'] > 0}
    
    if proj_com_alocacao:
        projetos_nomes = list(proj_com_alocacao.keys())
        ganhos = [proj_com_alocacao[p]['Ganho'] for p in projetos_nomes]
        perdas = [proj_com_alocacao[p]['Perda'] for p in projetos_nomes]
        
        x = np.arange(len(projetos_nomes))
        width = 0.35
        
        plt.figure(figsize=(14, 6))
        plt.bar(x - width/2, ganhos, width, label='Ganho', color='#2ecc71')
        plt.bar(x + width/2, perdas, width, label='Perda', color='#e74c3c')
        plt.xlabel('Projetos')
        plt.ylabel('Quantidade de Alunos')
        plt.title('Ganho/Perda por Projeto')
        plt.xticks(x, projetos_nomes, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        plt.savefig("graficos/ganho_perda_por_projeto.png", dpi=150)
        plt.close()
    
    print("Gráfico de satisfação, ganho/perda por projeto e tabela Excel salvos.")

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
        
        # --- 5. Verificar Estabilidade ---
        print("--- 5. Verificando Estabilidade ---")
        é_estavel, blocking_pairs = verificar_estabilidade(projs, alus)
        print(f"Emparelhamento é estável: {é_estavel}")
        if not é_estavel:
            print(f"Pares bloqueadores encontrados: {len(blocking_pairs)}")
        
        # --- 6. Gerar Relatório Resumido ---
        print("--- 6. Gerando Relatório Resumido ---")
        total_alunos = len(alus)
        alocados = len([a for a in alus.values() if a.projeto_alocado])
        total_vagas = sum(p.vagas for p in projs.values())
        vagas_preenchidas = sum(len(p.alunos_alocados) for p in projs.values())
        
        relatorio = f"""RELATÓRIO DE EMPARELHAMENTO - GALE-SHAPLEY
{'='*60}

RESUMO EXECUTIVO:
  Total de Alunos: {total_alunos}
  Alunos Alocados: {alocados}
  Taxa de Alocação: {(alocados/total_alunos)*100:.1f}%
  
  Total de Vagas: {total_vagas}
  Vagas Preenchidas: {vagas_preenchidas}
  Taxa de Ocupação de Vagas: {(vagas_preenchidas/total_vagas)*100:.1f}%
  
  Total de Iterações: {len(historico)}
  Emparelhamento Estável: {é_estavel}
  Pares Bloqueadores Encontrados: {len(blocking_pairs)}

ESTATÍSTICAS:
  Projetos com Alocações: {len([p for p in projs.values() if len(p.alunos_alocados) > 0])}
  Alunos com 1ª Opção: {sum(1 for a in alus.values() if a.projeto_alocado and (a.preferencias_originais and a.projeto_alocado.codigo == a.preferencias_originais[0]))}
  Alunos com 2ª Opção: {sum(1 for a in alus.values() if a.projeto_alocado and (len(a.preferencias_originais) > 1 and a.projeto_alocado.codigo == a.preferencias_originais[1]))}
  Alunos com 3ª Opção: {sum(1 for a in alus.values() if a.projeto_alocado and (len(a.preferencias_originais) > 2 and a.projeto_alocado.codigo == a.preferencias_originais[2]))}

NOTA SOBRE ESTABILIDADE:
  A implementação utiliza a versão "proposta pelo aluno" do algoritmo Gale-Shapley,
  onde alunos fazem propostas e projetos aceitam/rejeitam. Isso garante que:
  - O emparelhamento é estável para os projetos (nenhum projeto quer trocar seus alunos)
  - Alguns alunos não alocados podem preferir projetos alocados
  
  Pares bloqueadores encontrados representam alunos que não foram alocados
  mas que poderiam ter sido, indicando há margem de otimização.

ARQUIVOS GERADOS:
  - snapshot_*.png: Snapshots das iterações (até 10)
  - emparelhamento_animacao.gif: Animação do processo
  - resultado_final.xlsx: Tabela completa de resultados
  - matriz_emparelhamento.xlsx: Matriz Projeto x Aluno
  - indice_satisfacao.png: Gráfico de satisfação geral
  - ganho_perda_por_projeto.png: Gráfico de ganho/perda por projeto
  - relatorio_resumo.txt: Este arquivo

{'='*60}
Relatório gerado automaticamente pelo algoritmo Gale-Shapley.
"""
        
        with open('graficos/relatorio_resumo.txt', 'w', encoding='utf-8') as f:
            f.write(relatorio)
        print("Relatório resumido salvo em 'graficos/relatorio_resumo.txt'.")
        
        print("\n--- Concluído! Verifique a pasta 'graficos'. ---")