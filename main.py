import re

# --- Estruturas de Dados ---
class Projeto:
    def __init__(self, codigo, vagas, nota_minima):
        self.codigo = codigo
        self.vagas = int(vagas)
        self.nota_minima = int(nota_minima)
        self.alunos_alocados = []

    def __repr__(self):
        return f"[{self.codigo}: Vagas={self.vagas}, Min={self.nota_minima}]"

class Aluno:
    def __init__(self, codigo, preferencias_raw, nota):
        self.codigo = codigo
        # Limpa espaços e cria lista: "P1, P30" -> ["P1", "P30"]
        self.preferencias = [p.strip() for p in preferencias_raw.split(',') if p.strip()]
        self.nota = int(nota)
        self.projeto_alocado = None

    def __repr__(self):
        return f"[{self.codigo}: Nota={self.nota}, Prefs={self.preferencias}]"

# --- Funções de Leitura e Processamento ---

def carregar_dados(caminho_arquivo):
    projetos = {}
    alunos = {}

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # 1. Extrair Projetos usando Regex
    # Padrão: (P1, 2, 5)
    padrao_projeto = r'\((P\d+),\s*(\d+),\s*(\d+)\)'
    matches_proj = re.findall(padrao_projeto, conteudo)
    
    for p_code, vagas, nota_min in matches_proj:
        projetos[p_code] = Projeto(p_code, vagas, nota_min)

    # 2. Extrair Alunos usando Regex
    # Padrão: (A1):(P1, P30, P50) (5)
    padrao_aluno = r'\((A\d+)\):\((.*?)\)\s*\((\d)\)'
    matches_aluno = re.findall(padrao_aluno, conteudo)

    for a_code, prefs_str, nota in matches_aluno:
        alunos[a_code] = Aluno(a_code, prefs_str, nota)

    return projetos, alunos

def filtrar_preferencias(projetos, alunos):
    """
    Remove da lista de preferências dos alunos os projetos para os quais
    eles não possuem a nota mínima exigida.
    """
    contagem_remocoes = 0
    
    for aluno in alunos.values():
        prefs_validas = []
        for proj_codigo in aluno.preferencias:
            projeto = projetos.get(proj_codigo)
            
            # Verifica se o projeto existe e se o aluno tem nota suficiente
            if projeto:
                if aluno.nota >= projeto.nota_minima:
                    prefs_validas.append(proj_codigo)
                else:
                    # Debug: Mostra quem foi cortado (opcional)
                    # print(f"Aluno {aluno.codigo} (Nota {aluno.nota}) não qualificado para {proj_codigo} (Min {projeto.nota_minima})")
                    contagem_remocoes += 1
            else:
                print(f"Aviso: Projeto {proj_codigo} citado por {aluno.codigo} não existe.")
        
        aluno.preferencias = prefs_validas

    print(f"Filtragem concluída. Total de preferências inválidas removidas: {contagem_remocoes}")

# --- Lógica do Gale-Shapley ---

def executar_gale_shapley(projetos, alunos):
    """
    Executa o algoritmo de Gale-Shapley (Proposta dos Alunos).
    Considera capacidade > 1 e critério de nota para 'roubar' vaga.
    Retorna o histórico de iterações para visualização.
    """
    # Fila de alunos livres que ainda têm propostas a fazer
    # Apenas alunos que têm pelo menos uma preferência válida entram aqui
    fila_alunos = [a_code for a_code, a in alunos.items() if a.preferencias and a.projeto_alocado is None]
    
    iteracao = 0
    snapshots = [] # Para guardar o estado a cada passo (exigência do projeto)

    print(f"\n--- Iniciando Gale-Shapley com {len(fila_alunos)} alunos ativos ---")

    while fila_alunos:
        iteracao += 1
        aluno_codigo = fila_alunos.pop(0)
        aluno = alunos[aluno_codigo]

        # Se o aluno não tem mais preferências, ele fica sem projeto
        if not aluno.preferencias:
            continue

        # Pega a próxima preferência (o topo da lista)
        # Não removemos da lista permanentemente ainda, apenas "tentamos"
        projeto_codigo = aluno.preferencias.pop(0) 
        projeto = projetos[projeto_codigo]

        # -- Registro do Snapshot (Tentativa) --
        snapshots.append({
            'iteracao': iteracao,
            'tipo': 'proposta',
            'aluno': aluno_codigo,
            'projeto': projeto_codigo,
            'msg': f"{aluno_codigo} (Nota {aluno.nota}) propõe para {projeto_codigo}"
        })

        # Lógica de Aceitação/Rejeição
        aceito = False
        
        # Caso 1: O projeto tem vaga livre
        if len(projeto.alunos_alocados) < projeto.vagas:
            projeto.alunos_alocados.append(aluno)
            aluno.projeto_alocado = projeto
            aceito = True
            snapshots.append({'iteracao': iteracao, 'tipo': 'aceito', 'aluno': aluno_codigo, 'projeto': projeto_codigo, 'msg': "Aceito (Vaga livre)"})

        # Caso 2: O projeto está cheio, mas vamos ver se o aluno é melhor que o pior atual
        else:
            # Ordena os alunos atuais pela nota (crescente). 
            # O primeiro da lista é o de menor nota.
            # Critério de desempate: quem chegou antes fica (estabilidade).
            projeto.alunos_alocados.sort(key=lambda x: x.nota)
            pior_aluno_atual = projeto.alunos_alocados[0]

            if aluno.nota > pior_aluno_atual.nota:
                # Troca!
                projeto.alunos_alocados.pop(0) # Remove o pior
                pior_aluno_atual.projeto_alocado = None # Torna ele livre
                fila_alunos.append(pior_aluno_atual.codigo) # Volta pra fila

                projeto.alunos_alocados.append(aluno)
                aluno.projeto_alocado = projeto
                aceito = True
                
                snapshots.append({
                    'iteracao': iteracao, 
                    'tipo': 'troca', 
                    'aluno': aluno_codigo, 
                    'projeto': projeto_codigo, 
                    'removido': pior_aluno_atual.codigo,
                    'msg': f"Aceito (Substituiu {pior_aluno_atual.codigo})"
                })
            else:
                # Rejeitado (não superou o pior)
                aceito = False
                fila_alunos.append(aluno_codigo) # Volta pra fila para tentar o próximo
                snapshots.append({'iteracao': iteracao, 'tipo': 'rejeitado', 'aluno': aluno_codigo, 'projeto': projeto_codigo, 'msg': "Rejeitado (Nota insuficiente)"})

    return snapshots

# --- Execução Principal ---
if __name__ == "__main__":
    arquivo_entrada = 'entradaProj2.txt'
    
    try:
        print("--- 1. Carregando Dados ---")
        projetos, alunos = carregar_dados(arquivo_entrada)
        
        print("\n--- 2. Aplicando Filtros ---")
        filtrar_preferencias(projetos, alunos)
        
        print("\n--- 3. Executando Algoritmo de Alocação ---")
        historico = executar_gale_shapley(projetos, alunos)
        
        print(f"\nAlgoritmo finalizado em {len(historico)} passos registrados.")
        
        # Relatório Rápido no Terminal
        print("\n--- Resultado Final (Amostra) ---")
        alocados = 0
        for p in projetos.values():
            alocados += len(p.alunos_alocados)
            if p.alunos_alocados:
                print(f"{p.codigo}: {[a.codigo for a in p.alunos_alocados]}")
        
        print(f"\nTotal de Alunos Alocados: {alocados} de {len(alunos)}")

    except FileNotFoundError:
        print("Erro: Arquivo 'entradaProj2.txt' não encontrado.")