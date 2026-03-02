"""
Sala de Reunião Virtual — Backend
Gerencia sessões, orquestra turnos, gera TTS e transmite via WebSocket.
"""
import os, json, asyncio, uuid, logging, base64
from datetime import datetime
from pathlib import Path
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.sala")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SALAS_DIR = BASE_DIR / "nucleo" / "data" / "salas"
SALAS_DIR.mkdir(parents=True, exist_ok=True)

# ── Vozes por agente ─────────────────────────────────────────────
VOZES = {
    "lucas":   {"voz": "onyx",   "nome": "Lucas Mendes",  "cargo": "CEO",    "genero": "M"},
    "pedro":   {"voz": "echo",   "nome": "Pedro Lima",    "cargo": "CFO",    "genero": "M"},
    "rafael":  {"voz": "fable",  "nome": "Rafael Torres", "cargo": "CPO",    "genero": "M"},
    "ze":      {"voz": "alloy",  "nome": "Zé Carvalho",   "cargo": "Coach",  "genero": "M"},
    "beto":    {"voz": "echo",   "nome": "Beto Rocha",    "cargo": "COO",    "genero": "M"},
    "diana":   {"voz": "nova",   "nome": "Diana Vaz",     "cargo": "CNO",    "genero": "F"},
    "mariana": {"voz": "shimmer","nome": "Mariana Oliveira","cargo": "CMO",  "genero": "F"},
    "carla":   {"voz": "nova",   "nome": "Carla Santos",  "cargo": "COO",    "genero": "F"},
    "ana":     {"voz": "shimmer","nome": "Ana Costa",     "cargo": "CHRO",   "genero": "F"},
    "dani":    {"voz": "nova",   "nome": "Dani Ferreira", "cargo": "Dados",  "genero": "F"},
}

AGENTES_DIR = BASE_DIR / "nucleo" / "agentes"

def carregar_md(agente: str) -> str:
    arquivos = {
        "lucas": "lucas_mendes_ceo.md", "pedro": "pedro_lima_cfo.md",
        "diana": "diana_vaz_cno.md", "mariana": "mariana_oliveira_cmo.md",
        "carla": "carla_santos_coo.md", "rafael": "rafael_torres_cpo.md",
        "ana": "ana_costa_chro.md", "dani": "dani_ferreira_dados.md",
        "ze": "ze_carvalho_coach.md", "beto": "beto_rocha_otimizador.md",
    }
    f = AGENTES_DIR / arquivos.get(agente, "")
    return f.read_text() if f.exists() else ""

def carregar_empresa() -> dict:
    mem = BASE_DIR / "nucleo" / "data" / "memoria.json"
    try:
        return json.loads(mem.read_text()).get("empresa", {}) if mem.exists() else {}
    except: return {}

# ── TTS — gera áudio mp3 base64 ──────────────────────────────────
async def gerar_audio(texto: str, agente: str) -> Optional[str]:
    """Retorna áudio em base64 ou None se falhar."""
    if not OPENAI_API_KEY:
        return None
    voz_info = VOZES.get(agente, {})
    voz = voz_info.get("voz", "alloy")
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": "tts-1", "input": texto[:500], "voice": voz}
            )
            if r.status_code == 200:
                return base64.b64encode(r.content).decode()
    except Exception as e:
        logger.error(f"TTS erro: {e}")
    return None

# ── Gemini para fala dos agentes ─────────────────────────────────
async def gemini_fala(system: str, prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.9, "maxOutputTokens": 200}
                }
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[{e}]"

# ── Sessão de Sala ───────────────────────────────────────────────
class SalaReuniao:
    def __init__(self, sala_id: str, tema: str, agentes: list, empresa: dict):
        self.id = sala_id
        self.tema = tema
        self.agentes = agentes  # lista de nomes
        self.empresa = empresa
        self.historico = []  # [{agente, fala, ts}]
        self.status = "aguardando"  # aguardando | em_andamento | encerrada
        self.decisao_final = ""
        self.mensagens_externas = []  # mensagens do cliente via WhatsApp
        self.ws_connections = set()
        self.turno_atual = 0
        self.criado_em = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id, "tema": self.tema, "agentes": self.agentes,
            "status": self.status, "historico": self.historico,
            "decisao_final": self.decisao_final, "criado_em": self.criado_em,
            "empresa": self.empresa
        }

    async def broadcast(self, evento: dict):
        """Envia evento para todos os WebSockets conectados."""
        msg = json.dumps(evento, ensure_ascii=False)
        mortos = set()
        for ws in self.ws_connections:
            try:
                await ws.send_text(msg)
            except:
                mortos.add(ws)
        self.ws_connections -= mortos

    async def conduzir_reuniao(self):
        """Orquestra a reunião completa."""
        self.status = "em_andamento"
        empresa_str = json.dumps(self.empresa, ensure_ascii=False) if self.empresa else "em configuração"
        historico_str = ""

        await self.broadcast({"tipo": "inicio", "tema": self.tema, "agentes": self.agentes})
        await asyncio.sleep(1)

        # Fase 1: Lucas abre a reunião
        lucas_abertura = await self._fala_agente(
            "lucas",
            f"Você está abrindo uma reunião de diretoria sobre: {self.tema}\n"
            f"Presentes: {', '.join([VOZES[a]['nome'] for a in self.agentes if a in VOZES])}\n"
            f"Empresa: {empresa_str}\n\n"
            "Faça uma abertura de 2-3 frases: apresente o tema, a urgência e passe a palavra para o primeiro diretor.",
            historico_str
        )
        historico_str += f"\nLucas: {lucas_abertura}"
        await asyncio.sleep(2)

        # Fase 2: Cada agente fala na sua vez (2 rodadas)
        agentes_sem_lucas = [a for a in self.agentes if a != "lucas"]
        
        for rodada in range(2):
            # Injetar mensagem do cliente se houver
            if self.mensagens_externas:
                msg_cliente = self.mensagens_externas.pop(0)
                await self.broadcast({
                    "tipo": "mensagem_cliente",
                    "texto": f"💬 Direção do proprietário: {msg_cliente}"
                })
                historico_str += f"\n[PROPRIETÁRIO]: {msg_cliente}"

            for agente in agentes_sem_lucas:
                prompt_agente = (
                    f"Reunião sobre: {self.tema}\n"
                    f"Empresa: {empresa_str}\n"
                    f"Histórico da reunião até agora:\n{historico_str}\n\n"
                    f"É sua vez de falar. Contribua com sua perspectiva da área de "
                    f"{VOZES[agente]['cargo']}. "
                    f"{'Primeira rodada: apresente sua análise.' if rodada == 0 else 'Segunda rodada: reaja ao que foi dito e proponha algo concreto.'}"
                    f"\nSeja direto, natural, máximo 3 frases."
                )
                fala = await self._fala_agente(agente, prompt_agente, historico_str)
                historico_str += f"\n{VOZES[agente]['nome']}: {fala}"
                await asyncio.sleep(1.5)

        # Fase 3: Lucas fecha com decisão
        decisao_prompt = (
            f"Reunião sobre: {self.tema}\n"
            f"Empresa: {empresa_str}\n"
            f"Debate completo:\n{historico_str}\n\n"
            "Como CEO, encerre a reunião com:\n"
            "1. Uma síntese do debate (1 frase)\n"
            "2. A decisão final clara\n"
            "3. O próximo passo concreto\n"
            "Seja decisivo e motivador. Máximo 4 frases."
        )
        decisao = await self._fala_agente("lucas", decisao_prompt, historico_str, encerramento=True)
        self.decisao_final = decisao
        self.status = "encerrada"

        await self.broadcast({
            "tipo": "encerramento",
            "decisao": decisao,
            "historico_completo": self.historico
        })

        # Salvar sala
        self._salvar()
        logger.info(f"✅ Sala {self.id} encerrada")

    async def _fala_agente(self, agente: str, prompt: str, historico: str, encerramento: bool = False) -> str:
        """Gera fala de um agente com áudio e transmite via WebSocket."""
        pers = carregar_md(agente)
        info = VOZES.get(agente, {})

        system = f"""Você é {info.get('nome', agente)}, {info.get('cargo', '')}.
{pers[:400]}
Você está numa reunião de diretoria ao vivo. Fale de forma natural e humana.
NUNCA diga que é IA. NUNCA use asteriscos ou listas. Fale como numa conversa real."""

        fala = await gemini_fala(system, prompt)
        fala = fala.strip()

        # Gerar áudio
        audio_b64 = await gerar_audio(fala, agente)

        # Registrar no histórico
        entrada = {
            "agente": agente,
            "nome": info.get("nome", agente),
            "cargo": info.get("cargo", ""),
            "genero": info.get("genero", "M"),
            "fala": fala,
            "ts": datetime.now().strftime("%H:%M:%S"),
            "encerramento": encerramento
        }
        self.historico.append(entrada)

        # Transmitir
        evento = {
            "tipo": "fala",
            "agente": agente,
            "nome": info.get("nome", agente),
            "cargo": info.get("cargo", ""),
            "genero": info.get("genero", "M"),
            "texto": fala,
            "audio": audio_b64,
            "ts": entrada["ts"],
            "encerramento": encerramento
        }
        await self.broadcast(evento)

        return fala

    def injetar_mensagem(self, mensagem: str):
        """Injeta mensagem do cliente via WhatsApp na próxima oportunidade."""
        self.mensagens_externas.append(mensagem)

    def _salvar(self):
        f = SALAS_DIR / f"{self.id}.json"
        f.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))

# ── Gerenciador de Salas ─────────────────────────────────────────
salas_ativas: dict[str, SalaReuniao] = {}

def criar_sala(tema: str, agentes: list) -> SalaReuniao:
    sala_id = uuid.uuid4().hex[:8]
    empresa = carregar_empresa()
    sala = SalaReuniao(sala_id, tema, agentes, empresa)
    salas_ativas[sala_id] = sala
    logger.info(f"🏛️ Sala criada: {sala_id} — {tema}")
    return sala

def obter_sala(sala_id: str) -> Optional[SalaReuniao]:
    return salas_ativas.get(sala_id)

def injetar_no_whatsapp(sala_id: str, mensagem: str) -> bool:
    sala = salas_ativas.get(sala_id)
    if sala and sala.status == "em_andamento":
        sala.injetar_mensagem(mensagem)
        return True
    return False
