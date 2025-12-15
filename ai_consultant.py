import google.generativeai as genai
import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO GLOBAL ---
# Chave agora vem dos Secrets (Segurança)

def analyze_finances(df, api_key=None):
    """
    Gera uma análise financeira usando o Google Gemini.
    Usa a chave configurada nos Secrets do Streamlit.
    Args:
        df (pd.DataFrame): DataFrame com colunas 'Data', 'Descrição', 'Categoria', 'Valor'.
    """
    try:
        # Tenta pegar a chave dos segredos
        try:
            secrets_key = st.secrets["gemini"]["api_key"]
            genai.configure(api_key=secrets_key)
        except Exception:
             return "❌ Erro: Chave da API (Gemini) não encontrada nos Secrets. Configure [gemini] api_key = '...'."
        
        # Lista de tentativas de modelo (do mais novo para o mais compatível)
        models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-flash-001', 'gemini-pro']
        final_error = None
        
        # 1. Prepara o Resumo dos Dados
        summary = prepare_data_summary(df)
        
        # 2. Monta o Prompt (mesmo para todos)
        prompt = f"""
        Quero que você aja como um consultor financeiro pessoal experiente, direto e carismático.
        Você receberá um resumo dos meus gastos recentes. 
        Seu objetivo é identificar padrões, puxar minha orelha se necessário e dar dicas práticas.

        --- DADOS FINANCEIROS (Mês Atual/Filtrado) ---
        {summary}
        ----------------------------------------------

        # SUAS INSTRUÇÕES:
        1.  **Resumo Geral 🗓️**: 3-4 frases sobre o clima do mês.
        2.  **🚨 Onde Sangrou Dinheiro**: Liste o que está "vazando" (ex: muita Conveniência, Farmácia, Ifood). Seja específico.
        3.  **⚠️ Hábito Perigoso**: Identifique um comportamento de risco (ex: gastar tudo o que ganha, muitas compras pequenas).
        4.  **✅ Plano de Ação**: 3 coisas práticas para eu fazer amanhã.
        5.  **💡 Frase do Dia**: Motivacional e focada em disciplina.

        **Regras de Formatação (CRÍTICO):**
        1. **NUNCA use o símbolo de cifrão ($)** para valores. Use sempre **"R$ "** (texto puro). Exemplo: "R$ 1.500,00".
        2. **NÃO use LaTeX** (nada de `\text`, `\bold`, `$$`). Isso quebra a visualização.
        3. **Respeite os espaços**: Não junte palavras. Escreva frases normais.
        4. **Negrito**: Use apenas `**texto**` para destaque.
        5. Use linguagem simples e direta.
        """
        
        # 3. Loop de Tentativa de Modelos
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                with st.spinner(f"🤖 Consultando IA ({model_name})..."):
                    response = model.generate_content(prompt)
                    return response.text
            except Exception as e:
                final_error = e
                continue # Tenta o próximo
        
        # Se chegou aqui, nenhum funcionou
        extracted_models = []
        try:
            # Tenta listar os modelos disponíveis para ajudar no debug
            all_models = list(genai.list_models())
            extracted_models = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
        except:
            pass
            
        return f"""❌ Erro: Nenhum modelo padrão funcionou.
        
        **Detalhes do Erro:** {str(final_error)}
        
        **Modelos Disponíveis na sua Chave:**
        {chr(10).join(extracted_models) if extracted_models else 'Nenhum modelo encontrado. Verifique se a API "Generative Language API" está ativada no Google Cloud Console.'}
        """
            
    except Exception as e:
        return f"❌ Erro Geral: {str(e)}"

def prepare_data_summary(df):
    """
    Transforma o DataFrame em um texto resumido para a IA.
    """
    if df.empty:
        return "Sem dados disponíveis."
        
    # Totais
    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    total_saidas = df[df['Valor'] < 0]['Valor'].abs().sum()
    saldo = total_entradas - total_saidas
    
    # Top Categorias
    rank_cat = df[df['Valor'] < 0].groupby('Categoria')['Valor'].sum().abs().sort_values(ascending=False).head(5)
    rank_cat_str = "\n".join([f"- {cat}: R$ {val:,.2f}" for cat, val in rank_cat.items()])
    
    # Top 10 Gastos Específicos (para ver onde foi o dinheiro)
    top_itens = df[df['Valor'] < 0].sort_values('Valor').head(10)
    itens_str = "\n".join([f"- {row['Data'].strftime('%d/%m')} | {row['Descrição']} | R$ {abs(row['Valor']):,.2f}" for _, row in top_itens.iterrows()])
    
    # Gastos com Conveniência e Farmácia (Foco do usuário)
    gasto_conv = df[(df['Categoria'] == 'Conveniência') & (df['Valor'] < 0)]['Valor'].sum()
    gasto_farm = df[(df['Categoria'] == 'Farmácia') & (df['Valor'] < 0)]['Valor'].sum()
    
    summary = f"""
    - **Total Receitas**: R$ {total_entradas:,.2f}
    - **Total Despesas**: R$ {total_saidas:,.2f}
    - **Saldo Final**: R$ {saldo:,.2f}
    - **Poupança (%)**: {((total_entradas - total_saidas) / total_entradas * 100) if total_entradas > 0 else 0:.1f}%

    **Top 5 Categorias de Gasto:**
    {rank_cat_str}

    **Detalhamento (Conveniência/Farmácia):**
    - Conveniência: R$ {abs(gasto_conv):,.2f}
    - Farmácia: R$ {abs(gasto_farm):,.2f}

    **Top 10 Maiores Despesas (Detalhe):**
    {itens_str}
    """
    return summary
