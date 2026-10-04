# Vendas em E-commerce no Brasil (2015–2024)

Projeto desenvolvido para a disciplina **Linguagem de Programação: Análise e Visualização de Dados com Python**.

O projeto realiza uma análise exploratória e visualização de uma base **simulada com 4.440 pedidos de e-commerce**, abrangendo o período de 2015 a 2024.

## Objetivo

Analisar os dados de vendas para identificar padrões relacionados a:

* Faturamento e lucro;
* Categorias e produtos;
* Regiões e estados;
* Canais de venda;
* Sazonalidade;
* Ticket médio;
* Prazo de entrega e avaliação dos clientes.

## Resultados principais

* **Faturamento:** R$ 85,1 milhões
* **Lucro:** R$ 26,9 milhões
* **Margem:** 31,6%
* **Ticket médio:** R$ 19.173
* **Categoria líder:** Beleza
* **Região com maior faturamento:** Sudeste
* **Sazonalidade:** fraca, com maior volume em outubro e menor em junho
* **Evolução do faturamento:** relativamente estável durante o período analisado

A análise também indicou que, nesta base simulada, **prazo de entrega, avaliação e volume de vendas apresentam baixa relação entre si**.

## Dashboard

O projeto possui um dashboard interativo desenvolvido com **Streamlit**, contendo:

* Visão geral;
* Análise temporal e sazonalidade;
* Regiões e mapa;
* Categorias e canais;
* Lucro, logística e avaliação;
* Tabela dinâmica;
* Consultas SQL;
* Conclusão executiva.

Os dados podem ser filtrados por **ano, mês, região, estado, categoria e canal de venda**.

### Links

* **GitHub:** https://github.com/PedroDuarteMachado/ecommerce
* **Dashboard:** https://ecommerce-7qnsytbn9qqwwkppsapqfb.streamlit.app/
* **Página do projeto:** https://pedroduartemachado.github.io/ecommerce/

## Tecnologias

* Python
* Pandas
* NumPy
* Matplotlib
* Seaborn
* Plotly
* Streamlit
* SQLAlchemy
* SQLite
* Jupyter Notebook
* Git/GitHub

## Estrutura do projeto

```text
ecommerce/
├── app.py
├── requirements.txt
├── README.md
├── index.html
├── dados/
│   └── simulacao_ecommerce_brasil.csv
├── database/
│   └── ecommerce.db
├── notebooks/
│   └── analise_ecommerce.ipynb
└── imagens/
```

## Como executar

Clone o repositório:

```bash
git clone https://github.com/PedroDuarteMachado/ecommerce.git
cd ecommerce
```

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente no Windows:

```bash
.venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute o dashboard:

```bash
streamlit run app.py
```

O notebook pode ser aberto com:

```bash
jupyter notebook notebooks/analise_ecommerce.ipynb
```

## Banco de dados

A aplicação utiliza **SQLite** para armazenar os dados tratados e **SQLAlchemy** para realizar a comunicação com o banco.

O banco é criado automaticamente caso não exista.

## Observação

Os dados utilizados neste projeto são **simulados** e foram utilizados exclusivamente para fins acadêmicos e de demonstração de técnicas de análise e visualização de dados.
