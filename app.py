import streamlit as st
import pandas as pd
from datetime import datetime

# Imporar Módulos Locais
from load_data import load_data
import transform
import views
import ai_consultant
import rules_manager
import auth
import time

# Configuração da Página
st.set_page_config(
    page_title="Dashboard de Análise de Consumo",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)
# -----------------------------------------------------------------------------
# 1. THEME MANAGER & CSS
# -----------------------------------------------------------------------------
def get_theme_css(theme_name):
    # Paletas de Cores
    themes = {
        "Cyberpunk (Padrão)":   {"primary": "#bf00ff", "bg": "#0e1117", "card": "#1c1f26", "text": "#ffffff"},
        "Nubank (Roxo)":        {"primary": "#820ad1", "bg": "#2e034e", "card": "#481c6e", "text": "#ffffff"},
        "Mercado Pago (Azul)":  {"primary": "#009ee3", "bg": "#00253b", "card": "#00446e", "text": "#ffffff"},
        "Santander (Vermelho)": {"primary": "#ec0000", "bg": "#2b0000", "card": "#4a0000", "text": "#ffffff"},
        "Inter (Laranja)":      {"primary": "#ff7a00", "bg": "#1a0d00", "card": "#331a00", "text": "#ffffff"},
        "Itaú (Laranja/Azul)":  {"primary": "#ff6200", "bg": "#001833", "card": "#002855", "text": "#ffffff"},
        "Bradesco (Vermelho)":  {"primary": "#cc092f", "bg": "#1f0007", "card": "#3d000e", "text": "#ffffff"},
    }
    
    # Fallback
    c = themes.get(theme_name, themes["Cyberpunk (Padrão)"])
    
    return f"""
    <style>
    :root {{
    /* Full App Background */
    .stApp {{
        background-color: {c['bg']};
        color: {c['text']};
    }}
    
    /* Metrics Cards */
    div[data-testid="stMetric"] {{
        background-color: {c['card']};
        border-left: 5px solid {c['primary']};
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    
    /* Buttons */
    div.stButton > button {{
        background-color: {c['primary']};
        border: none;
        color: white !important;
        box-shadow: 0 0 10px {c['primary']}4D;
    }}
    
    /* APLICA AS VARIÁVEIS (Igual ao CSS anterior, mas dinâmico) */
    html, body, [class*="css"] {{
        background-color: var(--background);
        color: var(--text);
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}

    div[data-testid="stMetric"] {{
        background-color: var(--card-bg) !important;
        border: 1px solid rgba(255,255,255,0.1);
        border-left: 5px solid var(--primary) !important;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        color: white !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    div[data-testid="stMetric"]:hover {{
        transform: translateY(-5px);
        box-shadow: 0 0 15px {c['primary']}66; /* Hex alpha 40% */
    }}

    div[data-testid="stMetric"] label {{ color: #e0e0e0 !important; font-size: 0.9rem; }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{ color: #fff !important; font-weight: 700; font-size: 1.8rem; }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--primary) !important;
        border-color: var(--primary) !important;
        background-color: {c['primary']}1A; /* 10% opacity */
    }}

    button[kind="primary"] {{
        background-color: var(--primary) !important;
        border: none;
        color: white !important;
        box-shadow: 0 0 10px {c['primary']}4D;
    }}
    
    section[data-testid="stSidebar"] {{
        background-color: {c['primary']}10; /* Tinted Background (10% opacity) */
        border-right: 1px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(10px); /* Modern Glass Effect */
    }}
    
    /* Clean Expanders in Sidebar */
    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        background-color: transparent;
        border: none;
    }}
    
    div[data-testid="stDataFrame"] {{
        border: 1px solid #333;
        border-radius: 10px;
    }}
    
    /* --- MOBILE OPTIMIZATION (PWA Feel) --- */
    @media only screen and (max-width: 768px) {{
        /* Gain vertical space */
        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }}
        
        /* Typography adjustments */
        h1 {{ font-size: 1.8rem !important; }}
        h3 {{ font-size: 1.2rem !important; }}
        
        /* Valid for Streamlit Metrics */
        div[data-testid="stMetric"] {{
            padding: 10px !important;
        }}
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
            font-size: 1.4rem !important;
        }}
        
        /* Make tabs scrollable/better touch */
        div[data-baseweb="tab-list"] {{
            gap: 10px;
            overflow-x: auto;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch;
        }}
        button[data-baseweb="tab"] {{
            padding: 10px 15px !important;
            white-space: nowrap;
            font-size: 0.9rem !important;
        }}
    }}
    </style>
    """

# -----------------------------------------------------------------------------
# AUTHENTICATION & SESSION
# -----------------------------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

# Apply theme early for consistent look
if 'selected_theme' not in st.session_state:
    st.session_state.selected_theme = "Cyberpunk (Padrão)"
st.markdown(get_theme_css(st.session_state.selected_theme), unsafe_allow_html=True)

# LOGIN FLOW
# Verifica se está logado via Google ou via Sistema Próprio (Legacy)
if not st.session_state.get('logged_in', False):
    # Tenta recuperar login do Google (se configurado)
    try:
        if st.user.get("is_logged_in"):
            email = st.user.get("email")
            # Garante que a pasta do usuário existe (primeiro acesso Google)
            auth.init_user_env(email)
            st.session_state['logged_in'] = True
            st.session_state['username'] = email
            st.rerun()
    except:
        pass # Streamlit < 1.42 ou erro na config

    # Hero Section Layout
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("## 🚀 Domine suas Finanças")
        st.markdown("""
        **O painel financeiro definitivo.**
        
        ✅ **Consolidação Automática**: Todos seus bancos num só lugar.
        🧠 **Inteligência Artificial**: Consultor pessoal 24/7.
        🔒 **100% Privado**: Dados isolados e seguros.
        """)
        st.image("https://cdn-icons-png.flaticon.com/512/2641/2641409.png", width=300)

    with col2:
        st.markdown("### 🔐 Acesso ao Painel")
        with st.container(border=True):
            st.markdown("#### Entrar com Google")
            
            # Botão Nativo do Streamlit (Requer v1.42+)
            if st.button("🌐 Fazer Login com Google", type="primary", use_container_width=True):
                st.login("google")
            
            st.divider()
            
            # Fallback: Login Manual (Antigo)
            with st.expander("Ou entre com Usuário/Senha"):
                tab_login, tab_register = st.tabs(["Entrar", "Criar"])
                with tab_login:
                    username = st.text_input("Usuário", key="login_user")
                    password = st.text_input("Senha", type="password", key="login_pass")
                    if st.button("Entrar", key="btn_login"):
                        if auth.authenticate(username, password):
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = username
                            st.rerun()
                        else:
                            st.error("Erro no login.")
                
                with tab_register:
                    new_user = st.text_input("Novo User", key="reg_user")
                    new_pass = st.text_input("Nova Senha", type="password", key="reg_pass")
                    if st.button("Cadastrar", key="btn_reg"):
                        success, msg = auth.register_user(new_user, new_pass)
                        if success: st.success(msg)
                        else: st.error(msg)

    st.stop()

# =============================================================================
# MAIN APP (LOGGED IN)
# =============================================================================

# -----------------------------------------------------------------------------
# 1. SIDEBAR & DATA LOADING (Controller)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2910/2910311.png", width=60)
    
    # User Profile & Logout
    st.markdown(f"#### 👤 Olá, {st.session_state['username']}")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.rerun()
    st.divider()

    st.title("Painel")
    
    # SELETOR DE TEMA
    current_index = 0
    theme_options = ["Cyberpunk (Padrão)", "Nubank (Roxo)", "Mercado Pago (Azul)", "Santander (Vermelho)", "Inter (Laranja)", "Itaú (Laranja/Azul)", "Bradesco (Vermelho)"]
    if 'selected_theme' in st.session_state:
        try:
            current_index = theme_options.index(st.session_state.selected_theme)
        except: pass
        
    selected_theme = st.selectbox("Tema", theme_options, index=current_index, label_visibility="collapsed")
    st.session_state.selected_theme = selected_theme
    
    st.divider()

    # --- UPLOAD ---
    st.caption("📂 **ARQUIVOS**")
    uploaded_files = st.file_uploader(
        "Carregar Extratos", 
        type=['csv', 'xlsx'],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Suporta: Nubank, Mercado Pago, Bradesco, Itaú, Inter e XLS genérico."
    )
    
    if uploaded_files:
        # DATA ISOLATION: Pass username to enforce rules and void fake data
        df = load_data(uploaded_files, username=st.session_state['username'])
        # Resumo Mínimalista
        if not df.empty and 'Banco' in df.columns:
            df['Mes_Ref'] = df['Data'].dt.to_period('M')
            summary = df.groupby(['Banco', 'Mes_Ref']).size().reset_index()
            with st.expander("📋 Arquivos Carregados", expanded=False):
                for _, row in summary.iterrows():
                    st.caption(f"✅ {row['Banco']} • {row['Mes_Ref'].strftime('%m/%Y')}")
    else:
        # DATA ISOLATION: Pass username (will return empty if user exists)
        df = load_data(None, username=st.session_state['username'])
    
    if df.empty:
        st.warning("Nenhum dado carregado. Faça upload dos seus extratos.")
        df = pd.DataFrame(columns=['Data', 'Descrição', 'Categoria', 'Valor', 'Banco'])

    st.divider()

    # --- FILTROS ---
    if not df.empty:
        with st.expander("🔍 **Filtros**", expanded=True):
            # Filtro de Data
            min_date = df['Data'].min().date()
            max_date = df['Data'].max().date()
            
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Início", min_date, format="DD/MM/YYYY")
            end_date = col2.date_input("Fim", max_date, format="DD/MM/YYYY")

            # Filtro de Banco
            if 'Banco' in df.columns:
                all_banks = sorted(df['Banco'].unique().tolist())
                selected_banks = st.multiselect("Bancos", all_banks, default=all_banks, placeholder="Todos")
            else:
                selected_banks = []
            
            # Filtro de Categoria
            all_cats = transform.get_categories_list(df)
            selected_cats = st.multiselect("Categorias", all_cats, default=all_cats, placeholder="Todas")

        # --- METAS ---
        with st.expander("🎯 **Metas**", expanded=False):
            meta_gastos = st.number_input("Teto Mensal (R$)", min_value=0.0, value=5000.0, step=100.0)

        # Aplica Filtros
        df_filtered = transform.filter_data(df, start_date, end_date, selected_banks, selected_cats)
    else:
        df_filtered = pd.DataFrame()
        start_date, end_date = datetime.today(), datetime.today()
        meta_gastos = 5000.0

if df.empty:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
            st.markdown("## 📂 Comece sua Análise")
            # Ícone 3D Colorido para destaque no modo dark
            st.image("https://cdn-icons-png.flaticon.com/512/7486/7486744.png", width=120)
            st.markdown("### Nenhum dado carregado.")
            st.markdown("#### Siga os passos abaixo:")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("""
            1. 🏦 **Exporte o extrato** do seu banco (CSV/Excel).
            2. 📂 **Arraste o arquivo** para a barra lateral esquerda.
            3. 📊 **Analise** seus gastos com IA automática.
            """)
            
            st.info("💡 **Dica:** O sistema aceita múltiplos arquivos de bancos diferentes!")
    st.stop()

# -----------------------------------------------------------------------------
# 3. TRANSFORM (Business Logic)
# -----------------------------------------------------------------------------
# (Data filtered in Sidebar above)


# Calcula KPIs
entradas, saidas, saidas_abs, saldo, taxa_poupanca = transform.get_kpis(df_filtered)

# Calcula Comparativo (Mês/Período Anterior)
delta_saidas, delta_entradas, _, _ = transform.get_period_comparison(df, start_date, end_date)

# Detecta Assinaturas
subs_df = transform.detect_subscriptions(df)

# Prepara dados para gráficos
monthly_data = transform.get_monthly_flow(df_filtered)
cat_ranking, expenses_df = transform.get_categories_ranking(df_filtered)
pix_only, total_pix, qtd_pix, avg_pix, max_pix, pix_rank = transform.get_pix_metrics(df_filtered)

# -----------------------------------------------------------------------------
# 4. VIEW (Presentation)
# -----------------------------------------------------------------------------
st.title("Dashboard Financeiro")
st.caption(f"Visão geral de **{start_date.strftime('%d/%m/%Y')}** até **{end_date.strftime('%d/%m/%Y')}**")

# Renderiza Header (KPIs removidos daqui e movidos para Visão Geral)
# col1, col2, col3, col4 = st.columns(4)
# ... (Código antigo removido para limpar interface) ...

st.markdown("---")

# Abas de navegação
tab_overview, tab_categories, tab_pix, tab_subs, tab_ai, tab_teach, tab_data = st.tabs(["📅 Visão Geral", "📊 Categorias", "💠 Pix", "🔄 Assinaturas", "🧠 Consultor IA", "🎓 Ensinar IA", "📝 Extrato"])

with tab_overview:
    # Empacota dados para a view
    kpi_data = (entradas, saidas, saidas_abs, saldo, taxa_poupanca, delta_entradas, delta_saidas, meta_gastos)
    views.render_overview_tab(monthly_data, df_filtered, kpi_data)

with tab_categories:
    views.render_categories_tab(cat_ranking, expenses_df)
    
with tab_pix:
    views.render_pix_tab(pix_only, pix_rank, total_pix, qtd_pix, avg_pix, max_pix)

with tab_subs:
    if not subs_df.empty:
        st.info("🤖 **IA Scanner:** Identifiquei estes possíveis pagamentos recorrentes (Assinaturas/Fixos).")
        st.dataframe(
            subs_df.style.format({'Valor Médio': 'R$ {:,.2f}', 'Último Pagto': '{:%d/%m/%Y}'}),
            use_container_width=True
        )
        st.metric("Estimativa Custo Fixo Mensal", f"R$ {subs_df['Valor Médio'].abs().sum():,.2f}")
    else:
        st.info("Nenhuma assinatura recorrente detectada com clareza ainda.")

with tab_ai:
    st.markdown("### 🧠 Consultor Financeiro IA")
    st.write("Receba uma análise completa dos seus gastos com base nos dados filtrados.")
    
    # Input da Chave (Removido - Uso Global)
    # api_key = st.text_input("Insira sua Google Gemini API Key:", type="password", help="Pegue sua chave no Google AI Studio.")
    
    if st.button("Gerar Análise Financeira", type="primary"):
        with st.spinner("🤖 O Consultor IA está analisando seus dados..."):
            # Chama sem passar chave (usa a global hardcoded)
            analysis = ai_consultant.analyze_finances(df_filtered)
            st.markdown(analysis)

with tab_teach:
    st.markdown("### 🎓 Ensinar o Robô")
    st.write("Ensine ao sistema que 'Padaria do Zé' é 'Alimentação' e ele nunca mais errará.")
    st.info(f"As regras são salvas apenas para o usuário: **{st.session_state['username']}**")
    
    col_input, col_view = st.columns([1, 1])
    
    with col_input:
        st.markdown("#### Nova Regra")
        new_keyword = st.text_input("Se a descrição contiver o texto:", placeholder="Ex: padaria x")
        new_category = st.selectbox("Classificar automaticamente como:", transform.get_categories_list(df))
        
        if st.button("Salvar Regra", type="primary"):
            if len(new_keyword) < 3:
                st.error("Texto muito curto para ser uma regra.")
            else:
                success, msg = rules_manager.save_rule(new_keyword, new_category, username=st.session_state['username'])
                if success:
                    st.success(msg)
                    st.cache_data.clear() # Limpa cache para reler com novas regras
                else:
                    st.error(msg)

    with col_view:
        st.markdown("#### Regras Ativas")
        current_rules = rules_manager.load_rules(username=st.session_state['username'])
        if current_rules:
            # Converte para DF para mostrar bonito
            rules_df = pd.DataFrame(list(current_rules.items()), columns=['Texto (Contém)', 'Categoria Destino'])
            st.dataframe(rules_df, use_container_width=True, hide_index=True)
            
            # Opção de Deletar
            st.markdown("---")
            del_key = st.selectbox("Selecione para excluir:", [""] + list(current_rules.keys()))
            if del_key and st.button("🗑️ Excluir Regra"):
                success, msg = rules_manager.delete_rule(del_key, username=st.session_state['username'])
                if success:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.info("Nenhuma regra personalizada criada ainda.")

with tab_data:
    views.render_extract_tab(df_filtered)
