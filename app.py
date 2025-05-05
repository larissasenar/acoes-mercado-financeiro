import os
import requests
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, time
import streamlit as st
from auth import verificar_login, cadastrar_usuario
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid
import plotly.express as px
import numpy as np

# Carregar a chave da API da Alpha Vantage do arquivo .env
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Função para buscar dados da Alpha Vantage
def obter_cotacao_acao(symbol, start_date, end_date):
    start_date = datetime.combine(start_date, time.min)
    end_date = datetime.combine(end_date, time.max)

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        dados = response.json()
        if "Time Series (Daily)" in dados:
            time_series = dados["Time Series (Daily)"]
            data = []
            for date_str, values in time_series.items():
                date = datetime.strptime(date_str, "%Y-%m-%d")
                if start_date <= date <= end_date:
                    data.append([date, float(values["4. close"])])
            df = pd.DataFrame(data, columns=["Date", "Close"])
            df.set_index("Date", inplace=True)
            return df
    return None


# Função de login
def tela_login():
    st.title("🔐 Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if verificar_login(usuario, senha):
            st.success("Login realizado com sucesso!")
            st.session_state.logado = True
            st.session_state.usuario = usuario
        else:
            st.error("Usuário ou senha incorretos.")

# Função de cadastro
def tela_cadastro():
    st.title("📝 Cadastro de Novo Usuário")
    novo_usuario = st.text_input("Novo Usuário")
    nova_senha = st.text_input("Nova Senha", type="password")
    if st.button("Cadastrar"):
        if cadastrar_usuario(novo_usuario, nova_senha):
            st.success("Usuário cadastrado! Faça login.")
        else:
            st.error("Usuário já existe.")

# Função para configurar a barra lateral
def build_sidebar():
    st.markdown("# 📈 Projeto em Python para Investidores")

    df = pd.read_csv("tickers_ibra_corrigido.csv")
    df["label"] = df["empresa"] + " (" + df["ticker"] + ")"
    selected_labels = st.multiselect("Selecione as Empresas", options=df["label"], placeholder="Códigos")

    selected_tickers = [label.split("(")[-1].replace(")", "") for label in selected_labels]
    tickers = [t + ".SA" for t in selected_tickers]

    start_date = st.date_input("De", format="DD/MM/YYYY", value=datetime(2023, 1, 2))
    end_date = st.date_input("Até", format="DD/MM/YYYY", value=datetime.today())

    if start_date > end_date:
        st.error("Data inicial não pode ser maior que a data final.")
        return None, None

    if tickers:
        prices = {}
        for ticker in tickers:
            df_prices = obter_cotacao_acao(ticker, start_date, end_date)
            if df_prices is not None:
                prices[ticker.replace(".SA", "")] = df_prices["Close"]
            else:
                st.warning(f"Não foi possível carregar os dados para {ticker}")

        if prices:
            df_prices = pd.DataFrame(prices)
            return selected_tickers, df_prices

    return None, None

# Função para exibir os dados principais
def build_main(tickers, prices):
    st.header("🧮 Pesos Personalizados")

    weights = {}
    total_weight = 0

    for ticker in tickers:
        w = st.slider(f"Peso de {ticker}", 0.0, 1.0, value=1.0/len(tickers), step=0.01)
        weights[ticker] = w
        total_weight += w

    weights_array = np.array([weights[t] for t in tickers])
    if total_weight > 0:
        weights_array /= total_weight

    carteira = prices[tickers] @ weights_array
    prices["portfolio"] = carteira

    norm_prices = 100 * prices / prices.iloc[0]
    returns = prices.pct_change().dropna()
    vols = returns.std() * np.sqrt(252)
    rets = (norm_prices.iloc[-1] - 100) / 100

    st.subheader("📈 Desempenho Relativo")
    st.line_chart(norm_prices, height=600)

    st.subheader("📉 Risco-Retorno")
    fig = px.scatter(
        x=vols,
        y=rets,
        text=vols.index,
        color=rets / vols,
        color_continuous_scale=px.colors.sequential.Bluered_r,
    )
    fig.update_traces(textfont_color="white", marker=dict(size=45), textfont_size=10)
    fig.update_layout(
        height=600,
        xaxis_title="Volatilidade (anualizada)",
        yaxis_title="Retorno Total",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
        coloraxis_colorbar_title="Sharpe",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Tabela de Retornos Acumulados")
    tabela = pd.DataFrame({
        "Retorno (%)": (norm_prices.iloc[-1] / norm_prices.iloc[0] - 1) * 100
    }).round(2)
    st.dataframe(tabela)

# Função principal que executa o app
if "logado" not in st.session_state:
    st.session_state.logado = False

aba = st.sidebar.radio("Navegação", ["Login", "Cadastro"])

if not st.session_state.logado:
    if aba == "Login":
        tela_login()
    else:
        tela_cadastro()
    st.stop()  # Não seja carregado sem login

# Executa o app principal
with st.sidebar:
    tickers, prices = build_sidebar()

st.title("📊 Python para Investidores")
if tickers and prices is not None:
    build_main(tickers, prices)
else:
    st.info("Use a barra lateral para selecionar as ações.")
