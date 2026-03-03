"""
╔══════════════════════════════════════════════════════════════╗
║   INCREASE TEAM — Banco de Dados Central                 ║
║                                                             ║
║   SQLite: persistência permanente                           ║
║   Redis:  contexto rápido por agente                        ║
║                                                             ║
║   Tabelas:                                                  ║
║   - empresa       → configuração e perfil                   ║
║   - agentes       → estado, memória e contexto              ║
║   - conversas     → histórico completo por agente           ║
║   - acoes         → tudo que foi executado                  ║
║   - transacoes    → financeiro                              ║
║   - campanhas     → marketing                               ║
║   - equipe        → RH                                      ║
║   - contratos     → jurídico                                ║
║   - tarefas       → produto                                 ║
║   - fornecedores  → operações                               ║
║   - memorias      → fatos permanentes por agente            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DB_PATH = Path("nucleo/data/nucleo.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Redis
try:
    import redis as _redis_lib
    _redis = _redis_lib.from_url(os.getenv("REDIS_URL","redis://localhost:6379"), decode_responses=True)
    _redis.ping()
    REDIS_OK = True
except:
    REDIS_OK = False
    _redis = None

# ══════════════════════════════════════════════════════════════
# INICIALIZAÇÃO DO BANCO
# ══════════════════════════════════════════════════════════════

SCHEMA = """
-- Configuração da empresa
CREATE TABLE IF NOT EXISTS empresa (
    chave     TEXT PRIMARY KEY,
    valor     TEXT,
    tipo      TEXT DEFAULT 'texto',
    agente    TEXT DEFAULT 'sistema',
    criado_em TEXT,
    atualizado_em TEXT
);

-- Estado e memória de cada agente
CREATE TABLE IF NOT EXISTS agentes (
    id        TEXT PRIMARY KEY,
    nome      TEXT,
    cargo     TEXT,
    estado    TEXT DEFAULT 'ativo',
    memoria   TEXT DEFAULT '{}',   -- JSON com fatos do agente
    contexto  TEXT DEFAULT '',      -- resumo do que está fazendo
    score     REAL DEFAULT 7.0,
    atualizado_em TEXT
);

-- Histórico de todas as conversas por agente
CREATE TABLE IF NOT EXISTS conversas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    agente    TEXT NOT NULL,
    role      TEXT NOT NULL,   -- user | assistant
    conteudo  TEXT NOT NULL,
    numero    TEXT,            -- número WhatsApp
    canal     TEXT DEFAULT 'whatsapp',
    ts        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_agente ON conversas(agente, ts);

-- Todas as ações executadas
CREATE TABLE IF NOT EXISTS acoes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    agente    TEXT NOT NULL,
    tipo      TEXT NOT NULL,
    descricao TEXT,
    dados     TEXT DEFAULT '{}',
    resultado TEXT,
    status    TEXT DEFAULT 'ok',
    ts        TEXT NOT NULL
);

-- Transações financeiras
CREATE TABLE IF NOT EXISTS transacoes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo      TEXT NOT NULL,   -- receita | gasto | transferencia
    valor     REAL NOT NULL,
    categoria TEXT,
    descricao TEXT,
    parte     TEXT,            -- cliente ou fornecedor
    agente    TEXT DEFAULT 'pedro',
    status    TEXT DEFAULT 'registrado',
    ts        TEXT NOT NULL
);

-- Campanhas de marketing
CREATE TABLE IF NOT EXISTS campanhas (
    id        TEXT PRIMARY KEY,
    nome      TEXT,
    produto   TEXT,
    objetivo  TEXT,
    orcamento REAL,
    plataforma TEXT,
    status    TEXT DEFAULT 'planejada',
    dados     TEXT DEFAULT '{}',
    criado_em TEXT,
    atualizado_em TEXT
);

-- Equipe / RH
CREATE TABLE IF NOT EXISTS equipe (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT,
    cargo     TEXT NOT NULL,
    salario   REAL,
    status    TEXT DEFAULT 'ativo',
    dados     TEXT DEFAULT '{}',
    contratado_em TEXT,
    desligado_em  TEXT
);

-- Contratos
CREATE TABLE IF NOT EXISTS contratos (
    id        TEXT PRIMARY KEY,
    parte     TEXT NOT NULL,
    tipo      TEXT,
    valor     REAL,
    status    TEXT DEFAULT 'rascunho',
    clausulas TEXT,
    arquivo   TEXT,
    criado_em TEXT,
    assinado_em TEXT
);

-- Tarefas / backlog
CREATE TABLE IF NOT EXISTS tarefas (
    id        TEXT PRIMARY KEY,
    titulo    TEXT NOT NULL,
    descricao TEXT,
    agente    TEXT DEFAULT 'rafael',
    prioridade TEXT DEFAULT 'media',
    status    TEXT DEFAULT 'backlog',
    prazo     TEXT,
    criado_em TEXT,
    concluido_em TEXT
);

-- Fornecedores
CREATE TABLE IF NOT EXISTS fornecedores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    categoria TEXT,
    contato   TEXT,
    condicoes TEXT,
    status    TEXT DEFAULT 'ativo',
    dados     TEXT DEFAULT '{}',
    criado_em TEXT
);

-- Memórias permanentes por agente (fatos extraídos)
CREATE TABLE IF NOT EXISTS memorias (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    agente    TEXT NOT NULL,
    categoria TEXT NOT NULL,  -- empresa | decisao | preferencia | contexto | fato
    conteudo  TEXT NOT NULL,
    importancia INTEGER DEFAULT 5,
    ts        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mem_agente ON memorias(agente, categoria);
"""

def init_db():
    """Inicializa o banco e insere os 9 agentes."""
    with get_db() as db:
        db.executescript(SCHEMA)
        agentes = [
            ("lucas_mendes",    "Lucas Mendes",    "CEO"),
            ("mariana_oliveira","Mariana Oliveira", "CMO"),
            ("pedro_lima",      "Pedro Lima",       "CFO"),
            ("carla_santos",    "Carla Santos",     "COO"),
            ("rafael_torres",   "Rafael Torres",    "CPO"),
            ("ana_costa",       "Ana Costa",        "CHRO"),
            ("dani_ferreira",   "Dani Ferreira",    "Analista de Dados"),
            ("ze_carvalho",     "Zé Carvalho",      "Coach"),
            ("beto_rocha",      "Beto Rocha",       "Otimizador"),
        ]
        for aid, nome, cargo in agentes:
            db.execute("""
                INSERT OR IGNORE INTO agentes (id, nome, cargo, atualizado_em)
                VALUES (?, ?, ?, ?)
            """, (aid, nome, cargo, datetime.now().isoformat()))
        db.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

# ══════════════════════════════════════════════════════════════
# EMPRESA
# ══════════════════════════════════════════════════════════════

def empresa_set(chave: str, valor: str, agente: str = "sistema"):
    with get_db() as db:
        db.execute("""
            INSERT INTO empresa (chave, valor, agente, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                valor=excluded.valor, agente=excluded.agente, atualizado_em=excluded.atualizado_em
        """, (chave, valor, agente, datetime.now().isoformat(), datetime.now().isoformat()))
        db.commit()

def empresa_get(chave: str) -> Optional[str]:
    with get_db() as db:
        r = db.execute("SELECT valor FROM empresa WHERE chave=?", (chave,)).fetchone()
        return r["valor"] if r else None

def empresa_getall() -> dict:
    with get_db() as db:
        rows = db.execute("SELECT chave, valor FROM empresa").fetchall()
        return {r["chave"]: r["valor"] for r in rows}

# ══════════════════════════════════════════════════════════════
# CONVERSAS (histórico por agente)
# ══════════════════════════════════════════════════════════════

def conv_salvar(agente: str, role: str, conteudo: str, numero: str = "", canal: str = "whatsapp"):
    ts = datetime.now().isoformat()
    with get_db() as db:
        db.execute("""
            INSERT INTO conversas (agente, role, conteudo, numero, canal, ts)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agente, role, conteudo[:4000], numero, canal, ts))
        db.commit()
    # Redis para acesso rápido
    if REDIS_OK:
        key = f"nucleo:hist:{agente}"
        msg = json.dumps({"role": role, "conteudo": conteudo[:500], "ts": ts[:16]})
        _redis.rpush(key, msg)
        _redis.ltrim(key, -50, -1)  # manter últimas 50 por agente
        _redis.expire(key, 86400 * 7)  # 7 dias

def conv_historico(agente: str, n: int = 20) -> list[dict]:
    """Retorna histórico recente de um agente."""
    # Tentar Redis primeiro
    if REDIS_OK:
        key = f"nucleo:hist:{agente}"
        msgs = _redis.lrange(key, -n, -1)
        if msgs:
            result = []
            for m in msgs:
                try: result.append(json.loads(m))
                except: pass
            return result
    # Fallback SQLite
    with get_db() as db:
        rows = db.execute("""
            SELECT role, conteudo, ts FROM conversas
            WHERE agente=? ORDER BY id DESC LIMIT ?
        """, (agente, n)).fetchall()
        return [{"role": r["role"], "conteudo": r["conteudo"], "ts": r["ts"][:16]} for r in reversed(rows)]

def conv_historico_texto(agente: str, n: int = 15) -> str:
    """Formata histórico para incluir no prompt."""
    msgs = conv_historico(agente, n)
    if not msgs:
        return "Sem histórico anterior."
    nomes = {"user": "José", "assistant": agente.split("_")[0].title()}
    return "\n".join(f"[{m['ts']}] {nomes.get(m['role'], m['role'])}: {m['conteudo'][:200]}" for m in msgs)

# ══════════════════════════════════════════════════════════════
# MEMÓRIAS PERMANENTES
# ══════════════════════════════════════════════════════════════

def mem_salvar(agente: str, categoria: str, conteudo: str, importancia: int = 5):
    with get_db() as db:
        db.execute("""
            INSERT INTO memorias (agente, categoria, conteudo, importancia, ts)
            VALUES (?, ?, ?, ?, ?)
        """, (agente, categoria, conteudo, importancia, datetime.now().isoformat()))
        db.commit()

def mem_buscar(agente: str, categoria: str = None, n: int = 10) -> list[dict]:
    with get_db() as db:
        if categoria:
            rows = db.execute("""
                SELECT categoria, conteudo, importancia, ts FROM memorias
                WHERE agente=? AND categoria=?
                ORDER BY importancia DESC, id DESC LIMIT ?
            """, (agente, categoria, n)).fetchall()
        else:
            rows = db.execute("""
                SELECT categoria, conteudo, importancia, ts FROM memorias
                WHERE agente=? ORDER BY importancia DESC, id DESC LIMIT ?
            """, (agente, n)).fetchall()
        return [dict(r) for r in rows]

def mem_contexto_agente(agente: str) -> str:
    """Monta contexto completo de memória para o prompt do agente."""
    empresa = empresa_getall()
    mems    = mem_buscar(agente, n=15)
    hist    = conv_historico_texto(agente, n=15)

    linhas = [f"═══ MEMÓRIA DO {agente.upper()} ═══\n"]

    # Empresa
    if empresa:
        linhas.append("🏢 EMPRESA:")
        for k, v in empresa.items():
            linhas.append(f"  • {k}: {v}")

    # Memórias do agente
    if mems:
        linhas.append("\n🧠 FATOS QUE SEI:")
        for m in mems:
            linhas.append(f"  [{m['categoria']}] {m['conteudo']}")

    # Histórico recente
    linhas.append(f"\n💬 HISTÓRICO RECENTE:\n{hist}")

    return "\n".join(linhas)

# ══════════════════════════════════════════════════════════════
# AÇÕES
# ══════════════════════════════════════════════════════════════

def acao_registrar(agente: str, tipo: str, descricao: str, dados: dict = {}, resultado: str = "ok"):
    with get_db() as db:
        db.execute("""
            INSERT INTO acoes (agente, tipo, descricao, dados, resultado, ts)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agente, tipo, descricao, json.dumps(dados, ensure_ascii=False), resultado, datetime.now().isoformat()))
        db.commit()
    # Salvar também como memória
    mem_salvar(agente, "acao", f"{tipo}: {descricao}", importancia=6)

# ══════════════════════════════════════════════════════════════
# HELPERS POR AGENTE
# ══════════════════════════════════════════════════════════════

# Financeiro
def fin_registrar(tipo, valor, categoria, descricao="", parte="", agente="pedro"):
    with get_db() as db:
        db.execute("""
            INSERT INTO transacoes (tipo, valor, categoria, descricao, parte, agente, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tipo, float(valor), categoria, descricao, parte, agente, datetime.now().isoformat()))
        db.commit()

def fin_saldo() -> dict:
    with get_db() as db:
        receitas = db.execute("SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE tipo='receita'").fetchone()[0]
        gastos   = db.execute("SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE tipo='gasto'").fetchone()[0]
        return {"receitas": receitas, "gastos": gastos, "saldo": receitas - gastos}

# Marketing
def camp_salvar(id, nome, produto, orcamento, plataforma, objetivo, dados={}):
    with get_db() as db:
        db.execute("""
            INSERT INTO campanhas (id, nome, produto, orcamento, plataforma, objetivo, dados, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET status=excluded.status, atualizado_em=excluded.atualizado_em
        """, (id, nome, produto, orcamento, plataforma, objetivo, json.dumps(dados), datetime.now().isoformat(), datetime.now().isoformat()))
        db.commit()

def camp_listar() -> list:
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM campanhas ORDER BY criado_em DESC").fetchall()]

# RH
def rh_contratar(cargo, nome="", salario=0, dados={}):
    with get_db() as db:
        db.execute("""
            INSERT INTO equipe (nome, cargo, salario, dados, contratado_em)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, cargo, salario, json.dumps(dados), datetime.now().isoformat()))
        db.commit()

def rh_equipe() -> list:
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM equipe WHERE status='ativo'").fetchall()]

# Tarefas
def task_criar(titulo, descricao="", agente="rafael", prioridade="media", prazo=None):
    n = 1
    with get_db() as db:
        n = (db.execute("SELECT COUNT(*) FROM tarefas").fetchone()[0] or 0) + 1
        tid = f"TASK-{n:03d}"
        db.execute("""
            INSERT INTO tarefas (id, titulo, descricao, agente, prioridade, prazo, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tid, titulo, descricao, agente, prioridade, prazo, datetime.now().isoformat()))
        db.commit()
        return tid

def task_listar(status="backlog") -> list:
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM tarefas WHERE status=? ORDER BY criado_em DESC", (status,)).fetchall()]

# Contratos
def contrato_criar(parte, tipo="", valor=0):
    cid = f"CTR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    with get_db() as db:
        db.execute("""
            INSERT INTO contratos (id, parte, tipo, valor, criado_em)
            VALUES (?, ?, ?, ?, ?)
        """, (cid, parte, tipo, valor, datetime.now().isoformat()))
        db.commit()
    return cid

# Fornecedores
def forn_adicionar(nome, categoria="", contato="", condicoes=""):
    with get_db() as db:
        db.execute("""
            INSERT INTO fornecedores (nome, categoria, contato, condicoes, criado_em)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, categoria, contato, condicoes, datetime.now().isoformat()))
        db.commit()

def forn_listar() -> list:
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM fornecedores WHERE status='ativo'").fetchall()]

# ══════════════════════════════════════════════════════════════
# EXTRATOR AUTOMÁTICO DE FATOS
# ══════════════════════════════════════════════════════════════

import re

PADROES_EXTRACAO = {
    "ramo":        [r"ramo\s+(?:[ée]\s+)?(.+)", r"(?:somos|empresa)\s+de\s+(.+)"],
    "produto":     [r"produto\s+(?:[ée]\s+)?(.+)", r"(?:vendemos|vendo)\s+(.+)"],
    "publico_alvo":[r"público.alvo\s+(?:[ée]\s+)?(.+)"],
    "meta":        [r"meta\s+de\s+faturamento\s+r?\$?\s*([\d.,]+\w*)"],
    "nome_empresa":[r"nome\s+da\s+empresa\s+(?:[ée]\s+)?(.+)"],
    "missao":      [r"missão\s+(?:[ée]\s+)?(.+)"],
    "visao":       [r"visão\s+(?:[ée]\s+)?(.+)"],
}

def extrair_fatos(texto: str, agente: str = "lucas_mendes"):
    """Extrai fatos do texto e salva no banco."""
    for campo, padroes in PADROES_EXTRACAO.items():
        for p in padroes:
            m = re.search(p, texto, re.IGNORECASE)
            if m:
                valor = m.group(1).strip().rstrip(".")
                empresa_set(campo, valor, agente)
                mem_salvar(agente, "empresa", f"{campo}: {valor}", importancia=8)
                break

# ══════════════════════════════════════════════════════════════
# INICIALIZAR
# ══════════════════════════════════════════════════════════════

# Auto-inicializa na importação
try:
    init_db()
except Exception as e:
    print(f"[DB] Erro na inicialização: {e}")
