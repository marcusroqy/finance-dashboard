import json
import os
import streamlit as st

def get_budget_file(username):
    """Retorna o caminho do arquivo de metas do usuário."""
    return f"userdata/{username}/budgets.json"

def load_budgets(username):
    """
    Carrega as metas do usuário.
    Retorna um dict: {'Alimentação': 500.0, 'Transporte': 300.0}
    """
    filepath = get_budget_file(username)
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar metas: {e}")
        return {}

def save_budget(username, category, amount):
    """
    Salva ou atualiza a meta de uma categoria.
    Se amount for 0, remove a meta.
    """
    budgets = load_budgets(username)
    
    if amount <= 0:
        if category in budgets:
            del budgets[category]
    else:
        budgets[category] = float(amount)
        
    filepath = get_budget_file(username)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(budgets, f, indent=4, ensure_ascii=False)
        
    return budgets
