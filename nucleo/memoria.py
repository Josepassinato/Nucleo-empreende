"""
╔══════════════════════════════════════════════════════════════╗
║   INCREASE TEAM — Sistema de Memória Longa               ║
║                                                             ║
║   Cada conversa é salva e resumida.                         ║
║   O Lucas lembra de tudo que você disse em todas as         ║
║   conversas anteriores — empresa, decisões, pedidos.        ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, re
from pathlib import Path
from datetime import datetime
from typing import Optional

# Redis para histórico rápido
try:
    import redis
    _redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
    _redis.ping()
    REDIS_OK = True
except:
    REDIS_OK = False
    _redis = None

# Caminhos
MEM_DIR  = Path("nucleo/memoria")
MEM_DIR.mkdir(parents=True, exist_ok=True)
MEM_FILE = MEM_DIR / "contexto_dono.json"   # Fatos permanentes sobre o dono/empresa
HIST_DIR = MEM_DIR / "historico"            # Histórico por data
HIST_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# MEMÓRIA PERMANENTE (fatos extraídos das conversas)
# ══════════════════════════════════════════════════════════════

def carregar_memoria() -> dict:
    """Carrega todos os fatos que o sistema sabe sobre o dono e a empresa."""
    if MEM_FILE.exists():
        try: return json.loads(MEM_FILE.read_text())
        except: pass
    return {
        "empresa": {},
        "dono": {"nome": os.getenv("DONO_NOME", "José")},
        "decisoes": [],        # Decisões tomadas
        "preferencias": [],    # Preferências do dono
        "contextos": [],       # Assuntos recorrentes
        "ultimas_acoes": [],   # Últimas ações executadas
        "resumo_geral": "",    # Resumo narrativo de tudo
        "atualizado_em": "",
    }

def salvar_memoria(mem: dict):
    mem["atualizado_em"] = datetime.now().isoformat()
    MEM_FILE.write_text(json.dumps(mem, ensure_ascii=False, indent=2))

# ══════════════════════════════════════════════════════════════
# HISTÓRICO DE CONVERSA (Redis + arquivo)
# ══════════════════════════════════════════════════════════════

HIST_KEY   = "nucleo:historico"
MAX_REDIS  = 40   # últimas 40 mensagens no Redis (acesso rápido)
MAX_RESUMO = 10   # resumir a cada 10 mensagens

def salvar_mensagem(role: str, conteudo: str, agente: str = "lucas"):
    """Salva mensagem no Redis e no arquivo."""
    msg = {
        "ts": datetime.now().isoformat(),
        "role": role,   # "user" ou "assistant"
        "conteudo": conteudo,
        "agente": agente,
    }
    linha = json.dumps(msg, ensure_ascii=False)

    # Redis (acesso rápido)
    if REDIS_OK:
        _redis.rpush(HIST_KEY, linha)
        # Manter só as últimas MAX_REDIS
        total = _redis.llen(HIST_KEY)
        if total > MAX_REDIS:
            _redis.ltrim(HIST_KEY, total - MAX_REDIS, -1)

    # Arquivo diário (memória longa)
    hoje = datetime.now().strftime("%Y-%m-%d")
    arq  = HIST_DIR / f"{hoje}.jsonl"
    with open(arq, "a") as f:
        f.write(linha + "\n")

def carregar_historico_recente(n: int = 20) -> list[dict]:
    """Retorna as últimas N mensagens."""
    if REDIS_OK:
        msgs = _redis.lrange(HIST_KEY, -n, -1)
        result = []
        for m in msgs:
            try: result.append(json.loads(m))
            except: pass
        return result

    # Fallback: ler arquivos
    msgs = []
    for arq in sorted(HIST_DIR.glob("*.jsonl"))[-3:]:
        for linha in arq.read_text().splitlines():
            try: msgs.append(json.loads(linha))
            except: pass
    return msgs[-n:]

def historico_para_texto(n: int = 15) -> str:
    """Formata histórico recente para incluir no prompt."""
    msgs = carregar_historico_recente(n)
    if not msgs:
        return "Sem histórico anterior."
    linhas = []
    for m in msgs:
        ts   = m.get("ts","")[:16].replace("T"," ")
        role = "José" if m.get("role") == "user" else m.get("agente","Lucas").title()
        linhas.append(f"[{ts}] {role}: {m.get('conteudo','')[:200]}")
    return "\n".join(linhas)

# ══════════════════════════════════════════════════════════════
# EXTRATOR DE FATOS (aprende com cada mensagem)
# ══════════════════════════════════════════════════════════════

PADROES_FATOS = {
    "empresa.ramo":    [r"ramo\s+(?:[ée]\s+)?(.+)", r"(?:somos|empresa)\s+de\s+(.+)"],
    "empresa.produto": [r"produto\s+(?:[ée]\s+)?(.+)", r"(?:vendemos|vendo)\s+(.+)"],
    "empresa.publico": [r"público.alvo\s+(?:[ée]\s+)?(.+)", r"(?:atendemos|clientes?)\s+(.+)"],
    "empresa.meta":    [r"meta\s+(?:de\s+)?faturamento\s+r?\$?\s*([\d.,]+\w*)"],
    "empresa.nome":    [r"nome\s+da\s+empresa\s+(?:[ée]\s+)?(.+)"],
    "dono.preferencia":[r"(?:prefiro|gosto de|quero sempre)\s+(.+)", r"não\s+(?:gosto|quero)\s+(.+)"],
}

def extrair_e_memorizar(texto: str):
    """Extrai fatos da mensagem e salva na memória permanente."""
    mem = carregar_memoria()
    atualizado = False

    for campo, padroes in PADROES_FATOS.items():
        for padrao in padroes:
            m = re.search(padrao, texto, re.IGNORECASE)
            if m:
                valor = m.group(1).strip().rstrip(".")
                partes = campo.split(".")
                obj = mem
                for p in partes[:-1]:
                    obj = obj.setdefault(p, {})
                obj[partes[-1]] = valor
                atualizado = True
                break

    # Registrar última ação
    if len(texto) > 20:
        mem.setdefault("ultimas_acoes", []).append({
            "ts": datetime.now().isoformat()[:16],
            "acao": texto[:100],
        })
        # Manter só as últimas 20
        mem["ultimas_acoes"] = mem["ultimas_acoes"][-20:]
        atualizado = True

    if atualizado:
        salvar_memoria(mem)

# ══════════════════════════════════════════════════════════════
# CONTEXTO COMPLETO PARA O PROMPT
# ══════════════════════════════════════════════════════════════

def montar_contexto_completo() -> str:
    """
    Monta o contexto completo para incluir no system prompt.
    Combina: fatos permanentes + histórico recente + config da empresa.
    """
    mem = carregar_memoria()
    emp = mem.get("empresa", {})

    # Tentar carregar config do projeto também
    config_proj = {}
    try:
        cfg_file = Path("nucleo/config/projeto.json")
        if cfg_file.exists():
            config_proj = json.loads(cfg_file.read_text())
            emp.update(config_proj.get("empresa", {}))
    except: pass

    linhas = ["═══ CONTEXTO PERMANENTE ═══"]

    # Empresa
    if any(emp.values()):
        linhas.append("\n🏢 EMPRESA:")
        for k, v in emp.items():
            if v: linhas.append(f"  • {k}: {v}")

    # Dono
    dono = mem.get("dono", {})
    if dono:
        linhas.append(f"\n👤 DONO: {dono.get('nome', 'José')}")
        if dono.get("preferencia"):
            linhas.append(f"  • Preferência: {dono['preferencia']}")

    # Últimas ações (contexto recente permanente)
    acoes = mem.get("ultimas_acoes", [])[-5:]
    if acoes:
        linhas.append("\n📋 ÚLTIMAS AÇÕES:")
        for a in acoes:
            linhas.append(f"  [{a['ts']}] {a['acao'][:80]}")

    # Equipe e campanhas do config
    equipe = config_proj.get("equipe", [])
    if equipe:
        linhas.append(f"\n👥 EQUIPE: {len(equipe)} funcionários")

    campanhas = config_proj.get("campanhas", [])
    if campanhas:
        linhas.append(f"\n📢 CAMPANHAS ATIVAS: {len([c for c in campanhas if c.get('status')=='ativa'])}")

    # Histórico recente da conversa
    hist = historico_para_texto(15)
    linhas.append("\n═══ HISTÓRICO RECENTE ═══")
    linhas.append(hist)

    return "\n".join(linhas)

# ══════════════════════════════════════════════════════════════
# RESUMO PERIÓDICO (chamado a cada 10 mensagens)
# ══════════════════════════════════════════════════════════════

async def resumir_se_necessario():
    """A cada 10 mensagens, usa o Gemini para criar um resumo do dia."""
    if not REDIS_OK: return
    total = _redis.llen(HIST_KEY)
    if total % 10 != 0: return

    try:
        import httpx
        GOOGLE_KEY = os.getenv("GOOGLE_API_KEY","")
        if not GOOGLE_KEY: return

        hist = historico_para_texto(10)
        mem  = carregar_memoria()

        prompt = f"""Analise essa conversa e extraia os fatos mais importantes em JSON:

CONVERSA:
{hist}

Retorne APENAS JSON com essa estrutura:
{{
  "empresa": {{"ramo":"","produto":"","publico":"","meta":""}},
  "decisoes_tomadas": ["decisão1","decisão2"],
  "preferencias_dono": ["preferencia1"],
  "resumo": "Resumo em 2 frases do que foi discutido"
}}"""

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_KEY}",
                json={"contents":[{"parts":[{"text": prompt}]}]}
            )
        if r.status_code == 200:
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            txt = re.sub(r"```json|```","",txt).strip()
            dados = json.loads(txt)

            # Mesclar com memória existente
            for k, v in dados.get("empresa",{}).items():
                if v: mem.setdefault("empresa",{})[k] = v
            mem.setdefault("decisoes",[]).extend(dados.get("decisoes_tomadas",[]))
            mem.setdefault("preferencias",[]).extend(dados.get("preferencias_dono",[]))
            mem["resumo_geral"] = dados.get("resumo","")
            mem["decisoes"] = mem["decisoes"][-20:]
            mem["preferencias"] = list(set(mem["preferencias"]))[-10:]
            salvar_memoria(mem)
    except: pass
