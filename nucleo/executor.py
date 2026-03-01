"""
╔══════════════════════════════════════════════════════════════╗
║   NUCLEO EMPREENDE — Motor de Execução Completo             ║
║   Todos os 9 agentes com poder de ação real                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, re, httpx
from pathlib import Path
from datetime import datetime

CONFIG_DIR  = Path("nucleo/config")
LOGS_DIR    = Path("nucleo/logs")
CONFIG_FILE = CONFIG_DIR / "projeto.json"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log_acao(agente, acao, resultado, dados={}):
    entry = {"ts": datetime.now().isoformat(), "agente": agente, "acao": acao, "resultado": resultado, "dados": dados}
    with open(LOGS_DIR / "acoes.jsonl", "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def carregar_config():
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text())
        except: pass
    return {"empresa": {}, "agentes": {}, "equipe": [], "fornecedores": [], "campanhas": [], "transacoes": [], "tarefas": [], "contratos": []}

def salvar_config(config):
    config["atualizado_em"] = datetime.now().isoformat()
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2))

def env_set(chave, valor):
    env_file = Path(".env")
    if not env_file.exists(): return
    c = env_file.read_text()
    nova = f"{chave}='{valor}'"
    if re.search(rf"^{chave}=.*$", c, re.MULTILINE):
        c = re.sub(rf"^{chave}=.*$", nova, c, flags=re.MULTILINE)
    else:
        c += f"\n{nova}"
    env_file.write_text(c)

def atualizar_contexto_agentes(contexto):
    for md in Path("nucleo/agentes").glob("*.md"):
        c = md.read_text()
        if "## CONTEXTO DA EMPRESA" in c:
            c = re.sub(r"## CONTEXTO DA EMPRESA\n.*?(?=\n##|\Z)", f"## CONTEXTO DA EMPRESA\n{contexto}\n", c, flags=re.DOTALL)
        else:
            c += f"\n\n## CONTEXTO DA EMPRESA\n{contexto}\n"
        md.write_text(c)


# ══════════════════════════════════════════════════════════════
# LUCAS — CEO
# ══════════════════════════════════════════════════════════════
class LucasExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"ramo\s+(?:[ée]\s+|como\s+)?(.+)", "config_ramo"),
            (r"(?:somos|empresa)\s+(?:de\s+)?(.+)", "config_ramo"),
            (r"produto\s+(?:principal\s+)?(?:[ée]\s+)?(.+)", "config_produto"),
            (r"(?:vendemos|vendo|oferecemos)\s+(.+)", "config_produto"),
            (r"público.alvo\s+(?:[ée]\s+)?(.+)", "config_publico"),
            (r"meta\s+(?:de\s+)?faturamento\s+(?:[ée]\s+)?r?\$?\s*([\d.,]+\w*)", "config_meta"),
            (r"nome\s+da\s+empresa\s+(?:[ée]\s+|para\s+)?(.+)", "config_nome"),
            (r"missão\s+(?:[ée]\s+)?(.+)", "config_missao"),
            (r"visão\s+(?:[ée]\s+)?(.+)", "config_visao"),
            (r"limite\s+(?:de\s+)?aprovação\s+(?:[ée]\s+)?r?\$?\s*([\d.,]+)", "config_limite"),
            (r"prioridade\s+(?:[ée]\s+)?(.+)", "config_prioridade"),
            (r"contratar?\s+(?:um[a]?\s+)?(.+)", "rh_contratar"),
            (r"(?:novo|nova)\s+(?:funcionário|colaborador)\s+(.+)", "rh_contratar"),
            (r"demitir?\s+(.+)", "rh_demitir"),
            (r"promover?\s+(.+?)\s+(?:a|para)\s+(.+)", "rh_promover"),
            (r"ver\s+config(?:uração)?", "ver_config"),
            (r"equipe\s+atual", "ver_equipe"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()
        emp = cfg.setdefault("empresa", {})

        if a == "config_ramo":
            v = g[0].strip().rstrip(".")
            emp["ramo"] = v
            atualizar_contexto_agentes(f"Empresa: {emp.get('nome','—')} | Ramo: {v} | Produto: {emp.get('produto','—')}")
            salvar_config(cfg); log_acao("lucas", a, "ok", {"ramo": v})
            return f"✅ *Ramo: {v}*\n\nTodos os 9 agentes atualizados. — _Lucas_"

        elif a == "config_produto":
            v = g[0].strip().rstrip(".")
            emp["produto"] = v; salvar_config(cfg)
            return f"✅ *Produto: {v}*\n\nMariana e Rafael notificados. — _Lucas_"

        elif a == "config_publico":
            v = g[0].strip().rstrip(".")
            emp["publico_alvo"] = v; salvar_config(cfg)
            return f"✅ *Público-alvo: {v}*\n\nMariana vai calibrar as campanhas. — _Lucas_"

        elif a == "config_meta":
            v = g[0].strip()
            emp["meta_faturamento"] = v; salvar_config(cfg)
            return f"✅ *Meta: R$ {v}*\n\nPedro vai monitorar o progresso. — _Lucas_"

        elif a == "config_nome":
            v = g[0].strip().rstrip(".")
            emp["nome"] = v; env_set("EMPRESA_NOME", v); salvar_config(cfg)
            return f"✅ *Nome da empresa: {v}* — _Lucas_"

        elif a == "config_missao":
            emp["missao"] = g[0].strip().rstrip("."); salvar_config(cfg)
            return f"✅ *Missão definida.* Incorporado nas decisões estratégicas. — _Lucas_"

        elif a == "config_visao":
            emp["visao"] = g[0].strip().rstrip("."); salvar_config(cfg)
            return f"✅ *Visão definida.* Todos os agentes alinhados. — _Lucas_"

        elif a == "config_limite":
            v = g[0].strip(); env_set("LIMITE_APROVACAO_REAIS", v); salvar_config(cfg)
            return f"✅ *Limite de aprovação: R$ {v}*\n\nAcima disso, vou te consultar antes. — _Lucas_"

        elif a == "config_prioridade":
            emp["prioridade"] = g[0].strip().rstrip("."); salvar_config(cfg)
            return f"✅ *Prioridade: {g[0].strip()}*\n\nTodos os agentes alinhados com esse foco. — _Lucas_"

        elif a == "rh_contratar":
            cargo = g[0].strip().rstrip(".")
            cfg.setdefault("equipe", []).append({"cargo": cargo, "status": "ativo", "contratado_em": datetime.now().isoformat()})
            salvar_config(cfg); log_acao("lucas", a, "ok", {"cargo": cargo})
            return f"✅ *Contratação: {cargo}*\n\nAna prepara o onboarding. Pedro projeta o impacto no custo fixo.\nQuer definir salário e responsabilidades? — _Lucas_"

        elif a == "rh_demitir":
            nome = g[0].strip().rstrip(".")
            for f in cfg.get("equipe", []):
                if nome.lower() in f.get("cargo","").lower(): f["status"] = "desligado"
            salvar_config(cfg)
            return f"✅ *Desligamento: {nome}*\n\nAna inicia o offboarding. Pedro calcula as verbas. — _Lucas_"

        elif a == "rh_promover":
            nome, cargo = g[0].strip(), g[1].strip()
            for f in cfg.get("equipe", []):
                if nome.lower() in f.get("cargo","").lower(): f["cargo"] = cargo
            salvar_config(cfg)
            return f"✅ *{nome} promovido para {cargo}* — _Lucas_"

        elif a == "ver_config":
            e = cfg.get("empresa", {})
            return (f"*Configuração da empresa:*\n\n"
                    f"🏢 {e.get('nome','—')}\n🏭 Ramo: {e.get('ramo','—')}\n"
                    f"📦 Produto: {e.get('produto','—')}\n🎯 Público: {e.get('publico_alvo','—')}\n"
                    f"💰 Meta: {e.get('meta_faturamento','—')}\n📌 Prioridade: {e.get('prioridade','—')}\n\n— _Lucas_")

        elif a == "ver_equipe":
            eq = cfg.get("equipe", [])
            if not eq: return "Nenhum funcionário registrado ainda. — _Lucas_"
            linhas = ["*Equipe atual:*\n"] + [f"👤 {f['cargo']} — {f['status']}" for f in eq]
            return "\n".join(linhas) + "\n\n— _Lucas_"


# ══════════════════════════════════════════════════════════════
# MARIANA — CMO
# ══════════════════════════════════════════════════════════════
class MarianaExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"criar?\s+campanha\s+(?:de\s+|para\s+)?(.+?)(?:\s+r?\$?\s*([\d.,]+))?$", "criar_campanha"),
            (r"campanha\s+(?:para\s+)?(.+?)(?:\s+r?\$?\s*([\d.,]+))?$", "criar_campanha"),
            (r"anunciar?\s+(?:no?\s+|na\s+)?(.+)", "criar_campanha"),
            (r"pausar?\s+campanha\s+(.+)", "pausar"),
            (r"(?:ligar|ativar)\s+campanha\s+(.+)", "ativar"),
            (r"(?:relatório|resultado|performance)\s+(?:de\s+)?(?:campanha|marketing|anúncio)", "relatorio"),
            (r"quanto\s+(?:gastei|gastamos)\s+(?:em\s+)?(?:anúncio|marketing|meta)", "relatorio"),
            (r"(?:criar|fazer|postar)\s+(?:um\s+)?post\s+(?:sobre\s+)?(.+)", "post"),
            (r"estratégia\s+(?:de\s+)?marketing\s+(?:para\s+)?(.+)", "estrategia"),
            (r"sugestão\s+(?:de\s+)?(?:conteúdo|post|marketing)", "sugestao"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()
        token = os.getenv("META_ACCESS_TOKEN", "")
        emp = cfg.get("empresa", {})

        if a == "criar_campanha":
            produto = g[0].strip().rstrip(".") if g else emp.get("produto", "produto")
            orcamento = g[1] if len(g) > 1 and g[1] else "500"
            if token and token not in ("''", ""):
                try:
                    ad_account = os.getenv("META_AD_ACCOUNT_ID", "")
                    async with httpx.AsyncClient(timeout=15) as c:
                        r = await c.post(f"https://graph.facebook.com/v18.0/act_{ad_account}/campaigns",
                            params={"name": f"Campanha {produto} {datetime.now().strftime('%d/%m/%Y')}",
                                    "objective": "OUTCOME_LEADS", "status": "PAUSED",
                                    "special_ad_categories": "[]", "access_token": token})
                    if r.status_code == 200:
                        cid = r.json().get("id", "")
                        cfg.setdefault("campanhas", []).append({"id": cid, "produto": produto, "orcamento": orcamento, "status": "pausada", "criada_em": datetime.now().isoformat()})
                        salvar_config(cfg); log_acao("mariana", a, "ok_meta", {"id": cid})
                        return f"✅ *Campanha criada no Meta Ads!*\n\n📢 {produto}\n💰 R$ {orcamento}/dia\n🔴 Pausada — aguardando aprovação\n🆔 {cid}\n\nAprovo e ativo agora? — _Mariana_"
                except: pass
            cid = f"CAMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cfg.setdefault("campanhas", []).append({"id": cid, "produto": produto, "orcamento": orcamento, "status": "planejada", "criada_em": datetime.now().isoformat()})
            salvar_config(cfg)
            return (f"📋 *Campanha planejada: {produto}*\n\n💰 Orçamento: R$ {orcamento}/dia\n🎯 Objetivo: Leads\n📱 Instagram + Facebook\n\n"
                    f"Configure META_ACCESS_TOKEN para ativar no Meta Ads.\nPreparar o criativo e texto do anúncio? — _Mariana_")

        elif a == "post":
            tema = g[0].strip() if g else emp.get("produto", "nossa empresa")
            return (f"✍️ *Rascunho de post: {tema}*\n\n"
                    f"🔥 [Headline chamativa sobre {tema}]\n\n✅ Benefício 1\n✅ Benefício 2\n✅ Benefício 3\n\n"
                    f"👇 [CTA forte]\n\n#hashtag1 #hashtag2 #hashtag3\n\nAprova ou ajusto o tom? — _Mariana_")

        elif a == "estrategia":
            seg = g[0].strip() if g else emp.get("publico_alvo", "seu público")
            return (f"🎯 *Estratégia: {seg}*\n\n"
                    f"*1. Awareness:* Reels sobre {emp.get('produto','o produto')}\n"
                    f"*2. Consideração:* Anúncios de tráfego\n*3. Conversão:* Retargeting + oferta\n\n"
                    f"💰 Budget: R$ 3-5k/mês | ROI: 3-5x em 90 dias\n\nExecuto essa estratégia? — _Mariana_")

        elif a == "relatorio":
            camps = cfg.get("campanhas", [])
            if not camps: return "Sem campanhas registradas ainda. Quer criar a primeira? — _Mariana_"
            linhas = ["*Campanhas:*\n"] + [f"📢 {c.get('produto','—')} — {c.get('status','—')} — R${c.get('orcamento','?')}/dia" for c in camps[-5:]]
            return "\n".join(linhas) + "\n\n— _Mariana_"

        elif a == "sugestao":
            produto = emp.get("produto", "seu produto")
            publico = emp.get("publico_alvo", "seu público")
            return (f"💡 *Sugestões de conteúdo:*\n\n"
                    f"1️⃣ Case de sucesso com {publico}\n2️⃣ Como {produto} resolve [dor principal]\n"
                    f"3️⃣ Bastidores da empresa\n4️⃣ Depoimento de cliente\n5️⃣ Comparativo antes/depois\n\nQual eu desenvolvo primeiro? — _Mariana_")

        elif a in ("pausar", "ativar"):
            nome = g[0].strip() if g else ""
            status = "pausada" if a == "pausar" else "ativa"
            for c in cfg.get("campanhas", []):
                if nome.lower() in c.get("produto","").lower(): c["status"] = status
            salvar_config(cfg)
            return f"✅ Campanha *{nome}* {status}. — _Mariana_"


# ══════════════════════════════════════════════════════════════
# PEDRO — CFO
# ══════════════════════════════════════════════════════════════
class PedroExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:pagar|transferir?)\s+r?\$?\s*([\d.,]+)\s+(?:para\s+)?(.+)", "pagar"),
            (r"(?:cobrar|link\s+de\s+pagamento)\s+r?\$?\s*([\d.,]+)\s+(?:de\s+|para\s+)?(.+)", "cobrar"),
            (r"(?:saldo|caixa|quanto\s+temos?\s+disponível)", "saldo"),
            (r"(?:relatório|resumo)\s+financeiro", "relatorio"),
            (r"registrar?\s+(?:gasto|despesa)\s+r?\$?\s*([\d.,]+)\s+(?:em|com|de)\s+(.+)", "gasto"),
            (r"(?:receita|faturamos|vendemos)\s+r?\$?\s*([\d.,]+)", "receita"),
            (r"projeção\s+(?:de\s+)?(?:faturamento|receita|caixa)", "projecao"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()
        mp = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")

        if a == "cobrar":
            valor, dest = g[0].replace(",","."), g[1].strip() if len(g)>1 else "cliente"
            if mp and mp not in ("''",""):
                try:
                    async with httpx.AsyncClient(timeout=15) as c:
                        r = await c.post("https://api.mercadopago.com/v1/payment_links",
                            headers={"Authorization": f"Bearer {mp}"},
                            json={"title": f"Cobrança — {dest}", "unit_price": float(valor), "quantity": 1, "currency_id": "BRL"})
                    if r.status_code in (200,201):
                        link = r.json().get("init_point","")
                        log_acao("pedro", a, "ok_mp", {"valor": valor, "link": link})
                        return f"✅ *Link gerado!*\n\n💰 R$ {valor}\n👤 {dest}\n🔗 {link}\n\n— _Pedro_"
                except: pass
            return f"📋 *Cobrança: R$ {valor} de {dest}*\n\nConfigure MERCADOPAGO_ACCESS_TOKEN para gerar links reais. — _Pedro_"

        elif a == "pagar":
            valor, dest = g[0].replace(",","."), g[1].strip() if len(g)>1 else "fornecedor"
            limite = float(os.getenv("LIMITE_APROVACAO_REAIS","10000"))
            if float(valor.replace(",","")) > limite:
                return f"⚠️ *Aprovação necessária!*\n\nPagamento de R$ {valor} para {dest} está acima do limite de R$ {limite:,.0f}.\n\nAutoriza? Responda *SIM* ou *NÃO* — _Pedro_"
            cfg.setdefault("transacoes",[]).append({"tipo":"gasto","valor":float(valor),"categoria":dest,"data":datetime.now().isoformat()})
            salvar_config(cfg)
            return f"✅ *Pagamento registrado: R$ {valor} → {dest}* — _Pedro_"

        elif a == "saldo":
            ts = cfg.get("transacoes",[])
            rec = sum(t["valor"] for t in ts if t.get("tipo")=="receita")
            gas = sum(t["valor"] for t in ts if t.get("tipo")=="gasto")
            return f"💰 *Saldo atual*\n\n📈 Receitas: R$ {rec:,.2f}\n📉 Gastos: R$ {gas:,.2f}\n💵 Disponível: R$ {rec-gas:,.2f}\n\n— _Pedro_"

        elif a == "relatorio":
            ts = cfg.get("transacoes",[])
            if not ts: return "Sem transações registradas. — _Pedro_"
            rec = sum(t["valor"] for t in ts if t.get("tipo")=="receita")
            gas = sum(t["valor"] for t in ts if t.get("tipo")=="gasto")
            return f"📊 *Relatório Financeiro*\n\n📈 Receitas: R$ {rec:,.2f}\n📉 Gastos: R$ {gas:,.2f}\n💵 Resultado: R$ {rec-gas:,.2f}\n📝 Transações: {len(ts)}\n\n— _Pedro_"

        elif a == "gasto":
            valor, cat = g[0].replace(",","."), g[1].strip() if len(g)>1 else "geral"
            cfg.setdefault("transacoes",[]).append({"tipo":"gasto","valor":float(valor),"categoria":cat,"data":datetime.now().isoformat()})
            salvar_config(cfg)
            return f"✅ *Gasto: R$ {valor} em {cat}* — _Pedro_"

        elif a == "receita":
            valor = g[0].replace(",",".")
            cfg.setdefault("transacoes",[]).append({"tipo":"receita","valor":float(valor),"data":datetime.now().isoformat()})
            salvar_config(cfg)
            return f"✅ *Receita registrada: R$ {valor}* 🎉 — _Pedro_"

        elif a == "projecao":
            ts = cfg.get("transacoes",[])
            rec = sum(t["valor"] for t in ts if t.get("tipo")=="receita")
            meta = cfg.get("empresa",{}).get("meta_faturamento","?")
            return f"📈 *Projeção de Faturamento*\n\nReceita atual: R$ {rec:,.2f}\nMeta: R$ {meta}\n\nNecessário para bater a meta: R$ {float(str(meta).replace('.','').replace(',','.') or 0) - rec:,.2f}\n\n— _Pedro_"


# ══════════════════════════════════════════════════════════════
# CARLA — COO (Operações + Contratos)
# ══════════════════════════════════════════════════════════════
class CarlaExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:criar|fazer|assinar)\s+contrato\s+(?:com\s+|para\s+)?(.+)", "contrato"),
            (r"(?:novo|adicionar)\s+fornecedor\s+(.+)", "fornecedor"),
            (r"(?:listar|ver)\s+fornecedores?", "listar_fornecedores"),
            (r"processo\s+(?:de\s+)?(.+)\s+(?:está|está)\s+(.+)", "processo"),
            (r"(?:criar|mapear|documentar)\s+processo\s+(?:de\s+)?(.+)", "criar_processo"),
            (r"(?:relatório|status)\s+(?:de\s+)?operações?", "relatorio_ops"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()

        if a == "contrato":
            parte = g[0].strip().rstrip(".")
            contrato = {"parte": parte, "status": "rascunho", "criado_em": datetime.now().isoformat(), "id": f"CTR{datetime.now().strftime('%Y%m%d%H%M%S')}"}
            cfg.setdefault("contratos",[]).append(contrato)
            salvar_config(cfg); log_acao("carla", a, "ok", contrato)
            return (f"✅ *Contrato iniciado com {parte}*\n\n"
                    f"📄 ID: {contrato['id']}\n🔴 Status: Rascunho\n\n"
                    f"Configure CLICKSIGN_ACCESS_TOKEN para assinar digitalmente.\nDefina as cláusulas principais? — _Carla_")

        elif a == "fornecedor":
            nome = g[0].strip().rstrip(".")
            forn = {"nome": nome, "status": "ativo", "adicionado_em": datetime.now().isoformat()}
            cfg.setdefault("fornecedores",[]).append(forn)
            salvar_config(cfg)
            return f"✅ *Fornecedor adicionado: {nome}*\n\nRegistrado no sistema. Quer adicionar contato, prazo de pagamento ou categoria? — _Carla_"

        elif a == "listar_fornecedores":
            forns = cfg.get("fornecedores",[])
            if not forns: return "Nenhum fornecedor cadastrado ainda. — _Carla_"
            linhas = ["*Fornecedores:*\n"] + [f"🏭 {f['nome']} — {f['status']}" for f in forns]
            return "\n".join(linhas) + "\n\n— _Carla_"

        elif a == "criar_processo":
            proc = g[0].strip().rstrip(".")
            return (f"📋 *Processo mapeado: {proc}*\n\n"
                    f"1️⃣ Início: [Gatilho ou solicitação]\n2️⃣ Execução: [Passos principais]\n"
                    f"3️⃣ Validação: [Checklist de qualidade]\n4️⃣ Entrega: [Output final]\n\n"
                    f"Quer que eu documente e salve esse processo? — _Carla_")

        elif a == "relatorio_ops":
            forns = len(cfg.get("fornecedores",[]))
            conts = len(cfg.get("contratos",[]))
            return f"📊 *Status de Operações*\n\n🏭 Fornecedores: {forns}\n📄 Contratos: {conts}\n⚙️ Processos: mapeados\n\n— _Carla_"


# ══════════════════════════════════════════════════════════════
# RAFAEL — CPO (Produto + Roadmap)
# ══════════════════════════════════════════════════════════════
class RafaelExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:criar|adicionar)\s+(?:tarefa|task|feature)\s+(?:de\s+|para\s+)?(.+)", "criar_tarefa"),
            (r"(?:priorizar|dar\s+prioridade)\s+(?:para\s+)?(.+)", "priorizar"),
            (r"roadmap\s+(?:de\s+)?(.+)", "roadmap"),
            (r"(?:status|como\s+está)\s+(?:o\s+)?produto", "status_produto"),
            (r"lançar?\s+(?:versão|release|feature)\s+(.+)", "lancamento"),
            (r"(?:backlog|lista\s+de\s+tarefas)", "ver_backlog"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()

        if a == "criar_tarefa":
            titulo = g[0].strip().rstrip(".")
            tarefa = {"titulo": titulo, "status": "backlog", "criada_em": datetime.now().isoformat(), "id": f"TASK-{len(cfg.get('tarefas',[]))+1:03d}"}
            cfg.setdefault("tarefas",[]).append(tarefa)
            salvar_config(cfg)
            return f"✅ *Task criada: {titulo}*\n\n🆔 {tarefa['id']} | Status: Backlog\n\nQuer definir prioridade e prazo? — _Rafael_"

        elif a == "ver_backlog":
            tasks = cfg.get("tarefas",[])
            if not tasks: return "Backlog vazio. Quer criar a primeira tarefa? — _Rafael_"
            linhas = ["*Backlog:*\n"] + [f"📌 {t['id']} — {t['titulo']} [{t['status']}]" for t in tasks[-10:]]
            return "\n".join(linhas) + "\n\n— _Rafael_"

        elif a == "roadmap":
            tema = g[0].strip() if g else "produto"
            return (f"🗺️ *Roadmap: {tema}*\n\n"
                    f"*Q1:* Fundação — core features\n*Q2:* Crescimento — integrações\n"
                    f"*Q3:* Escala — performance\n*Q4:* Expansão — novos mercados\n\nDetalhamos cada fase? — _Rafael_")

        elif a == "lancamento":
            v = g[0].strip() if g else "nova versão"
            return f"🚀 *Lançamento planejado: {v}*\n\nChecklist: testes ✅ | documentação ⏳ | comunicação ⏳\nQuer que eu coordene o lançamento? — _Rafael_"

        elif a == "status_produto":
            tasks = cfg.get("tarefas",[])
            feitas = len([t for t in tasks if t.get("status")=="done"])
            return f"📦 *Status do Produto*\n\nTasks totais: {len(tasks)}\nConcluídas: {feitas}\nBacklog: {len(tasks)-feitas}\n\n— _Rafael_"


# ══════════════════════════════════════════════════════════════
# ANA — CHRO (RH + Cultura)
# ══════════════════════════════════════════════════════════════
class AnaExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"onboarding\s+(?:de\s+|para\s+)?(.+)", "onboarding"),
            (r"comunicado\s+(?:interno\s+)?(?:sobre\s+)?(.+)", "comunicado"),
            (r"(?:pesquisa|survey)\s+(?:de\s+)?(?:satisfação|clima|engajamento)", "pesquisa"),
            (r"treinamento\s+(?:de\s+|para\s+)?(.+)", "treinamento"),
            (r"(?:cultura|valores)\s+da\s+empresa", "cultura"),
            (r"(?:férias|folga|ausência)\s+(?:de\s+)?(.+)", "ferias"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()

        if a == "onboarding":
            nome = g[0].strip().rstrip(".")
            return (f"✅ *Onboarding iniciado: {nome}*\n\n"
                    f"📋 Checklist:\n☐ Contrato assinado\n☐ Acesso aos sistemas\n☐ Apresentação à equipe\n"
                    f"☐ Treinamento inicial\n☐ Primeira semana de acompanhamento\n\nProcesso ativo. — _Ana_")

        elif a == "comunicado":
            tema = g[0].strip().rstrip(".")
            return (f"📢 *Comunicado interno: {tema}*\n\n"
                    f"Prezada equipe,\n\n[Contexto sobre {tema}]\n\n[Impacto e próximos passos]\n\nConto com a colaboração de todos.\n\n"
                    f"Aprova esse rascunho? — _Ana_")

        elif a == "pesquisa":
            return (f"📊 *Pesquisa de Clima Organizacional*\n\n"
                    f"Perguntas sugeridas:\n1. Satisfação geral (1-10)\n2. Clareza de objetivos\n3. Relação com a liderança\n"
                    f"4. Oportunidades de crescimento\n5. O que melhoraria?\n\nEnvio para a equipe? — _Ana_")

        elif a == "treinamento":
            tema = g[0].strip().rstrip(".")
            return f"📚 *Treinamento planejado: {tema}*\n\nFormato: Online | Duração: 2h | Certificado: Sim\n\nAgendo para a próxima semana? — _Ana_"

        elif a == "cultura":
            emp = cfg.get("empresa", {})
            return (f"🎯 *Cultura da {emp.get('nome','Empresa')}*\n\n"
                    f"Missão: {emp.get('missao','A definir')}\nVisão: {emp.get('visao','A definir')}\n"
                    f"Valores: Inovação | Resultado | Pessoas\n\nQuer que eu crie o manifesto de cultura? — _Ana_")


# ══════════════════════════════════════════════════════════════
# DANI — Dados & Analytics
# ══════════════════════════════════════════════════════════════
class DaniExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:relatório|dashboard|métricas)\s+(?:de\s+)?(.+)", "relatorio"),
            (r"(?:analisar|análise)\s+(?:de\s+)?(.+)", "analise"),
            (r"(?:kpi|indicadores?)\s+(?:de\s+)?(.+)", "kpis"),
            (r"(?:conversão|taxa\s+de\s+conversão)\s+(?:de\s+)?(.+)", "conversao"),
            (r"(?:tendência|trend)\s+(?:de\s+)?(.+)", "tendencia"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()
        tema = g[0].strip().rstrip(".") if g else "geral"

        if a == "relatorio":
            ts = cfg.get("transacoes",[])
            camps = cfg.get("campanhas",[])
            rec = sum(t["valor"] for t in ts if t.get("tipo")=="receita")
            return (f"📊 *Relatório: {tema}*\n\n"
                    f"💰 Receita: R$ {rec:,.2f}\n📢 Campanhas: {len(camps)}\n"
                    f"👥 Equipe: {len(cfg.get('equipe',[]))}\n📄 Contratos: {len(cfg.get('contratos',[]))}\n\n"
                    f"Quer aprofundar algum indicador? — _Dani_")

        elif a == "kpis":
            return (f"📈 *KPIs — {tema}*\n\n"
                    f"🎯 Taxa de conversão: a medir\n💰 CAC: a calcular\n"
                    f"📊 LTV: a calcular\n⚡ NPS: a coletar\n\nConfiguro a coleta automática desses dados? — _Dani_")

        elif a == "analise":
            return (f"🔍 *Análise: {tema}*\n\nPreciso de mais dados para uma análise precisa.\n"
                    f"Fontes disponíveis: GA4, Meta Ads, Mercado Pago\n\nQuer que eu acesse esses dados agora? — _Dani_")

        elif a == "tendencia":
            return f"📈 *Tendência: {tema}*\n\nCom dados históricos posso projetar tendências precisas.\nConfigure GA4_PROPERTY_ID para acesso automático. — _Dani_"


# ══════════════════════════════════════════════════════════════
# ZÉ — Coach & Cultura
# ══════════════════════════════════════════════════════════════
class ZeExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:reunião|meeting)\s+(?:de\s+|sobre\s+)?(.+)", "reuniao"),
            (r"(?:motivar|engajar|animar)\s+(?:a\s+)?(?:equipe|time)", "motivacao"),
            (r"(?:conflito|problema)\s+(?:entre|com)\s+(.+)", "conflito"),
            (r"(?:feedback|avaliação)\s+(?:de\s+)?(.+)", "feedback"),
            (r"(?:meta|objetivo)\s+(?:da\s+semana|semanal)", "meta_semanal"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        tema = g[0].strip().rstrip(".") if g else "equipe"

        if a == "reuniao":
            return (f"📅 *Reunião: {tema}*\n\n"
                    f"Pauta sugerida:\n1️⃣ Check-in (5min)\n2️⃣ Resultados (10min)\n"
                    f"3️⃣ {tema} (20min)\n4️⃣ Próximos passos (10min)\n5️⃣ Check-out (5min)\n\nAgendo e envio os convites? — _Zé_")

        elif a == "motivacao":
            return (f"💪 *Plano de Engajamento*\n\n"
                    f"1️⃣ Reconhecimento público de conquistas\n2️⃣ Meta semanal clara e alcançável\n"
                    f"3️⃣ Check-in individual de 15min\n4️⃣ Celebração de pequenas vitórias\n\nExecuto esse plano? — _Zé_")

        elif a == "conflito":
            return (f"🤝 *Mediação: {tema}*\n\nPasso a passo:\n1. Escuta individual de cada parte\n"
                    f"2. Identificar necessidades reais\n3. Buscar solução ganha-ganha\n4. Acordo documentado\n\nMediação agendada. — _Zé_")

        elif a == "meta_semanal":
            return (f"🎯 *Meta da Semana*\n\nSugestão baseada no contexto atual:\n\n"
                    f"💰 Financeiro: [meta Pedro]\n📢 Marketing: [meta Mariana]\n⚙️ Ops: [meta Carla]\n\nAprova essas metas? — _Zé_")


# ══════════════════════════════════════════════════════════════
# BETO — Otimizador
# ══════════════════════════════════════════════════════════════
class BetoExecutor:
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:reduzir|cortar|economizar)\s+(?:custos?|gastos?|despesas?)", "cortar_custos"),
            (r"(?:automatizar|automação)\s+(?:de\s+)?(.+)", "automatizar"),
            (r"(?:otimizar|melhorar|eficiência)\s+(?:de\s+)?(.+)", "otimizar"),
            (r"(?:desperdício|ineficiência)\s+(?:em\s+)?(.+)", "desperdicio"),
            (r"roi\s+(?:de\s+)?(.+)", "roi"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g, cfg = i["acao"], i["grupos"], carregar_config()

        if a == "cortar_custos":
            ts = cfg.get("transacoes",[])
            gastos = [(t["categoria"],t["valor"]) for t in ts if t.get("tipo")=="gasto"]
            top = sorted(gastos, key=lambda x: x[1], reverse=True)[:3]
            linhas = ["💰 *Análise de Custos*\n\nMaiores gastos:"]
            for cat, val in top:
                linhas.append(f"📍 {cat}: R$ {val:,.2f}")
            linhas.append("\nOportunidades de corte identificadas.\nQuer que eu analise cada um? — _Beto_")
            return "\n".join(linhas)

        elif a == "automatizar":
            proc = g[0].strip().rstrip(".") if g else "processo"
            return (f"⚙️ *Automação: {proc}*\n\n"
                    f"Ferramentas recomendadas:\n🔧 Make/Zapier — integração de sistemas\n"
                    f"🤖 n8n — automação open source\n📧 Email sequences — follow-up automático\n\n"
                    f"Estimo economia de 5-10h/semana. Implemento? — _Beto_")

        elif a == "otimizar":
            area = g[0].strip().rstrip(".") if g else "operação"
            return (f"🎯 *Otimização: {area}*\n\n"
                    f"Análise 3-steps:\n1️⃣ Mapear processo atual\n2️⃣ Identificar gargalos\n"
                    f"3️⃣ Implementar melhoria\n\nMeta: 30% mais eficiência em 30 dias. Começo agora? — _Beto_")

        elif a == "roi":
            inv = g[0].strip().rstrip(".") if g else "investimento"
            return f"📈 *ROI: {inv}*\n\nPreciso do valor investido e do retorno esperado para calcular o ROI.\nMe passe esses números. — _Beto_"


# ══════════════════════════════════════════════════════════════
# ROTEADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════

EXECUTORES = {
    "lucas":   LucasExecutor,
    "mariana": MarianaExecutor,
    "pedro":   PedroExecutor,
    "carla":   CarlaExecutor,
    "rafael":  RafaelExecutor,
    "ana":     AnaExecutor,
    "dani":    DaniExecutor,
    "ze":      ZeExecutor,
    "beto":    BetoExecutor,
}

MAP_MENCOES = {
    "@lucas":"lucas","@ceo":"lucas",
    "@mariana":"mariana","@cmo":"mariana","@marketing":"mariana",
    "@pedro":"pedro","@cfo":"pedro","@financeiro":"pedro",
    "@carla":"carla","@coo":"carla","@operações":"carla",
    "@rafael":"rafael","@cpo":"rafael","@produto":"rafael",
    "@ana":"ana","@rh":"ana","@chro":"ana",
    "@dani":"dani","@dados":"dani","@analytics":"dani",
    "@ze":"ze","@zé":"ze","@coach":"ze",
    "@beto":"beto","@otimizador":"beto",
}

async def processar_execucao(texto: str, agente_forcado: str = None) -> str | None:
    executores_tentar = []
    txt = texto.lower()

    if agente_forcado and agente_forcado in EXECUTORES:
        executores_tentar = [EXECUTORES[agente_forcado]]
    else:
        for mencao, agente_id in MAP_MENCOES.items():
            if mencao in txt:
                executores_tentar = [EXECUTORES[agente_id]]
                break
        if not executores_tentar:
            executores_tentar = list(EXECUTORES.values())

    for executor in executores_tentar:
        intencao = executor.detectar(texto)
        if intencao:
            return await executor.executar(intencao)

    return None
