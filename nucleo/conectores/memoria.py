"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Memória Connector                       ║
║   Pinecone (vetorial) + Supabase (estruturado) + Redis (cache)║
║                                                             ║
║   Cada agente tem sua própria "memória":                    ║
║   • Curto prazo: Redis (TTL 24h) — contexto da sessão       ║
║   • Médio prazo: Supabase — decisões, tarefas, eventos      ║
║   • Longo prazo: Pinecone — conhecimento semântico vetorial ║
║                                                             ║
║   Funções:                                                  ║
║   • lembrar(agente, contexto) → recupera memórias relevantes║
║   • memorizar(agente, conteudo) → salva nova memória        ║
║   • esquecer(agente, topico) → remove memórias por tópico   ║
║   • resumo_agente(agente) → estado completo do agente       ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.memoria")

MEMORIA_DIR = Path("nucleo/logs/memoria_local")


# ──────────────────────────────────────────────────────────────
# Tipos de memória
# ──────────────────────────────────────────────────────────────

@dataclass
class Memoria:
    agente_id: str
    conteudo: str
    tipo: str                    # "decisao" | "tarefa" | "interacao" | "aprendizado" | "contexto"
    relevancia: float = 1.0      # 0.0 – 1.0
    tags: list = None
    ts: str = None
    id: str = None

    def __post_init__(self):
        self.ts = self.ts or datetime.now().isoformat()
        self.tags = self.tags or []
        self.id = self.id or hashlib.md5(
            f"{self.agente_id}{self.conteudo}{self.ts}".encode()
        ).hexdigest()[:12]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_pinecone_metadata(self) -> dict:
        return {
            "agente_id": self.agente_id,
            "tipo": self.tipo,
            "conteudo": self.conteudo[:500],  # Pinecone limita metadata
            "tags": ",".join(self.tags),
            "relevancia": self.relevancia,
            "ts": self.ts,
        }


# ──────────────────────────────────────────────────────────────
# Redis — memória curto prazo
# ──────────────────────────────────────────────────────────────

class MemoriaRedis:
    def __init__(self):
        self.r = None
        try:
            import redis
            url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.r = redis.from_url(url, decode_responses=True)
            self.r.ping()
            logger.info("✅ Redis conectado (memória curto prazo).")
        except Exception as e:
            logger.warning(f"Redis não disponível: {e}. Usando memória local.")

    def set(self, agente_id: str, chave: str, valor: Any, ttl_horas: float = 24):
        key = f"nucleo:{agente_id}:{chave}"
        valor_str = json.dumps(valor, ensure_ascii=False)
        ttl_seg = int(ttl_horas * 3600)

        if self.r:
            self.r.setex(key, ttl_seg, valor_str)
        else:
            self._fallback_set(key, valor_str, ttl_seg)

    def get(self, agente_id: str, chave: str) -> Optional[Any]:
        key = f"nucleo:{agente_id}:{chave}"
        raw = None

        if self.r:
            raw = self.r.get(key)
        else:
            raw = self._fallback_get(key)

        return json.loads(raw) if raw else None

    def delete(self, agente_id: str, chave: str):
        key = f"nucleo:{agente_id}:{chave}"
        if self.r:
            self.r.delete(key)

    def contexto_sessao(self, agente_id: str) -> list[dict]:
        """Retorna histórico de conversa da sessão atual."""
        return self.get(agente_id, "contexto_sessao") or []

    def adicionar_ao_contexto(self, agente_id: str, role: str, conteudo: str):
        """Adiciona mensagem ao contexto da sessão (formato OpenAI messages)."""
        historico = self.contexto_sessao(agente_id)
        historico.append({"role": role, "content": conteudo, "ts": datetime.now().isoformat()})
        # Mantém apenas as últimas 20 mensagens
        historico = historico[-20:]
        self.set(agente_id, "contexto_sessao", historico, ttl_horas=8)

    def limpar_contexto(self, agente_id: str):
        self.delete(agente_id, "contexto_sessao")

    # Fallback em arquivo quando Redis não disponível
    def _fallback_path(self, key: str) -> Path:
        MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
        safe_key = key.replace(":", "_").replace("/", "_")
        return MEMORIA_DIR / f"{safe_key}.json"

    def _fallback_set(self, key: str, valor: str, ttl: int):
        p = self._fallback_path(key)
        expira = (datetime.now() + timedelta(seconds=ttl)).isoformat()
        p.write_text(json.dumps({"valor": valor, "expira": expira}))

    def _fallback_get(self, key: str) -> Optional[str]:
        p = self._fallback_path(key)
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        if datetime.now() > datetime.fromisoformat(data["expira"]):
            p.unlink()
            return None
        return data["valor"]


# ──────────────────────────────────────────────────────────────
# Supabase — memória médio prazo
# ──────────────────────────────────────────────────────────────

class MemoriaSupabase:
    def __init__(self):
        self.client = None
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if url and key:
            try:
                from supabase import create_client
                self.client = create_client(url, key)
                logger.info("✅ Supabase conectado (memória médio prazo).")
            except Exception as e:
                logger.warning(f"Supabase não disponível: {e}")
        else:
            logger.warning("Supabase não configurado. Usando arquivo local.")

    def salvar(self, memoria: Memoria):
        dados = memoria.to_dict()
        if self.client:
            try:
                self.client.table("memorias_agentes").insert(dados).execute()
                return
            except Exception as e:
                logger.warning(f"Supabase insert falhou: {e}. Salvando local.")
        self._salvar_local(dados)

    def buscar(
        self,
        agente_id: str,
        tipo: Optional[str] = None,
        limite: int = 20,
        desde_horas: Optional[float] = None,
    ) -> list[Memoria]:
        if self.client:
            try:
                q = self.client.table("memorias_agentes").select("*").eq("agente_id", agente_id)
                if tipo:
                    q = q.eq("tipo", tipo)
                if desde_horas:
                    corte = (datetime.now() - timedelta(hours=desde_horas)).isoformat()
                    q = q.gte("ts", corte)
                r = q.order("ts", desc=True).limit(limite).execute()
                return [Memoria(**d) for d in r.data]
            except Exception as e:
                logger.warning(f"Supabase query falhou: {e}")
        return self._buscar_local(agente_id, tipo, limite)

    def resumo_agente(self, agente_id: str) -> dict:
        """Retorna estatísticas do agente baseadas nas memórias."""
        memorias = self.buscar(agente_id, limite=100)
        tipos = {}
        for m in memorias:
            tipos[m.tipo] = tipos.get(m.tipo, 0) + 1
        return {
            "agente_id": agente_id,
            "total_memorias": len(memorias),
            "por_tipo": tipos,
            "ultima_atividade": memorias[0].ts if memorias else None,
        }

    def _salvar_local(self, dados: dict):
        MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
        p = MEMORIA_DIR / f"memorias_{dados['agente_id']}.jsonl"
        with open(p, "a") as f:
            f.write(json.dumps(dados, ensure_ascii=False) + "\n")

    def _buscar_local(self, agente_id: str, tipo: Optional[str], limite: int) -> list[Memoria]:
        p = MEMORIA_DIR / f"memorias_{agente_id}.jsonl"
        if not p.exists():
            return []
        linhas = p.read_text().strip().split("\n")
        memorias = [Memoria(**json.loads(l)) for l in linhas if l]
        if tipo:
            memorias = [m for m in memorias if m.tipo == tipo]
        return list(reversed(memorias))[:limite]


# ──────────────────────────────────────────────────────────────
# Pinecone — memória longo prazo (semântica / vetorial)
# ──────────────────────────────────────────────────────────────

class MemoriaPinecone:
    def __init__(self):
        self.index = None
        self.embed_fn = None
        key = os.getenv("PINECONE_API_KEY")

        if key:
            try:
                from pinecone import Pinecone, ServerlessSpec
                pc = Pinecone(api_key=key)

                index_name = "nucleo-agentes"
                if index_name not in pc.list_indexes().names():
                    pc.create_index(
                        name=index_name,
                        dimension=768,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                    )
                self.index = pc.Index(index_name)
                logger.info("✅ Pinecone conectado (memória longo prazo).")
            except Exception as e:
                logger.warning(f"Pinecone não disponível: {e}")
        else:
            logger.warning("Pinecone não configurado. Busca semântica desativada.")

        self._init_embedder()

    def _init_embedder(self):
        """Inicializa função de embedding — usa Groq/Gemini se disponível."""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            self.embed_fn = lambda text: model.encode(text).tolist()
            logger.info("✅ Embedder local (MiniLM) ativo.")
        except ImportError:
            # Fallback: embedding simples por hash (não semântico, mas funciona)
            logger.warning("sentence-transformers não instalado. Usando embedding hash (baixa qualidade).")
            self.embed_fn = self._hash_embedding

    def _hash_embedding(self, texto: str) -> list[float]:
        """Embedding degradado por hash — substitua por modelo real."""
        import struct
        h = hashlib.sha256(texto.encode()).digest()
        floats = struct.unpack("64f", h * 4)[:64]
        norm = sum(f**2 for f in floats) ** 0.5
        base = [f / norm for f in floats]
        # Expandir para 768 dimensões replicando
        return (base * 12)[:768]

    def salvar(self, memoria: Memoria):
        if not self.index or not self.embed_fn:
            return

        try:
            vetor = self.embed_fn(memoria.conteudo)
            self.index.upsert(vectors=[{
                "id": memoria.id,
                "values": vetor,
                "metadata": memoria.to_pinecone_metadata(),
            }], namespace=memoria.agente_id)
        except Exception as e:
            logger.warning(f"Pinecone upsert falhou: {e}")

    def buscar_similar(
        self,
        agente_id: str,
        consulta: str,
        top_k: int = 5,
        filtro_tipo: Optional[str] = None,
    ) -> list[dict]:
        """Busca semântica: encontra memórias mais relevantes para a consulta."""
        if not self.index or not self.embed_fn:
            return []

        try:
            vetor_consulta = self.embed_fn(consulta)
            filtro = {"agente_id": {"$eq": agente_id}}
            if filtro_tipo:
                filtro["tipo"] = {"$eq": filtro_tipo}

            resultado = self.index.query(
                vector=vetor_consulta,
                top_k=top_k,
                filter=filtro,
                include_metadata=True,
                namespace=agente_id,
            )

            return [
                {
                    "id": m.id,
                    "score": round(m.score, 3),
                    "conteudo": m.metadata.get("conteudo", ""),
                    "tipo": m.metadata.get("tipo", ""),
                    "ts": m.metadata.get("ts", ""),
                }
                for m in resultado.matches
            ]
        except Exception as e:
            logger.warning(f"Pinecone query falhou: {e}")
            return []

    def deletar_por_agente(self, agente_id: str):
        """Remove todas as memórias de um agente (ex: reset)."""
        if self.index:
            try:
                self.index.delete(delete_all=True, namespace=agente_id)
            except Exception as e:
                logger.warning(f"Pinecone delete falhou: {e}")


# ──────────────────────────────────────────────────────────────
# Interface unificada — GerenciadorMemoria
# ──────────────────────────────────────────────────────────────

class GerenciadorMemoria:
    """
    Interface única que os agentes usam para toda operação de memória.
    Orquestra Redis (curto), Supabase (médio) e Pinecone (longo).
    """

    def __init__(self):
        self.cache   = MemoriaRedis()
        self.banco   = MemoriaSupabase()
        self.vetorial = MemoriaPinecone()

    # ── Memorizar ─────────────────────────────────────────────

    def memorizar(
        self,
        agente_id: str,
        conteudo: str,
        tipo: str = "contexto",
        relevancia: float = 0.8,
        tags: list = None,
        camadas: str = "todas",    # "todas" | "banco" | "vetorial" | "cache"
    ) -> Memoria:
        """
        Salva uma memória no(s) armazenamento(s) especificado(s).
        camadas="todas" salva nas 3 camadas.
        """
        mem = Memoria(
            agente_id=agente_id,
            conteudo=conteudo,
            tipo=tipo,
            relevancia=relevancia,
            tags=tags or [],
        )

        if camadas in ("todas", "cache"):
            self.cache.set(agente_id, f"ultima_{tipo}", conteudo, ttl_horas=24)

        if camadas in ("todas", "banco"):
            self.banco.salvar(mem)

        if camadas in ("todas", "vetorial") and relevancia >= 0.6:
            self.vetorial.salvar(mem)

        logger.debug(f"[{agente_id}] Memorizado ({tipo}): {conteudo[:60]}...")
        return mem

    # ── Lembrar ───────────────────────────────────────────────

    def lembrar(
        self,
        agente_id: str,
        consulta: str,
        top_k: int = 5,
        incluir_cache: bool = True,
    ) -> dict:
        """
        Recupera memórias relevantes para a consulta.
        Retorna contexto formatado pronto para injetar no prompt.
        """
        resultado = {
            "cache":    [],
            "banco":    [],
            "vetorial": [],
        }

        # Cache (contexto recente da sessão)
        if incluir_cache:
            resultado["cache"] = self.cache.contexto_sessao(agente_id)

        # Banco (últimas 10 memórias)
        resultado["banco"] = [
            m.to_dict() for m in self.banco.buscar(agente_id, limite=10)
        ]

        # Pinecone (memórias semanticamente similares)
        resultado["vetorial"] = self.vetorial.buscar_similar(
            agente_id, consulta, top_k=top_k
        )

        return resultado

    def lembrar_formatado(self, agente_id: str, consulta: str) -> str:
        """
        Retorna string formatada para injetar no prompt do agente.
        Inclui memórias mais relevantes de todas as camadas.
        """
        dados = self.lembrar(agente_id, consulta)
        partes = []

        if dados["vetorial"]:
            partes.append("=== MEMÓRIAS RELEVANTES ===")
            for m in dados["vetorial"][:3]:
                partes.append(f"[{m['tipo'].upper()} | score:{m['score']}] {m['conteudo']}")

        if dados["banco"]:
            partes.append("\n=== ATIVIDADE RECENTE ===")
            for m in dados["banco"][:5]:
                ts = m["ts"][:10]
                partes.append(f"[{ts}] {m['tipo']}: {m['conteudo'][:100]}")

        if dados["cache"]:
            partes.append("\n=== CONTEXTO DA SESSÃO ===")
            for msg in dados["cache"][-3:]:
                partes.append(f"[{msg['role']}]: {msg['content'][:150]}")

        return "\n".join(partes) if partes else "Sem memórias anteriores relevantes."

    # ── Atalhos por tipo ──────────────────────────────────────

    def registrar_decisao(self, agente_id: str, decisao: str, contexto: str = ""):
        self.memorizar(agente_id, f"DECISÃO: {decisao}. Contexto: {contexto}", tipo="decisao", relevancia=0.95)

    def registrar_tarefa_concluida(self, agente_id: str, tarefa: str, resultado: str):
        self.memorizar(agente_id, f"Tarefa concluída: {tarefa}. Resultado: {resultado}", tipo="tarefa", relevancia=0.8)

    def registrar_interacao(self, agente_id: str, contato: str, resumo: str):
        self.memorizar(agente_id, f"Interação com {contato}: {resumo}", tipo="interacao", relevancia=0.7)

    def registrar_aprendizado(self, agente_id: str, aprendizado: str):
        self.memorizar(agente_id, aprendizado, tipo="aprendizado", relevancia=1.0)

    def adicionar_mensagem(self, agente_id: str, role: str, conteudo: str):
        """Adiciona ao contexto de sessão (curto prazo)."""
        self.cache.adicionar_ao_contexto(agente_id, role, conteudo)

    # ── Gerenciamento ─────────────────────────────────────────

    def resumo_agente(self, agente_id: str) -> dict:
        return self.banco.resumo_agente(agente_id)

    def resetar_sessao(self, agente_id: str):
        self.cache.limpar_contexto(agente_id)
        logger.info(f"Sessão de {agente_id} resetada.")

    def resetar_tudo(self, agente_id: str):
        """CUIDADO: apaga todas as memórias do agente."""
        self.cache.limpar_contexto(agente_id)
        self.vetorial.deletar_por_agente(agente_id)
        logger.warning(f"⚠️ Memória completa de {agente_id} apagada.")


# Singleton global
memoria = GerenciadorMemoria()


# ──────────────────────────────────────────────────────────────
# SQL para criar tabela no Supabase
# ──────────────────────────────────────────────────────────────
"""
-- Execute no Supabase SQL Editor:

CREATE TABLE memorias_agentes (
    id          TEXT PRIMARY KEY,
    agente_id   TEXT NOT NULL,
    conteudo    TEXT NOT NULL,
    tipo        TEXT NOT NULL DEFAULT 'contexto',
    relevancia  FLOAT DEFAULT 0.8,
    tags        TEXT[] DEFAULT '{}',
    ts          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memorias_agente ON memorias_agentes (agente_id);
CREATE INDEX idx_memorias_tipo   ON memorias_agentes (tipo);
CREATE INDEX idx_memorias_ts     ON memorias_agentes (ts DESC);
"""

# ──────────────────────────────────────────────────────────────
# Exemplo de uso nos agentes
# ──────────────────────────────────────────────────────────────
"""
from nucleo.conectores.memoria import memoria

# Agente salva o que aprendeu
memoria.registrar_aprendizado(
    "dani_ferreira",
    "Concorrente X lança features novas toda 3ª feira. Monitorar terças-feiras."
)

# Agente registra decisão
memoria.registrar_decisao(
    "lucas_mendes",
    "Aprovar campanha Instagram de R$8.000",
    "CTR atual 2.1%, meta 3.5%. Mariana confia no criativo."
)

# Antes de responder, agente busca contexto relevante
contexto = memoria.lembrar_formatado("pedro_lima", "fluxo de caixa março")
# → injeta no prompt: "Memórias relevantes: [decisões sobre caixa...] [interações com banco...]"

# Adicionar à conversa atual
memoria.adicionar_mensagem("ana_costa", "user", "Quando João começa?")
memoria.adicionar_mensagem("ana_costa", "assistant", "João começa segunda-feira, dia 2.")
"""
