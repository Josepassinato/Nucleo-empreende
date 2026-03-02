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
