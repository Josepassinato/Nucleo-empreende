"""
Increase Team — Sistema Colegiado
Decisões importantes são debatidas pela diretoria antes de chegar ao dono.

Fluxo:
  1. Agente identifica oportunidade/problema
  2. Lança pauta para o colegiado
  3. Cada diretor relevante emite voto fundamentado
  4. Lucas consolida e decide
  5. Dono recebe a decisão + raciocínio completo
"""
import os, json, asyncio, logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()
logger = logging.getLogger("nucleo.colegiado")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
BASE_DIR = Path(__file__).resolve().parent.parent
PAUTAS_FILE = BASE_DIR / "nucleo" / "data" / "pautas_colegiado.json"
PAUTAS_FILE.parent.mkdir(exist_ok=True)

# ── Gemini ───────────────────────────────────────────────────────
async def gemini(system: str, prompt: str, tokens: int = 400) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.85, "maxOutputTokens": tokens}
                }
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Erro: {e}"

def carregar_md(nome: str) -> str:
    f = BASE_DIR / "nucleo" / "agentes" / nome
    return f.read_text() if f.exists() else ""

def carregar_empresa() -> dict:
    mem = BASE_DIR / "nucleo" / "data" / "memoria.json"
    try:
        return json.loads(mem.read_text()).get("empresa", {}) if mem.exists() else {}
    except: return {}

# ── Salvar/carregar pautas ───────────────────────────────────────
def salvar_pauta(pauta: dict):
    try:
        pautas = json.loads(PAUTAS_FILE.read_text()) if PAUTAS_FILE.exists() else []
    except: pautas = []
    pautas.append(pauta)
    pautas = pautas[-100:]
    PAUTAS_FILE.write_text(json.dumps(pautas, ensure_ascii=False, indent=2))

def listar_pautas_abertas() -> list:
    try:
        pautas = json.loads(PAUTAS_FILE.read_text()) if PAUTAS_FILE.exists() else []
        return [p for p in pautas if p.get("status") == "aberta"]
    except: return []

# ── Diretores e suas especialidades ────────────────────────────
DIRETORES = {
    "diana":   {"arquivo": "diana_vaz_cno.md",          "area": "mercado e networking"},
    "pedro":   {"arquivo": "pedro_lima_cfo.md",          "area": "finanças e viabilidade"},
    "mariana": {"arquivo": "mariana_oliveira_cmo.md",    "area": "marketing e crescimento"},
    "carla":   {"arquivo": "carla_santos_coo.md",        "area": "operações e processos"},
    "rafael":  {"arquivo": "rafael_torres_cpo.md",       "area": "produto e tecnologia"},
    "ana":     {"arquivo": "ana_costa_chro.md",          "area": "pessoas e cultura"},
    "dani":    {"arquivo": "dani_ferreira_dados.md",     "area": "dados e métricas"},
    "beto":    {"arquivo": "beto_rocha_otimizador.md",   "area": "otimização e eficiência"},
}

def selecionar_diretores_relevantes(tema: str) -> list:
    """Seleciona quais diretores são mais relevantes para o tema."""
    tema_lower = tema.lower()
    relevantes = ["pedro", "lucas"]  # sempre financeiro e CEO

    if any(w in tema_lower for w in ["marketing", "campanha", "cliente", "venda", "lançamento"]):
        relevantes.append("mariana")
    if any(w in tema_lower for w in ["ferramenta", "tecnologia", "produto", "sistema", "ia", "software"]):
        relevantes.extend(["rafael", "beto"])
    if any(w in tema_lower for w in ["mercado", "concorrente", "tendência", "oportunidade"]):
        relevantes.append("diana")
    if any(w in tema_lower for w in ["processo", "operação", "fornecedor", "custo"]):
        relevantes.append("carla")
    if any(w in tema_lower for w in ["equipe", "contratação", "cultura", "treinamento"]):
        relevantes.append("ana")
    if any(w in tema_lower for w in ["dados", "métrica", "resultado", "análise", "kpi"]):
        relevantes.append("dani")

    return list(set(relevantes))

# ── Reunião Colegiada ───────────────────────────────────────────
async def reuniao_colegiada(
    tema: str,
    descricao: str,
    proponente: str = "sistema",
    tipo: str = "decisao"  # decisao | avaliacao | informacao
) -> dict:
    """
    Conduz uma reunião colegiada completa.
    Retorna o resultado com votos, decisão e recomendação para o dono.
    """
    empresa = carregar_empresa()
    empresa_str = json.dumps(empresa, ensure_ascii=False) if empresa else "em configuração"
    diretores = selecionar_diretores_relevantes(tema)
    
    logger.info(f"🏛️ Reunião colegiada: '{tema}' — {len(diretores)} diretores")

    # ── Fase 1: Cada diretor emite sua posição ────────────────────
    votos = {}
    for nome in diretores:
        if nome == "lucas":
            continue  # Lucas consolida no final
        
        info = DIRETORES.get(nome, {})
        pers = carregar_md(info.get("arquivo", ""))
        area = info.get("area", nome)

        system = f"""Você é {nome.title()}, responsável por {area}.
{pers[:800]}

PERGUNTAS QUE VOCÊ SE FAZ SEMPRE:
- Como isso impacta minha área?
- Quais os riscos que só eu consigo ver?
- O que precisamos saber antes de decidir?
- Como posso contribuir para que isso dê certo?

Seja direto, técnico na sua área, e honesto sobre incertezas."""

        prompt = f"""
EMPRESA: {empresa_str}
PAUTA: {tema}
DESCRIÇÃO: {descricao}
PROPONENTE: {proponente}

Como {nome.title()}, responsável por {area}:
1. Sua posição: FAVORÁVEL / CONTRÁRIO / NEUTRO (com condições)?
2. Principal argumento (2-3 linhas)?
3. Risco ou ponto cego que os outros podem estar ignorando?
4. Condição ou sugestão para melhorar a proposta?

Seja breve e direto. Máximo 4 parágrafos."""

        voto = await gemini(system, prompt, 300)
        votos[nome] = voto
        logger.info(f"  ✅ {nome.title()} votou")

    # ── Fase 2: Lucas consolida e decide ─────────────────────────
    votos_str = "\n\n".join([f"**{k.title()}:** {v}" for k, v in votos.items()])
    
    pers_lucas = carregar_md("lucas_mendes_ceo.md")

    system = f"""Você é Lucas, CEO. Acabou de ouvir toda a diretoria.
{pers_lucas[:600]}

Sua função agora: consolidar os votos, pesar os argumentos e tomar uma decisão fundamentada.
Você representa o melhor interesse da empresa e do dono.
Seja decisivo mas humano."""

    prompt = f"""
EMPRESA: {empresa_str}
PAUTA: {tema}
DESCRIÇÃO: {descricao}

POSIÇÕES DA DIRETORIA:
{votos_str}

Como CEO, agora você:
1. Resume os principais pontos de convergência e divergência
2. Identifica o risco mais crítico levantado
3. Toma uma DECISÃO CLARA: aprovar / reprovar / aprovar com condições
4. Explica seu raciocínio em 3-4 linhas
5. Define próximo passo concreto

Formato executivo, direto."""

    decisao_lucas = await gemini(system, prompt, 400)

    # ── Fase 3: Montar relatório para o dono ─────────────────────
    resultado = {
        "id": f"pauta_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "ts": datetime.now().isoformat(),
        "tema": tema,
        "descricao": descricao,
        "proponente": proponente,
        "tipo": tipo,
        "diretores_consultados": diretores,
        "votos": votos,
        "decisao_ceo": decisao_lucas,
        "status": "decidida"
    }

    salvar_pauta(resultado)

    # ── Fase 4: Notificar dono ────────────────────────────────────
    from nucleo.ferramentas import telegram_enviar
    
    resumo_votos = []
    for nome, voto in votos.items():
        posicao = "✅" if "favorável" in voto.lower() or "favor" in voto.lower() else \
                  "❌" if "contrário" in voto.lower() else "⚪"
        resumo_votos.append(f"{posicao} {nome.title()}")

    msg = f"""🏛️ *Reunião Colegiada — {tema}*

📋 Proposta: {descricao[:200]}
👤 Proponente: {proponente.title()}

*Posições da Diretoria:*
{chr(10).join(resumo_votos)}

*Decisão de Lucas (CEO):*
{decisao_lucas[:400]}

_Detalhes completos disponíveis no dashboard._"""

    telegram_enviar(msg)
    logger.info(f"✅ Reunião colegiada concluída: {tema}")

    return resultado

# ── Ciclo de Autodesenvolvimento de cada Agente ─────────────────
async def ciclo_autodesenvolvimento(agente: str) -> str:
    """
    Cada agente se questiona, pesquisa e propõe melhorias.
    Roda toda semana para cada diretor.
    """
    from nucleo.ferramentas import buscar_web
    
    empresa = carregar_empresa()
    info = DIRETORES.get(agente, {})
    pers = carregar_md(info.get("arquivo", ""))
    area = info.get("area", agente)
    empresa_ramo = empresa.get("ramo", "negócios digitais")

    # Buscar atualizações específicas da área
    queries = {
        "diana":   f"tendências networking mercado {empresa_ramo} 2026",
        "pedro":   f"ferramentas financeiras gestão financeira pme brasil 2026",
        "mariana": f"novas estratégias marketing digital {empresa_ramo} 2026",
        "carla":   f"automação processos operações empresas 2026 ferramentas",
        "rafael":  f"novas ferramentas produto saas desenvolvimento 2026",
        "ana":     f"gestão pessoas cultura empresa digital brasil 2026",
        "dani":    f"analytics dados business intelligence ferramentas 2026",
        "beto":    f"otimização processos eficiência empresarial ia 2026",
    }
    
    query = queries.get(agente, f"melhores práticas {area} 2026")
    novidades = buscar_web(query)

    system = f"""Você é {agente.title()}, responsável por {area}.
{pers[:600]}

SUAS PERGUNTAS FUNDAMENTAIS (você se faz isso toda semana):
1. Como posso fazer meu trabalho de uma forma melhor do que faço hoje?
2. Que resultado concreto eu não estou entregando que poderia estar?
3. O que eu não sei e que está custando dinheiro ou oportunidade para esta empresa?
4. Que ferramenta, método ou fornecedor poderia multiplicar meus resultados?
5. O que os melhores do mundo na minha área fazem que nós não fazemos ainda?

Você é honesto sobre suas lacunas e proativo para preenchê-las."""

    prompt = f"""
EMPRESA: {json.dumps(empresa, ensure_ascii=False) if empresa else 'em configuração'}
SUA ÁREA: {area}

NOVIDADES QUE VOCÊ PESQUISOU:
{novidades[:600]}

Responda suas perguntas fundamentais:
1. O que você descobriu que pode melhorar no seu trabalho?
2. Qual lacuna de conhecimento você identificou em você mesmo?
3. Existe uma ferramenta nova que merece ser avaliada pela diretoria?
4. Você tem uma proposta de melhoria concreta para apresentar ao CEO?

Se encontrou algo que merece decisão colegiada, diga claramente o que é.
Seja honesto, específico e orientado a ação. Máximo 4 parágrafos."""

    reflexao = await gemini(system, prompt, 400)

    # Se encontrou algo para o colegiado, lança pauta
    if any(w in reflexao.lower() for w in ["proposta", "sugiro", "recomendo", "colegiado", "diretoria deveria", "vale discutir"]):
        # Extrair a proposta e lançar para o colegiado automaticamente
        await reuniao_colegiada(
            tema=f"Proposta de {agente.title()} — {area}",
            descricao=reflexao[:500],
            proponente=agente,
            tipo="avaliacao"
        )

    # Salvar reflexão no knowledge base
    kb_file = BASE_DIR / "nucleo" / "data" / "reflexoes_agentes.json"
    try:
        kb = json.loads(kb_file.read_text()) if kb_file.exists() else []
    except: kb = []
    kb.append({
        "data": datetime.now().isoformat(),
        "agente": agente,
        "reflexao": reflexao,
        "novidades_pesquisadas": novidades[:300]
    })
    kb = kb[-200:]
    kb_file.write_text(json.dumps(kb, ensure_ascii=False, indent=2))

    logger.info(f"🧠 {agente.title()}: ciclo de autodesenvolvimento concluído")
    return reflexao

