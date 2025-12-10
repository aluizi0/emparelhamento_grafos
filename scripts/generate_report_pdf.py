#!/usr/bin/env python3
"""Gera `graficos/relatorio_completo.pdf` combinando o texto de
`graficos/relatorio_resumo.txt` com até 10 snapshots e gráficos.

Uso:
  python scripts/generate_report_pdf.py

Dependências:
  pip install reportlab Pillow
"""
import os
import glob
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm


def read_summary(path):
    if not os.path.exists(path):
        return 'Relatório resumo não encontrado.'
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def collect_images(graficos_dir, max_snapshots=10):
    def _extract_index(fname):
        base = os.path.splitext(os.path.basename(fname))[0]
        parts = base.split('_')
        try:
            return int(parts[1])
        except Exception:
            return 0

    snapshots = sorted(glob.glob(os.path.join(graficos_dir, 'snapshot_*.png')), key=_extract_index)
    snapshots = snapshots[:max_snapshots]
    others = sorted(glob.glob(os.path.join(graficos_dir, '*.png')))
    # Excluir snapshots já coletados
    others = [p for p in others if p not in snapshots]
    # Priorizar indice_satisfacao e ganho_perda_por_projeto
    prioritized = []
    for name in ('indice_satisfacao.png', 'ganho_perda_por_projeto.png'):
        p = os.path.join(graficos_dir, name)
        if p in others:
            prioritized.append(p)
            others.remove(p)
    return snapshots + prioritized + others


def build_pdf(out_path, summary_text, images):
    doc = SimpleDocTemplate(out_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Capa
    story.append(Paragraph('EMPARELHAMENTO ESTÁVEL MÁXIMO: ALOCAÇÃO DE ALUNOS EM PROJETOS', styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph('Relatório gerado automaticamente', styles['Normal']))
    story.append(Spacer(1, 24))

    # Sumário (texto)
    for line in summary_text.splitlines():
        if line.strip() == '':
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(line.replace('  ', '&nbsp;&nbsp;'), styles['BodyText']))
    story.append(PageBreak())

    # Imagens: uma por página (ajusta largura máxima)
    for img in images:
        try:
            im = Image(img)
            im._restrictSize(16*cm, 22*cm)
            story.append(im)
            story.append(Spacer(1, 12))
            story.append(Paragraph(os.path.basename(img), styles['Caption'] if 'Caption' in styles else styles['Normal']))
            story.append(PageBreak())
        except Exception as e:
            story.append(Paragraph(f'Erro ao incluir imagem {img}: {e}', styles['Normal']))

    doc.build(story)


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    graficos = os.path.join(repo_root, 'graficos')
    resumo = os.path.join(graficos, 'relatorio_resumo.txt')
    out_pdf = os.path.join(graficos, 'relatorio_completo.pdf')

    print('Lendo resumo...')
    summary_text = read_summary(resumo)

    print('Coletando imagens (até 10 snapshots)...')
    imgs = collect_images(graficos, max_snapshots=10)
    print(f'Encontrei {len(imgs)} imagens; gerando PDF em {out_pdf}')

    build_pdf(out_pdf, summary_text, imgs)
    print('PDF gerado com sucesso:', out_pdf)


if __name__ == '__main__':
    main()
