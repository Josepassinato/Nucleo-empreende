import os, httpx, smtplib, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("nucleo.tools")

def buscar_web(q: str) -> str:
    """Diana pesquisa mercado em tempo real."""
    try:
        r = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": q, "format": "json", "no_html": "1"},
            timeout=10
        )
        d = r.json()
        res = []
        if d.get("Abstract"):
            res.append(f"📌 {d['Abstract']}")
        for t in d.get("RelatedTopics", [])[:5]:
            if isinstance(t, dict) and t.get("Text"):
                res.append(f"• {t['Text'][:200]}")
        return "\n".join(res) if res else "Sem resultados para: " + q
    except Exception as e:
        return f"Erro busca: {e}"

def enviar_email_zoho(para: str, assunto: str, corpo: str) -> str:
    """Agentes enviam email via Zoho bot."""
    user = os.getenv("ZOHO_EMAIL", "")
    pwd  = os.getenv("ZOHO_PASSWORD", "")
    if not user:
        return "❌ ZOHO_EMAIL não configurado"
    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = para
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        with smtplib.SMTP("smtp.zoho.com", 587) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        return f"✅ Email enviado para {para}"
    except Exception as e:
        return f"❌ Erro email: {e}"

def enviar_email_gmail(para: str, assunto: str, corpo: str) -> str:
    """Lucas envia email pelo Gmail pessoal."""
    user = os.getenv("GMAIL_USER", "")
    pwd  = os.getenv("GMAIL_APP_PASSWORD", "")
    if not user:
        return "❌ GMAIL_USER não configurado"
    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = para
        msg["Subject"] = assunto
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        return f"✅ Email Gmail enviado para {para}"
    except Exception as e:
        return f"❌ Erro Gmail: {e}"

def supabase_query(tabela: str, filtro: dict = None) -> str:
    """Dani consulta dados do Supabase VibeSchool."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url:
        return "❌ SUPABASE_URL não configurado"
    try:
        params = "?limit=10"
        if filtro:
            for k, v in filtro.items():
                params += f"&{k}=eq.{v}"
        r = httpx.get(
            f"{url}/rest/v1/{tabela}{params}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=10
        )
        data = r.json()
        return f"📊 {tabela}: {len(data)} registros\n{str(data)[:500]}"
    except Exception as e:
        return f"❌ Erro Supabase: {e}"

def testar_ferramentas() -> str:
    """Testa todas as ferramentas disponíveis."""
    resultados = []
    
    # Teste busca web
    r = buscar_web("inteligencia artificial negócios brasil 2025")
    resultados.append(f"🔍 Busca web: {'✅ OK' if 'Sem resultados' not in r and 'Erro' not in r else '⚠️ ' + r[:50]}")
    
    # Teste email Zoho
    user = os.getenv("ZOHO_EMAIL", "")
    resultados.append(f"📧 Zoho: {'✅ Configurado' if user else '❌ Não configurado'}")
    
    # Teste Gmail
    user = os.getenv("GMAIL_USER", "")
    resultados.append(f"📧 Gmail: {'✅ Configurado' if user else '❌ Não configurado'}")
    
    # Teste Supabase
    url = os.getenv("SUPABASE_URL", "")
    resultados.append(f"🗄️ Supabase: {'✅ Configurado' if url else '❌ Não configurado'}")
    
    return "\n".join(resultados)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(testar_ferramentas())

def navegar_web(instrucao: str, url: str = None) -> str:
    """Diana navega em sites reais como humano."""
    try:
        from browser_use import BrowserUse
        config = {
            "browser": "chromium",
            "headless": True,
            "stealth": True,
            "timeout": 60000
        }
        bu = BrowserUse(config=config)
        result = bu.run_instruction(
            instruction=instrucao,
            start_url=url,
            max_steps=15,
            save_screenshot=False,
            return_html=False
        )
        return result.text_content[:1000] if result.text_content else "Navegação concluída sem resultado"
    except Exception as e:
        return f"Erro navegação: {e}"

def telegram_enviar(mensagem: str) -> str:
    """Envia alerta via Telegram para o dono."""
    import urllib.request, urllib.parse
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat  = os.getenv("TELEGRAM_CHAT_DONO", "")
    if not token or not chat:
        return "❌ Telegram não configurado"
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat, "text": mensagem, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        return "✅ Alerta Telegram enviado"
    except Exception as e:
        return f"❌ Erro Telegram: {e}"

def hotmart_vendas(dias: int = 30) -> str:
    """Pedro consulta vendas reais do Hotmart."""
    client_id     = os.getenv("HOTMART_CLIENT_ID", "")
    client_secret = os.getenv("HOTMART_CLIENT_SECRET", "")
    if not client_id:
        return "❌ Hotmart não configurado"
    try:
        auth = httpx.post(
            "https://api-sec-vlc.hotmart.com/security/oauth/token",
            params={"grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret},
            timeout=10
        )
        token = auth.json().get("access_token")
        if not token:
            return f"❌ Hotmart auth falhou: {auth.text[:100]}"
        r = httpx.get(
            "https://developers.hotmart.com/payments/api/v1/sales/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        d = r.json()
        total = d.get("total_value", {}).get("value", 0)
        qtd   = d.get("total_items", 0)
        return f"📊 Hotmart últimos {dias}d:\n💰 R$ {total:,.2f}\n🛒 {qtd} vendas"
    except Exception as e:
        return f"❌ Erro Hotmart: {e}"

def meta_ads_resumo() -> str:
    """Mariana consulta campanhas do Meta Ads."""
    token      = os.getenv("META_ACCESS_TOKEN", "")
    account_id = os.getenv("META_AD_ACCOUNT_ID", "")
    if not token or not account_id:
        return "❌ Meta Ads não configurado"
    try:
        r = httpx.get(
            f"https://graph.facebook.com/v18.0/act_{account_id}/insights",
            params={
                "access_token": token,
                "fields": "campaign_name,impressions,clicks,spend,ctr",
                "date_preset": "last_30d",
                "level": "campaign"
            },
            timeout=10
        )
        data = r.json().get("data", [])
        if not data:
            return "📊 Meta Ads: nenhuma campanha ativa no período"
        linhas = [f"📊 Meta Ads — últimos 30 dias:"]
        for c in data[:5]:
            linhas.append(
                f"• {c.get('campaign_name','?')}: "
                f"R${c.get('spend','0')} | "
                f"{c.get('impressions','0')} impressões | "
                f"CTR {c.get('ctr','0')}%"
            )
        return "\n".join(linhas)
    except Exception as e:
        return f"❌ Erro Meta Ads: {e}"
