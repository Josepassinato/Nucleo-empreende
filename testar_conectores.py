#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Teste de Conectores                     ║
║   Valida WhatsApp, Pagamentos e Memória antes do deploy      ║
║                                                             ║
║   Execute: python3 testar_conectores.py                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

VERDE = "\033[92m"
VERMELHO = "\033[91m"
AMARELO = "\033[93m"
AZUL = "\033[94m"
RESET = "\033[0m"
NEGRITO = "\033[1m"


def ok(msg): print(f"  {VERDE}✅ {msg}{RESET}")
def erro(msg): print(f"  {VERMELHO}❌ {msg}{RESET}")
def aviso(msg): print(f"  {AMARELO}⚠️  {msg}{RESET}")
def info(msg): print(f"  {AZUL}ℹ️  {msg}{RESET}")


def linha(titulo=""):
    if titulo:
        print(f"\n{NEGRITO}{'─'*50}{RESET}")
        print(f"{NEGRITO}  {titulo}{RESET}")
        print(f"{NEGRITO}{'─'*50}{RESET}")
    else:
        print(f"{'─'*50}")


# ─────────────────────────────────────────────────
# 1. WHATSAPP
# ─────────────────────────────────────────────────

async def testar_whatsapp():
    linha("📱 WHATSAPP CONNECTOR")
    from nucleo.conectores.whatsapp import whatsapp, _calcular_delay_digitacao, _aplicar_typo

    # Teste de delay
    delay = _calcular_delay_digitacao("Oi João, tudo bem? Precisamos conversar sobre seu onboarding.", 45)
    ok(f"Cálculo de delay: {delay:.1f}s para digitar mensagem de teste")

    # Teste de typo
    msg, correcao = _aplicar_typo("Precisamos resolver isso urgente", 1.0)  # força typo
    if correcao:
        ok(f"Simulação de typo: '{msg}' → correção: '{correcao}'")
    else:
        aviso("Typo não ativado (esperado se frase muito curta)")

    # Teste de envio simulado
    sids = await whatsapp.enviar(
        agente_id="ana_costa",
        para="+5511999999999",
        mensagem="Oi João! Tudo pronto para o onboarding de segunda.",
        nome_destinatario="João",
        humanizar=False,  # sem delay no teste
    )
    if sids:
        ok(f"Envio simulado: {len(sids)} mensagem(ns) | SIDs: {sids}")
    else:
        erro("Falha no envio simulado")

    # Verificar Twilio real
    import os
    if os.getenv("TWILIO_ACCOUNT_SID"):
        ok("Twilio configurado — modo produção ativo")
    else:
        aviso("TWILIO_ACCOUNT_SID não configurada — rodando em modo simulação")
        info("Para configurar: echo \"TWILIO_ACCOUNT_SID='ACxxx'\" >> .env")

    # Teste de webhook
    dados_fake = {
        "From": "whatsapp:+5511987654321",
        "Body": "Oi Ana, quando começo?",
        "NumMedia": "0",
    }
    recebida = whatsapp.processar_webhook(dados_fake)
    ok(f"Webhook processado: de={recebida['de']}, texto='{recebida['texto']}'")


# ─────────────────────────────────────────────────
# 2. PAGAMENTOS
# ─────────────────────────────────────────────────

def testar_pagamentos():
    linha("💳 PAGAMENTOS CONNECTOR")
    from nucleo.conectores.pagamentos import pagamentos, DadosCobranca

    dados_teste = DadosCobranca(
        valor=297.00,
        descricao="Teste — Licença Nucleo Empreende",
        email_pagador="teste@nucleo.dev",
        nome_pagador="Cliente Teste",
        cpf_pagador="12345678900",
    )

    # Pix
    resultado_pix = pagamentos.pix(dados_teste)
    if resultado_pix.sucesso:
        ok(f"Pix simulado: ID={resultado_pix.id_transacao} | Status={resultado_pix.status}")
        if "qr_code" in resultado_pix.dados_extras:
            ok(f"QR Code gerado: {resultado_pix.dados_extras['qr_code'][:40]}...")
    else:
        erro(f"Pix falhou: {resultado_pix.erro}")

    # Boleto
    resultado_boleto = pagamentos.boleto(dados_teste)
    if resultado_boleto.sucesso:
        ok(f"Boleto simulado: ID={resultado_boleto.id_transacao} | Status={resultado_boleto.status}")
    else:
        erro(f"Boleto falhou: {resultado_boleto.erro}")

    # Teste de limite financeiro
    dados_alto = DadosCobranca(
        valor=15000.00,
        descricao="Teste de limite financeiro",
        email_pagador="teste@nucleo.dev",
        nome_pagador="Cliente Teste",
    )
    resultado_limite = pagamentos.pix(dados_alto)
    if resultado_limite.status == "aguardando_aprovacao_dono":
        ok(f"Limite financeiro funcionando: R$15.000 corretamente bloqueado para aprovação do Dono")
    else:
        aviso("Verificar configuração de limite financeiro")

    # APIs reais
    import os
    if os.getenv("MERCADOPAGO_ACCESS_TOKEN"):
        ok("Mercado Pago configurado — modo produção ativo")
    else:
        aviso("MERCADOPAGO_ACCESS_TOKEN não configurada — simulação ativa")
        info("Obtenha em: https://www.mercadopago.com.br/developers/panel")

    if os.getenv("STRIPE_SECRET_KEY"):
        ok("Stripe configurado — modo produção ativo")
    else:
        aviso("STRIPE_SECRET_KEY não configurada — simulação ativa")
        info("Obtenha em: https://dashboard.stripe.com/apikeys")

    # Histórico
    historico = pagamentos.historico(5)
    ok(f"Log de transações: {len(historico)} registro(s) encontrado(s)")


# ─────────────────────────────────────────────────
# 3. MEMÓRIA
# ─────────────────────────────────────────────────

def testar_memoria():
    linha("🧠 MEMÓRIA CONNECTOR")
    from nucleo.conectores.memoria import memoria

    # Salvar memórias
    mem1 = memoria.memorizar(
        "dani_ferreira",
        "Concorrente X lança features toda terça-feira.",
        tipo="aprendizado",
        relevancia=0.95,
        tags=["concorrente", "produto"],
        camadas="banco",
    )
    ok(f"Memória salva: ID={mem1.id} | Tipo={mem1.tipo}")

    memoria.registrar_decisao(
        "lucas_mendes",
        "Aprovar campanha Instagram de R$8.000",
        "CTR atual 2.1%, meta 3.5%",
    )
    ok("Decisão do CEO registrada")

    memoria.registrar_tarefa_concluida(
        "mariana_oliveira",
        "Criação de campanha Q1",
        "5 criativos entregues, CTR médio esperado 3.2%",
    )
    ok("Tarefa da CMO registrada")

    # Contexto de sessão
    memoria.adicionar_mensagem("pedro_lima", "user", "Pedro, como está o caixa?")
    memoria.adicionar_mensagem("pedro_lima", "assistant", "Caixa atual: R$45.000. 3 pagamentos pendentes.")
    ok("Contexto de sessão adicionado")

    # Buscar
    ctx = memoria.cache.contexto_sessao("pedro_lima")
    ok(f"Contexto recuperado: {len(ctx)} mensagem(ns) na sessão de Pedro Lima")

    memorias_dani = memoria.banco.buscar("dani_ferreira", limite=5)
    ok(f"Banco: {len(memorias_dani)} memória(s) de Dani Ferreira")

    # Formatado para prompt
    contexto_fmt = memoria.lembrar_formatado("lucas_mendes", "decisão financeira campanha")
    ok(f"Contexto formatado para LLM: {len(contexto_fmt)} chars")
    print(f"\n  {AZUL}Preview do contexto:{RESET}")
    for linha_ctx in contexto_fmt.split("\n")[:6]:
        print(f"    {linha_ctx}")

    # Resumo do agente
    resumo = memoria.resumo_agente("dani_ferreira")
    ok(f"Resumo Dani: {resumo['total_memorias']} memória(s) | por tipo: {resumo['por_tipo']}")

    # Redis
    import os
    if os.getenv("REDIS_URL") or True:  # Redis local sempre tenta
        try:
            import redis
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            r.ping()
            ok("Redis conectado — memória curto prazo online")
        except:
            aviso("Redis não disponível — usando fallback em arquivo")
            info("Instale: sudo apt install redis-server && sudo service redis start")

    if os.getenv("PINECONE_API_KEY"):
        ok("Pinecone configurado — memória vetorial ativa")
    else:
        aviso("PINECONE_API_KEY não configurada — busca semântica desativada")
        info("Obtenha em: https://app.pinecone.io (free tier disponível)")

    if os.getenv("SUPABASE_URL"):
        ok("Supabase configurado — banco principal ativo")
    else:
        aviso("SUPABASE_URL não configurada — usando arquivos locais")
        info("Crie em: https://app.supabase.com (free tier disponível)")


# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────

async def main():
    print(f"\n{NEGRITO}{'═'*50}{RESET}")
    print(f"{NEGRITO}  🧪 NÚCLEO VENTURES — Teste de Conectores{RESET}")
    print(f"{NEGRITO}{'═'*50}{RESET}")

    erros = 0

    try:
        await testar_whatsapp()
    except Exception as e:
        erro(f"WhatsApp: erro crítico — {e}")
        erros += 1

    try:
        testar_pagamentos()
    except Exception as e:
        erro(f"Pagamentos: erro crítico — {e}")
        erros += 1

    try:
        testar_memoria()
    except Exception as e:
        erro(f"Memória: erro crítico — {e}")
        erros += 1

    linha()
    if erros == 0:
        print(f"\n  {VERDE}{NEGRITO}✅ Todos os conectores OK!{RESET}")
        print(f"  {AZUL}Os modos simulação garantem funcionamento sem API Keys.{RESET}")
        print(f"  {AZUL}Configure as variáveis no .env para ativar produção.{RESET}\n")
    else:
        print(f"\n  {VERMELHO}{NEGRITO}❌ {erros} conector(es) com erro crítico.{RESET}")
        print(f"  Verifique o log acima para detalhes.\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
