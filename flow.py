"""
Increase Team — Onboarding Flow
Endpoint que conecta: Supabase → CEO Gemini → WhatsApp → Dashboard
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.flow")

router = APIRouter(prefix="/api/flow", tags=["flow"])

# ── Config ──────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

ANALISES_DIR = Path(__file__).resolve().parent / "nucleo" / "logs" / "analises"
ANALISES_DIR.mkdir(parents=True, exist_ok=True)

# ── Supabase client ─────────────────────────────────────────

_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


# ── Endpoint principal ──────────────────────────────────────

@router.post("/onboarding-complete")
async def onboarding_complete(request: Request):
    """
    Chamado pelo frontend apos o onboarding salvar no Supabase.
    Recebe: { "user_id": "uuid" }
    Faz: busca empresa → gera analise CEO → envia WhatsApp → salva resultado
    """
    try:
        body = await request.json()
        user_id = body.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id obrigatorio")

        logger.info(f"Onboarding flow iniciado para user_id={user_id}")

        # 1. Buscar dados da empresa no Supabase
        sb = get_supabase()

        profile_resp = sb.table("users_profile").select("*").eq("id", user_id).single().execute()
        profile = profile_resp.data
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil nao encontrado")

        company_resp = sb.table("companies").select("*").eq("user_id", user_id).single().execute()
        company = company_resp.data
        if not company:
            raise HTTPException(status_code=404, detail="Empresa nao encontrada")

        logger.info(f"Empresa: {company['company_name']} | Setor: {company.get('sector')}")

        # 2. CEO Lucas gera analise estrategica via Gemini
        from ceo_engine import gerar_analise_ceo, formatar_para_whatsapp

        nome_dono = profile.get("full_name", "Empreendedor")
        analise = await gerar_analise_ceo(company, nome_dono)

        logger.info(f"Analise gerada: {len(analise)} chars")

        # 3. Salvar analise localmente e no Supabase
        analise_data = {
            "user_id": user_id,
            "company_name": company["company_name"],
            "analise": analise,
            "generated_at": datetime.now().isoformat(),
            "agent": "lucas_mendes",
            "agent_role": "CEO",
        }

        # Salvar em arquivo local
        safe_name = company["company_name"].replace(" ", "_").replace("/", "_")[:30]
        analise_path = ANALISES_DIR / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(analise_path, "w", encoding="utf-8") as f:
            json.dump(analise_data, f, ensure_ascii=False, indent=2)

        # Tentar salvar no Supabase (tabela analises, se existir)
        try:
            sb.table("analises").insert({
                "user_id": user_id,
                "agent_id": "lucas_mendes",
                "agent_role": "CEO",
                "content": analise,
                "company_name": company["company_name"],
            }).execute()
        except Exception as e:
            logger.warning(f"Tabela analises nao existe ou erro ao salvar: {e}")

        # 4. Enviar via WhatsApp
        whatsapp_numero = profile.get("whatsapp", "") or os.getenv("DONO_WHATSAPP_NUMBER", "")
        whatsapp_enviado = False
        whatsapp_sid = None

        if whatsapp_numero:
            try:
                from nucleo.conectores.whatsapp import whatsapp as wpp
                texto_wpp = formatar_para_whatsapp(analise, company["company_name"])

                sids = await wpp.enviar(
                    agente_id="lucas_mendes",
                    para=whatsapp_numero,
                    mensagem=texto_wpp,
                    nome_destinatario=nome_dono.split()[0] if nome_dono else "",
                    humanizar=False,  # Analise vai direto, sem delay
                )
                whatsapp_enviado = bool(sids)
                whatsapp_sid = sids[0] if sids else None
                logger.info(f"WhatsApp enviado: {whatsapp_enviado} | SIDs: {sids}")
            except Exception as e:
                logger.error(f"Erro ao enviar WhatsApp: {e}")

        # 5. Retornar resultado para o frontend
        return JSONResponse({
            "status": "ok",
            "company": company["company_name"],
            "analise": analise,
            "whatsapp_enviado": whatsapp_enviado,
            "whatsapp_sid": whatsapp_sid,
            "generated_at": analise_data["generated_at"],
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no onboarding flow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoint para buscar analise (dashboard) ────────────────

@router.get("/analise/{user_id}")
async def get_analise(user_id: str):
    """Retorna a ultima analise gerada para o usuario."""
    try:
        # Tentar Supabase primeiro
        sb = get_supabase()
        try:
            resp = sb.table("analises").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if resp.data:
                return JSONResponse(resp.data[0])
        except Exception:
            pass

        # Fallback: buscar em arquivos locais
        analises = sorted(ANALISES_DIR.glob("*.json"), reverse=True)
        for path in analises:
            with open(path) as f:
                data = json.load(f)
                if data.get("user_id") == user_id:
                    return JSONResponse(data)

        return JSONResponse({"status": "not_found", "analise": None}, status_code=404)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Health check ────────────────────────────────────────────

@router.get("/health")
async def flow_health():
    has_gemini = bool(os.getenv("GOOGLE_API_KEY"))
    has_twilio = bool(os.getenv("TWILIO_ACCOUNT_SID"))
    has_supabase = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

    return {
        "status": "ok",
        "gemini": has_gemini,
        "twilio": has_twilio,
        "supabase": has_supabase,
        "timestamp": datetime.now().isoformat(),
    }
