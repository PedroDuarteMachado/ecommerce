"""
Dashboard — Vendas em E-commerce no Brasil (2015–2024)
Projeto G1/G2 · Linguagem de Programação — Análise e Visualização de Dados com Python

Tecnologias: Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit, SQLAlchemy + SQLite.
Executar com:  streamlit run app.py
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st
from matplotlib.ticker import FuncFormatter
from sqlalchemy import create_engine, inspect, text


st.set_page_config(
    page_title="E-commerce Brasil · Dashboard de Vendas",
    page_icon="🛒",
    layout="wide",
)

BASE = Path(__file__).parent
CSV_PATH = BASE / "dados" / "simulacao_ecommerce_brasil.csv"
DB_PATH = BASE / "database" / "ecommerce.db"

PRIMARY = "#1F4E79"
ACCENT = "#E07A1F"
GREY = "#B8C2CC"
REG_PAL = {
    "Norte": "#4C9F70",
    "Nordeste": "#E07A1F",
    "Centro-Oeste": "#8E6BBF",
    "Sudeste": "#1F4E79",
    "Sul": "#C2185B",
}
MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
         7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
COLUNAS = ["ano", "mes", "data", "regiao", "uf", "cidade", "canal_venda", "categoria",
           "produto", "quantidade", "preco_unitario", "faturamento", "custo", "lucro",
           "prazo_entrega", "avaliacao_cliente"]
FAIXAS_PRAZO = ["Até 5 dias", "5–10 dias", "10–15 dias", "Acima de 15 dias"]
FAIXAS_AVAL = ["Até 3,0", "3,0–3,5", "3,5–4,0", "4,0–4,5", "4,5–5,0"]

UF_COORD = {
    "AC": (-9.0, -70.8), "AL": (-9.6, -36.8), "AP": (1.4, -51.8), "AM": (-3.4, -65.0),
    "BA": (-12.9, -41.7), "CE": (-5.2, -39.3), "DF": (-15.8, -47.9), "ES": (-19.6, -40.5),
    "GO": (-15.9, -49.8), "MA": (-5.0, -45.3), "MT": (-12.9, -55.9), "MS": (-20.5, -54.5),
    "MG": (-18.5, -44.6), "PA": (-3.8, -52.5), "PB": (-7.1, -36.8), "PR": (-24.6, -51.6),
    "PE": (-8.4, -37.9), "PI": (-7.7, -42.7), "RJ": (-22.2, -42.7), "RN": (-5.8, -36.5),
    "RS": (-29.7, -53.5), "RO": (-10.9, -62.8), "RR": (2.1, -61.4), "SC": (-27.2, -50.5),
    "SP": (-22.2, -48.8), "SE": (-10.6, -37.4), "TO": (-10.2, -48.3),
}

sns.set_theme(style="whitegrid", context="notebook", font_scale=0.95,
              rc={"axes.spines.top": False, "axes.spines.right": False})

def _br(s: str) -> str:
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def brl(v: float) -> str:
    return _br(f"R$ {v:,.2f}")


def mi(v: float) -> str:
    return _br(f"R$ {v / 1e6:,.1f} mi")


def num(v: float, casas: int = 0) -> str:
    return _br(f"{v:,.{casas}f}")


def pct(v: float, casas: int = 1) -> str:
    return _br(f"{v:,.{casas}f}%")



def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Limpeza e engenharia de atributos (mesma lógica do notebook)."""
    df = df.copy()
    df.columns = [c.replace("﻿", "").strip().lower() for c in df.columns]
    faltando = set(COLUNAS) - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes: {', '.join(sorted(faltando))}")
    df = df[COLUNAS]

    for c in ["regiao", "uf", "cidade", "canal_venda", "categoria", "produto"]:
        df[c] = df[c].astype(str).str.strip()
    df["uf"] = df["uf"].str.upper()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for c in ["quantidade", "preco_unitario", "faturamento", "custo", "lucro",
              "prazo_entrega", "avaliacao_cliente"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=COLUNAS).drop_duplicates()
    df = df[(df["quantidade"] > 0) & (df["faturamento"] > 0)].copy()

    # a data é a fonte de verdade para ano/mês
    df["ano"] = df["data"].dt.year.astype(int)
    df["mes"] = df["data"].dt.month.astype(int)

    # engenharia de atributos
    df["periodo"] = df["data"].dt.to_period("M").dt.to_timestamp()
    df["trimestre"] = df["data"].dt.quarter.astype(int)
    df["margem_pct"] = df["lucro"] / df["faturamento"] * 100
    df["resultado_calc"] = df["faturamento"] - df["custo"]
    df["faixa_prazo"] = pd.cut(df["prazo_entrega"], [0, 5, 10, 15, np.inf],
                               labels=FAIXAS_PRAZO).astype(str)
    df["faixa_avaliacao"] = pd.cut(df["avaliacao_cliente"], [0, 3, 3.5, 4, 4.5, 5],
                                   labels=FAIXAS_AVAL, include_lowest=True).astype(str)
    return df.reset_index(drop=True)


def _ordenar_faixas(df: pd.DataFrame) -> pd.DataFrame:
    df["faixa_prazo"] = pd.Categorical(df["faixa_prazo"], FAIXAS_PRAZO, ordered=True)
    df["faixa_avaliacao"] = pd.Categorical(df["faixa_avaliacao"], FAIXAS_AVAL, ordered=True)
    return df


@st.cache_resource
def get_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH.as_posix()}")


@st.cache_data(show_spinner="Carregando base de dados…")
def carregar_base() -> pd.DataFrame:
    """Lê a tabela `vendas` do SQLite; se o banco não existir, cria a partir do CSV."""
    engine = get_engine()
    if "vendas" not in inspect(engine).get_table_names():
        bruto = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        preparar(bruto).to_sql("vendas", engine, if_exists="replace", index=False)
    df = pd.read_sql("SELECT * FROM vendas", engine, parse_dates=["data", "periodo"])
    return _ordenar_faixas(df)


@st.cache_data(show_spinner="Processando arquivo enviado…")
def carregar_upload(conteudo: bytes) -> pd.DataFrame:
    import io

    bruto = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8-sig")
    return _ordenar_faixas(preparar(bruto))


def engine_para_sql(df: pd.DataFrame, enviado: bool):
    """Banco persistido (somente leitura) ou banco em memória quando há upload."""
    if not enviado:
        get_engine()  # garante a criação do arquivo
        return create_engine(f"sqlite:///file:{DB_PATH.as_posix()}?mode=ro&uri=true")
    eng = create_engine("sqlite://")
    df.assign(faixa_prazo=df["faixa_prazo"].astype(str),
              faixa_avaliacao=df["faixa_avaliacao"].astype(str)).to_sql("vendas", eng, index=False)
    return eng


def calcular_kpis(df: pd.DataFrame) -> dict:
    fat, luc = df["faturamento"].sum(), df["lucro"].sum()
    por_prod = df.groupby("produto")["quantidade"].sum().sort_values(ascending=False)
    por_cat = df.groupby("categoria")["lucro"].sum().sort_values(ascending=False)
    por_reg = df.groupby("regiao")["faturamento"].sum().sort_values(ascending=False)
    return {
        "faturamento": fat,
        "lucro": luc,
        "margem": luc / fat * 100,
        "pedidos": len(df),
        "itens": int(df["quantidade"].sum()),
        "ticket": fat / len(df),
        "produto": por_prod.index[0], "produto_qtd": int(por_prod.iloc[0]),
        "categoria": por_cat.index[0], "categoria_lucro": por_cat.iloc[0],
        "regiao": por_reg.index[0], "regiao_fat": por_reg.iloc[0],
        "avaliacao": df["avaliacao_cliente"].mean(),
        "prazo": df["prazo_entrega"].mean(),
    }


def resumo(df: pd.DataFrame, por: str) -> pd.DataFrame:
    g = df.groupby(por, observed=True).agg(
        pedidos=("faturamento", "size"),
        itens=("quantidade", "sum"),
        faturamento=("faturamento", "sum"),
        lucro=("lucro", "sum"),
        prazo=("prazo_entrega", "mean"),
        avaliacao=("avaliacao_cliente", "mean"),
    )
    g["ticket"] = g["faturamento"] / g["pedidos"]
    g["margem"] = g["lucro"] / g["faturamento"] * 100
    return g


def serie_mensal(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("periodo", as_index=False)[["faturamento", "lucro"]].sum()


def indice_sazonal(df: pd.DataFrame) -> pd.Series:
    """Média do faturamento de cada mês dividida pela média mensal geral (1,00 = média)."""
    mensal = df.groupby(["ano", "mes"])["faturamento"].sum()
    return mensal.groupby("mes").mean() / mensal.mean()


def cagr(df: pd.DataFrame):
    anual = df.groupby("ano")["faturamento"].sum()
    if len(anual) < 2 or anual.iloc[0] <= 0:
        return None
    n = anual.index[-1] - anual.index[0]
    return (anual.iloc[-1] / anual.iloc[0]) ** (1 / n) - 1


def mostrar(fig) -> None:
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def barras(ax, serie: pd.Series, fmt, horizontal: bool = True, destaque: bool = True) -> None:
    """Barras ordenadas (maior → menor) com rótulos e destaque no líder."""
    s = serie.sort_values(ascending=False)
    chaves = s.index.astype(str)
    cores = {k: (ACCENT if (i == 0 and destaque) else PRIMARY) for i, k in enumerate(chaves)}
    if horizontal:
        sns.barplot(x=s.values, y=chaves, hue=chaves, palette=cores, legend=False, ax=ax)
        for i, v in enumerate(s.values):
            ax.text(v, i, " " + fmt(v), va="center", fontsize=9)
        ax.set_xlim(0, s.max() * 1.25)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt(v)))
    else:
        sns.barplot(x=chaves, y=s.values, hue=chaves, palette=cores, legend=False, ax=ax)
        for i, v in enumerate(s.values):
            ax.text(i, v, fmt(v), ha="center", va="bottom", fontsize=9)
        ax.set_ylim(0, s.max() * 1.15)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt(v)))


def plotly_layout(fig, y_prefix: str = "R$ ") -> None:
    fig.update_layout(template="plotly_white", hovermode="x unified",
                      margin=dict(l=10, r=10, t=40, b=10), legend_title_text="")
    fig.update_yaxes(tickprefix=y_prefix, separatethousands=True)


def mostrar_plotly(fig) -> None:
    st.plotly_chart(fig, width="stretch")


def interpretacao(*linhas: str) -> None:
    st.info("**Interpretação.** " + " ".join(linhas), icon="💡")


def cabecalho(titulo: str, subtitulo: str) -> None:
    st.title(titulo)
    st.caption(subtitulo)


CTX: dict = {}


def pagina_visao_geral() -> None:
    df, total = CTX["df"], CTX["df_all"]
    cabecalho("🛒 Vendas em E-commerce no Brasil (2015–2024)",
              "Visão geral · KPIs e evolução temporal das vendas")

    st.markdown(
        """
**O problema.** O comércio eletrônico é hoje um dos principais canais de venda do país e gera
grandes volumes de dados. Este dashboard investiga uma base **simulada** de vendas (2015–2024) para
responder: *quais categorias, estados e canais geram mais receita e lucro? Existe sazonalidade?
Como evoluiu o faturamento? O desempenho logístico e a avaliação do cliente se relacionam com as vendas?*

Use os **filtros na barra lateral** — todos os KPIs, gráficos e interpretações se recalculam.
        """
    )

    k = calcular_kpis(df)
    c = st.columns(4)
    c[0].metric("Faturamento total", mi(k["faturamento"]), help=brl(k["faturamento"]))
    c[1].metric("Lucro total", mi(k["lucro"]), help=brl(k["lucro"]))
    c[2].metric("Margem de lucro", pct(k["margem"]))
    c[3].metric("Ticket médio", brl(k["ticket"]),
                help="Faturamento ÷ número de pedidos (cada linha da base é um pedido).")
    c = st.columns(4)
    c[0].metric("Produto mais vendido", k["produto"], f"{num(k['produto_qtd'])} unidades",
                delta_color="off")
    c[1].metric("Categoria mais lucrativa", k["categoria"], mi(k["categoria_lucro"]),
                delta_color="off")
    c[2].metric("Região com maior faturamento", k["regiao"], mi(k["regiao_fat"]),
                delta_color="off")
    c[3].metric("Nº de pedidos", num(k["pedidos"]), f"{num(k['itens'])} itens", delta_color="off")
    c = st.columns(2)
    c[0].metric("Avaliação média do cliente", f"{num(k['avaliacao'], 2)} / 5")
    c[1].metric("Prazo médio de entrega", f"{num(k['prazo'], 1)} dias")

    st.subheader("Evolução mensal do faturamento e do lucro")
    m = serie_mensal(df)
    fig = px.line(m, x="periodo", y=["faturamento", "lucro"],
                  labels={"periodo": "", "value": "", "variable": ""},
                  color_discrete_map={"faturamento": PRIMARY, "lucro": ACCENT})
    plotly_layout(fig)
    mostrar_plotly(fig)

    anual = df.groupby("ano")["faturamento"].sum()
    melhor, pior = anual.idxmax(), anual.idxmin()
    c_ = cagr(df)
    txt = [f"No recorte selecionado, o faturamento somou {mi(k['faturamento'])} e o lucro {mi(k['lucro'])} "
           f"(margem de {pct(k['margem'])})."]
    if len(anual) > 1:
        txt.append(f"O melhor ano foi {melhor} ({mi(anual.max())}) e o mais fraco, {pior} ({mi(anual.min())}); "
                   f"a diferença entre eles é de {pct((anual.max() / anual.min() - 1) * 100)}.")
        if c_ is not None:
            txt.append(f"A taxa de crescimento anual composta entre {anual.index[0]} e {anual.index[-1]} é de "
                       f"{pct(c_ * 100, 2)} ao ano — {'praticamente estável' if abs(c_) < 0.01 else ('crescimento' if c_ > 0 else 'retração')}.")
    interpretacao(*txt)

    with st.expander("🔎 Qualidade e escopo dos dados"):
        incons = (total["faturamento"] - total["custo"] - total["lucro"]).abs().gt(0.5).mean() * 100
        st.markdown(
            f"- **{num(len(total))} pedidos** de {total['data'].min():%m/%Y} a {total['data'].max():%m/%Y}, "
            f"{total['uf'].nunique()} estados, {total['categoria'].nunique()} categorias, "
            f"{total['canal_venda'].nunique()} canais.\n"
            f"- Sem valores nulos nem duplicatas após o tratamento; `faturamento = quantidade × preço` em 100% das linhas.\n"
            f"- ⚠️ Em **{pct(incons, 1)}** das linhas, `lucro ≠ faturamento − custo` (característica da simulação). "
            f"Os KPIs usam a coluna `lucro` fornecida; `resultado_calc` guarda faturamento − custo para conferência."
        )
    st.write("""
    Aluno: Pedro Duarte Machado

    Professor: Alexandre Neves Louzada
    """)


def pagina_temporal() -> None:
    df = CTX["df"]
    cabecalho("📈 Análise temporal e sazonalidade",
              "Tendência, média móvel, variação anual e padrão mensal")

    st.subheader("Série mensal com média móvel de 12 meses")
    m = serie_mensal(df).sort_values("periodo")
    m["media_movel_12m"] = m["faturamento"].rolling(12, min_periods=12).mean()
    fig = px.line(m, x="periodo", y=["faturamento", "media_movel_12m"],
                  labels={"periodo": "", "value": "", "variable": ""},
                  color_discrete_map={"faturamento": GREY, "media_movel_12m": PRIMARY})
    plotly_layout(fig)
    mostrar_plotly(fig)

    anual = df.groupby("ano")["faturamento"].sum()
    yoy = anual.pct_change() * 100

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Faturamento por ano")
        fig, ax = plt.subplots(figsize=(6, 4))
        barras(ax, anual.sort_index(), mi, horizontal=False, destaque=False)
        ax.axhline(anual.mean(), color=ACCENT, ls="--", lw=1.2, label="Média anual")
        ax.legend(frameon=False)
        mostrar(fig)
    with c2:
        st.subheader("Variação em relação ao ano anterior")
        y = yoy.dropna()
        if y.empty:
            st.caption("Selecione ao menos dois anos para ver a variação anual.")
        else:
            fig, ax = plt.subplots(figsize=(6, 4))
            cores = [PRIMARY if v >= 0 else ACCENT for v in y.values]
            sns.barplot(x=y.index.astype(str), y=y.values, hue=y.index.astype(str),
                        palette=dict(zip(y.index.astype(str), cores)), legend=False, ax=ax)
            for i, v in enumerate(y.values):
                ax.text(i, v, f"{v:+.1f}%".replace(".", ","), ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=9)
            ax.axhline(0, color="black", lw=0.8)
            ax.set_xlabel("")
            ax.set_ylabel("Variação (%)")
            mostrar(fig)

    st.subheader("Sazonalidade mensal")
    idx = indice_sazonal(df)
    c1, c2 = st.columns([1, 1.4])
    with c1:
        fig, ax = plt.subplots(figsize=(5, 4.2))
        s = idx.rename(index=MESES)
        cores = [ACCENT if v == idx.max() else (GREY if v != idx.min() else PRIMARY) for v in idx.values]
        sns.barplot(x=s.index, y=s.values, hue=s.index, palette=dict(zip(s.index, cores)),
                    legend=False, ax=ax)
        ax.axhline(1, color="black", lw=1, ls="--")
        ax.set_ylim(min(0.8, idx.min() - 0.05), max(1.2, idx.max() + 0.05))
        ax.set_title("Índice sazonal (1,00 = média mensal)", fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("")
        mostrar(fig)
    with c2:
        piv = df.pivot_table(index="ano", columns="mes", values="faturamento", aggfunc="sum") / 1e6
        piv.columns = [MESES[c] for c in piv.columns]
        fig, ax = plt.subplots(figsize=(8, 4.2))
        sns.heatmap(piv, annot=True, fmt=".2f", cmap="YlGnBu", linewidths=0.4,
                    cbar_kws={"label": "R$ milhões"}, annot_kws={"size": 8}, ax=ax)
        ax.set_title("Heatmap mensal do faturamento (R$ milhões)", fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("")
        mostrar(fig)

    pico, vale = idx.idxmax(), idx.idxmin()
    amplitude = (idx.max() - idx.min()) * 100
    forca = "fraca" if amplitude < 15 else ("moderada" if amplitude < 30 else "forte")
    interpretacao(
        f"O mês de maior movimento é **{MESES[pico]}** (índice {num(idx.max(), 2)}) e o de menor é "
        f"**{MESES[vale]}** (índice {num(idx.min(), 2)}); a amplitude entre eles é de {num(amplitude, 0)} pontos percentuais, "
        f"o que indica sazonalidade **{forca}**.",
        "Os meses de outubro a dezembro ficam acima do meio do ano (jun–set)."
        if idx.reindex([10, 11, 12]).mean() > idx.reindex([6, 7, 8, 9]).mean() else
        "O fim do ano não se destaca claramente sobre o meio do ano (jun–set).",
        "Como a base é simulada, não há picos típicos de varejo real (Black Friday, Natal) — vale confirmar isso "
        "com dados reais antes de planejar estoque ou campanhas.",
    )


def pagina_regioes() -> None:
    df = CTX["df"]
    cabecalho("🗺️ Comparação regional", "Estados, regiões, ticket médio e mapa interativo")

    por_uf = resumo(df, "uf").join(df.drop_duplicates("uf").set_index("uf")["regiao"])
    por_reg = resumo(df, "regiao")

    st.subheader("Faturamento por estado")
    s = por_uf.sort_values("faturamento", ascending=False)
    fig, ax = plt.subplots(figsize=(9, max(4, 0.32 * len(s))))
    sns.barplot(data=s.reset_index(), x="faturamento", y="uf", hue="regiao", palette=REG_PAL,
                dodge=False, order=s.index, ax=ax)
    for i, v in enumerate(s["faturamento"].values):
        ax.text(v, i, " " + mi(v), va="center", fontsize=8)
    ax.set_xlim(0, s["faturamento"].max() * 1.2)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: mi(v)))
    ax.legend(title="Região", frameon=False, loc="lower right")
    mostrar(fig)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Faturamento por região")
        fig, ax = plt.subplots(figsize=(6, 3.6))
        barras(ax, por_reg["faturamento"], mi)
        mostrar(fig)
    with c2:
        st.subheader("Ticket médio por região")
        fig, ax = plt.subplots(figsize=(6, 3.6))
        barras(ax, por_reg["ticket"], lambda v: brl(v).replace(",00", ""))
        mostrar(fig)

    st.subheader("Mapa interativo")
    mapa = por_uf.reset_index()
    mapa["lat"] = mapa["uf"].map(lambda u: UF_COORD.get(u, (np.nan, np.nan))[0])
    mapa["lon"] = mapa["uf"].map(lambda u: UF_COORD.get(u, (np.nan, np.nan))[1])
    mapa = mapa.dropna(subset=["lat", "lon"])
    if mapa.empty:
        st.caption("Sem coordenadas disponíveis para os estados selecionados.")
    else:
        medida = st.radio("Colorir pelo(a)", ["Ticket médio", "Margem de lucro", "Avaliação média", "Prazo médio"],
                          horizontal=True)
        col = {"Ticket médio": "ticket", "Margem de lucro": "margem",
               "Avaliação média": "avaliacao", "Prazo médio": "prazo"}[medida]
        fig = px.scatter_map(mapa, lat="lat", lon="lon", size="faturamento", color=col,
                             hover_name="uf", hover_data={"faturamento": ":,.0f", "ticket": ":,.0f",
                                                          "margem": ":.1f", "avaliacao": ":.2f",
                                                          "prazo": ":.1f", "lat": False, "lon": False},
                             color_continuous_scale="Viridis", size_max=45, zoom=3,
                             center={"lat": -14.5, "lon": -52}, map_style="carto-positron",
                             labels={col: medida}, height=520)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        mostrar_plotly(fig)
        st.caption("O tamanho da bolha representa o faturamento do estado.")

    st.subheader("Tabela por estado")
    tab = s[["regiao", "pedidos", "faturamento", "lucro", "ticket", "margem", "prazo", "avaliacao"]].copy()
    st.dataframe(tab, width="stretch",
                 column_config={
                     "regiao": "Região", "pedidos": st.column_config.NumberColumn("Pedidos", format="%d"),
                     "faturamento": st.column_config.NumberColumn("Faturamento", format="R$ %.0f"),
                     "lucro": st.column_config.NumberColumn("Lucro", format="R$ %.0f"),
                     "ticket": st.column_config.NumberColumn("Ticket médio", format="R$ %.0f"),
                     "margem": st.column_config.NumberColumn("Margem", format="%.1f%%"),
                     "prazo": st.column_config.NumberColumn("Prazo (dias)", format="%.1f"),
                     "avaliacao": st.column_config.NumberColumn("Avaliação", format="%.2f")})

    top = por_reg["faturamento"].idxmax()
    share = por_reg["faturamento"].max() / por_reg["faturamento"].sum() * 100
    t_max, t_min = por_reg["ticket"].idxmax(), por_reg["ticket"].idxmin()
    spread = (por_reg["ticket"].max() / por_reg["ticket"].min() - 1) * 100
    pedidos_top = por_reg.loc[top, "pedidos"] / por_reg["pedidos"].sum() * 100
    origem = ("a liderança vem do **volume de pedidos**, não de vendas maiores"
              if pedidos_top >= share - 1 else "além do volume, os pedidos dessa região têm valor acima da média")
    interpretacao(
        f"**{top}** lidera o faturamento, com {pct(share)} do total, e concentra {pct(pedidos_top)} dos pedidos — {origem}.",
        f"O ticket médio é maior no(a) **{t_max}** ({brl(por_reg['ticket'].max())}) e menor no(a) **{t_min}** "
        f"({brl(por_reg['ticket'].min())}), uma diferença de apenas {pct(spread)}: na prática, o ticket é parecido entre regiões.",
        "Para comparar regiões de forma justa, prefira ticket médio e margem ao faturamento bruto.",
    )


def pagina_categorias() -> None:
    df = CTX["df"]
    cabecalho("🏷️ Categorias, produtos e canais", "O que vende, o que lucra e por onde vende")

    por_cat = resumo(df, "categoria")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Faturamento por categoria")
        fig, ax = plt.subplots(figsize=(6, 4))
        barras(ax, por_cat["faturamento"], mi)
        mostrar(fig)
    with c2:
        st.subheader("Lucro por categoria")
        fig, ax = plt.subplots(figsize=(6, 4))
        barras(ax, por_cat["lucro"], mi)
        mostrar(fig)

    st.subheader("Margem de lucro por categoria")
    fig, ax = plt.subplots(figsize=(10, 3.4))
    barras(ax, por_cat["margem"], lambda v: pct(v), horizontal=False)
    ax.set_ylim(0, por_cat["margem"].max() * 1.25)
    mostrar(fig)

    st.subheader("Ranking de produtos")
    por_prod = resumo(df, "produto")
    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.4))
        barras(ax, por_prod["itens"], lambda v: num(v))
        ax.set_title("Unidades vendidas", fontsize=10)
        mostrar(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 3.4))
        barras(ax, por_prod["faturamento"], mi)
        ax.set_title("Faturamento", fontsize=10)
        mostrar(fig)

    st.subheader("Canais de venda")
    por_canal = resumo(df, "canal_venda")
    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.4))
        barras(ax, por_canal["faturamento"], mi)
        ax.set_title("Faturamento por canal", fontsize=10)
        mostrar(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 3.4))
        barras(ax, por_canal["ticket"], lambda v: brl(v).replace(",00", ""))
        ax.set_title("Ticket médio por canal", fontsize=10)
        mostrar(fig)

    st.subheader("Cruzamento categoria × canal (faturamento, R$ milhões)")
    cruz = df.pivot_table(index="categoria", columns="canal_venda", values="faturamento", aggfunc="sum") / 1e6
    fig, ax = plt.subplots(figsize=(9, 3.8))
    sns.heatmap(cruz, annot=True, fmt=".1f", cmap="YlGnBu", linewidths=0.4, ax=ax,
                cbar_kws={"label": "R$ milhões"})
    ax.set_xlabel("")
    ax.set_ylabel("")
    mostrar(fig)

    cat_fat, cat_luc = por_cat["faturamento"].idxmax(), por_cat["lucro"].idxmax()
    cat_mar = por_cat["margem"].idxmax()
    canal = por_canal["faturamento"].idxmax()
    dif_canal = (por_canal["faturamento"].max() / por_canal["faturamento"].min() - 1) * 100
    dif_prod = (por_prod["itens"].max() / por_prod["itens"].min() - 1) * 100
    dif_cat = (por_cat["faturamento"].max() / por_cat["faturamento"].min() - 1) * 100
    dif_margem = por_cat["margem"].max() - por_cat["margem"].min()
    if cat_fat == cat_luc:
        lider = (f"**{cat_fat}** lidera tanto o faturamento ({mi(por_cat['faturamento'].max())}) quanto o lucro "
                 f"({mi(por_cat['lucro'].max())}).")
    else:
        lider = (f"**{cat_fat}** é a categoria de maior faturamento ({mi(por_cat['faturamento'].max())}) e **{cat_luc}** "
                 f"a de maior lucro ({mi(por_cat['lucro'].max())}).")
    interpretacao(
        lider,
        f"A distância entre a melhor e a pior categoria em faturamento é de {pct(dif_cat)}, enquanto a margem varia só "
        f"{num(dif_margem, 1)} ponto(s) percentual(is) (de {pct(por_cat['margem'].min())} a {pct(por_cat['margem'].max())}; "
        f"a melhor é **{cat_mar}**): o que separa as categorias é o **volume vendido**, não a rentabilidade.",
        f"O canal **{canal}** lidera em faturamento, {pct(dif_canal)} acima do menor canal.",
        f"Entre os produtos, **{por_prod['itens'].idxmax()}** vende mais unidades, {pct(dif_prod)} acima do último colocado.",
    )


def pagina_lucro_logistica() -> None:
    df = CTX["df"]
    cabecalho("💰 Lucro, logística e avaliação do cliente",
              "Relação financeira, prazos de entrega, satisfação e correlações")

    st.subheader("Lucro × faturamento")
    amostra = df if len(df) <= 3000 else df.sample(3000, random_state=1)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    sns.scatterplot(data=amostra, x="faturamento", y="lucro", hue="categoria", palette="colorblind",
                    alpha=0.55, s=22, ax=ax)
    sns.regplot(data=df, x="faturamento", y="lucro", scatter=False, color="black",
                line_kws={"lw": 1.5, "ls": "--"}, ax=ax)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e3:,.0f} mil".replace(",", ".")))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e3:,.0f} mil".replace(",", ".")))
    ax.set_xlabel("Faturamento por pedido (R$)")
    ax.set_ylabel("Lucro por pedido (R$)")
    ax.legend(title="Categoria", frameon=False, ncol=2, fontsize=8)
    mostrar(fig)
    r_fl = df["faturamento"].corr(df["lucro"])

    st.subheader("Distribuição da margem de lucro")
    fig, ax = plt.subplots(figsize=(9, 3.4))
    sns.boxplot(data=df, x="canal_venda", y="margem_pct", color=PRIMARY, fliersize=2, ax=ax,
                boxprops={"alpha": 0.75})
    ax.set_xlabel("")
    ax.set_ylabel("Margem (%)")
    mostrar(fig)

    st.subheader("Desempenho logístico")
    c1, c2 = st.columns(2)
    por_reg = resumo(df, "regiao")
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.6))
        barras(ax, por_reg["prazo"], lambda v: f"{num(v, 1)} d")
        ax.set_title("Prazo médio de entrega por região", fontsize=10)
        mostrar(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 3.6))
        sns.histplot(df["prazo_entrega"], bins=14, color=PRIMARY, ax=ax)
        ax.axvline(df["prazo_entrega"].mean(), color=ACCENT, ls="--", label="Média")
        ax.set_xlabel("Prazo de entrega (dias)")
        ax.set_ylabel("Pedidos")
        ax.legend(frameon=False)
        mostrar(fig)

    st.subheader("Avaliação do cliente × vendas e prazo")
    c1, c2 = st.columns(2)
    por_av = resumo(df, "faixa_avaliacao").reindex(FAIXAS_AVAL).dropna(subset=["pedidos"])
    por_pz = resumo(df, "faixa_prazo").reindex(FAIXAS_PRAZO).dropna(subset=["pedidos"])
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.6))
        sns.barplot(x=por_av.index.astype(str), y=por_av["ticket"].values, color=PRIMARY, ax=ax)
        ax.set_title("Ticket médio por faixa de avaliação", fontsize=10)
        ax.set_xlabel("Avaliação do cliente")
        ax.set_ylabel("")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e3:,.0f} mil".replace(",", ".")))
        mostrar(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 3.6))
        sns.barplot(x=por_pz.index.astype(str), y=por_pz["avaliacao"].values, color=ACCENT, ax=ax)
        ax.set_ylim(0, 5)
        ax.set_title("Avaliação média por faixa de prazo", fontsize=10)
        ax.set_xlabel("Prazo de entrega")
        ax.set_ylabel("Nota média")
        mostrar(fig)

    st.subheader("Correlação estatística")
    cols = {"faturamento": "Faturamento", "lucro": "Lucro", "quantidade": "Quantidade",
            "preco_unitario": "Preço unit.", "custo": "Custo", "margem_pct": "Margem %",
            "prazo_entrega": "Prazo", "avaliacao_cliente": "Avaliação"}
    metodo = st.radio("Método", ["pearson", "spearman"], horizontal=True,
                      format_func=lambda x: {"pearson": "Pearson (linear)", "spearman": "Spearman (postos)"}[x])
    corr = df[list(cols)].rename(columns=cols).corr(method=metodo)
    fig, ax = plt.subplots(figsize=(8, 5.2))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1,
                linewidths=0.4, ax=ax, cbar_kws={"label": "Coeficiente"})
    mostrar(fig)

    r_aval = df["avaliacao_cliente"].corr(df["faturamento"])
    r_prazo = df["prazo_entrega"].corr(df["avaliacao_cliente"])
    r_qtd = df["quantidade"].corr(df["faturamento"])
    forca = lambda r: "praticamente nula" if abs(r) < 0.1 else ("fraca" if abs(r) < 0.3 else ("moderada" if abs(r) < 0.7 else "forte"))
    interpretacao(
        f"Lucro e faturamento têm correlação **forte** (r = {num(r_fl, 2)}): pedidos maiores geram lucro maior em valor absoluto, "
        f"e a margem média é de {pct(df['lucro'].sum() / df['faturamento'].sum() * 100)}.",
        f"O faturamento é explicado em medida parecida pela **quantidade** (r = {num(r_qtd, 2)}) e pelo **preço unitário** "
        f"(r = {num(df['preco_unitario'].corr(df['faturamento']), 2)}).",
        f"A relação entre avaliação e faturamento é {forca(r_aval)} (r = {num(r_aval, 2)}) e entre prazo e avaliação é "
        f"{forca(r_prazo)} (r = {num(r_prazo, 2)}).",
        "Ou seja, nesta base, **clientes mais satisfeitos ou entregas mais rápidas não aparecem associados a vendas maiores** — "
        "em dados reais esperaríamos que prazos longos derrubassem a nota, o que aqui não ocorre.",
    )


def pagina_tabela() -> None:
    df = CTX["df"]
    cabecalho("🧮 Tabela dinâmica", "Exploração detalhada com agrupamentos à sua escolha")

    dims = {"Ano": "ano", "Mês": "mes", "Trimestre": "trimestre", "Região": "regiao", "Estado": "uf",
            "Cidade": "cidade", "Categoria": "categoria", "Produto": "produto", "Canal de venda": "canal_venda"}
    meds = {"Faturamento": "faturamento", "Lucro": "lucro", "Custo": "custo", "Quantidade": "quantidade",
            "Prazo de entrega": "prazo_entrega", "Avaliação do cliente": "avaliacao_cliente",
            "Margem (%)": "margem_pct"}
    c = st.columns(4)
    linhas = c[0].selectbox("Linhas", list(dims), index=list(dims).index("Categoria"))
    colunas = c[1].selectbox("Colunas", ["(nenhuma)"] + list(dims), index=list(dims).index("Canal de venda") + 1)
    medida = c[2].selectbox("Valor", list(meds))
    agg = c[3].selectbox("Agregação", ["Soma", "Média", "Mediana", "Contagem"],
                         index=0 if medida in ("Faturamento", "Lucro", "Custo", "Quantidade") else 1)
    func = {"Soma": "sum", "Média": "mean", "Mediana": "median", "Contagem": "count"}[agg]

    if colunas != "(nenhuma)" and colunas == linhas:
        st.warning("Escolha dimensões diferentes para linhas e colunas.")
        return
    tab = df.pivot_table(index=dims[linhas], columns=None if colunas == "(nenhuma)" else dims[colunas],
                         values=meds[medida], aggfunc=func, margins=True, margins_name="Total",
                         observed=True)
    if isinstance(tab, pd.Series):
        tab = tab.to_frame(f"{agg} de {medida}")
    st.dataframe(tab.style.format(lambda v: num(v, 2) if pd.notna(v) else "—").background_gradient(
        cmap="Blues", axis=None), width="stretch", height=430)
    st.download_button("⬇️ Baixar tabela (CSV)", tab.to_csv().encode("utf-8-sig"),
                       "tabela_dinamica.csv", "text/csv")

    with st.expander("Ver dados detalhados (registros filtrados)"):
        st.dataframe(df.drop(columns=["periodo"]), width="stretch", height=350)
        st.download_button("⬇️ Baixar dados filtrados (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                           "vendas_filtradas.csv", "text/csv")


PRESETS = {
    "Faturamento e lucro por ano": """SELECT ano, ROUND(SUM(faturamento), 2) AS faturamento,
       ROUND(SUM(lucro), 2) AS lucro,
       ROUND(100.0 * SUM(lucro) / SUM(faturamento), 1) AS margem_pct
FROM vendas
GROUP BY ano
ORDER BY ano""",
    "Top 5 estados por faturamento": """SELECT uf, regiao, COUNT(*) AS pedidos,
       ROUND(SUM(faturamento), 2) AS faturamento,
       ROUND(AVG(faturamento), 2) AS ticket_medio
FROM vendas
GROUP BY uf, regiao
ORDER BY faturamento DESC
LIMIT 5""",
    "Categorias por canal": """SELECT categoria, canal_venda, ROUND(SUM(lucro), 2) AS lucro
FROM vendas
GROUP BY categoria, canal_venda
ORDER BY lucro DESC""",
    "Prazo e avaliação por região": """SELECT regiao, ROUND(AVG(prazo_entrega), 2) AS prazo_medio,
       ROUND(AVG(avaliacao_cliente), 2) AS avaliacao_media
FROM vendas
GROUP BY regiao
ORDER BY prazo_medio""",
}
PROIBIDAS = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|reindex)\b", re.I)


def pagina_sql() -> None:
    df = CTX["df_all"]
    cabecalho("🗄️ Consultas SQL", "Banco SQLite persistido e consultado via SQLAlchemy")
    enviado = CTX["enviado"]
    st.markdown(
        "A base tratada fica gravada no arquivo `database/ecommerce.db` (tabela **`vendas`**) e é lida com "
        "**SQLAlchemy**. Aqui as consultas rodam sobre a base completa, **sem** os filtros da barra lateral. "
        "Apenas comandos `SELECT` são aceitos."
        + (" *(Arquivo enviado: consultando uma cópia em memória.)*" if enviado else "")
    )
    escolha = st.selectbox("Consultas prontas", list(PRESETS))
    consulta = st.text_area("Consulta SQL", PRESETS[escolha], height=170, key=f"sql_{escolha}")
    if st.button("▶️ Executar", type="primary"):
        q = consulta.strip().rstrip(";").strip()
        if not re.match(r"^(select|with)\b", q, re.I) or ";" in q or PROIBIDAS.search(q):
            st.error("Somente uma consulta `SELECT` é permitida.")
            return
        try:
            res = pd.read_sql(text(q), engine_para_sql(df, enviado))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Erro na consulta: {exc}")
            return
        st.success(f"{len(res)} linha(s) retornada(s).")
        st.dataframe(res, width="stretch")
    with st.expander("Esquema da tabela `vendas`"):
        st.code(", ".join(df.columns), language="text")


def pagina_conclusao() -> None:
    df = CTX["df"]
    cabecalho("📌 Conclusão executiva", "Respostas às perguntas orientadoras e recomendações")

    k = calcular_kpis(df)
    por_cat, por_reg = resumo(df, "categoria"), resumo(df, "regiao")
    por_uf, por_canal, por_prod = resumo(df, "uf"), resumo(df, "canal_venda"), resumo(df, "produto")
    idx = indice_sazonal(df)
    anual = df.groupby("ano")["faturamento"].sum()
    c_ = cagr(df)

    st.subheader("Resumo")
    st.markdown(
        f"No recorte selecionado, a operação faturou **{mi(k['faturamento'])}** com lucro de **{mi(k['lucro'])}** "
        f"(margem de **{pct(k['margem'])}**) em {num(k['pedidos'])} pedidos, com ticket médio de **{brl(k['ticket'])}**, "
        f"avaliação média de {num(k['avaliacao'], 2)} e prazo médio de {num(k['prazo'], 1)} dias."
    )

    st.subheader("O que os dados respondem")
    tendencia = (f"A taxa de crescimento anual composta é de {pct(c_ * 100, 2)} (de {mi(anual.iloc[0])} em "
                 f"{anual.index[0]} para {mi(anual.iloc[-1])} em {anual.index[-1]}), com oscilações de ano a ano sem tendência clara."
                 if c_ is not None else "Selecione ao menos dois anos para avaliar a evolução.")
    st.markdown(
        f"""
- **Categorias com maior faturamento:** {por_cat['faturamento'].idxmax()} ({mi(por_cat['faturamento'].max())}); a mais lucrativa é **{por_cat['lucro'].idxmax()}**.
- **Estados que concentram mais vendas:** {', '.join(por_uf['faturamento'].nlargest(3).index)} — liderados pelo Sudeste, que responde por {pct(por_reg.loc['Sudeste', 'faturamento'] / por_reg['faturamento'].sum() * 100) if 'Sudeste' in por_reg.index else '—'} do faturamento.
- **Sazonalidade:** pico em {MESES[idx.idxmax()]} e vale em {MESES[idx.idxmin()]}, amplitude de {num((idx.max() - idx.min()) * 100, 0)} p.p. — padrão **{'fraco' if (idx.max() - idx.min()) < 0.15 else 'relevante'}**.
- **Melhor canal:** {por_canal['faturamento'].idxmax()} em faturamento; os canais ficam muito próximos entre si.
- **Produto mais vendido:** {k['produto']} ({num(k['produto_qtd'])} unidades).
- **Evolução no tempo:** {tendencia}
- **Maior ticket médio:** região {por_reg['ticket'].idxmax()} ({brl(por_reg['ticket'].max())}) — diferença pequena para as demais.
"""
    )

    st.subheader("Recomendações")
    st.markdown(
        f"""
1. **Apostar nas categorias de maior volume.** A margem é quase igual entre categorias ({pct(por_cat['margem'].min())} a {pct(por_cat['margem'].max())}), então {por_cat['lucro'].idxmax()} lidera o lucro simplesmente por vender mais; campanhas e estoque devem seguir o volume.
2. **Aumentar o ticket médio** (combos, frete grátis acima de um valor), já que ele varia pouco entre regiões e canais e é a alavanca mais direta de receita.
3. **Investigar as regiões de menor participação** ({por_reg['faturamento'].idxmin()} tem a menor fatia, com {pct(por_reg['faturamento'].min() / por_reg['faturamento'].sum() * 100)} do faturamento e {num(por_reg.loc[por_reg['faturamento'].idxmin(), 'pedidos'])} pedidos): a fatia menor vem de menos pedidos, não de ticket menor — verificar com dados reais se há demanda não atendida.
4. **Monitorar a logística:** o prazo médio é de {num(k['prazo'], 1)} dias; como a nota do cliente não depende do prazo nesta base, vale medir isso com dados reais antes de investir em frete rápido.
"""
    )

    st.warning(
        "**Limitações.** A base é simulada: não há tendência de crescimento, sazonalidade forte nem relação entre "
        "avaliação, prazo e vendas, e o lucro informado não é igual a faturamento − custo na maioria das linhas. "
        "Os resultados mostram o método de análise; as conclusões de negócio devem ser validadas com dados reais.",
        icon="⚠️",
    )

def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    sb = st.sidebar
    sb.header("🔎 Filtros")
    anos = sorted(df["ano"].unique())
    sel_ano = sb.multiselect("Ano", anos, default=anos)
    sel_mes = sb.multiselect("Mês", list(MESES), default=list(MESES), format_func=lambda m: MESES[m])
    regioes = sorted(df["regiao"].unique())
    sel_reg = sb.multiselect("Região", regioes, default=regioes)
    ufs = sorted(df.loc[df["regiao"].isin(sel_reg), "uf"].unique())
    sel_uf = sb.multiselect("Estado", ufs, default=ufs)
    cats = sorted(df["categoria"].unique())
    sel_cat = sb.multiselect("Categoria", cats, default=cats)
    canais = sorted(df["canal_venda"].unique())
    sel_canal = sb.multiselect("Canal de venda", canais, default=canais)

    return df[
        df["ano"].isin(sel_ano) & df["mes"].isin(sel_mes) & df["regiao"].isin(sel_reg)
        & df["uf"].isin(sel_uf) & df["categoria"].isin(sel_cat) & df["canal_venda"].isin(sel_canal)
    ]


def main() -> None:
    st.sidebar.markdown("### 🛒 E-commerce Brasil")
    st.sidebar.caption("Projeto de Análise e Visualização de Dados com Python")

    arquivo = st.sidebar.file_uploader("📤 Enviar outro CSV (opcional)", type="csv",
                                       help="Deve ter as mesmas colunas da base original.")
    enviado = False
    try:
        if arquivo is not None:
            df_all = carregar_upload(arquivo.getvalue())
            enviado = True
            st.sidebar.success(f"Usando {arquivo.name}")
        else:
            df_all = carregar_base()
    except Exception as exc: 
        st.sidebar.error(f"Não foi possível ler o arquivo: {exc}")
        df_all = carregar_base()

    df = aplicar_filtros(df_all)
    st.sidebar.caption(f"{num(len(df))} de {num(len(df_all))} pedidos selecionados")

    paginas = [
        st.Page(pagina_visao_geral, title="Visão geral", icon="📊", url_path="visao-geral", default=True),
        st.Page(pagina_temporal, title="Temporal e sazonalidade", icon="📈", url_path="temporal"),
        st.Page(pagina_regioes, title="Regiões e mapa", icon="🗺️", url_path="regioes"),
        st.Page(pagina_categorias, title="Categorias e canais", icon="🏷️", url_path="categorias"),
        st.Page(pagina_lucro_logistica, title="Lucro, logística e avaliação", icon="💰", url_path="lucro-logistica"),
        st.Page(pagina_tabela, title="Tabela dinâmica", icon="🧮", url_path="tabela"),
        st.Page(pagina_sql, title="Consultas SQL", icon="🗄️", url_path="sql"),
        st.Page(pagina_conclusao, title="Conclusão executiva", icon="📌", url_path="conclusao"),
    ]
    pg = st.navigation(paginas)

    if df.empty:
        st.title("🛒 Vendas em E-commerce no Brasil")
        st.warning("Nenhum pedido corresponde aos filtros selecionados. Ajuste a barra lateral.")
        st.stop()

    CTX.update(df=df, df_all=df_all, enviado=enviado)
    pg.run()


main()
