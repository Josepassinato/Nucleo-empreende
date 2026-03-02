"""
Ata Digital — registra reuniões no Supabase
Extração de tarefas via LLM (não keywords) — confiável e completa
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
GOOGLE_KEY   = os.getenv("GOOGLE_API_KEY", "")

async def salvar_ata(sala) -> dict | None:
    """Gera e salva ata completa da reunião no Supabase."""
    if not SUPABASE_KEY:
        logger.warning("SUPABASE_ANON_KEY não configurada — ata não salva")
        return None

    # Fix 2: Extrair tarefas via LLM — não keyword matching
    tarefas = await _extrair_tarefas_llm(sala.historico, sala.decisao_final)

    ata = {
        "sala_id":      sala.id,
        "tema":         sala.tema,
        "data":         datetime.now().isoformat(),
        "participantes": sala.agentes,
        "historico":    sala.historico,
        "decisao_final": sala.decisao_final or "",
        "tarefas":      tarefas,
        "status":       "pendente",
        "criado_em":    datetime.now().isoformat()
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
                logger.info(f"✅ Ata salva — sala {sala.id} — {len(tarefas)} tarefas")
                return result[0] if isinstance(result, list) else result
            else:
                logger.error(f"Supabase erro {r.status_code}: {r.text[:200]}")
                return None
    except Exception as e:
        logger.error(f"Erro ao salvar ata: {e}")
        return None


async def listar_atas(limit: int = 20) -> list:
    if not SUPABASE_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{SUPABASE_URL}/rest/v1/atas_reuniao?order=criado_em.desc&limit={limit}",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            )
            return r.json() if r.status_code == 200 else []
    except:
        return []


async def buscar_ata(sala_id: str) -> dict | None:
    if not SUPABASE_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{SUPABASE_URL}/rest/v1/atas_reuniao?sala_id=eq.{sala_id}",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            )
            if r.status_code == 200:
                data = r.json()
                return data[0] if data else None
            return None
    except:
        return None


async def atualizar_tarefa(sala_id: str, tarefa_idx: int, status: str) -> bool:
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


# ── Fix 2: Extração via LLM ─────────────────────────────────────
async def _extrair_tarefas_llm(historico: list, decisao: str) -> list:
    """
    Extrai tarefas do 5W2H via LLM.
    Confiável independente de como o Lucas formulou o encerramento.
    """
    if not GOOGLE_KEY:
        return _extrair_tarefas_fallback(historico, decisao)

    # Montar texto completo da reunião
    texto = ""
    for fala in historico:
        nome = fala.get("nome", fala.get("agente", "?"))
        texto += f"{nome}: {fala.get('fala', '')}\n"
    if decisao:
        texto += f"\n--- ENCERRAMENTO / 5W2H ---\n{decisao}"

    prompt = f"""Analise esta reunião executiva e extraia TODOS os compromissos e tarefas definidos.
Foque especialmente no encerramento com 5W2H se houver.

REUNIÃO:
{texto[:3500]}

Retorne SOMENTE JSON válido, sem markdown:
{{
  "tarefas": [
    {{
      "responsavel": "Nome completo do responsável",
      "agente_id": "id em minúsculas: lucas|mariana|pedro|carla|rafael|ana|dani|ze|beto|diana",
      "descricao": "descrição clara da tarefa",
      "o_que": "ação concreta",
      "por_que": "razão de negócio",
      "onde": "sistema ou canal de execução",
      "quando": "prazo ou data específica",
      "como": "método ou abordagem",
      "quanto": "custo estimado em R$ e horas",
      "status": "pendente"
    }}
  ]
}}

Regras:
- Inclua TODAS as tarefas, mesmo sem todos os campos 5W2H preenchidos
- Se não houver tarefas claras, retorne {{"tarefas": []}}
- Campos vazios ficam como string vazia ""
- agente_id sempre em minúsculas sem acento"""

    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1200}
                }
            )
            if r.status_code == 200:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                txt = txt.replace("```json", "").replace("```", "").strip()
                dados = json.loads(txt)
                tarefas = dados.get("tarefas", [])
                for t in tarefas:
                    t["criado_em"] = datetime.now().isoformat()
                logger.info(f"✅ LLM extraiu {len(tarefas)} tarefas")
                return tarefas
    except Exception as e:
        logger.warning(f"LLM extração falhou, usando fallback: {e}")

    return _extrair_tarefas_fallback(historico, decisao)


def _extrair_tarefas_fallback(historico: list, decisao: str) -> list:
    """Fallback com parsing do 5W2H estruturado — só usado se LLM falhar."""
    tarefas = []
    if not decisao or ("QUEM:" not in decisao and "✅" not in decisao):
        return tarefas

    tarefa: dict = {"status": "pendente", "criado_em": datetime.now().isoformat()}
    agentes_map = {
        "lucas": "Lucas Mendes", "mariana": "Mariana Oliveira",
        "pedro": "Pedro Lima", "carla": "Carla Santos",
        "rafael": "Rafael Torres", "ana": "Ana Costa",
        "dani": "Dani Ferreira", "ze": "Zé Carvalho",
        "beto": "Beto Rocha", "diana": "Diana Vaz"
    }

    for linha in decisao.split("\n"):
        linha = linha.strip()
        for campo, chaves in [
            ("descricao",   ["O QUÊ:", "O QUE:"]),
            ("por_que",     ["POR QUÊ:", "POR QUE:"]),
            ("responsavel", ["QUEM:"]),
            ("onde",        ["ONDE:"]),
            ("quando",      ["QUANDO:"]),
            ("como",        ["COMO:"]),
            ("quanto",      ["QUANTO:"]),
        ]:
            for chave in chaves:
                if chave in linha:
                    tarefa[campo] = linha.split(chave, 1)[-1].strip()
                    if campo == "responsavel":
                        nome = tarefa["responsavel"].lower()
                        for aid in agentes_map:
                            if aid in nome:
                                tarefa["agente_id"] = aid
                                break
                    break

    if tarefa.get("responsavel") or tarefa.get("descricao"):
        tarefa.setdefault("descricao", tarefa.get("o_que", ""))
        tarefas.append(tarefa)

    return tarefas
