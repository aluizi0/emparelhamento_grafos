# Projeto 2: Emparelhamento Estável Máximo (Alunos x Projetos)

Este projeto implementa uma solução para o problema de alocação de alunos em projetos acadêmicos, utilizando uma variação do algoritmo de **Gale-Shapley**.

## 📋 Sobre o Algoritmo e Variações
Para atender aos requisitos de maximizar o interesse dos alunos qualificados e preencher as vagas de forma competitiva, implementamos a seguinte lógica:

1.  **Modelo "Student-Proposing" (Proposta dos Alunos):**
    * Os alunos fazem as propostas para os projetos de sua preferência. Isso tende a gerar um emparelhamento "otimizado para os alunos" (dentro do possível).

2.  **Capacidade Múltipla (Many-to-One):**
    * Diferente do casamento clássico (1-para-1), os projetos possuem capacidades variadas (vagas > 1). Eles aceitam propostas enquanto houver vagas.

3.  **Competitividade por Nota (Estabilidade baseada em Mérito):**
    * Se um projeto estiver cheio e receber uma proposta de um aluno com **nota superior** a um dos alunos já alocados, o projeto **troca**: ele rejeita o aluno de menor nota (que volta para a fila) e aceita o novo candidato de maior nota.
    * Isso garante que as vagas fiquem com os candidatos mais qualificados interessados.

4.  **Filtragem de Requisitos:**
    * Antes da execução, são removidas as preferências onde o aluno não atende à nota mínima exigida pelo projeto.

## 📊 Visualização
O software gera:
* **Grafo Bipartido Radial:** Mostra a evolução das conexões em 10 etapas (snapshots).
    * 🟢 **Verde:** Emparelhamento estável/aceito.
    * 🔵 **Azul:** Nova proposta aceita no momento.
    * 🔴 **Vermelho:** Proposta rejeitada.
* **Matriz de Resultados:** Planilha Excel com o rank de escolha de cada aluno.
* **Gráfico de Satisfação:** Distribuição de quantos alunos conseguiram sua 1ª, 2ª ou 3ª opção.

## 🛠️ Tecnologias
* Python 3
* NetworkX (Grafos)
* Matplotlib (Visualização)
* Pandas (Manipulação de dados)

## 🚀 Como Executar este Projeto

Siga os passos abaixo para rodar a simulação e gerar os gráficos.

### 1. Pré-requisitos
Certifique-se de ter o **Python 3** instalado. Em seguida, instale as bibliotecas necessárias executando o comando abaixo no terminal e logo em seguida para rodar o projeto:

```bash
pip install pandas networkx matplotlib numpy openpyxl

python main.py

