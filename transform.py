import pandas as pd
import streamlit as st

def get_kpis(df):
    """Calcular KPIs principais: Entradas, Saídas, Saldo, Taxa de Poupança."""
    if df.empty:
        return 0, 0, 0, 0, 0
    
    entradas = df[df['Valor'] > 0]['Valor'].sum()
    saidas = df[df['Valor'] < 0]['Valor'].sum()
    saidas_abs = abs(saidas)
    saldo = entradas + saidas
    taxa_poupanca = (saldo / entradas * 100) if entradas > 0 else 0
    
    return entradas, saidas, saidas_abs, saldo, taxa_poupanca

def get_period_comparison(df, inicio_atual, fim_atual):
    """Calcula variação percentual em relação ao período anterior."""
    # Define periodo anterior (mesmo delta de dias, deslocado para trás)
    delta_days = (fim_atual - inicio_atual).days + 1
    fim_anterior = inicio_atual - pd.Timedelta(days=1)
    inicio_anterior = fim_anterior - pd.Timedelta(days=delta_days - 1)
    
    # Filtra dados anteriores
    df_anterior = df[(df['Data'].dt.date >= inicio_anterior) & (df['Data'].dt.date <= fim_anterior)]
    
    # Filtra dados atuais (para garantir consistência caso o df passado não esteja filtrado por data)
    df_atual = df[(df['Data'].dt.date >= inicio_atual) & (df['Data'].dt.date <= fim_atual)]
    
    # Totais
    saidas_atual = abs(df_atual[df_atual['Valor'] < 0]['Valor'].sum())
    saidas_anterior = abs(df_anterior[df_anterior['Valor'] < 0]['Valor'].sum())
    
    entradas_atual = df_atual[df_atual['Valor'] > 0]['Valor'].sum()
    entradas_anterior = df_anterior[df_anterior['Valor'] > 0]['Valor'].sum()
    
    # Deltas
    delta_saidas = ((saidas_atual - saidas_anterior) / saidas_anterior * 100) if saidas_anterior > 0 else 0
    delta_entradas = ((entradas_atual - entradas_anterior) / entradas_anterior * 100) if entradas_anterior > 0 else 0
    
    return delta_saidas, delta_entradas, inicio_anterior, fim_anterior

def filter_data(df, inicio, fim, bancos_selecionados=None, categorias_selecionadas=None):
    """Aplica filtros de data, categoria e bancos."""
    df_filtered = df[(df['Data'].dt.date >= inicio) & (df['Data'].dt.date <= fim)]
    
    # Filtro de Bancos (Prioridade)
    if bancos_selecionados:
        df_filtered = df_filtered[df_filtered['Banco'].isin(bancos_selecionados)]

    # Filtro de Categorias
    if categorias_selecionadas:
        df_filtered = df_filtered[df_filtered['Categoria'].isin(categorias_selecionadas)]
        
    return df_filtered

def get_monthly_flow(df):
    """Prepara dados para gráfico de fluxo mensal."""
    df = df.copy()
    df['Mes_Ano'] = df['Data'].dt.to_period('M').astype(str)
    df['Fluxo'] = df['Valor'].apply(lambda x: 'Entrada' if x >= 0 else 'Saída')
    
    monthly = df.groupby(['Mes_Ano', 'Fluxo'])['Valor'].sum().reset_index()
    monthly['Valor'] = monthly['Valor'].abs()
    return monthly

def get_categories_ranking(df):
    """Retorna dados de despesas por categoria rankeados (Visão Macro)."""
    expenses = df[df['Valor'] < 0].copy()
    expenses['Valor Abs'] = expenses['Valor'].abs()
    ranking = expenses.groupby('Categoria')['Valor Abs'].sum().sort_values(ascending=True)
    return ranking, expenses

def get_category_details(df, category):
    """Retorna detalhamento de uma categoria específica."""
    details = df[(df['Categoria'] == category) & (df['Valor'] < 0)].copy()
    details['Valor Abs'] = details['Valor'].abs()
    
    # Agrupa por descrição
    grouped = details.groupby('Descrição')['Valor Abs'].sum().reset_index().sort_values('Valor Abs', ascending=False)
    return grouped, details

def extract_pix_beneficiary(desc):
    """Extrai nome do beneficiário Pix da descrição."""
    desc = str(desc).lower()
    if 'pix' in desc and ('enviado' in desc or 'enviada' in desc):
        try:
            if 'enviada' in desc: parts = desc.split('enviada')
            else: parts = desc.split('enviado')
            
            if len(parts) > 1:
                # Pega a parte depois de "enviada..."
                raw_name = parts[1].lower().strip()
                
                # Remove prefixos comuns de sujeira
                for prefix in ['pelo pix -', 'via pix -', 'pelo pix', 'via pix', 'pix -', '- ']:
                    if raw_name.startswith(prefix):
                        raw_name = raw_name.replace(prefix, "").strip()
                
                # Formata Nome Próprio
                return raw_name.title()[:30] # Limita tamanho
        except: pass
    return "Outros"

def get_pix_metrics(df):
    """Calcula métricas e ranking de Pix."""
    df = df.copy()
    df['Beneficiario_Pix'] = df['Descrição'].apply(extract_pix_beneficiary)
    
    pix_only = df[(df['Beneficiario_Pix'] != "Outros") & (df['Valor'] < 0)].copy()
    pix_only['Valor Abs'] = pix_only['Valor'].abs()
    
    if pix_only.empty:
        return None, None, None, None, pd.DataFrame(), pd.DataFrame()

    total_pix = pix_only['Valor Abs'].sum()
    qtd_pix = len(pix_only)
    avg_pix = total_pix / qtd_pix
    max_pix = pix_only['Valor Abs'].max()
    
    pix_rank = pix_only.groupby('Beneficiario_Pix')['Valor Abs'].sum().sort_values(ascending=True).tail(10)
    
    return pix_only, total_pix, qtd_pix, avg_pix, max_pix, pix_rank

def detect_subscriptions(df):
    """Detecta possíveis assinaturas (Valores recorrentes). Normaliza nomes de serviços."""
    # Filtra saídas
    expenses = df[df['Valor'] < 0].copy()
    
    # --- Normalização de Apps (Refinamento) ---
    def normalize_service(desc):
        d_lower = str(desc).lower()
        if 'uber' in d_lower: return 'Uber'
        if '99' in d_lower and '99 ' in d_lower: return '99 App' # Evita '9.99'
        if 'ifood' in d_lower: return 'iFood'
        if 'rappi' in d_lower: return 'Rappi'
        if 'netflix' in d_lower: return 'Netflix'
        if 'spotify' in d_lower: return 'Spotify'
        if 'amazon' in d_lower or 'amzn' in d_lower: return 'Amazon'
        if 'apple' in d_lower: return 'Apple'
        if 'google' in d_lower: return 'Google'
        # Mantém original se não for app conhecido
        return desc

    # Cria coluna temporária normalizada
    expenses['Service_Norm'] = expenses['Descrição'].apply(normalize_service)
    
    # Agrupa por Serviço Normalizado e conta ocorrências
    counts = expenses['Service_Norm'].value_counts()
    potential_subs = counts[counts >= 2].index
    
    subs_data = []
    
    for service_name in potential_subs:
        # Pega transações desse serviço
        dfo = expenses[expenses['Service_Norm'] == service_name].sort_values('Data')
        
        # O desvio padrão do valor para iFood/Uber é ALTO (valores variam), mas a FREQUÊNCIA é alta.
        # Para serviços fixos (Netflix), desvio é baixo.
        
        # Média de dias entre transações
        dfo['Delta'] = dfo['Data'].diff().dt.days
        avg_days = dfo['Delta'].mean()
        
        freq = "Recorrente"
        is_subscription = False
        
        # Lógica Híbrida:
        # 1. Valor Fixo (Assinatura Real: Netflix, Spotify)
        std_val = dfo['Valor'].std()
        if (pd.isna(std_val) or std_val < 5.0) and (25 <= avg_days <= 35):
            freq = "Mensal (Fixo)"
            is_subscription = True
            
        # 2. Uso Frequente (iFood, Uber) - Valores variam, mas uso é constante
        elif service_name in ['Uber', 'iFood', '99 App', 'Rappi'] and (avg_days <= 10):
            freq = "Uso Frequente"
            is_subscription = True
            
        # 3. Pix recorrente (Para pessoas)
        elif 25 <= avg_days <= 35:
            # Se for mensal e não for app variante, pode ser aluguel/faxina
            freq = "Mensal (Variável)"
            is_subscription = True

        if is_subscription:
            last_date = dfo['Data'].max()
            avg_val = dfo['Valor'].mean()
            total_val = dfo['Valor'].sum()
            
            subs_data.append({
                'Serviço': service_name if len(service_name) < 20 else service_name[:20] + '...',
                'Valor Médio': avg_val,
                'Frequência': freq,
                'Último Pagto': last_date
            })
            
    return pd.DataFrame(subs_data)

def get_categories_list(df):
    """Retorna lista única de categorias ordenadas para o selectbox."""
    if df.empty or 'Categoria' not in df.columns:
        return ["Outros", "Alimentação", "Transporte", "Lazer", "Farmácia", "Conveniência"] # Fallback
    
    cats = sorted(df['Categoria'].dropna().unique().tolist())
    # Garante que as principais estejam presentes caso não tenha dados
    defaults = ["Outros", "Alimentação", "Transporte", "Lazer", "Farmácia", "Conveniência"]
    for d in defaults:
        if d not in cats:
            cats.append(d)
            
    return sorted(list(set(cats)))
