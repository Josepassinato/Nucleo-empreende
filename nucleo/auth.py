"""
╔══════════════════════════════════════════════════════════════╗
║   INCREASE TEAM — Autenticação                              ║
║                                                             ║
║   POST /api/auth/registrar  → cria conta nova               ║
║   POST /api/auth/login      → autentica e retorna JWT       ║
║   GET  /api/auth/me         → dados da conta autenticada    ║
║   POST /api/auth/empresa    → cria empresa na conta         ║
╚══════════════════════════════════════════════════════════════╝
"""
import os, uuid, sqlite3, hashlib, hmac, base64, json, logging
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional

logger = logging.getLogger("nucleo.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

DB_PATH = Path("nucleo/data/nucleo.db")
SECRET   = os.getenv("JWT_SECRET", "increase-team-secret-2026-change-in-prod")
TOKEN_EXP_DAYS = 30

# ── Pydantic Models ──────────────────────────────────────────
class RegistrarRequest(BaseModel):
    nome:      str
    email:     str
    senha:     str
    whatsapp:  Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    senha: str

class EmpresaRequest(BaseModel):
    nome:     str
    segmento: Optional[str] = None
    porte:    Optional[str] = None

# ── Helpers ──────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_senha(senha: str) -> str:
    """SHA-256 com salt fixo derivado do SECRET. Simples e sem deps extras."""
    salt = SECRET[:16].encode()
    dk = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt, 200_000)
    return base64.b64encode(dk).decode()

def verificar_senha(senha: str, hash_stored: str) -> bool:
    return hmac.compare_digest(hash_senha(senha), hash_stored)

# ── JWT simples sem biblioteca externa ───────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + '=' * (pad % 4))

def criar_token(conta_id: str, empresa_id: Optional[str] = None,
                empresas: list = []) -> str:
    header  = _b64url(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    payload = _b64url(json.dumps({
        "sub":        conta_id,
        "empresa_id": empresa_id,
        "empresas":   empresas,
        "exp":        int((datetime.utcnow() + timedelta(days=TOKEN_EXP_DAYS)).timestamp()),
        "iat":        int(datetime.utcnow().timestamp()),
    }).encode())
    msg = f"{header}.{payload}"
    sig = _b64url(hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest())
    return f"{msg}.{sig}"

def verificar_token(token: str) -> dict:
    try:
        header, payload, sig = token.split('.')
        msg = f"{header}.{payload}"
        expected = _b64url(hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=401, detail="Token inválido")
        data = json.loads(_b64url_decode(payload))
        if data.get("exp", 0) < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail="Token expirado")
        return data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

def get_current_conta(request: Request) -> dict:
    """Dependency: extrai e valida JWT do header Authorization."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Não autenticado")
    return verificar_token(auth[7:])

# ── Rotas ────────────────────────────────────────────────────

@router.post("/registrar")
async def registrar(body: RegistrarRequest):
    """Cria nova conta. Retorna JWT imediatamente."""
    email = body.email.strip().lower()
    nome  = body.nome.strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="E-mail inválido")
    if len(body.senha) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")
    if not nome:
        raise HTTPException(status_code=400, detail="Nome obrigatório")

    conn = get_conn()
    try:
        # Verificar se email já existe
        existe = conn.execute("SELECT id FROM contas WHERE email=?", (email,)).fetchone()
        if existe:
            raise HTTPException(status_code=409, detail="E-mail já cadastrado")

        conta_id  = str(uuid.uuid4())
        agora     = datetime.now().isoformat()
        senha_h   = hash_senha(body.senha)

        conn.execute("""
            INSERT INTO contas (id, nome, email, senha_hash, whatsapp, plano, ativo, criado_em)
            VALUES (?, ?, ?, ?, ?, 'starter', 1, ?)
        """, (conta_id, nome, email, senha_h, body.whatsapp or "", agora))
        conn.commit()

        token = criar_token(conta_id, empresa_id=None, empresas=[])
        logger.info(f"✅ Nova conta registrada: {email}")

        return JSONResponse({
            "token": token,
            "conta": {
                "id":              conta_id,
                "nome":            nome,
                "email":           email,
                "plano":           "starter",
                "empresas_count":  0,
            }
        })
    finally:
        conn.close()


@router.post("/login")
async def login(body: LoginRequest):
    """Autentica e retorna JWT com lista de empresas da conta."""
    email = body.email.strip().lower()

    conn = get_conn()
    try:
        conta = conn.execute(
            "SELECT * FROM contas WHERE email=? AND ativo=1", (email,)
        ).fetchone()

        if not conta or not verificar_senha(body.senha, conta["senha_hash"]):
            raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

        # Buscar empresas da conta
        rows = conn.execute(
            "SELECT id, nome, status FROM empresas WHERE conta_id=?", (conta["id"],)
        ).fetchall()
        empresas = [{"id": r["id"], "nome": r["nome"], "status": r["status"]} for r in rows]
        empresa_ativa = empresas[0]["id"] if empresas else None

        # Atualizar último acesso
        conn.execute(
            "UPDATE contas SET ultimo_acesso=? WHERE id=?",
            (datetime.now().isoformat(), conta["id"])
        )
        conn.commit()

        token = criar_token(conta["id"], empresa_id=empresa_ativa, empresas=[e["id"] for e in empresas])
        logger.info(f"✅ Login: {email} ({len(empresas)} empresa(s))")

        return JSONResponse({
            "token": token,
            "conta": {
                "id":             conta["id"],
                "nome":           conta["nome"],
                "email":          conta["email"],
                "plano":          conta["plano"],
                "empresas":       empresas,
                "empresas_count": len(empresas),
            }
        })
    finally:
        conn.close()


@router.get("/me")
async def me(token_data: dict = Depends(get_current_conta)):
    """Retorna dados da conta autenticada."""
    conn = get_conn()
    try:
        conta = conn.execute(
            "SELECT id, nome, email, plano, criado_em FROM contas WHERE id=?",
            (token_data["sub"],)
        ).fetchone()
        if not conta:
            raise HTTPException(status_code=404, detail="Conta não encontrada")

        empresas = conn.execute(
            "SELECT id, nome, segmento, status FROM empresas WHERE conta_id=?",
            (token_data["sub"],)
        ).fetchall()

        return JSONResponse({
            "conta": {
                "id":       conta["id"],
                "nome":     conta["nome"],
                "email":    conta["email"],
                "plano":    conta["plano"],
                "criado_em": conta["criado_em"],
            },
            "empresas": [dict(e) for e in empresas],
        })
    finally:
        conn.close()


@router.post("/empresa")
async def criar_empresa(body: EmpresaRequest,
                        token_data: dict = Depends(get_current_conta)):
    """Cria uma nova empresa para a conta autenticada."""
    conta_id   = token_data["sub"]
    empresa_id = str(uuid.uuid4())
    agora      = datetime.now().isoformat()

    conn = get_conn()
    try:
        # Verificar limite do plano
        plano = conn.execute(
            "SELECT plano FROM contas WHERE id=?", (conta_id,)
        ).fetchone()["plano"]
        count = conn.execute(
            "SELECT COUNT(*) as n FROM empresas WHERE conta_id=?", (conta_id,)
        ).fetchone()["n"]

        limites = {"starter": 1, "pro": 3, "enterprise": 999}
        if count >= limites.get(plano, 1):
            raise HTTPException(
                status_code=403,
                detail=f"Plano {plano} permite até {limites[plano]} empresa(s). Faça upgrade para adicionar mais."
            )

        conn.execute("""
            INSERT INTO empresas (id, conta_id, nome, segmento, porte, status, criado_em)
            VALUES (?, ?, ?, ?, ?, 'onboarding', ?)
        """, (empresa_id, conta_id, body.nome, body.segmento or "", body.porte or "", agora))
        conn.commit()

        logger.info(f"✅ Nova empresa criada: {body.nome} (conta {conta_id})")

        return JSONResponse({
            "empresa_id": empresa_id,
            "nome":       body.nome,
            "status":     "onboarding",
        })
    finally:
        conn.close()


@router.post("/logout")
async def logout():
    """Client-side logout — apenas instrução para limpar token."""
    return JSONResponse({"ok": True, "mensagem": "Token removido no cliente"})
