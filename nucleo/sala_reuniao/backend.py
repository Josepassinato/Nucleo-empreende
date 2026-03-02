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

def carregar_contexto_completo() -> str:
    """Carrega memória persistente completa para injetar nas reuniões."""
    linhas = []

    # Dados da empresa
    mem_file = BASE_DIR / "nucleo" / "data" / "memoria.json"
    if mem_file.exists():
        try:
            mem = json.loads(mem_file.read_text())
            emp = mem.get("empresa", {})
            if emp:
                linhas.append("=== EMPRESA ===")
                for k, v in emp.items():
                    if v: linhas.append(f"  {k}: {v}")
            decisoes = mem.get("decisoes", [])[-5:]
            if decisoes:
                linhas.append("=== DECISÕES ANTERIORES ===")
                for d in decisoes: linhas.append(f"  • {d}")
        except: pass

    # Pendências 5W2H de reuniões anteriores
    pendencias = carregar_pendencias_5w2h()
    if pendencias:
        linhas.append("=== COMPROMISSOS PENDENTES (5W2H reuniões anteriores) ===")
        for p in pendencias[:5]:
            linhas.append(f"  ⚠ [{p['responsavel']}] {p['descricao'][:100]} — prazo: {p.get('prazo','indefinido')}")

    # Ações autônomas recentes
    acoes_file = BASE_DIR / "nucleo" / "data" / "acoes_autonomas.json"
    if acoes_file.exists():
        try:
            acoes = json.loads(acoes_file.read_text())[-5:]
            if acoes:
                linhas.append("=== AÇÕES RECENTES DA DIRETORIA ===")
                for a in acoes:
                    ts = a.get("ts","")[:16]
                    linhas.append(f"  [{ts}] {a.get('agente','')}: {a.get('acao','')[:80]}")
        except: pass

    # Shared context — o que os outros agentes descobriram recentemente
    shared_file = BASE_DIR / "nucleo" / "data" / "contexto_compartilhado.json"
    if shared_file.exists():
        try:
            ctx = json.loads(shared_file.read_text())
            linhas.append("=== DESCOBERTAS RECENTES DA DIRETORIA ===")
            for agente, dados in ctx.items():
                if agente.startswith("_"): continue
                for chave, info in list(dados.items())[:3]:
                    ts = info.get("ts","")[:16]
                    linhas.append(f"  [{agente.upper()} | {ts}] {chave}: {info.get('valor','')[:100]}")
        except: pass

    return "\n".join(linhas) if linhas else ""

def carregar_pendencias_5w2h() -> list:
    """Carrega tarefas pendentes das atas anteriores."""
    pendencias = []

    # Da ata local (JSON)
    salas_files = list(SALAS_DIR.glob("*.json"))
    for f in sorted(salas_files, reverse=True)[:10]:
        try:
            sala = json.loads(f.read_text())
            if sala.get("status") == "encerrada":
                decisao = sala.get("decisao_final", "")
                # Extrair itens 5W2H da decisão
                if "✅ QUEM:" in decisao or "QUEM:" in decisao:
                    linhas = decisao.split("\n")
                    tarefa = {"descricao": sala.get("tema",""), "sala_id": sala.get("id","")}
                    for linha in linhas:
                        if "QUEM:" in linha:
                            tarefa["responsavel"] = linha.split("QUEM:")[-1].strip()
                        if "QUANDO:" in linha:
                            tarefa["prazo"] = linha.split("QUANDO:")[-1].strip()
                        if "O QUÊ:" in linha or "O QUE:" in linha:
                            tarefa["descricao"] = linha.split(":")[-1].strip()
                    if tarefa.get("responsavel"):
                        pendencias.append(tarefa)
        except: pass

    return pendencias

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

# ── Gemini para fala dos agentes — com circuit breaker ───────────
async def gemini_fala(system: str, prompt: str, tentativas: int = 3) -> str:
    """
    Gera fala do agente com retry automático.
    NUNCA retorna o erro como texto — levanta exceção para o caller tratar.
    """
    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                    json={
                        "system_instruction": {"parts": [{"text": system}]},
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 200}
                    }
                )
                if r.status_code == 200:
                    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    if texto and len(texto.strip()) > 5:
                        return texto.strip()
                    raise ValueError(f"Resposta vazia ou muito curta: '{texto}'")
                else:
                    raise ValueError(f"HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            ultimo_erro = e
            logger.warning(f"gemini_fala tentativa {tentativa+1}/{tentativas} falhou: {e}")
            if tentativa < tentativas - 1:
                await asyncio.sleep(2 * (tentativa + 1))  # backoff: 2s, 4s
    # Todas as tentativas falharam — levanta exceção real
    raise RuntimeError(f"gemini_fala falhou após {tentativas} tentativas: {ultimo_erro}")

# ── Sessão de Sala ───────────────────────────────────────────────
class SalaReuniao:
    def __init__(self, sala_id: str, tema: str, agentes: list, empresa: dict):
        self.id = sala_id
        self.tema = tema
        self.agentes = agentes  # lista de nomes
        self.empresa = empresa
        self.historico = []
        self.status = "aguardando"
        self.decisao_final = ""
        self.mensagens_externas = []
        self.ws_connections = set()
        self.turno_atual = 0
        self.criado_em = datetime.now().isoformat()
        # Memória persistente carregada no início de cada reunião
        self.contexto_persistente = carregar_contexto_completo()
        logger.info(f"📋 Contexto persistente carregado: {len(self.contexto_persistente)} chars")

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

        try:
            # Fase 1: Lucas abre a reunião anunciando o 5W2H
            lucas_abertura = await self._fala_agente(
                "lucas",
                f"Você está abrindo uma reunião de diretoria sobre: {self.tema}\n"
                f"Presentes: {', '.join([VOZES[a]['nome'] for a in self.agentes if a in VOZES])}\n"
                f"Empresa: {empresa_str}\n\n"
                "Faça a abertura em 2-3 frases:\n"
                "1. Apresente o tema e a urgência\n"
                "2. Deixe claro que a reunião SÓ termina com o 5W2H definido (O quê, Por quê, Quem, Onde, Quando, Como, Quanto)\n"
                "3. Passe a palavra para o primeiro diretor\n"
                "Seja direto. Português brasileiro.",
                historico_str
            )
            historico_str += f"\nLucas: {lucas_abertura}"
            await asyncio.sleep(2)

            # Fase 2: Cada agente fala na sua vez (2 rodadas)
            agentes_sem_lucas = [a for a in self.agentes if a != "lucas"]

            # Mapa de conflitos estruturados — quem questiona quem
            CONFLITOS = {
                "pedro":   {"alvo": "mariana", "angulo": "Questione o custo e ROI do que a Mariana propôs. Qual o impacto no caixa?"},
                "rafael":  {"alvo": "mariana", "angulo": "Questione se o que foi proposto resolve dor real do usuário ou é só hype."},
                "carla":   {"alvo": "rafael",  "angulo": "Questione se o produto proposto é operacionalmente viável. Como escala?"},
                "dani":    {"alvo": None,       "angulo": "Questione qualquer afirmação sem dado concreto feita na reunião."},
                "beto":    {"alvo": "mariana",  "angulo": "Existe forma mais barata de testar essa ideia antes de investir?"},
            }
            
            for rodada in range(2):
                if self.mensagens_externas:
                    msg_cliente = self.mensagens_externas.pop(0)
                    await self.broadcast({
                        "tipo": "mensagem_cliente",
                        "texto": f"💬 Direção do proprietário: {msg_cliente}"
                    })
                    historico_str += f"\n[PROPRIETÁRIO]: {msg_cliente}"

                for agente in agentes_sem_lucas:
                    conflito_info = CONFLITOS.get(agente, {})

                    if rodada == 0:
                        angulo = f"Contribua com sua análise da área de {VOZES[agente]['cargo']}."
                    else:
                        # Rodada 2: conflito estruturado
                        angulo = conflito_info.get("angulo",
                            f"Reaja ao que foi dito. Proponha algo concreto ou questione o que está vago.")

                    prompt_agente = (
                        f"Reunião sobre: {self.tema}\n"
                        f"Empresa: {empresa_str}\n"
                        f"Histórico da reunião:\n{historico_str}\n\n"
                        f"{angulo}\n"
                        f"{'Primeira rodada: apresente sua análise com dados.' if rodada == 0 else 'Segunda rodada: questione, contradiga se necessário, proponha algo concreto.'}"
                        f"\nSeja direto. Máximo 3 frases. Português brasileiro."
                    )
                    fala = await self._fala_agente(agente, prompt_agente, historico_str)
                    historico_str += f"\n{VOZES[agente]['nome']}: {fala}"
                    await asyncio.sleep(1.5)

            # Fase 3: Lucas fecha com 5W2H obrigatório
            decisao_prompt = (
                f"Reunião sobre: {self.tema}\n"
                f"Empresa: {empresa_str}\n"
                f"Debate completo:\n{historico_str}\n\n"
                "Como CEO, encerre a reunião aplicando o 5W2H obrigatório.\n"
                "A reunião SÓ termina com todos os 7 campos definidos.\n\n"
                "Primeiro faça uma síntese do debate em 1 frase.\n"
                "Depois apresente o 5W2H completo neste formato exato:\n\n"
                "✅ O QUÊ: [ação concreta e específica decidida]\n"
                "✅ POR QUÊ: [razão de negócio + qual métrica isso move]\n"
                "✅ QUEM: [nome do responsável único pela execução]\n"
                "✅ ONDE: [sistema, canal ou ambiente de execução]\n"
                "✅ QUANDO: [data específica de entrega]\n"
                "✅ COMO: [método, abordagem ou ferramentas]\n"
                "✅ QUANTO: [custo estimado em R$ e horas]\n\n"
                "Finalize confirmando o compromisso com o responsável: '[Nome], você confirma?'\n"
                "Se algum campo não foi definido no debate, você mesmo define com base no contexto.\n"
                "Seja direto e decisivo. Português brasileiro."
            )
            decisao = await self._fala_agente("lucas", decisao_prompt, historico_str, encerramento=True)
            self.decisao_final = decisao
            self.status = "encerrada"

            await self.broadcast({
                "tipo": "encerramento",
                "decisao": decisao,
                "historico_completo": self.historico
            })

            self._salvar()

            # Salvar ata no Supabase (não bloqueia)
            try:
                from nucleo.sala_reuniao.ata import salvar_ata
                asyncio.create_task(salvar_ata(self))
                logger.info(f"📋 Ata sendo salva — sala {self.id}")
            except Exception as ata_err:
                logger.warning(f"Ata não salva: {ata_err}")

            logger.info(f"✅ Sala {self.id} encerrada")

        except Exception as e:
            logger.error(f"❌ Erro na reunião {self.id}: {e}", exc_info=True)
            self.status = "erro"
            await self.broadcast({
                "tipo": "erro",
                "mensagem": str(e),
                "detalhe": "Verifique as API keys no .env do servidor"
            })

    async def _fala_agente(self, agente: str, prompt: str, historico: str, encerramento: bool = False) -> str:
        """Gera fala de um agente com áudio e transmite via WebSocket."""
        pers = carregar_md(agente)
        info = VOZES.get(agente, {})

        try:
            from nucleo.sala_reuniao.estilos_fala import ESTILOS, REGRAS_GERAIS
            estilo = ESTILOS.get(agente, "")
        except:
            estilo = ""
            REGRAS_GERAIS = ""

        system = f"""{estilo}
{REGRAS_GERAIS}
{pers[:300] if pers else 'startup de tech brasileira'}

CONTEXTO PERMANENTE DA EMPRESA:
{self.contexto_persistente}

NUNCA diga que é IA. ZERO asteriscos. ZERO listas. Fale em voz alta naturalmente.
Se nao souber algo com certeza, diga: "Nao tenho esse dado. Precisamos medir." ou "Isso vai alem da minha area - sugiro consultar um especialista."
"""

        # Circuit breaker: se gemini_fala falhar, pausa reunião e notifica
        try:
            fala = await gemini_fala(system, prompt)
            fala = fala.strip()
        except RuntimeError as e:
            logger.error(f"❌ Circuit breaker ativado — {agente}: {e}")
            # Notifica no frontend que este agente falhou
            await self.broadcast({
                "tipo": "aviso",
                "mensagem": f"⚠ {info.get('nome', agente)} teve problema de conexão. Continuando sem ele."
            })
            # Retorna fala de fallback segura — não o erro
            return f"[Conexão instável. Continuando.]"

        # Gerar áudio — multi-provider (ElevenLabs > Gemini > OpenAI)
        audio_b64 = None
        try:
            from nucleo.sala_reuniao.tts_engine import gerar_audio_multi
            audio_b64 = await gerar_audio_multi(fala, agente)
        except Exception as e:
            logger.warning(f"TTS engine erro: {e}")
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
