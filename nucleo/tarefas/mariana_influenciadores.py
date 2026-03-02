"""
Tarefa da Mariana: Levantamento de micro-influenciadores para VibeSchool
"""
import os, asyncio, httpx, logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.mariana")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

PROMPT = """Você é Mariana Oliveira, CMO de startup brasileira de tecnologia.
Produto: VibeSchool (vibeschool.live) — escola de IA e vibe coding para empreendedores brasileiros.

A diretoria decidiu que você deve levantar micro-influenciadores para divulgar a escola.

Escreva um relatório executivo COMPLETO em português brasileiro com:

1. CRITÉRIOS DE SELEÇÃO (seguidores, engajamento, nicho, sinais de alinhamento)
2. PLATAFORMAS E FERRAMENTAS (onde buscar, ferramentas gratuitas de análise)
3. 5 PERFIS IDEAIS DE INFLUENCIADORES (descrição detalhada de cada tipo)
4. ROTEIRO DE ABORDAGEM (mensagem de primeiro contato pronta, valores de mercado por porte, como negociar)
5. MÉTRICAS DE CAMPANHA (KPIs, como medir resultado)
6. PLANO DE EXECUÇÃO — 30 dias (semana a semana, ações concretas)

Seja específica e prática. Ações que posso executar amanhã."""

async def gerar_relatorio() -> dict:
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={"contents": [{"parts": [{"text": PROMPT}]}],
                      "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4000}}
            )
            if r.status_code == 200:
                texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                await _salvar(texto)
                return {"ok": True, "relatorio": texto}
            return {"ok": False, "erro": f"Gemini {r.status_code}"}
    except Exception as e:
        return {"ok": False, "erro": str(e)}

async def _salvar(texto: str):
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://armabaquiyqmdgwflslq.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    if not SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"{SUPABASE_URL}/rest/v1/relatorios_agentes",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                         "Content-Type": "application/json"},
                json={"agente": "mariana", "tipo": "influenciadores_vibeschool",
                      "conteudo": texto, "status": "concluido",
                      "criado_em": datetime.now().isoformat()}
            )
    except Exception as e:
        logger.warning(f"Supabase: {e}")

if __name__ == "__main__":
    result = asyncio.run(gerar_relatorio())
    if result["ok"]:
        print(result["relatorio"])
    else:
        print(f"Erro: {result['erro']}")
