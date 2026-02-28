
# ─────────────────────────────────────────────────────────────
# HOTMART (adicionar ao testar_tudo.py)
# ─────────────────────────────────────────────────────────────
async def testar_hotmart():
    head("🛒  HOTMART — Vendas, Assinaturas, Afiliados, Webhooks")
    passou = True
    try:
        from nucleo.conectores.hotmart import hotmart

        # Vendas
        vendas = hotmart.listar_vendas(dias=30)
        ok(f"Vendas (30 dias): {len(vendas)} encontradas")
        aprovadas = [v for v in vendas if v.status == "APPROVED"]
        ok(f"  Aprovadas: {len(aprovadas)} | Faturamento: R$ {sum(v.valor for v in aprovadas):,.2f}")

        # Assinaturas
        n_ativos = hotmart.assinantes_ativos()
        ok(f"Assinantes ativos: {n_ativos}")

        # Carrinho abandonado
        carrinhos = hotmart.carrinhos_abandonados(dias=7)
        ok(f"Carrinhos abandonados (7 dias): {len(carrinhos)}")

        # Cupom
        r = hotmart.criar_cupom("NUCLEO20", 20.0, validade_dias=30)
        ok(f"Cupom criado: NUCLEO20 — 20% off | ID: {r.get('id','simulado')}")

        # Webhook simulado — compra aprovada
        payload_fake = {
            "event": "PURCHASE_APPROVED",
            "data": {
                "buyer": {"name": "Carlos Mendonça", "email": "carlos@empresa.com"},
                "product": {"name": "Nucleo Empreende Pro"},
                "payment": {"value": {"value": 997.0}, "type": "PIX", "installments_number": 1},
                "purchase": {"transaction": "HP20260228001", "status": "APPROVED"},
            }
        }
        evento = hotmart.processar_webhook(payload_fake)
        ok(f"Webhook PURCHASE_APPROVED → {evento['acao_sugerida'][:55]}")

        # Webhook chargeback
        payload_cb = {**payload_fake, "event": "PURCHASE_CHARGEBACK"}
        ev_cb = hotmart.processar_webhook(payload_cb)
        ok(f"Webhook PURCHASE_CHARGEBACK → {ev_cb['acao_sugerida'][:55]}")

        # Relatório mensal
        rel = hotmart.relatorio_mensal()
        ok(f"Relatório {rel.periodo}: R$ {rel.faturamento_bruto:,.2f} bruto | {rel.vendas_aprovadas} vendas | churn {rel.churn_rate}%")
        print(f"\n{B}  Preview do relatório:{X}")
        for linha in hotmart.relatorio_texto().split("\n")[:10]:
            print(f"    {linha}")

        info(f"Hotmart configurado: {'SIM' if os.getenv('HOTMART_CLIENT_ID') else 'NÃO — usando simulação'}")
        info(f"Ambiente: {os.getenv('HOTMART_AMBIENTE','sandbox').upper()}")

    except Exception as e:
        err(f"Erro: {e}"); passou = False
    registrar("hotmart", passou)
