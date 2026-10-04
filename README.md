# Vendas em E-commerce no Brasil (2015–2024)

Projeto de **análise e visualização de dados com Python** — disciplina *Linguagem de Programação: Análise e Visualização de Dados com Python* (Tema 13).

Analisa uma base **simulada** de 4.440 pedidos de e-commerce (2015–2024) e entrega um notebook de análise, um dashboard interativo em Streamlit e uma página de apresentação.

| Entrega | Link |
| Página do projeto (GitHub Pages) | `https://github.com/PedroDuarteMachado/ecommerce/tree/main` |
| Dashboard (Streamlit Community Cloud) | `https://ecommerce-7qnsytbn9qqwwkppsapqfb.streamlit.app/` |

## Perguntas respondidas

Categorias de maior faturamento e lucro · estados que concentram vendas · sazonalidade · desempenho por canal · produtos mais vendidos · evolução do faturamento · ticket médio por região · relação entre prazo de entrega, avaliação e vendas.

## Dashboard

Páginas (navegação lateral): **Visão geral** · **Temporal e sazonalidade** · **Regiões e mapa** · **Categorias e canais** · **Lucro, logística e avaliação** · **Tabela dinâmica** · **Consultas SQL** · **Conclusão executiva**.

- **Filtros:** ano, mês, região, estado, categoria e canal de venda (todos recalculam KPIs, gráficos e textos).
- **KPIs:** faturamento total, lucro total, margem, ticket médio, produto mais vendido, categoria mais lucrativa, região com maior faturamento, avaliação e prazo médios.
- **Gráficos:** linha temporal, barras por categoria e por estado, dispersão lucro × faturamento, heatmap mensal, índice sazonal, mapa interativo, matriz de correlação.
- **Interpretação textual** em cada página e **conclusão executiva** com recomendações.
- **Upload de CSV** opcional (mesmas colunas da base original).

### Funcionalidades avançadas
1. **Persistência em banco:** a base tratada é gravada em `database/ecommerce.db` (SQLite) e lida com **SQLAlchemy**; a página *Consultas SQL* executa `SELECT` somente leitura.
2. **Dashboard multipágina** com `st.navigation`.
3. **Mapa interativo** com Plotly (bolhas por estado).
4. **Correlação estatística** (Pearson/Spearman) com Pandas/NumPy.
5. **Série temporal avançada:** média móvel de 12 meses, variação anual e índice sazonal.

## Estrutura

```
projeto-g1/
├── app.py                  # dashboard Streamlit
├── requirements.txt
├── README.md
├── index.html              # página de apresentação (GitHub Pages)
├── .streamlit/config.toml  # tema do dashboard
├── dados/
│   └── simulacao_ecommerce_brasil.csv
├── database/
│   └── ecommerce.db        # SQLite (recriado automaticamente se ausente)
├── notebooks/
│   └── analise_ecommerce.ipynb
└── imagens/                # gráficos exportados pelo notebook
```

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O notebook pode ser aberto com `jupyter notebook notebooks/analise_ecommerce.ipynb` (requer `pip install jupyter`).

## Tratamento dos dados (resumo)

- Remoção do caractere BOM no nome da coluna `ano`; padronização de textos e tipos.
- Sem nulos nem duplicatas; `faturamento = quantidade × preço_unitario` em todas as linhas.
- Novos atributos: `periodo`, `trimestre`, `margem_pct`, `resultado_calc`, `faixa_prazo`, `faixa_avaliacao`.
-  Em 99,9% das linhas, `lucro ≠ faturamento − custo` (característica da simulação). Os KPIs usam a coluna `lucro` fornecida; `resultado_calc` guarda a diferença para conferência.
- **Ticket médio** = faturamento ÷ número de pedidos (cada linha da base é um pedido).

## Principais resultados

- Faturamento de **R$ 85,1 mi** e lucro de **R$ 26,9 mi** (margem de 31,6%); ticket médio de R$ 19.173.
- Faturamento estável ao longo dos anos (~0,02% a.a.) e **sazonalidade fraca** (pico em outubro, vale em junho).
- **Beleza** lidera faturamento e lucro; a margem é quase igual entre categorias, então a diferença é de volume.
- **Sudeste** concentra 34,6% do faturamento por ter mais pedidos; o ticket médio é parecido entre regiões (maior no Nordeste).
- Prazo de entrega, avaliação e vendas **não** se correlacionam nesta base.

## Publicação

1. **GitHub:** crie o repositório e envie todos os arquivos (`git init`, `git add .`, `git commit`, `git push`).
2. **GitHub Pages:** *Settings → Pages → Deploy from a branch → `main` / root*. O `index.html` será a página inicial.
3. **Streamlit Community Cloud:** em [share.streamlit.io](https://share.streamlit.io), *New app*, escolha o repositório, branch `main` e arquivo `app.py`.

## Tecnologias

Python · Pandas · NumPy · Matplotlib · Seaborn · Plotly · Streamlit · SQLAlchemy · SQLite · GitHub
