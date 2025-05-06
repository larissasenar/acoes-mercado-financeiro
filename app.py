import os
import requests
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, time
import streamlit as st
from supabase import create_client, Client
from auth import verificar_login, cadastrar_usuario
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid
import plotly.express as px
import numpy as np
import yfinance as yf  # Importar a biblioteca yfinance

# Carregar a chave da API da Alpha Vantage do arquivo .env
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Configuração do Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(url, key)

# Função para buscar dados da Alpha Vantage OU do yfinance
def obter_cotacao_acao(symbol, start_date, end_date, use_yfinance=False):
    start_date = datetime.combine(start_date, time.min)
    end_date = datetime.combine(end_date, time.max)

    if use_yfinance:
        try:
            data = yf.download(symbol, start=start_date, end=end_date)
            if data is not None and not data.empty:
                df = data[['Close']].copy()
                df.index.name = "Date"
                print(f"yfinance retornou para {symbol}:\n{df.head()}")
                return df
            else:
                st.warning(f"Não foi possível obter dados com yfinance para {symbol} no período selecionado.")
                return None
        except Exception as e:
            st.error(f"Erro ao obter dados com yfinance para {symbol}: {e}")
            return None
    else:
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
                if data:  # Garante que há dados antes de criar o DataFrame
                    df = pd.DataFrame(data, columns=["Date", "Close"])
                    df.set_index("Date", inplace=True)
                    print(f"Alpha Vantage retornou para {symbol}:\n{df.head()}")
                    return df
                else:
                    st.warning(f"Alpha Vantage não retornou dados para {symbol} no período selecionado.")
                    return None
            else:
                st.warning(f"Falha ao obter dados da Alpha Vantage para {symbol}. Código de status: {response.status_code}")
                return None
        return None # Garante que None seja retornado explicitamente em caso de falha


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

    # Chamada para tentar cadastrar
    if st.button("Cadastrar", type="primary"):
        if not novo_usuario or not nova_senha:
            st.warning("Preencha todos os campos.")
        elif verificar_usuario_existe(novo_usuario):
            st.error("Usuário já existe. Escolha outro nome.")
        elif cadastrar_usuario(novo_usuario, nova_senha):
            st.success("Usuário cadastrado com sucesso! Faça login.")
        else:
            st.error("Erro ao cadastrar o usuário. Verifique se a política RLS permite a inserção.")

# Função para verificar se o usuário existe
def verificar_usuario_existe(usuario):
    try:
        response = supabase.table('usuarios').select('usuario').eq('usuario', usuario).execute()
        dados = response.data or []
        return len(dados) > 0
    except Exception as e:
        st.error(f"Erro ao verificar usuário: {e}")
        return False

# Função para construir a barra lateral (otimizada)
def build_sidebar():
    st.markdown("<h2 style='font-size: 20px;'>📊 Análise de Investimentos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 14px;'>Selecione ações, defina um período e visualize o desempenho da sua carteira personalizada.</p>", unsafe_allow_html=True)

    df = pd.read_csv("tickers_ibra_corrigido.csv")
    df["label"] = df["empresa"] + " (" + df["ticker"] + ")"
    selected_labels = st.multiselect("Selecione as Empresas", options=df["label"], placeholder="Códigos")
    selected_tickers = [label.split("(")[-1].replace(")", "") for label in selected_labels]
    tickers = [t + ".SA" for t in selected_tickers]

    start_date = st.date_input("De", format="DD/MM/YYYY", value=datetime(2023, 1, 2))
    end_date = st.date_input("Até", format="DD/MM/YYYY", value=datetime.today())

    use_yfinance = st.checkbox("Usar yfinance para dados (pode ser mais rápido)", value=False)

    if start_date > end_date:
        st.error("Data inicial não pode ser maior que a data final.")
        return tickers, start_date, end_date, use_yfinance

    return tickers, start_date, end_date, use_yfinance

# Função para construir a área principal (otimizada)
def build_main(tickers, start_date, end_date, use_yfinance):
    if not tickers:
        st.info("Bem-vindo ao app de análise de carteira de ações! Utilize a barra lateral para navegar e realizar análises personalizadas.")
        return

    st.markdown("<h2 style='font-size: 1.5em;'>📈 Desempenho da Carteira Selecionada</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1em;'>Visualize o desempenho da sua carteira de ações ao longo do tempo e compare com o risco e retorno de cada ativo.</p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.9em; color: gray;'>*Ajuste os pesos na barra lateral para simular diferentes alocações de capital.*</p>", unsafe_allow_html=True)

    prices = {}
    all_dates = pd.Series(pd.date_range(start=start_date, end=end_date)) # Cria uma série com todas as datas possíveis
    for ticker in tickers:
        df_prices_temp = obter_cotacao_acao(ticker, start_date, end_date, use_yfinance)
        if df_prices_temp is not None and not df_prices_temp.empty:
            # Reindexa o DataFrame temporário para incluir todas as datas do período
            df_prices_temp = df_prices_temp.reindex(all_dates.dt.date)
            prices[ticker.replace(".SA", "")] = df_prices_temp
            print(f"Dados carregados para {ticker.replace('.SA', '')}:\n{df_prices_temp.head()}")
        else:
            st.warning(f"Não foi possível carregar dados válidos para {ticker}")

    if not prices:
        st.warning("Nenhum dado de preço válido foi carregado para as ações selecionadas.")
        return

    valid_prices = {ticker: df.dropna() for ticker, df in prices.items() if isinstance(df, pd.DataFrame) and not df.empty and 'Close' in df.columns and df.index.name == None} # Ajuste na condição do índice

    if not valid_prices:
        st.error("Erro: Nenhum dado de preço válido encontrado após a verificação.")
        return

    try:
        df_prices = pd.DataFrame({ticker: df['Close'] for ticker, df in valid_prices.items()})
        tickers_limpos = list(valid_prices.keys())

        # Verificar se as colunas esperadas existem no DataFrame
        colunas_esperadas = tickers_limpos
        colunas_presentes = df_prices.columns.tolist()

        for ticker_limpo in colunas_esperadas:
            if ticker_limpo not in colunas_presentes:
                st.error(f"Erro: Dados para a ação {ticker_limpo} não foram encontrados no DataFrame final.")
                return
    except ValueError as e:
        st.error(f"Erro ao criar DataFrame de preços: {e}")
        return

    st.markdown("<h3 style='font-size: 1.5em;'>🧮 Pesos Personalizados</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1em;'>Defina a alocação de capital desejada para cada ação selecionada. Os pesos são normalizados para somar 100%.</p>", unsafe_allow_html=True)

    weights = {}
    total_weight = 0
    cols = st.columns(len(tickers_limpos)) # Usar tickers_limpos aqui
    for i, ticker_limpo in enumerate(tickers_limpos):
        with cols[i]:
            st.markdown(f"<span style='font-size: 1.1em;'>Peso de {ticker_limpo}</span>", unsafe_allow_html=True)
            w = st.slider(f"_", 0.0, 1.0, value=1.0/len(tickers_limpos), step=0.01, key=f"slider_{ticker_limpo}")
            weights[ticker_limpo] = w
            total_weight += w

    weights_array = np.array([weights[t] for t in tickers_limpos])
    if total_weight > 0:
        weights_array /= total_weight
    else:
        st.warning("A soma dos pesos é zero. Ajuste os pesos.")
        return

    carteira = (df_prices[tickers_limpos] * weights_array).sum(axis=1)
    df_prices["portfolio"] = carteira

    norm_prices = 100 * df_prices / df_prices.iloc[0]
    returns = df_prices.pct_change().dropna()
    vols_acoes = returns[tickers_limpos].std() * np.sqrt(252)
    vols_carteira = returns['portfolio'].std() * np.sqrt(252) if 'portfolio' in returns.columns else None
    rets = (norm_prices["portfolio"].iloc[-1] - 100) / 100 if "portfolio" in norm_prices.columns else None

    rets_final = returns[tickers_limpos].iloc[-1] if not returns.empty else pd.Series([0] * len(tickers_limpos), index=df_prices.index if not df_prices.empty else None) # Usar índice de df_prices

    # Criar DataFrame para o gráfico de risco-retorno
    risk_return_df = pd.DataFrame({'Volatilidade': vols_acoes, 'Retorno': rets_final})
    risk_return_df.index.name = 'Ticker'
    risk_return_df = risk_return_df.reset_index()
    # Correção: Garante que 'Retorno' e 'Volatilidade' sejam numéricos antes da divisão
    if not risk_return_df['Volatilidade'].empty and not risk_return_df['Retorno'].empty:
        risk_return_df['Sharpe'] = pd.to_numeric(risk_return_df['Retorno'], errors='coerce') / pd.to_numeric(risk_return_df['Volatilidade'], errors='coerce')
    else:
        risk_return_df['Sharpe'] = np.nan

    # Métricas Destacadas
    st.markdown("<h3 style='font-size: 1.5em;'>📊 Desempenho da Carteira (Período Selecionado)</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1em;'>Métricas chave de desempenho da carteira com os pesos definidos.</p>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<span style='font-size: 1.1em;'>Retorno Total</span>", unsafe_allow_html=True)
        st.metric("", f"{rets * 100:.2f}%" if rets is not None else "N/A")
    with col2:
        st.markdown(f"<span style='font-size: 1.1em;'>Volatilidade Anualizada</span>", unsafe_allow_html=True)
        st.metric("", f"{vols_carteira * 100:.2f}%" if vols_carteira is not None else "N/A")

    # Gráfico de Desempenho Relativo
    st.markdown("<h3 style='font-size: 1.5em;'>📈 Desempenho Relativo das Ações e da Carteira</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1em;'>Gráfico comparando o desempenho das ações selecionadas e da carteira ao longo do tempo, normalizado para um ponto inicial de 100.</p>", unsafe_allow_html=True)
    st.line_chart(norm_prices, height=500)

    # Gráfico de Risco-Retorno
    st.markdown("<h3 style='font-size: 1.6em;'>📉 Risco vs. Retorno</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1em;'>Scatter plot mostrando a relação entre o risco (volatilidade anualizada) e o retorno (retorno diário) de cada ação. A cor dos pontos representa o Índice de Sharpe (retorno/risco).</p>", unsafe_allow_html=True)
    fig_risk_return = px.scatter(
        risk_return_df,
        x="Volatilidade",
        y="Retorno",
        text="Ticker",
        color="Sharpe",
        color_continuous_scale=px.colors.sequential.Bluered_r,
    )
    fig_risk_return.update_traces(textfont_color="white", marker=dict(size=20), textfont_size=10)
    fig_risk_return.update_layout(
        height=500,
        xaxis_title="Volatilidade Anualizada",
        yaxis_title="Retorno Diário",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".2%",
        coloraxis_colorbar_title="Sharpe",
    )
    st.plotly_chart(fig_risk_return, use_container_width=True)

    # Tabela de Pesos
    st.markdown("<h3 style='font-size: 1.5em;'>⚖️ Pesos da Carteira</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1em;'>Tabela mostrando o peso atribuído a cada ação na carteira.</p>", unsafe_allow_html=True)
    weights_df = pd.DataFrame(weights, index=["Peso"]).T
    st.dataframe(weights_df)


# Função Principal
if "logado" not in st.session_state:
    st.session_state.logado = False

aba = st.sidebar.radio("Navegação", ["Login", "Cadastro"])

if not st.session_state.logado:
    if aba == "Login":
        tela_login()
    else:
        tela_cadastro()
    st.stop()

# Executa App
with st.sidebar:
    tickers, start_date, end_date, use_yfinance = build_sidebar()

st.title("📊 Análise de Carteira de Ações")
build_main(tickers, start_date, end_date, use_yfinance)