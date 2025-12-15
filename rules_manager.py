import json
import os
import auth

def get_rules_file(username):
    if not username:
        return "rules.json" # Fallback legado
    
    # Garante que a pasta existe
    auth.init_user_env(username)
    return os.path.join("userdata", username, "rules.json")

def load_rules(username=None):
    """Carrega as regras do usuário específico."""
    rules_file = get_rules_file(username)
    
    if not os.path.exists(rules_file):
        return {}
    
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar regras: {e}")
        return {}

def save_rule(keyword, category, username=None):
    """Salva regra para o usuário."""
    rules = load_rules(username)
    k = keyword.lower().strip()
    rules[k] = category
    
    rules_file = get_rules_file(username)
    
    try:
        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=4)
        return True, f"Regra salva: '{keyword}' -> '{category}'"
    except Exception as e:
        return False, f"Erro ao salvar regra: {str(e)}"

def delete_rule(keyword, username=None):
    """Remove regra do usuário."""
    rules = load_rules(username)
    k = keyword.lower().strip()
    
    if k in rules:
        del rules[k]
        rules_file = get_rules_file(username)
        try:
            with open(rules_file, "w", encoding="utf-8") as f:
                json.dump(rules, f, ensure_ascii=False, indent=4)
            return True, f"Regra removida: '{keyword}'"
        except Exception as e:
            return False, f"Erro ao salvar após remocao: {str(e)}"
    
    return False, "Regra não encontrada."
