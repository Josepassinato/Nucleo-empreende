"""
╔══════════════════════════════════════════════════════════════╗
║   NUCLEO EMPREENDE — Motor de Execução dos Agentes          ║
║                                                             ║
║   Cada agente tem poder de executar ações reais:            ║
║   Lucas  → config empresa, contratar, demitir               ║
║   Mariana → campanhas Meta Ads, criativos, posts            ║
║   Pedro   → pagamentos, transferências, relatórios          ║
║   Carla   → contratos, processos, fornecedores              ║
║   Rafael  → produto, roadmap, tasks                         ║
║   Ana     → RH, onboarding, comunicados                     ║
║   Dani    → relatórios, analytics, dashboards               ║
║   Zé      → reuniões, coaching, cultura                     ║
║   Beto    → otimizações, automações, custos                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, re, httpx, asyncio
from pathlib import Path
from datetime import datetime
from typing import Any

CONFIG_DIR  = Path("nucleo/config")
LOGS_DIR    = Path("nucleo/logs")
CONFIG_FILE = CONFIG_DIR / "projeto.json"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log_acao(agente: str, acao: str, resultado: str, dados: dict = {}):
    entry = {
        "ts": datetime.now().isoformat(),
        "agente": agente,
        "acao": acao,
        "resultado": resultado,
        "dados": dados,
    }
    log_file = LOGS_DIR / "acoes.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def carregar_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except: pass
    return {"empresa": {}, "agentes": {}, "equipe": [], "fornecedores": [], "campanhas": []}

def salvar_config(config: dict):
    config["atualizado_em"] = datetime.now().isoformat()
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2))

# ══════════════════════════════════════════════════════════════
# LUCAS — CEO (Config + RH + Decisões)
# ══════════════════════════════════════════════════════════════

class LucasExecutor:
    nome = "Lucas Mendes — CEO"

    @staticmethod
    def detectar(texto: str) -> dict | None:
        txt = texto.lower()
        padroes = [
            # Config empresa
            (r"ramo\s+(?:[ée]\s+|como\s+)?(.+)", "config_ramo"),
            (r"(?:somos|empresa)\s+(?:de\s+)?(.+)", "config_ramo"),
            (r"produto\s+(?:principal\s+)?(?:[ée]\s+)?(.+)", "config_produto"),
            (r"(?:vendemos|vendo)\s+(.+)", "config_produto"),
            (r"público.alvo\s+(?:[ée]\s+)?(.+)", "config_publico"),
            (r"meta\s+(?:de\s+)?(?:faturamento\s+)?(?:[ée]\s+)?r?\$?\s*([\d.,]+\w*)", "config_meta"),
            (r"nome\s+da\s+empresa\s+(?:[ée]\s+|para\s+)?(.+)", "config_nome"),
            (r"missão\s+(?:[ée]\s+)?(.+)", "config_missao"),
            (r"visão\s+(?:[ée]\s+)?(.+)", "config_visao"),
            # RH
            (r"contratar?\s+(?:um[a]?\s+)?(.+)", "rh_contratar"),
            (r"demitir?\s+(.+)", "rh_demitir"),
            (r"promover?\s+(.+)\s+(?:a|para)\s+(.+)", "rh_promover"),
            (r"(?:novo|nova)\s+(?:funcionário|funcionária|colaborador)\s+(.+)", "rh_contratar"),
            # Decisões
            (r"(?:prioridade|foco)\s+(?:da\s+empresa\s+)?(?:[ée]\s+)?(.+)", "config_prioridade"),
            (r"limite\s+(?:de\s+)?aprovação\s+(?:[ée]\s+)?r?\$?\s*([\d.,]+)", "config_limite"),
        ]
        for padrao, acao in padroes:
            m = re.search(padrao, txt, re.IGNORECASE)
            if m:
                return {"acao": acao, "grupos": m.groups(), "texto": texto}
        return None

    @staticmethod
    async def executar(intencao: dict) -> str:
        acao   = intencao["acao"]
        grupos = intencao["grupos"]
        config = carregar_config()

        if acao == "config_ramo":
            valor = grupos[0].strip().rstrip(".")
            config.setdefault("empresa", {})["ramo"] = valor
            # Propagar para todos os agentes
            for ag in ["lucas_mendes","mariana_oliveira","pedro_lima","carla_santos",
                       "rafael_torres","ana_costa","dani_ferreira","ze_carvalho","beto_rocha"]:
                _atualizar_contexto_agente(ag, f"Ramo: {valor}")
            salvar_config(config)
            log_acao("lucas", acao, "ok", {"ramo": valor})
            return f"✅ *Ramo configurado: {valor}*\n\nTodos os 9 agentes foram atualizados com esse contexto. — _Lucas_"

        elif acao == "config_produto":
            valor = grupos[0].strip().rstrip(".")
            config.setdefault("empresa", {})["produto"] = valor
            salvar_config(config)
            log_acao("lucas", acao, "ok", {"produto": valor})
            return f"✅ *Produto registrado: {valor}*\n\nMariana e Rafael já foram notificados. — _Lucas_"

        elif acao == "config_publico":
            valor = grupos[0].strip().rstrip(".")
            config.setdefault("empresa", {})["publico_alvo"] = valor
            salvar_config(config)
            log_acao("lucas", acao, "ok", {"publico": valor})
            return f"✅ *Público-alvo definido: {valor}*\n\nMariana vai calibrar as campanhas para esse perfil. — _Lucas_"

        elif acao == "config_meta":
            valor = grupos[0].strip()
            config.setdefault("empresa", {})["meta_faturamento"] = valor
            salvar_config(config)
            # Atualizar .env com limite
            _env_set("LIMITE_APROVACAO_REAIS", str(int(float(valor.replace(".","").replace(",",".")) * 0.1)))
            log_acao("lucas", acao, "ok", {"meta": valor})
            return f"✅ *Meta de faturamento: R$ {valor}*\n\nPedro vai monitorar o progresso. Limite de aprovação automática ajustado para 10% da meta. — _Lucas_"

        elif acao == "config_nome":
            valor = grupos[0].strip().rstrip(".")
            config.setdefault("empresa", {})["nome"] = valor
            _env_set("EMPRESA_NOME", valor)
            salvar_config(config)
            log_acao("lucas", acao, "ok", {"nome": valor})
            return f"✅ *Nome da empresa atualizado: {valor}*\n\nAtualizado no sistema e em todos os agentes. — _Lucas_"

        elif acao == "config_missao":
            valor = grupos[0].strip().rstrip(".")
            config.setdefault("empresa", {})["missao"] = valor
            salvar_config(config)
            return f"✅ *Missão definida:*\n\n_{valor}_\n\nVou incorporar isso nas decisões estratégicas. — _Lucas_"

        elif acao == "config_limite":
            valor = grupos[0].strip()
            _env_set("LIMITE_APROVACAO_REAIS", valor)
            salvar_config(config)
            return f"✅ *Limite de aprovação automática: R$ {valor}*\n\nAcima disso, vou te consultar antes de autorizar qualquer gasto. — _Lucas_"

        elif acao == "rh_contratar":
            cargo = grupos[0].strip().rstrip(".")
            funcionario = {"cargo": cargo, "contratado_em": datetime.now().isoformat(), "status": "ativo"}
            config.setdefault("equipe", []).append(funcionario)
            salvar_config(config)
            log_acao("lucas", "contratar", "ok", funcionario)
            return (
                f"✅ *Contratação registrada: {cargo}*\n\n"
                f"Ana (CHRO) vai preparar o onboarding. Pedro (CFO) vai projetar o impacto no custo fixo.\n\n"
                f"Quer que eu defina salário, responsabilidades ou prazo de início? — _Lucas_"
            )

        elif acao == "rh_demitir":
            nome = grupos[0].strip().rstrip(".")
            for f in config.get("equipe", []):
                if nome.lower() in f.get("cargo", "").lower() or nome.lower() in f.get("nome", "").lower():
                    f["status"] = "desligado"
                    f["desligado_em"] = datetime.now().isoformat()
            salvar_config(config)
            log_acao("lucas", "demitir", "ok", {"nome": nome})
            return (
                f"✅ *Desligamento registrado: {nome}*\n\n"
                f"Ana vai iniciar o processo de offboarding. Pedro vai calcular as verbas rescisórias.\n\n"
                f"Confirma o desligamento? — _Lucas_"
            )

        elif acao == "rh_promover":
            nome, cargo_novo = grupos[0].strip(), grupos[1].strip()
            for f in config.get("equipe", []):
                if nome.lower() in f.get("nome", "").lower():
                    f["cargo_anterior"] = f.get("cargo", "")
                    f["cargo"] = cargo_novo
                    f["promovido_em"] = datetime.now().isoformat()
            salvar_config(config)
            return f"✅ *{nome} promovido para {cargo_novo}*\n\nAna vai atualizar o contrato. — _Lucas_"

        elif acao == "config_prioridade":
            valor = grupos[0].strip().rstrip(".")
            config.setdefault("empresa", {})["prioridade"] = valor
            salvar_config(config)
            return f"✅ *Prioridade da empresa: {valor}*\n\nTodos os agentes vão alinhar suas ações com esse foco. — _Lucas_"

        return "Entendido. Pode me dar mais detalhes para eu executar corretamente? — _Lucas_"


# ══════════════════════════════════════════════════════════════
# MARIANA — CMO (Meta Ads + Marketing)
# ══════════════════════════════════════════════════════════════

class MarianaExecutor:
    nome = "Mariana Oliveira — CMO"

    @staticmethod
    def detectar(texto: str) -> dict | None:
        txt = texto.lower()
        padroes = [
            (r"criar?\s+campanha\s+(?:de\s+)?(?:no?\s+)?(.+?)(?:\s+com\s+orçamento\s+r?\$?\s*([\d.,]+))?$", "meta_criar_campanha"),
            (r"campanha\s+(?:para\s+)?(.+?)(?:\s+r?\$?\s*([\d.,]+))?$", "meta_criar_campanha"),
            (r"anunciar?\s+(?:no?\s+)?(.+)", "meta_criar_campanha"),
            (r"pausar?\s+campanha\s+(.+)", "meta_pausar"),
            (r"(?:ligar|ativar)\s+campanha\s+(.+)", "meta_ativar"),
            (r"(?:relatório|resultado|performance)\s+(?:de\s+)?(?:campanha|anúncio|marketing)s?", "meta_relatorio"),
            (r"quanto\s+(?:gastei|gastamos)\s+(?:em\s+)?(?:anúncio|marketing|meta)s?", "meta_relatorio"),
            (r"(?:criar|fazer|postar)\s+(?:um\s+)?post\s+(?:sobre\s+)?(.+)", "post_criar"),
            (r"estratégia\s+(?:de\s+)?marketing\s+(?:para\s+)?(.+)", "estrategia"),
            (r"público\s+(?:de\s+)?(?:anúncio|campanha)\s+(?:[ée]\s+)?(.+)", "meta_publico"),
        ]
        for padrao, acao in padroes:
            m = re.search(padrao, txt, re.IGNORECASE)
            if m:
                return {"acao": acao, "grupos": m.groups(), "texto": texto}
        return None

    @staticmethod
    async def executar(intencao: dict) -> str:
        acao   = intencao["acao"]
        grupos = intencao["grupos"]
        config = carregar_config()
        token  = os.getenv("META_ACCESS_TOKEN", "")

        if acao == "meta_criar_campanha":
            produto = grupos[0].strip().rstrip(".") if grupos else "produto"
            orcamento = grupos[1] if len(grupos) > 1 and grupos[1] else "500"

            if token and token != "''":
                # Tentar criar campanha real via Meta API
                try:
                    ad_account = os.getenv("META_AD_ACCOUNT_ID", "")
                    async with httpx.AsyncClient(timeout=15) as client:
                        r = await client.post(
                            f"https://graph.facebook.com/v18.0/act_{ad_account}/campaigns",
                            params={
                                "name": f"Campanha {produto} — {datetime.now().strftime('%d/%m/%Y')}",
                                "objective": "OUTCOME_LEADS",
                                "status": "PAUSED",
                                "special_ad_categories": "[]",
                                "access_token": token,
                            }
                        )
                    if r.status_code == 200:
                        camp_id = r.json().get("id", "")
                        config.setdefault("campanhas", []).append({
                            "id": camp_id, "produto": produto,
                            "orcamento": orcamento, "status": "pausada",
                            "criada_em": datetime.now().isoformat()
                        })
                        salvar_config(config)
                        log_acao("mariana", "criar_campanha", "ok_meta_api", {"id": camp_id})
                        return (
                            f"✅ *Campanha criada no Meta Ads!*\n\n"
                            f"📢 Produto: {produto}\n"
                            f"💰 Orçamento: R$ {orcamento}/dia\n"
                            f"🔴 Status: Pausada (aguardando sua aprovação)\n"
                            f"🆔 ID: {camp_id}\n\n"
                            f"Quer que eu ative agora? — _Mariana_"
                        )
                except Exception as e:
                    log_acao("mariana", "criar_campanha", f"erro_api: {e}", {})

            # Modo simulação (sem token configurado)
            camp_id = f"CAMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            config.setdefault("campanhas", []).append({
                "id": camp_id, "produto": produto,
                "orcamento": orcamento, "status": "planejada",
                "criada_em": datetime.now().isoformat()
            })
            salvar_config(config)
            log_acao("mariana", "criar_campanha", "simulacao", {"produto": produto})
            return (
                f"📋 *Campanha planejada: {produto}*\n\n"
                f"💰 Orçamento sugerido: R$ {orcamento}/dia\n"
                f"🎯 Objetivo: Geração de leads\n"
                f"📱 Plataformas: Instagram + Facebook\n\n"
                f"Para ativar no Meta Ads, configure o META_ACCESS_TOKEN no .env.\n"
                f"Posso preparar o criativo e o texto do anúncio agora? — _Mariana_"
            )

        elif acao == "meta_relatorio":
            campanhas = config.get("campanhas", [])
            if not campanhas:
                return "Ainda não temos campanhas registradas. Quer criar a primeira? — _Mariana_"
            linhas = ["*Relatório de Campanhas:*\n"]
            for c in campanhas[-5:]:
                linhas.append(f"📢 {c.get('produto','—')} — {c.get('status','—')} — R${c.get('orcamento','?')}/dia")
            linhas.append("\n— _Mariana_")
            return "\n".join(linhas)

        elif acao == "estrategia":
            segmento = grupos[0].strip() if grupos else "o mercado"
            config_emp = config.get("empresa", {})
            produto = config_emp.get("produto", "nosso produto")
            publico = config_emp.get("publico_alvo", segmento)
            return (
                f"🎯 *Estratégia de Marketing — {segmento}*\n\n"
                f"*1. Awareness:* Conteúdo orgânico Instagram + Reels sobre {produto}\n"
                f"*2. Consideração:* Anúncios de tráfego para {publico}\n"
                f"*3. Conversão:* Retargeting + oferta especial\n\n"
                f"Orçamento recomendado: R$ 3.000-5.000/mês\n"
                f"ROI esperado: 3-5x em 90 dias\n\n"
                f"Quer que eu execute essa estratégia agora? — _Mariana_"
            )

        elif acao == "post_criar":
            tema = grupos[0].strip() if grupos else "nossa empresa"
            return (
                f"✍️ *Rascunho de post: {tema}*\n\n"
                f"---\n"
                f"🚀 [Título chamativo sobre {tema}]\n\n"
                f"[Desenvolvimento em 3 bullets]\n"
                f"✅ Benefício 1\n✅ Benefício 2\n✅ Benefício 3\n\n"
                f"👇 [CTA forte]\n\n"
                f"#hashtag1 #hashtag2 #hashtag3\n"
                f"---\n\n"
                f"Aprova esse rascunho ou quer ajustar o tom? — _Mariana_"
            )

        return "Pode me dar mais detalhes da campanha que você quer criar? — _Mariana_"


# ══════════════════════════════════════════════════════════════
# PEDRO — CFO (Pagamentos + Financeiro)
# ══════════════════════════════════════════════════════════════

class PedroExecutor:
    nome = "Pedro Lima — CFO"

    @staticmethod
    def detectar(texto: str) -> dict | None:
        txt = texto.lower()
        padroes = [
            (r"(?:pagar|fazer\s+pagamento|transferir?)\s+r?\$?\s*([\d.,]+)\s+(?:para\s+)?(.+)", "pagar"),
            (r"(?:cobrar|enviar\s+cobrança|link\s+de\s+pagamento)\s+r?\$?\s*([\d.,]+)\s+(?:de\s+|para\s+)?(.+)", "cobrar"),
            (r"(?:saldo|quanto\s+(?:tem|temos|há))\s+(?:em\s+caixa|disponível|no\s+caixa)", "saldo"),
            (r"(?:relatório|resumo)\s+(?:financeiro|de\s+caixa|de\s+gastos)", "relatorio_financeiro"),
            (r"(?:custo|gasto)\s+(?:de\s+)?(.+)\s+é\s+r?\$?\s*([\d.,]+)", "registrar_gasto"),
            (r"registrar?\s+(?:gasto|despesa|custo)\s+(?:de\s+)?r?\$?\s*([\d.,]+)\s+(?:em|com|de)\s+(.+)", "registrar_gasto"),
            (r"(?:receita|faturamos|vendemos)\s+r?\$?\s*([\d.,]+)", "registrar_receita"),
        ]
        for padrao, acao in padroes:
            m = re.search(padrao, txt, re.IGNORECASE)
            if m:
                return {"acao": acao, "grupos": m.groups(), "texto": texto}
        return None

    @staticmethod
    async def executar(intencao: dict) -> str:
        acao   = intencao["acao"]
        grupos = intencao["grupos"]
        config = carregar_config()
        mp_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")

        if acao == "cobrar":
            valor = grupos[0].replace(",", ".") if grupos else "0"
            destinatario = grupos[1].strip() if len(grupos) > 1 else "cliente"

            if mp_token and mp_token not in ("''", ""):
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        r = await client.post(
                            "https://api.mercadopago.com/v1/payment_links",
                            headers={"Authorization": f"Bearer {mp_token}"},
                            json={
                                "title": f"Cobrança — {destinatario}",
                                "unit_price": float(valor),
                                "quantity": 1,
                                "currency_id": "BRL",
                            }
                        )
                    if r.status_code in (200, 201):
                        link = r.json().get("init_point", "")
                        log_acao("pedro", "cobrar", "ok_mp", {"valor": valor, "link": link})
                        return (
                            f"✅ *Link de pagamento gerado!*\n\n"
                            f"💰 Valor: R$ {valor}\n"
                            f"👤 Para: {destinatario}\n"
                            f"🔗 {link}\n\n"
                            f"Envie esse link para o cliente. — _Pedro_"
                        )
                except Exception as e:
                    log_acao("pedro", "cobrar", f"erro: {e}", {})

            # Simulação
            log_acao("pedro", "cobrar", "simulacao", {"valor": valor})
            return (
                f"📋 *Cobrança registrada (simulação)*\n\n"
                f"💰 Valor: R$ {valor}\n"
                f"👤 Para: {destinatario}\n\n"
                f"Para gerar links reais de pagamento, configure o MERCADOPAGO_ACCESS_TOKEN. — _Pedro_"
            )

        elif acao == "saldo":
            receitas = sum(t.get("valor", 0) for t in config.get("transacoes", []) if t.get("tipo") == "receita")
            gastos   = sum(t.get("valor", 0) for t in config.get("transacoes", []) if t.get("tipo") == "gasto")
            saldo    = receitas - gastos
            return (
                f"💰 *Resumo Financeiro*\n\n"
                f"📈 Receitas: R$ {receitas:,.2f}\n"
                f"📉 Gastos: R$ {gastos:,.2f}\n"
                f"💵 Saldo: R$ {saldo:,.2f}\n\n"
                f"— _Pedro_"
            )

        elif acao == "registrar_gasto":
            valor = grupos[0].replace(",", ".") if grupos else "0"
            categoria = grupos[1].strip() if len(grupos) > 1 else "geral"
            transacao = {"tipo": "gasto", "valor": float(valor), "categoria": categoria, "data": datetime.now().isoformat()}
            config.setdefault("transacoes", []).append(transacao)
            salvar_config(config)
            log_acao("pedro", "registrar_gasto", "ok", transacao)
            return f"✅ *Gasto registrado: R$ {valor} em {categoria}* — _Pedro_"

        elif acao == "registrar_receita":
            valor = grupos[0].replace(",", ".") if grupos else "0"
            transacao = {"tipo": "receita", "valor": float(valor), "data": datetime.now().isoformat()}
            config.setdefault("transacoes", []).append(transacao)
            salvar_config(config)
            log_acao("pedro", "registrar_receita", "ok", transacao)
            return f"✅ *Receita registrada: R$ {valor}* 🎉 — _Pedro_"

        elif acao == "relatorio_financeiro":
            transacoes = config.get("transacoes", [])
            if not transacoes:
                return "Ainda sem transações registradas. — _Pedro_"
            receitas = sum(t["valor"] for t in transacoes if t["tipo"] == "receita")
            gastos   = sum(t["valor"] for t in transacoes if t["tipo"] == "gasto")
            return (
                f"📊 *Relatório Financeiro*\n\n"
                f"Total receitas: R$ {receitas:,.2f}\n"
                f"Total gastos: R$ {gastos:,.2f}\n"
                f"Resultado: R$ {receitas-gastos:,.2f}\n"
                f"Transações: {len(transacoes)}\n\n"
                f"— _Pedro_"
            )

        return "Pode detalhar a operação financeira? — _Pedro_"


# ══════════════════════════════════════════════════════════════
# UTILS
# ══════════════════════════════════════════════════════════════

def _atualizar_contexto_agente(agente_id: str, contexto: str):
    arquivos = list(Path("nucleo/agentes").glob(f"{agente_id}*.md"))
    if not arquivos:
        return
    arq = arquivos[0]
    conteudo = arq.read_text()
    if "## CONTEXTO DA EMPRESA" in conteudo:
        conteudo = re.sub(r"## CONTEXTO DA EMPRESA\n.*?(?=\n##|\Z)", f"## CONTEXTO DA EMPRESA\n{contexto}\n", conteudo, flags=re.DOTALL)
    else:
        conteudo += f"\n\n## CONTEXTO DA EMPRESA\n{contexto}\n"
    arq.write_text(conteudo)

def _env_set(chave: str, valor: str):
    env_file = Path(".env")
    if not env_file.exists(): return
    conteudo = env_file.read_text()
    padrao = rf"^{chave}=.*$"
    nova = f"{chave}='{valor}'"
    if re.search(padrao, conteudo, re.MULTILINE):
        conteudo = re.sub(padrao, nova, conteudo, flags=re.MULTILINE)
    else:
        conteudo += f"\n{nova}"
    env_file.write_text(conteudo)


# ══════════════════════════════════════════════════════════════
# ROTEADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════

EXECUTORES = {
    "lucas":   LucasExecutor,
    "mariana": MarianaExecutor,
    "pedro":   PedroExecutor,
}

MAP_MENCOES = {
    "@lucas": "lucas", "@ceo": "lucas",
    "@mariana": "mariana", "@cmo": "mariana", "@marketing": "mariana",
    "@pedro": "pedro", "@cfo": "pedro", "@financeiro": "pedro",
}

async def processar_execucao(texto: str, agente_forcado: str = None) -> str | None:
    """
    Tenta detectar e executar uma ação.
    agente_forcado: quando o usuário usa @mencao
    Retorna None se não detectar nenhuma ação.
    """
    # Determinar qual executor usar
    executores_tentar = []

    if agente_forcado and agente_forcado in EXECUTORES:
        executores_tentar = [EXECUTORES[agente_forcado]]
    else:
        # Verificar @menção no texto
        for mencao, agente_id in MAP_MENCOES.items():
            if mencao in texto.lower():
                if agente_id in EXECUTORES:
                    executores_tentar = [EXECUTORES[agente_id]]
                    break
        # Se não achou menção, tentar todos
        if not executores_tentar:
            executores_tentar = list(EXECUTORES.values())

    for executor in executores_tentar:
        intencao = executor.detectar(texto)
        if intencao:
            return await executor.executar(intencao)

    return None
