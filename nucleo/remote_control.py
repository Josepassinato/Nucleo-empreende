"""
Remote Control — Permite que Claude acesse a VPS via HTTP
Protegido por token secreto. Só aceita comandos específicos.
"""
import os, subprocess, json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()

# Token secreto — Claude usa para autenticar
RC_TOKEN = os.getenv("REMOTE_CONTROL_TOKEN", "nucleo_rc_2026_claude")

COMANDOS_PERMITIDOS = [
    "git pull origin main",
    "systemctl restart nucleo-empreende",
    "systemctl status nucleo-empreende",
    "journalctl -u nucleo-empreende -n 50 --no-pager",
    "cat nucleo/config/projeto.json",
    "ls nucleo/",
    "pip install",
    "python3 -c",
]

def cmd_permitido(cmd: str) -> bool:
    for p in COMANDOS_PERMITIDOS:
        if cmd.strip().startswith(p): return True
    return False

@router.post("/rc/exec")
async def exec_cmd(request: Request):
    data = await request.json()
    token = data.get("token","")
    cmd   = data.get("cmd","")
    
    if token != RC_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    if not cmd_permitido(cmd):
        raise HTTPException(status_code=403, detail=f"Comando não permitido: {cmd}")
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60,
            cwd="/root/Nucleo-empreende"
        )
        return JSONResponse({
            "ok": True,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-1000:],
            "returncode": result.returncode,
            "ts": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse({"ok": False, "erro": str(e)})

@router.get("/rc/status")
async def rc_status(token: str = ""):
    if token != RC_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"ok": True, "msg": "Remote Control ativo", "ts": datetime.now().isoformat()}

@router.post("/rc/write")
async def write_file(request: Request):
    """Escreve arquivo na VPS diretamente."""
    data = await request.json()
    if data.get("token") != RC_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    path = data.get("path","")
    content = data.get("content","")
    
    # Só permite escrever dentro do projeto
    if not path.startswith("nucleo/") and not path.endswith(".py") and not path.endswith(".md"):
        raise HTTPException(status_code=403, detail="Path não permitido")
    
    from pathlib import Path
    full_path = Path("/root/Nucleo-empreende") / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)
    
    return {"ok": True, "path": str(full_path)}

@router.get("/rc/read")
async def read_file(path: str, token: str = ""):
    if token != RC_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    from pathlib import Path
    full_path = Path("/root/Nucleo-empreende") / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return {"ok": True, "content": full_path.read_text()}
