import streamlit as st
import pandas as pd
import unicodedata
import numpy as np
from datetime import datetime
import rules_manager

def categorize(desc, custom_rules=None):
    """
    Função auxiliar para categorizar transações com base na descrição.
    Agora aceita custom_rules: dict (keyword -> category) carregados do JSON.
    """
    # Remove acentos e deixa minúsculo
    desc_clean = str(desc).lower()
    desc_clean = unicodedata.normalize('NFKD', desc_clean).encode('ASCII', 'ignore').decode('utf-8')
    
    # 0. REGRAS PERSONALIZADAS (Prioridade Máxima - Teach Mode)
    if custom_rules:
        for keyword, category in custom_rules.items():
            # A chave do JSON já deve estar minúscula, mas garantindo
            if keyword.lower() in desc_clean:
                return category
    
    # ... Lógica Normal (Codificada)
    desc = desc_clean

    # REGRAS ESPECÍFICAS (Hardcoded por solicitação)
    # Transferências para Banco Bradesco -> Pagamento de Fatura
    if 'bradesco' in desc and ('transferencia' in desc or 'pix enviado' in desc or 'ted' in desc or 'doc' in desc):
         return 'Pagamento de Fatura'
    
    # Conveniência (Novo - Antes de Alimentação para pegar itens específicos)
    if any(x in desc for x in ['conveniencia', 'condoveniencia', 'am pm', 'am/pm', 'select', '7 eleven', '7-eleven', 'loja de conveniencia']): return 'Conveniência'

    if any(x in desc for x in ['uber', '99', 'posto', 'combustivel', 'ipva', 'estacionamento', 'sem parar', 'veloe']): return 'Transporte'
    if any(x in desc for x in ['ifood', 'restaurante', 'mercado', 'market', 'padaria', 'mc donalds', 'burguer', 'sodiê', 'café', 'starbucks', 'pão de açúcar', 'carrefour', 'walmart', 'san club', 'atacadão']): return 'Alimentação'
    if any(x in desc for x in ['netflix', 'spotify', 'amazon', 'prime', 'hbo', 'disney', 'adobe', 'apple', 'google', 'youtube', 'globoplay', 'sky', 'claro', 'vivo', 'tim', 'oi']): return 'Assinaturas/TV/Net'
    
    # Saúde vs Farmácia (Separado)
    if any(x in desc for x in ['drogaria', 'farmacia', 'pacheco', 'raia', 'drogasil']): return 'Farmácia'
    if any(x in desc for x in ['consultorio', 'exame', 'laboratorio', 'hospital', 'medico', 'dentista', 'psicologo']): return 'Saúde'
    
    if any(x in desc for x in ['aluguel', 'condominio', 'luz', 'energia', 'agua', 'gas', 'internet', 'iptu', 'seguro incendio']): return 'Moradia'
    if any(x in desc for x in ['shein', 'shopee', 'mercadolivre', 'mercado livre', 'amazon mkt', 'magalu', 'loja', 'store', 'vestuario', 'roupa', 'zara', 'renner', 'riachuelo']): return 'Compras'
    if any(x in desc for x in ['curso', 'faculdade', 'escola', 'udemy', 'alura', 'livraria', 'papelaria']): return 'Educação'
    if any(x in desc for x in ['cinema', 'teatro', 'show', 'ingresso', 'sympla', 'eventim', 'bar', 'chopp', 'cerveja']): return 'Lazer'
    if any(x in desc for x in ['compra', 'debito', 'cartao']): return 'Gastos Gerais'
    
    # --- ÁREA FINANCEIRA GÉNÉRICA (Deixar por último) ---
    
    # Receita (Pix recebido entra aqui - Prioridade Alta para Entradas)
    if any(x in desc for x in ['pix recebido', 'transferencia recebida', 'salario', 'provento', 'deposito', 'credit', 'resgate', 'rendimento']): return 'Receita'

    # Pix (Saídas gerais via Pix) - Só pega se não caiu em nada específico acima
    if 'pix' in desc and 'enviado' in desc: return 'Pix' 
    if 'pix' in desc and 'pagamento' in desc: return 'Pix'
    
    # Transferências Genéricas
    if any(x in desc for x in ['transferencia enviada', 'ted enviado', 'doc enviado', 'pagamento']): return 'Transferências'
    
    # Catch-all para Pix que sobrou
    if 'pix' in desc: return 'Pix'
    
    return 'Outros'

@st.cache_data
def load_data(uploaded_files, username=None):
    """
    Lê uma LISTA de arquivos de upload (CSV ou Excel) e retorna um DataFrame consolidado.
    Colunas retornadas: ['Data', 'Descrição', 'Categoria', 'Valor', 'Banco']
    Aceita 'username' para carregar regras personalizadas e isolar dados.
    """
    
    # Se for um único arquivo (compatibilidade), transforma em lista
    if uploaded_files is not None and not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]
        
    # Carrega regras se existirem (Teach Mode) - DATA ISOLATION
    custom_rules = rules_manager.load_rules(username)

    if not uploaded_files:
        # DATA ISOLATION: Se estiver logado, não gera dados fake
        if username:
            return pd.DataFrame(columns=['Data', 'Descrição', 'Categoria', 'Valor', 'Banco'])

        # GERA DADOS FAKE DEMO (Apenas se não estiver logado)
        dates = pd.date_range(end=datetime.today(), periods=50)
        data = []
        for d in dates:
            tipo = np.random.choice(['Entrada', 'Saída'], p=[0.2, 0.8])
            if tipo == 'Entrada':
                val = np.random.uniform(1000, 5000)
                cat = 'Receita'
                desc = 'Salário/Pix'
            else:
                val = np.random.uniform(10, 500) * -1
                cat = np.random.choice(['Alimentação', 'Transporte', 'Lazer', 'Contas'])
                desc = f"Compra {cat}"
            data.append([d, desc, cat, val, 'Demo Bank'])
        return pd.DataFrame(data, columns=['Data', 'Descrição', 'Categoria', 'Valor', 'Banco'])

    all_dfs = []
    
    for file in uploaded_files:
        import re
        # Identifica nome do banco pelo arquivo (ex: nubank_2023.csv -> Nubank)
        filename = file.name
        # Divide por _ ou - ou . e pega o primeiro token
        tokens = re.split(r'[_\-\.]', filename)
        bank_name = tokens[0].title() if tokens else "Banco"
        
        # 1. Tenta pegar pelo nome do arquivo
        if len(bank_name) < 3: bank_name = "Banco" # Fallback
        
        # 2. Processa arquivo
        df_temp = process_single_file(file, custom_rules)

        # 3. Se nome for genérico, tenta olhar conteúdo
        if len(bank_name) < 3 or bank_name.lower() in ['extrato', 'statement', 'relatorio', 'financeiro', 'export', 'data', 'banco']:
             bank_name = detect_bank_from_content(df_temp, bank_name)
        
        if not df_temp.empty:
            df_temp['Banco'] = bank_name
            all_dfs.append(df_temp)
            
    if not all_dfs:
        return pd.DataFrame()
        
    # Consolida tudo
    final_df = pd.concat(all_dfs, ignore_index=True)
    return final_df.sort_values('Data')

def detect_bank_from_content(df, current_name):
    """Tenta adivinhar o banco pelo conteúdo das descrições."""
    if df.empty or 'Descrição' not in df.columns:
        return current_name
        
    # Amostra de texto para busca (primeiras 20 linhas)
    text_sample = " ".join(df['Descrição'].astype(str).head(20).tolist()).lower()
    
    if 'nu pagamentos' in text_sample or 'pagamento de fatura' in text_sample: return 'Nubank'
    if 'mercado pago' in text_sample or 'mercadopago' in text_sample: return 'Mercado Pago'
    if 'inter' in text_sample and 'banco' in text_sample: return 'Inter'
    if 'bradesco' in text_sample: return 'Bradesco'
    if 'itaú' in text_sample or 'itau' in text_sample: return 'Itaú'
    if 'santander' in text_sample: return 'Santander'
    
    return current_name

def process_single_file(file, custom_rules=None):
    """Processa um único arquivo (lógica original extraída)."""
    try:
        # Verifica extensão
        df = None
        if file.name.lower().endswith('.csv'):
            # 1. Detectar Encoding e Ler Linhas
            encodings = ['utf-8', 'latin-1', 'cp1252']
            content = None
            used_encoding = 'utf-8'
            
            # Reseta e lê bytes
            file.seek(0)
            file_bytes = file.read()
            
            for enc in encodings:
                try:
                    content = file_bytes.decode(enc)
                    used_encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                # st.error(f"Falha na codificação do arquivo {file.name}.")
                return pd.DataFrame()
            
            lines = content.splitlines()
            if not lines: return pd.DataFrame()

            # 2. Detectar Separador e Linha de Cabeçalho Manualmente
            best_sep = None
            header_row_idx = -1
            
            separators = [';', ',', '\t']
            keywords = ['data', 'date', 'dt', 'release_date', 'lançamento', 'valor', 'value', 'amount', 'net_amount']
            
            for i, line in enumerate(lines[:50]):
                if not line.strip(): continue
                line_lower = line.lower()
                
                found_keywords = [k for k in keywords if k in line_lower]
                if len(found_keywords) >= 2:
                    counts = {sep: line.count(sep) for sep in separators}
                    likely_sep = max(counts, key=counts.get)
                    if counts[likely_sep] > 0:
                        best_sep = likely_sep
                        header_row_idx = i
                        break
            
            if best_sep is None:
                # Fallback
                for i, line in enumerate(lines[:10]):
                    if not line.strip(): continue
                    cols_semicolon = len(line.split(';'))
                    cols_comma = len(line.split(','))
                    if cols_semicolon > cols_comma: best_sep = ';'; header_row_idx = i
                    else: best_sep = ','; header_row_idx = i
                    break
            
            if best_sep and header_row_idx != -1:
                try:
                    file.seek(0)
                    df = pd.read_csv(
                        file, 
                        sep=best_sep, 
                        skiprows=header_row_idx, 
                        encoding=used_encoding, 
                        on_bad_lines='skip',
                        engine='python'
                    )
                except Exception as e:
                    # st.error(f"Erro no parsing final: {e}")
                    return pd.DataFrame()
            else:
                return pd.DataFrame()
                
        else:
            df = pd.read_excel(file)
        
        # --- Normalização Financeira ---
        
        # 1. DATA
        date_col = None
        for col in df.columns:
            c_str = str(col).lower()
            if any(x in c_str for x in ['data', 'date', 'dt', 'release_date']):
                try:
                    if (pd.to_datetime(df[col].iloc[:20], dayfirst=True, errors='coerce').notna().mean() > 0.8):
                        date_col = col; break
                except: pass
        
        if not date_col:
            for col in df.columns:
                try:
                    if (pd.to_datetime(df[col].iloc[:20], dayfirst=True, errors='coerce').notna().mean() > 0.8):
                        date_col = col; break
                except: pass

        if date_col:
            df['Data'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Data'])
        else:
            return pd.DataFrame()

        # 2. VALOR
        value_col = None
        for col in df.columns:
            c_str = str(col).lower()
            if any(x in c_str for x in ['valor', 'value', 'amount', 'montante', 'net_amount']):
                value_col = col; break
        
        if not value_col:
            for col in df.columns:
                if col == date_col: continue
                try: 
                    pd.to_numeric(df[col].astype(str).str.replace(',','.'), errors='raise')
                    value_col = col; break
                except: pass
        
        if value_col:
            # Lógica de Parsing Numérico Safer
            def safe_parse(x):
                s = str(x).strip().replace('R$', '').replace(' ', '')
                if not s: return 0.0
                
                # Detecta formato (se tem vírgula no final como decimal)
                # Caso Brasil: 1.000,00 -> Tem virgula nas ultimas 3 pos
                # Caso US: 1,000.00 -> Tem ponto nas ultimas 3 pos
                
                try:
                    # Tenta converter direto (se for float python puro)
                    return float(s)
                except:
                    pass
                
                # Se tem vírgula como decimal (padrao BR)
                if ',' in s and ('.' not in s or s.find(',') > s.find('.')):
                     # Remove ponto de milhar e troca vírgula por ponto
                     s_clean = s.replace('.', '').replace(',', '.')
                     return float(s_clean)
                
                # Se tem ponto como decimal (padrao US)
                if '.' in s and (',' not in s or s.find('.') > s.find(',')):
                    # Remove vírgula de milhar
                    s_clean = s.replace(',', '')
                    return float(s_clean)
                    
                return 0.0

            df['Valor'] = df[value_col].apply(safe_parse).fillna(0)
        else:
            return pd.DataFrame()

        # 3. DESCRIÇÃO
        desc_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['desc', 'hist', 'memo', 'estabelecimento', 'type', 'transaction', 'tipo'])]
        df['Descrição'] = df[desc_cols[0]] if desc_cols else "Sem descrição"
        
        # 4. CATEGORIA
        df['Categoria'] = df['Descrição'].apply(lambda x: categorize(x, custom_rules))
        
        return df[['Data', 'Descrição', 'Categoria', 'Valor']].sort_values('Data')

    except Exception as e:
        # st.error(f"Erro ao processar arquivo: {e}")
        return pd.DataFrame()
