import json
import os
import streamlit as st
import uuid
import random
import string
import glob

# --- PATHS ---
def _get_list_file(list_id):
    return f"userdata/lists/{list_id}.json"

def _get_user_index_file(username):
    return f"userdata/{username}/my_lists.json"

# --- HELPER: GENERATE CODE ---
def _generate_invite_code(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# --- LIST MANAGEMENT ---

def create_list(name, owner):
    """Cria uma nova lista compartilhada."""
    list_id = str(uuid.uuid4())
    code = _generate_invite_code()
    
    data = {
        "id": list_id,
        "name": name,
        "owner": owner,
        "members": [owner],
        "invite_code": code,
        "created_at": str(uuid.uuid1()), # Timestamp roughly
        "bills": []
    }
    
    # Salva o arquivo da lista
    os.makedirs("userdata/lists", exist_ok=True)
    with open(_get_list_file(list_id), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    # Adiciona ao índice do usuário
    _add_list_to_user_index(owner, list_id, name)
    
    return list_id, code

def join_list(invite_code, user):
    """Entra em uma lista existente pelo código."""
    # Procura em todas as listas (simples para MVP)
    # Em produção, usaria um índice global de códigos.
    list_files = glob.glob("userdata/lists/*.json")
    
    target_list = None
    target_file = None
    
    for fpath in list_files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('invite_code') == invite_code.upper().strip():
                    target_list = data
                    target_file = fpath
                    break
        except:
            continue
            
    if not target_list:
        return False, "Código de convite inválido."
        
    if user in target_list['members']:
        return False, "Você já está nesta lista."
        
    # Adiciona user
    target_list['members'].append(user)
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(target_list, f, indent=4, ensure_ascii=False)
        
    # Atualiza índice do user
    _add_list_to_user_index(user, target_list['id'], target_list['name'])
    
    return True, f"Entrou na lista '{target_list['name']}' com sucesso!"

def get_user_lists(user):
    """Retorna lista de dicts [{'id', 'name'}] do usuário."""
    # 1. Migração de legado (se existir bills.json antigo)
    _migrate_legacy_bills(user)
    
    # 2. Leitura
    index_file = _get_user_index_file(user)
    if not os.path.exists(index_file):
        return []
        
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def get_list_details(list_id):
    """Retorna dados completos da lista (membros, bills, código)."""
    fpath = _get_list_file(list_id)
    if not os.path.exists(fpath):
        return None
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# --- BILLS CRUD (Agora baseados em LIST_ID) ---

def save_bill(list_id, bill_data, user_action):
    """Salva conta na lista especificada."""
    data = get_list_details(list_id)
    if not data:
        return False, "Lista não encontrada."
        
    bills = data.get('bills', [])
    
    if not bill_data.get('id'):
        bill_data['id'] = str(uuid.uuid4())
        bill_data['created_by'] = user_action
        bills.append(bill_data)
    else:
        for i, b in enumerate(bills):
            if b['id'] == bill_data['id']:
                bills[i] = {**b, **bill_data}
                break
    
    data['bills'] = bills
    _save_list_file(list_id, data)
    return True, "Conta salva!"

def delete_bill(list_id, bill_id):
    data = get_list_details(list_id)
    if not data: return
    
    bills = data.get('bills', [])
    new_bills = [b for b in bills if b['id'] != bill_id]
    
    data['bills'] = new_bills
    _save_list_file(list_id, data)

def toggle_status(list_id, bill_id, new_status):
    data = get_list_details(list_id)
    if not data: return
    
    updated = False
    for b in data.get('bills', []):
        if b['id'] == bill_id:
            b['status'] = new_status
            updated = True
            break
            
    if updated:
        _save_list_file(list_id, data)

# --- INTERNAL HELPERS ---

def _save_list_file(list_id, data):
    with open(_get_list_file(list_id), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def _add_list_to_user_index(user, list_id, name):
    fpath = _get_user_index_file(user)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    
    current = []
    if os.path.exists(fpath):
        try:
            with open(fpath, 'r') as f: current = json.load(f)
        except: pass
        
    # Evita duplictas
    if not any(l['id'] == list_id for l in current):
        current.append({'id': list_id, 'name': name})
        
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(current, f, indent=4, ensure_ascii=False)

def _migrate_legacy_bills(user):
    """Converte bills.json antigo em uma Lista Pessoal."""
    legacy_path = f"userdata/{user}/bills.json"
    index_path = _get_user_index_file(user)
    
    # Só migra se tiver legado E NÃO tiver índice (primeira vez no sistema de listas)
    if os.path.exists(legacy_path) and not os.path.exists(index_path):
        try:
            with open(legacy_path, 'r', encoding='utf-8') as f:
                old_bills = json.load(f)
            
            if old_bills:
                # Cria lista default
                list_id, code = create_list("Minhas Contas (Pessoal)", user)
                
                # Carrega e injeta as bills antigas
                data = get_list_details(list_id)
                data['bills'] = old_bills
                _save_list_file(list_id, data)
                
                # Renomeia antigo para backup (opcional)
                os.rename(legacy_path, legacy_path + ".bak")
        except Exception as e:
            print(f"Erro migração: {e}")
