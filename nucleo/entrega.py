"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Entrega Automática Pós-Compra           ║
║                                                             ║
║   Fluxo:                                                    ║
║   1. Hotmart webhook PURCHASE_APPROVED                      ║
║   2. Gerar licença única para o cliente                     ║
║   3. Enviar e-mail com instruções de instalação             ║
║   4. Enviar WhatsApp de boas-vindas                         ║
║   5. Criar acesso no GitHub (repositório privado)           ║
║   6. Registrar no CRM                                       ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, secrets, hashlib, json, logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.entrega")

LICENSES_DB = Path("nucleo/logs/licencas.jsonl")

@dataclass
class Compra:
    nome: str
    email: str
    plano: str          # starter | pro | enterprise
    valor: float
    transacao_id: str
    telefone: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# 1. GERAÇÃO DE LICENÇA
# ──────────────────────────────────────────────────────────────

def gerar_licenca(compra: Compra) -> str:
    """
    Gera chave de licença única, vinculada à transação.
    Formato: NF-XXXX-XXXX-XXXX-XXXX
    """
    base = f"{compra.transacao_id}{compra.email}{secrets.token_hex(8)}"
    h = hashlib.sha256(base.encode()).hexdigest().upper()
    key = f"NF-{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

    # Salvar no banco
    LICENSES_DB.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "key": key,
        "nome": compra.nome,
        "email": compra.email,
        "plano": compra.plano,
        "valor": compra.valor,
        "transacao_id": compra.transacao_id,
        "criada_em": datetime.now().isoformat(),
        "expira_em": (datetime.now() + timedelta(days=365 if compra.plano == "pro" else 90)).isoformat(),
        "ativa": True,
        "usos": 0,
    }
    with open(LICENSES_DB, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(f"✅ Licença gerada: {key} | {compra.email} | Plano {compra.plano}")
    return key


def validar_licenca(key: str) -> dict:
    """Chamado pelo instalador para validar a licença."""
    if not LICENSES_DB.exists():
        return {"valid": False, "erro": "Banco de licenças não encontrado"}
    for linha in LICENSES_DB.read_text().strip().split("\n"):
        if not linha: continue
        entry = json.loads(linha)
        if entry["key"] == key:
            if not entry["ativa"]:
                return {"valid": False, "erro": "Licença desativada"}
            if datetime.now() > datetime.fromisoformat(entry["expira_em"]):
                return {"valid": False, "erro": "Licença expirada. Renove em nucleoempreende.com.br/renovar"}
            return {
                "valid": True,
                "plano": entry["plano"],
                "nome": entry["nome"],
                "expira_em": entry["expira_em"][:10],
            }
    return {"valid": False, "erro": "Licença não encontrada"}


# ──────────────────────────────────────────────────────────────
# 2. E-MAIL DE ENTREGA
# ──────────────────────────────────────────────────────────────

def montar_email_entrega(compra: Compra, licenca: str) -> dict:
    """Monta o e-mail HTML de entrega automática."""
    primeiro_nome = compra.nome.split()[0]
    url_instalador = "https://install.nucleoempreende.com.br"
    url_docs = "https://docs.nucleoempreende.com.br"
    url_suporte = "https://wa.me/5511XXXXXXXXX"

    corpo_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI',Arial,sans-serif; background:#f1f5f9; margin:0; padding:20px; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:20px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
  .header {{ background:#080c14; padding:40px 40px 32px; text-align:center; }}
  .header h1 {{ color:#f59e0b; font-size:28px; margin:0 0 8px; font-weight:800; letter-spacing:-1px; }}
  .header p {{ color:#64748b; font-size:14px; margin:0; }}
  .body {{ padding:40px; }}
  .body h2 {{ font-size:22px; color:#111827; margin:0 0 16px; font-weight:700; }}
  .body p {{ color:#374151; font-size:15px; line-height:1.7; margin:0 0 16px; }}
  .license-box {{ background:#0d1220; border:1.5px solid rgba(245,158,11,0.4); border-radius:12px; padding:24px; text-align:center; margin:28px 0; }}
  .license-box p {{ color:#94a3b8; font-size:12px; margin:0 0 10px; font-family:monospace; letter-spacing:2px; }}
  .license-box .key {{ color:#f59e0b; font-family:monospace; font-size:22px; font-weight:700; letter-spacing:2px; }}
  .cmd-box {{ background:#0d1220; border-radius:10px; padding:16px 20px; margin:20px 0; }}
  .cmd-box code {{ color:#10b981; font-family:monospace; font-size:14px; }}
  .steps {{ display:block; }}
  .step {{ display:flex; gap:16px; align-items:flex-start; margin-bottom:20px; padding-bottom:20px; border-bottom:1px solid #f1f5f9; }}
  .step-num {{ width:32px; height:32px; border-radius:8px; background:#fef3c7; color:#d97706; font-weight:800; font-size:14px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
  .step-content h4 {{ margin:0 0 4px; color:#111827; font-size:14px; font-weight:600; }}
  .step-content p {{ margin:0; color:#6b7280; font-size:13px; line-height:1.5; }}
  .plano-badge {{ display:inline-block; background:#fef3c7; color:#d97706; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:700; margin-bottom:24px; }}
  .footer {{ background:#f8fafc; padding:28px 40px; text-align:center; border-top:1px solid #e2e8f0; }}
  .footer p {{ color:#94a3b8; font-size:12px; line-height:1.6; margin:0; }}
  .btn {{ display:inline-block; background:#f59e0b; color:#000; padding:14px 32px; border-radius:10px; font-weight:800; font-size:15px; text-decoration:none; margin:8px 4px; }}
  .btn-ghost {{ background:transparent; border:1.5px solid #e2e8f0; color:#374151; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Nucleo Empreende</h1>
    <p>Sua diretoria autônoma de IA está pronta</p>
  </div>
  <div class="body">
    <h2>Bem-vindo, {primeiro_nome}! 🎉</h2>
    <div class="plano-badge">Plano {compra.plano.upper()}</div>
    <p>Sua compra foi confirmada. Abaixo está sua chave de licença exclusiva e o passo a passo para colocar seus agentes de IA em operação ainda hoje.</p>

    <div class="license-box">
      <p>SUA CHAVE DE LICENÇA</p>
      <div class="key">{licenca}</div>
      <p style="margin-top:12px;font-size:11px;">Guarde esta chave. Você precisará dela na instalação.</p>
    </div>

    <h3 style="font-size:17px;color:#111827;margin:28px 0 20px;font-weight:700;">📋 Instalação em 3 passos</h3>

    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <div class="step-content">
          <h4>Abra o terminal da sua VPS ou máquina Linux/Mac</h4>
          <p>Precisa de acesso SSH? Use: <code style="font-family:monospace;background:#f1f5f9;padding:1px 6px;border-radius:4px;">ssh usuario@ip-do-servidor</code></p>
        </div>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <div class="step-content">
          <h4>Execute o instalador com sua licença</h4>
          <div class="cmd-box">
            <code>curl -fsSL {url_instalador} | bash -s {licenca}</code>
          </div>
          <p>O instalador fará tudo automaticamente: instala Python, dependências, Redis e abre o setup wizard.</p>
        </div>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <div class="step-content">
          <h4>Configure suas API keys no wizard</h4>
          <p>Uma interface interativa guiará você para configurar cada chave com dicas e links diretos. Leva ~10 minutos.</p>
        </div>
      </div>
    </div>

    <div style="text-align:center;margin-top:32px;">
      <a href="{url_docs}" class="btn">📖 Acessar Documentação</a>
      <a href="{url_suporte}" class="btn btn-ghost">💬 Suporte no WhatsApp</a>
    </div>

    {'<div style="background:#ecfdf5;border:1px solid #6ee7b7;border-radius:12px;padding:20px;margin-top:28px;"><strong style="color:#065f46;">🎁 Seu plano Pro inclui:</strong><br><p style="color:#047857;font-size:14px;margin:8px 0 0;">Uma sessão de onboarding ao vivo de 1h com nossa equipe. Responderemos em até 4h no WhatsApp para agendar.</p></div>' if compra.plano == "pro" else ""}

    <p style="color:#6b7280;font-size:13px;margin-top:28px;">
      Transação: <code style="font-family:monospace;">{compra.transacao_id}</code><br>
      Valor: R$ {compra.valor:,.2f} · Data: {datetime.now().strftime("%d/%m/%Y")}
    </p>
  </div>
  <div class="footer">
    <p>Nucleo Empreende · <a href="https://nucleoempreende.com.br" style="color:#f59e0b;">nucleoempreende.com.br</a><br>
    Dúvidas? <a href="{url_suporte}" style="color:#f59e0b;">WhatsApp</a> ou <a href="mailto:suporte@nucleoempreende.com.br" style="color:#f59e0b;">suporte@nucleoempreende.com.br</a><br>
    Você está recebendo este e-mail porque realizou uma compra.</p>
  </div>
</div>
</body>
</html>
"""

    return {
        "para": compra.email,
        "assunto": f"🚀 Seu Nucleo Empreende está pronto, {primeiro_nome}! — Chave de licença inclusa",
        "corpo_html": corpo_html,
    }


# ──────────────────────────────────────────────────────────────
# 3. WHATSAPP DE BOAS-VINDAS
# ──────────────────────────────────────────────────────────────

def montar_whatsapp_boas_vindas(compra: Compra, licenca: str) -> str:
    primeiro_nome = compra.nome.split()[0]
    return (
        f"Olá {primeiro_nome}! 🎉\n\n"
        f"Sua compra do *Nucleo Empreende* ({compra.plano.upper()}) foi confirmada!\n\n"
        f"🔑 *Sua licença:*\n`{licenca}`\n\n"
        f"⚡ *Para instalar, rode no terminal:*\n"
        f"`curl -fsSL https://install.nucleoempreende.com.br | bash -s {licenca}`\n\n"
        f"📧 Enviei o tutorial completo para {compra.email}\n\n"
        f"Qualquer dúvida, estou aqui! 👇"
    )


# ──────────────────────────────────────────────────────────────
# 4. FLUXO COMPLETO — chamado pelo webhook do Hotmart
# ──────────────────────────────────────────────────────────────

async def processar_nova_compra(dados_webhook: dict) -> dict:
    """
    Orquestra todo o fluxo de entrega após compra aprovada.
    Integre com: @app.post("/webhook/hotmart")
    """
    from nucleo.conectores.gmail import gmail
    from nucleo.conectores.whatsapp import whatsapp

    venda = dados_webhook.get("venda", {})
    compra = Compra(
        nome=venda.get("comprador_nome", "Cliente"),
        email=venda.get("comprador_email", ""),
        plano=_inferir_plano(venda.get("produto_nome", ""), venda.get("valor", 0)),
        valor=venda.get("valor", 0),
        transacao_id=venda.get("transaction", f"TX{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        telefone=venda.get("telefone"),
    )

    if not compra.email:
        logger.warning("E-mail não encontrado no webhook. Entrega não realizada.")
        return {"sucesso": False, "erro": "E-mail não encontrado"}

    resultado = {}

    # 1. Gerar licença
    licenca = gerar_licenca(compra)
    resultado["licenca"] = licenca

    # 2. Enviar e-mail
    email_dados = montar_email_entrega(compra, licenca)
    r_email = gmail.enviar(
        agente_id="lucas_mendes",
        para=compra.email,
        assunto=email_dados["assunto"],
        corpo_html=email_dados["corpo_html"],
    )
    resultado["email"] = "enviado" if not r_email.get("erro") else f"erro: {r_email['erro']}"
    logger.info(f"E-mail de entrega: {resultado['email']} → {compra.email}")

    # 3. WhatsApp de boas-vindas (se tiver telefone)
    if compra.telefone:
        mensagem_wpp = montar_whatsapp_boas_vindas(compra, licenca)
        sids = await whatsapp.enviar(
            agente_id="ana_costa",
            para=compra.telefone,
            mensagem=mensagem_wpp,
            humanizar=False,  # entrega imediata, sem delay
        )
        resultado["whatsapp"] = f"{len(sids)} mensagem(ns) enviada(s)"

    logger.info(f"✅ Entrega concluída: {compra.email} | Licença: {licenca}")
    return {"sucesso": True, "compra": compra.email, **resultado}


def _inferir_plano(produto_nome: str, valor: float) -> str:
    nome = produto_nome.lower()
    if "enterprise" in nome or valor >= 15000: return "enterprise"
    if "pro" in nome or valor >= 5000: return "pro"
    return "starter"


# ──────────────────────────────────────────────────────────────
# FastAPI endpoint completo
# ──────────────────────────────────────────────────────────────
"""
from fastapi import FastAPI, Request, Header, HTTPException
from nucleo.conectores.hotmart import hotmart
from nucleo.entrega import processar_nova_compra, validar_licenca

app = FastAPI()

@app.post("/webhook/hotmart")
async def webhook_compra(
    request: Request,
    x_hotmart_signature: str = Header(None),
):
    payload_raw = await request.body()
    if not hotmart.verificar_webhook(payload_raw, x_hotmart_signature or ""):
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    payload = await request.json()
    evento = hotmart.processar_webhook(payload)

    if evento["evento"] == "PURCHASE_APPROVED":
        resultado = await processar_nova_compra(evento)
        return {"status": "ok", "entrega": resultado}

    return {"status": "ok", "evento": evento["evento"]}


@app.get("/api/license/validate")
def validar(key: str):
    return validar_licenca(key)
"""
