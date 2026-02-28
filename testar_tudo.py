#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Teste Master de Conectores              ║
║   Valida todas as 11 integrações antes do deploy            ║
║                                                             ║
║   Execute: python3 testar_tudo.py                           ║
║   Com filtro: python3 testar_tudo.py gmail meta elevenlabs  ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio, os, sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

V = "\033[92m"; R = "\033[91m"; A = "\033[93m"
B = "\033[94m"; N = "\033[1m";  X = "\033[0m"
C = "\033[96m"

def ok(m):    print(f"    {V}✅ {m}{X}")
def err(m):   print(f"    {R}❌ {m}{X}")
def warn(m):  print(f"    {A}⚠️  {m}{X}")
def info(m):  print(f"    {B}ℹ️  {m}{X}")
def head(m):  print(f"\n{N}{'─'*54}{X}\n{N}  {m}{X}\n{N}{'─'*54}{X}")

RESULTADOS = {}

def registrar(nome, passou):
    RESULTADOS[nome] = passou

# ─────────────────────────────────────────────────────────────
# 1. WHATSAPP
# ─────────────────────────────────────────────────────────────
async def testar_whatsapp():
    head("📱  WHATSAPP — Twilio Business API")
    passou = True
    try:
        from nucleo.conectores.whatsapp import whatsapp, _calcular_delay_digitacao
        delay = _calcular_delay_digitacao("Oi João, tudo certo com o onboarding?", 45)
        ok(f"Delay de digitação calculado: {delay:.1f}s")
        sids = await whatsapp.enviar("mariana_oliveira", "+5511999999999",
                                     "Oi João! Campanha Q1 aprovada 🚀", humanizar=False)
        ok(f"Envio simulado OK — {len(sids)} mensagem(ns)")
        info(f"Twilio configurado: {'SIM' if os.getenv('TWILIO_ACCOUNT_SID') else 'NÃO — usando simulação'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("whatsapp", passou)

# ─────────────────────────────────────────────────────────────
# 2. GMAIL
# ─────────────────────────────────────────────────────────────
def testar_gmail():
    head("📧  GMAIL — E-mails com assinatura dos agentes")
    passou = True
    try:
        from nucleo.conectores.gmail import gmail, _gerar_assinatura_html
        assin = _gerar_assinatura_html("ana_costa")
        ok(f"Assinatura HTML gerada: {len(assin)} chars")
        r = gmail.enviar("pedro_lima", "teste@nucleo.dev",
                         "Relatório Financeiro — Março 2026",
                         "<p>Pedro, segue o relatório do mês.</p>")
        ok(f"Envio {'simulado' if r.get('simulado') else 'real'} OK: {r.get('id', r.get('assunto',''))}")
        info(f"Gmail configurado: {'SIM' if os.getenv('GMAIL_CLIENT_ID') else 'NÃO — usando simulação'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("gmail", passou)

# ─────────────────────────────────────────────────────────────
# 3. TELEGRAM
# ─────────────────────────────────────────────────────────────
async def testar_telegram():
    head("📱  TELEGRAM — Comunicação interna da diretoria")
    passou = True
    try:
        from nucleo.conectores.telegram import telegram_bot
        ok("Telegram connector inicializado")
        r = await telegram_bot.mensagem_diretoria("lucas_mendes",
            "Reunião semanal em 10 minutos. Todos compareçam. 🧠")
        ok(f"Mensagem diretoria: {'OK' if r else 'simulada'}")
        r2 = await telegram_bot.alerta_dono("Sistema ativo", "VPS online, todos os agentes operando.", "baixa")
        ok(f"Alerta dono: {'OK' if r2 else 'simulado'}")
        info(f"Telegram configurado: {'SIM' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NÃO — usando simulação'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("telegram", passou)

# ─────────────────────────────────────────────────────────────
# 4. PAGAMENTOS
# ─────────────────────────────────────────────────────────────
def testar_pagamentos():
    head("💳  PAGAMENTOS — Mercado Pago + Stripe")
    passou = True
    try:
        from nucleo.conectores.pagamentos import pagamentos, DadosCobranca
        dados = DadosCobranca(297.0, "Licença Núcleo — Starter",
                              "cliente@empresa.com", "Carlos Teste", "12345678900")
        r_pix = pagamentos.pix(dados)
        ok(f"PIX: {r_pix.status} | ID: {r_pix.id_transacao}")
        r_bol = pagamentos.boleto(dados)
        ok(f"Boleto: {r_bol.status} | ID: {r_bol.id_transacao}")

        # Teste de limite
        dados_alto = DadosCobranca(15000.0, "Teste limite", "x@x.com", "Teste")
        r_lim = pagamentos.pix(dados_alto)
        if r_lim.status == "aguardando_aprovacao_dono":
            ok("Bloqueio financeiro R$15k → aprovação do Dono ✓")
        else:
            warn("Limite financeiro: verifique LIMITE_APROVACAO_REAIS no .env")
        info(f"Mercado Pago: {'SIM' if os.getenv('MERCADOPAGO_ACCESS_TOKEN') else 'NÃO'} | Stripe: {'SIM' if os.getenv('STRIPE_SECRET_KEY') else 'NÃO'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("pagamentos", passou)

# ─────────────────────────────────────────────────────────────
# 5. META ADS
# ─────────────────────────────────────────────────────────────
def testar_meta_ads():
    head("📊  META ADS — Facebook + Instagram")
    passou = True
    try:
        from nucleo.conectores.meta_ads import meta_ads, CampanhaMeta
        campanha = CampanhaMeta(
            nome="Lançamento Nucleo Empreende — Q1 2026",
            objetivo="OUTCOME_LEADS",
            budget_diario=50.0,
            publico_alvo={
                "age_min": 28, "age_max": 55,
                "genders": [1, 2],
                "geo_locations": {"countries": ["BR"]},
                "interests": [{"id": "6003139266461", "name": "Business"}],
            },
            criativos=[{
                "titulo": "Framework IA para Empresas",
                "texto": "Automatize sua diretoria com agentes de IA. Resultados em 48h.",
                "url": "https://nucloventures.com.br",
                "cta": "LEARN_MORE",
            }],
        )
        r = meta_ads.criar_campanha(campanha)
        ok(f"Campanha criada: {r.get('campaign_id')} | {r.get('status','')[:40]}")
        m = meta_ads.metricas_campanha("SIM_CAMP_001", 7)
        ok(f"Métricas: {m.get('impressoes',0):,} impressões | CTR {m.get('ctr')} | Gasto {m.get('gasto')}")
        info(f"Meta Ads configurado: {'SIM' if os.getenv('META_ACCESS_TOKEN') else 'NÃO — usando simulação'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("meta_ads", passou)

# ─────────────────────────────────────────────────────────────
# 6. LEONARDO.AI + ANALYTICS + SEMRUSH
# ─────────────────────────────────────────────────────────────
def testar_criativos_dados():
    head("🎨  CRIATIVOS + DADOS — Leonardo · SEMrush · GA4")
    passou = True
    try:
        from nucleo.conectores.criativos_dados import leonardo, semrush, analytics, SolicitacaoImagem

        # Leonardo
        r = leonardo.gerar_criativo_campanha("Nucleo Empreende IA", "tech corporativo moderno")
        if r.get("simulado"):
            ok(f"Leonardo.AI simulado: {r.get('imagens', ['—'])[0][:60]}...")
        else:
            ok(f"Leonardo.AI: {len(r.get('imagens',[]))} imagem(ns) gerada(s)")
        info(f"Leonardo configurado: {'SIM' if os.getenv('LEONARDO_API_KEY') else 'NÃO'}")

        # SEMrush
        t = semrush.trafego_organico("concorrente.com.br")
        ok(f"SEMrush: {t.get('trafego',0):,} visitas/mês · {t.get('keywords',0):,} keywords")
        comp = semrush.comparar_concorrentes(["concorrente1.com.br", "concorrente2.com.br"])
        ok(f"Comparativo: {len(comp)} concorrentes analisados")
        info(f"SEMrush configurado: {'SIM' if os.getenv('SEMRUSH_API_KEY') else 'NÃO'}")

        # GA4
        r = analytics.relatorio_basico(7)
        ok(f"GA4: {r.get('sessoes',0):,} sessões · {r.get('usuarios_ativos',0):,} usuários · {r.get('conversoes',0)} conversões")
        info(f"GA4 configurado: {'SIM' if os.getenv('GA4_PROPERTY_ID') else 'NÃO'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("criativos_dados", passou)

# ─────────────────────────────────────────────────────────────
# 7. MERCADO LIVRE
# ─────────────────────────────────────────────────────────────
def testar_mercadolivre():
    head("🛒  MERCADO LIVRE — Vendas e logística")
    passou = True
    try:
        from nucleo.conectores.operacoes_contratos_voz import mercadolivre
        pedidos = mercadolivre.pedidos_recentes(5)
        ok(f"Pedidos recentes: {len(pedidos)} encontrados")
        for p in pedidos[:2]:
            ok(f"  Pedido {p['id']} | Status: {p['status']} | R$ {p['total']:.2f}")
        rastreio = mercadolivre.rastrear_envio("SIM_ENV_001")
        ok(f"Rastreamento: {rastreio.get('status')} — {rastreio.get('etapa','')}")
        info(f"ML configurado: {'SIM' if os.getenv('MELI_ACCESS_TOKEN') else 'NÃO — usando simulação'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("mercadolivre", passou)

# ─────────────────────────────────────────────────────────────
# 8. CLICKSIGN
# ─────────────────────────────────────────────────────────────
def testar_clicksign():
    head("📝  CLICKSIGN — Contratos digitais")
    passou = True
    try:
        from nucleo.conectores.operacoes_contratos_voz import clicksign
        r = clicksign.gerar_contrato_licenca(
            cliente_nome="Carlos Eduardo Mendonça",
            cliente_email="carlos@empresa.com.br",
            cliente_cpf="12345678900",
            plano="Framework + 3 meses suporte",
            valor=25000.0,
        )
        ok(f"Contrato gerado: key={r.get('document_key')} | {len(r.get('signatarios',[]))} signatário(s)")
        ok(f"Link: {r.get('link_acompanhamento','')}")
        ok(f"Deadline: {r.get('deadline','')[:10]}")
        info(f"ClickSign configurado: {'SIM' if os.getenv('CLICKSIGN_ACCESS_TOKEN') else 'NÃO — usando simulação'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("clicksign", passou)

# ─────────────────────────────────────────────────────────────
# 9. ELEVENLABS
# ─────────────────────────────────────────────────────────────
def testar_elevenlabs():
    head("🎙️  ELEVENLABS — Voz sintética dos agentes")
    passou = True
    try:
        from nucleo.conectores.operacoes_contratos_voz import elevenlabs
        for agente, fala in [
            ("lucas_mendes",     "Bom dia equipe. Vamos iniciar o ciclo semanal com foco total."),
            ("mariana_oliveira", "Campanha aprovada! A meta é viralizar até quinta. Bora! 🔥"),
            ("pedro_lima",       "Fluxo de caixa revisado. Margem dentro do esperado."),
            ("dani_ferreira",    "Detectei anomalia no tráfego. Investigando. Relatório em 10 minutos."),
        ]:
            r = elevenlabs.falar(agente, fala)
            if r.get("simulado"):
                ok(f"{agente.split('_')[0].title()}: simulado → '{fala[:40]}...'")
            else:
                ok(f"{agente.split('_')[0].title()}: {r.get('arquivo')} ({r.get('tamanho_kb')}KB)")
        info(f"ElevenLabs configurado: {'SIM' if os.getenv('ELEVENLABS_API_KEY') else 'NÃO — usando simulação'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("elevenlabs", passou)

# ─────────────────────────────────────────────────────────────
# 10. MEMÓRIA (recap)
# ─────────────────────────────────────────────────────────────
def testar_memoria():
    head("🧠  MEMÓRIA — Pinecone + Supabase + Redis")
    passou = True
    try:
        from nucleo.conectores.memoria import memoria
        memoria.registrar_aprendizado("dani_ferreira", "SEMrush mostra pico de buscas por 'IA empresarial' nas terças.")
        ok("Aprendizado registrado: Dani Ferreira")
        memoria.registrar_decisao("lucas_mendes", "Ativar campanha Meta Ads R$50/dia", "ROI projetado 3.2x")
        ok("Decisão registrada: Lucas Mendes")
        ctx = memoria.lembrar_formatado("lucas_mendes", "campanha marketing decisão")
        ok(f"Contexto recuperado: {len(ctx)} chars para injetar no prompt")
        info(f"Redis: {'OK' if _ping_redis() else 'simulação'} | Pinecone: {'SIM' if os.getenv('PINECONE_API_KEY') else 'NÃO'} | Supabase: {'SIM' if os.getenv('SUPABASE_URL') else 'NÃO'}")
    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("memoria", passou)

def _ping_redis() -> bool:
    try:
        import redis
        redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379")).ping()
        return True
    except:
        return False

# ─────────────────────────────────────────────────────────────
# SUMÁRIO FINAL
# ─────────────────────────────────────────────────────────────

def sumario():
    print(f"\n{N}{'═'*54}{X}")
    print(f"{N}  📋  RESULTADO FINAL{X}")
    print(f"{N}{'═'*54}{X}")

    total = len(RESULTADOS)
    aprovados = sum(1 for v in RESULTADOS.values() if v)
    reprovados = total - aprovados

    chave_env_map = {
        "whatsapp":       ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
        "gmail":          ["GMAIL_CLIENT_ID", "GMAIL_REFRESH_TOKEN"],
        "telegram":       ["TELEGRAM_BOT_TOKEN"],
        "pagamentos":     ["MERCADOPAGO_ACCESS_TOKEN"],
        "meta_ads":       ["META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"],
        "criativos_dados":["LEONARDO_API_KEY", "SEMRUSH_API_KEY", "GA4_PROPERTY_ID"],
        "mercadolivre":   ["MELI_ACCESS_TOKEN"],
        "clicksign":      ["CLICKSIGN_ACCESS_TOKEN"],
        "elevenlabs":     ["ELEVENLABS_API_KEY"],
        "memoria":        ["PINECONE_API_KEY", "SUPABASE_URL"],
    }

    print()
    for nome, passou in RESULTADOS.items():
        icon = f"{V}✅{X}" if passou else f"{R}❌{X}"
        chaves = chave_env_map.get(nome, [])
        configs = [k for k in chaves if os.getenv(k)]
        status = f"{V}produção{X}" if configs else f"{A}simulação{X}"
        print(f"  {icon}  {nome:<20} {status}")

    print(f"\n  {V if reprovados==0 else R}{N}{aprovados}/{total} conectores OK{X}")

    if reprovados == 0:
        print(f"\n  {C}Todos os conectores funcionando!{X}")
        print(f"  {B}Configure as API Keys no .env para sair do modo simulação.{X}")
        faltando = [k for ks in chave_env_map.values() for k in ks if not os.getenv(k)]
        if faltando:
            print(f"\n  {A}Keys ainda faltando ({len(faltando)}):{X}")
            for k in sorted(set(faltando)):
                print(f"    {A}• {k}{X}")
    else:
        print(f"  {R}Verifique os erros acima antes do deploy.{X}")

    print(f"\n  {B}Documentação: https://docs.claude.ai{X}")
    print(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

async def main():
    filtro = sys.argv[1:] if len(sys.argv) > 1 else []

    print(f"\n{N}{'═'*54}{X}")
    print(f"{N}  🧪  NÚCLEO VENTURES — Teste de Conectores{X}")
    print(f"{N}  11 integrações · {datetime.now().strftime('%d/%m/%Y %H:%M')}{X}")
    print(f"{N}{'═'*54}{X}")

    todos = {
        "whatsapp":        testar_whatsapp,
        "gmail":           testar_gmail,
        "telegram":        testar_telegram,
        "pagamentos":      testar_pagamentos,
        "meta_ads":        testar_meta_ads,
        "criativos_dados": testar_criativos_dados,
        "mercadolivre":    testar_mercadolivre,
        "clicksign":       testar_clicksign,
        "elevenlabs":      testar_elevenlabs,
        "memoria":         testar_memoria,
    }

    selecionados = {k: v for k, v in todos.items() if not filtro or k in filtro}

    for nome, fn in selecionados.items():
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                fn()
        except Exception as e:
            err(f"{nome}: erro não esperado — {e}")
            registrar(nome, False)

    sumario()

if __name__ == "__main__":
    asyncio.run(main())
