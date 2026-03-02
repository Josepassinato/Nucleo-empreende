"""
Ata Digital — registra reuniões no Supabase
Cada reunião gera uma ata com decisões, responsáveis e tarefas
"""
import os, json, logging
from datetime import datetime
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.ata")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://armabaquiyqmdgwflslq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

async def salvar_ata(sala) -> dict | None:
    """Gera e salva ata completa da reunião no Supabase."""
    if not SUPABASE_KEY:
        logger.warning("SUPABASE_ANON_KEY não configurada — ata não salva")
        return None

    # Extrair tarefas e responsáveis da decisão final
    tarefas = _extrair_tarefas(sala.historico, sala.decisao_final)

    ata = {
        "sala_id": sala.id,
        "tema": sala.tema,
        "data": datetime.now().isoformat(),
        "participantes": sala.agentes,
        "historico": sala.historico,
        "decisao_final": sala.decisao_final or "",
        "tarefas": tarefas,
        "status": "pendente",
        "criado_em": datetime.now().isoformat()
    }

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"{SUPABASE_URL}/rest/v1/atas_reuniao",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=ata
            )
            if r.status_code in (200, 201):
                result = r.json()
                logger.info(f"✅ Ata salva — sala {sala.id}")
                return result[0] if isinstance(result, list) else result
            else:
                logger.error(f"Supabase erro {r.status_code}: {r.text[:200]}")
                return None
    except Exception as e:
        logger.error(f"Erro ao salvar ata: {e}")
        return None

async def listar_atas(limit: int = 20) -> list:
    """Lista atas mais recentes."""
    if not SUPABASE_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{SUPABASE_URL}/rest/v1/atas_reuniao?order=criado_em.desc&limit={limit}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            if r.status_code == 200:
                return r.json()
            return []
    except:
        return []

async def buscar_ata(sala_id: str) -> dict | None:
    """Busca ata por ID da sala."""
    if not SUPABASE_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{SUPABASE_URL}/rest/v1/atas_reuniao?sala_id=eq.{sala_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            if r.status_code == 200:
                data = r.json()
                return data[0] if data else None
            return None
    except:
        return None

async def atualizar_tarefa(sala_id: str, tarefa_idx: int, status: str) -> bool:
    """Atualiza status de uma tarefa específica."""
    ata = await buscar_ata(sala_id)
    if not ata:
        return False
    tarefas = ata.get("tarefas", [])
    if tarefa_idx < len(tarefas):
        tarefas[tarefa_idx]["status"] = status
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.patch(
                f"{SUPABASE_URL}/rest/v1/atas_reuniao?sala_id=eq.{sala_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"tarefas": tarefas}
            )
            return r.status_code in (200, 204)
    except:
        return False

def _extrair_tarefas(historico: list, decisao: str) -> list:
    """Extrai tarefas e responsáveis do histórico da reunião."""
    tarefas = []
    keywords = ["vai fazer", "vai levantar", "vai pesquisar", "vai contatar",
                "responsável", "fica com", "cuida de", "vai verificar",
                "vai analisar", "vai montar", "vai criar", "vai preparar",
                "vai mapear", "vai identificar", "precisa fazer"]

    agentes_nomes = {
        "lucas": "Lucas Mendes", "diana": "Diana Vaz", "pedro": "Pedro Lima",
        "mariana": "Mariana Oliveira", "carla": "Carla Santos", "rafael": "Rafael Costa",
        "ana": "Ana Lima", "dani": "Dani Souza", "ze": "Zé Martins", "beto": "Beto Freitas"
    }

    # Analisar decisão final
    if decisao:
        for agente_id, agente_nome in agentes_nomes.items():
            nome_curto = agente_nome.split()[0]
            for kw in keywords:
                if nome_curto.lower() in decisao.lower() and kw in decisao.lower():
                    # Extrair a frase relevante
                    idx = decisao.lower().find(nome_curto.lower())
                    trecho = decisao[max(0, idx-10):idx+150].strip()
                    tarefas.append({
                        "responsavel": agente_nome,
                        "agente_id": agente_id,
                        "descricao": trecho,
                        "status": "pendente",
                        "criado_em": datetime.now().isoformat()
                    })
                    break

    # Se não encontrou na decisão, analisa histórico
    if not tarefas:
        for fala in historico[-5:]:  # últimas 5 falas
            texto = fala.get("fala", "")
            agente = fala.get("agente", "")
            for kw in keywords:
                if kw in texto.lower():
                    tarefas.append({
                        "responsavel": fala.get("nome", agente),
                        "agente_id": agente,
                        "descricao": texto[:200],
                        "status": "pendente",
                        "criado_em": datetime.now().isoformat()
                    })
                    break

    return tarefas
