from supabase_client import supabase
import hashlib

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def cadastrar_usuario(usuario, senha):
    try:
        hashed = hash_senha(senha)
        supabase.table("usuarios").insert({"usuario": usuario, "senha": hashed}).execute()
        return True
    except Exception as e:
        print("Erro ao cadastrar:", e)
        return False

def verificar_login(usuario, senha):
    hashed = hash_senha(senha)
    result = supabase.table("usuarios").select("*").eq("usuario", usuario).eq("senha", hashed).execute()
    return len(result.data) > 0
