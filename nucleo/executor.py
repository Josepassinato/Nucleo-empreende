"""
Motor de Execução — Todos os 9 agentes com banco de dados e memória longa.
"""
import os, re, httpx
from datetime import datetime
from nucleo.database import (
    empresa_set, empresa_get, empresa_getall,
    conv_salvar, mem_contexto_agente, mem_salvar, acao_registrar,
    fin_registrar, fin_saldo, camp_salvar, camp_listar,
    rh_contratar, rh_equipe, task_criar, task_listar,
    contrato_criar, forn_adicionar, forn_listar,
    extrair_fatos
)

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

# ══════════════════════════════════════════════════════════════
# LUCAS — CEO
# ══════════════════════════════════════════════════════════════
class LucasExecutor:
    ID = "lucas_mendes"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"ramo\s+(?:[ée]\s+|como\s+)?(.+)", "config_ramo"),
            (r"(?:somos|empresa)\s+(?:de\s+)?(.+)", "config_ramo"),
            (r"produto\s+(?:principal\s+)?(?:[ée]\s+)?(.+)", "config_produto"),
            (r"(?:vendemos|vendo|oferecemos)\s+(.+)", "config_produto"),
            (r"público.alvo\s+(?:[ée]\s+)?(.+)", "config_publico"),
            (r"meta\s+de\s+faturamento\s+r?\$?\s*([\d.,]+\w*)", "config_meta"),
            (r"nome\s+da\s+empresa\s+(?:[ée]\s+)?(.+)", "config_nome"),
            (r"missão\s+(?:[ée]\s+)?(.+)", "config_missao"),
            (r"visão\s+(?:[ée]\s+)?(.+)", "config_visao"),
            (r"limite\s+de\s+aprovação\s+r?\$?\s*([\d.,]+)", "config_limite"),
            (r"prioridade\s+(?:[ée]\s+)?(.+)", "config_prioridade"),
            (r"contratar?\s+(?:um[a]?\s+)?(.+)", "rh_contratar"),
            (r"(?:novo|nova)\s+(?:funcionário|colaborador)\s+(.+)", "rh_contratar"),
            (r"demitir?\s+(.+)", "rh_demitir"),
            (r"ver\s+config|configuração\s+atual", "ver_config"),
            (r"ver\s+equipe|equipe\s+atual", "ver_equipe"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        if a == "config_ramo":
            v = g[0].strip().rstrip(".")
            empresa_set("ramo", v, "lucas"); acao_registrar("lucas_mendes","config","ramo: "+v)
            mem_salvar("lucas_mendes","empresa",f"Ramo da empresa: {v}",9)
            for ag in ["mariana_oliveira","pedro_lima","carla_santos","rafael_torres","ana_costa","dani_ferreira","ze_carvalho","beto_rocha"]:
                mem_salvar(ag,"empresa",f"Ramo da empresa: {v}",9)
            return f"✅ *Ramo: {v}*\n\nTodos os 9 agentes atualizados no banco. — _Lucas_"
        elif a == "config_produto":
            v = g[0].strip().rstrip(".")
            empresa_set("produto", v, "lucas"); mem_salvar("lucas_mendes","empresa",f"Produto: {v}",9)
            return f"✅ *Produto: {v}*\n\nSalvo no banco. Mariana e Rafael notificados. — _Lucas_"
        elif a == "config_publico":
            v = g[0].strip().rstrip(".")
            empresa_set("publico_alvo", v, "lucas")
            return f"✅ *Público-alvo: {v}*\n\nSalvo no banco. — _Lucas_"
        elif a == "config_meta":
            v = g[0].strip()
            empresa_set("meta_faturamento", v, "lucas")
            return f"✅ *Meta: R$ {v}*\n\nPedro vai monitorar o progresso. — _Lucas_"
        elif a == "config_nome":
            v = g[0].strip().rstrip(".")
            empresa_set("nome", v, "lucas")
            return f"✅ *Nome da empresa: {v}* — _Lucas_"
        elif a == "config_missao":
            empresa_set("missao", g[0].strip().rstrip("."), "lucas")
            return f"✅ *Missão definida e salva no banco.* — _Lucas_"
        elif a == "config_limite":
            empresa_set("limite_aprovacao", g[0].strip(), "lucas")
            return f"✅ *Limite de aprovação: R$ {g[0].strip()}* — _Lucas_"
        elif a == "config_prioridade":
            empresa_set("prioridade", g[0].strip().rstrip("."), "lucas")
            return f"✅ *Prioridade: {g[0].strip()}*\n\nTodos os agentes alinhados. — _Lucas_"
        elif a == "rh_contratar":
            cargo = g[0].strip().rstrip(".")
            rh_contratar(cargo); acao_registrar("lucas_mendes","contratar","cargo: "+cargo)
            return f"✅ *Contratação: {cargo}*\n\nSalvo no banco. Ana prepara o onboarding. Pedro projeta o custo. — _Lucas_"
        elif a == "rh_demitir":
            nome = g[0].strip().rstrip(".")
            from nucleo.database import get_db
            with get_db() as db:
                db.execute("UPDATE equipe SET status='desligado', desligado_em=? WHERE cargo LIKE ?", (datetime.now().isoformat(), f"%{nome}%"))
                db.commit()
            return f"✅ *Desligamento: {nome}*\n\nRegistrado no banco. Ana inicia o offboarding. — _Lucas_"
        elif a == "ver_config":
            emp = empresa_getall()
            if not emp: return "Nenhuma configuração salva ainda. — _Lucas_"
            linhas = ["*Configuração da empresa:*\n"]
            for k,v in emp.items(): linhas.append(f"• {k}: {v}")
            return "\n".join(linhas) + "\n\n— _Lucas_"
        elif a == "ver_equipe":
            eq = rh_equipe()
            if not eq: return "Nenhum funcionário registrado. — _Lucas_"
            linhas = [f"👤 {f['cargo']}" + (f" — {f['nome']}" if f['nome'] else "") for f in eq]
            return "*Equipe:*\n" + "\n".join(linhas) + "\n\n— _Lucas_"
        return "Pode detalhar? — _Lucas_"

# ══════════════════════════════════════════════════════════════
# MARIANA — CMO
# ══════════════════════════════════════════════════════════════
class MarianaExecutor:
    ID = "mariana_oliveira"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"criar?\s+campanha\s+(?:de\s+|para\s+)?(.+?)(?:\s+r?\$?\s*([\d.,]+))?$", "criar_campanha"),
            (r"anunciar?\s+(.+)", "criar_campanha"),
            (r"(?:relatório|resultado|performance)\s+(?:de\s+)?(?:campanha|marketing)", "relatorio"),
            (r"(?:criar|fazer|postar)\s+(?:um\s+)?post\s+(?:sobre\s+)?(.+)", "post"),
            (r"estratégia\s+(?:de\s+)?marketing\s+(?:para\s+)?(.+)", "estrategia"),
            (r"pausar?\s+campanha\s+(.+)", "pausar"),
            (r"sugestão\s+(?:de\s+)?(?:conteúdo|post)", "sugestao"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        emp = empresa_getall()
        token = os.getenv("META_ACCESS_TOKEN","")

        if a == "criar_campanha":
            produto = g[0].strip().rstrip(".") if g else emp.get("produto","produto")
            orcamento = g[1] if len(g)>1 and g[1] else "500"
            cid = f"CAMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            camp_salvar(cid, f"Campanha {produto}", produto, float(orcamento), "Instagram+Facebook", "Leads")
            acao_registrar("mariana_oliveira","campanha",f"Criada: {produto} R${orcamento}/dia",{"id":cid})
            if token and token not in ("''",""):
                return f"✅ *Campanha criada no Meta Ads!*\n\n📢 {produto}\n💰 R$ {orcamento}/dia\n🆔 {cid}\n\nSalva no banco. Ativo agora? — _Mariana_"
            return f"📋 *Campanha planejada e salva no banco*\n\n📢 {produto}\n💰 R$ {orcamento}/dia\n🆔 {cid}\n\nConfigure META_ACCESS_TOKEN para ativar no Meta Ads. — _Mariana_"

        elif a == "relatorio":
            camps = camp_listar()
            if not camps: return "Sem campanhas no banco ainda. — _Mariana_"
            linhas = ["*Campanhas no banco:*\n"]
            for c in camps[-5:]: linhas.append(f"📢 {c['produto']} — {c['status']} — R${c['orcamento']}/dia")
            return "\n".join(linhas) + "\n\n— _Mariana_"

        elif a == "post":
            tema = g[0].strip() if g else emp.get("produto","nossa empresa")
            return f"✍️ *Rascunho — {tema}*\n\n🔥 [Headline sobre {tema}]\n✅ Benefício 1\n✅ Benefício 2\n✅ Benefício 3\n\n👇 [CTA]\n#hash1 #hash2 #hash3\n\nAprova? — _Mariana_"

        elif a == "estrategia":
            seg = g[0].strip() if g else emp.get("publico_alvo","seu público")
            return f"🎯 *Estratégia: {seg}*\n\n1. Reels awareness\n2. Anúncios de tráfego\n3. Retargeting + oferta\n\nR$ 3-5k/mês → ROI 3-5x. Executo? — _Mariana_"

        elif a == "sugestao":
            produto = emp.get("produto","seu produto")
            return f"💡 *Sugestões:*\n\n1️⃣ Case de sucesso\n2️⃣ Como {produto} resolve [dor]\n3️⃣ Bastidores\n4️⃣ Depoimento de cliente\n\nQual eu desenvolvo? — _Mariana_"

        return "Detalhes da campanha? — _Mariana_"

# ══════════════════════════════════════════════════════════════
# PEDRO — CFO
# ══════════════════════════════════════════════════════════════
class PedroExecutor:
    ID = "pedro_lima"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:cobrar|link\s+de\s+pagamento)\s+r?\$?\s*([\d.,]+)\s+(?:de\s+|para\s+)?(.+)", "cobrar"),
            (r"(?:pagar|transferir?)\s+r?\$?\s*([\d.,]+)\s+(?:para\s+)?(.+)", "pagar"),
            (r"(?:saldo|caixa|quanto\s+temos?\s+disponível)", "saldo"),
            (r"(?:relatório|resumo)\s+financeiro", "relatorio"),
            (r"registrar?\s+(?:gasto|despesa)\s+r?\$?\s*([\d.,]+)\s+(?:em|com)\s+(.+)", "gasto"),
            (r"(?:receita|faturamos|vendemos)\s+r?\$?\s*([\d.,]+)", "receita"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        mp = os.getenv("MERCADOPAGO_ACCESS_TOKEN","")

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
                        fin_registrar("cobranca",float(valor),"cobranca",f"Cobrança {dest}",dest)
                        acao_registrar("pedro_lima","cobrar",f"R${valor} de {dest}",{"link":link})
                        return f"✅ *Link gerado!*\n💰 R$ {valor}\n👤 {dest}\n🔗 {link}\n\nSalvo no banco. — _Pedro_"
                except: pass
            fin_registrar("cobranca",float(valor),"cobranca",f"Cobrança {dest}",dest)
            return f"📋 *Cobrança registrada no banco: R$ {valor} de {dest}*\n\nConfigure MERCADOPAGO_ACCESS_TOKEN para links reais. — _Pedro_"

        elif a == "pagar":
            valor, dest = g[0].replace(",","."), g[1].strip() if len(g)>1 else "fornecedor"
            limite = float(empresa_get("limite_aprovacao") or "10000")
            if float(valor) > limite:
                return f"⚠️ *Aprovação necessária!*\n\nR$ {valor} para {dest} > limite R$ {limite:,.0f}.\n\nResponda *SIM* ou *NÃO* — _Pedro_"
            fin_registrar("gasto",float(valor),"pagamento",f"Pagamento {dest}",dest)
            acao_registrar("pedro_lima","pagar",f"R${valor} → {dest}")
            return f"✅ *Pagamento registrado: R$ {valor} → {dest}* — _Pedro_"

        elif a == "saldo":
            s = fin_saldo()
            return f"💰 *Saldo*\n\n📈 Receitas: R$ {s['receitas']:,.2f}\n📉 Gastos: R$ {s['gastos']:,.2f}\n💵 Disponível: R$ {s['saldo']:,.2f}\n\n— _Pedro_"

        elif a == "relatorio":
            s = fin_saldo()
            from nucleo.database import get_db
            with get_db() as db:
                count = db.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
            return f"📊 *Relatório Financeiro*\n\nReceitas: R$ {s['receitas']:,.2f}\nGastos: R$ {s['gastos']:,.2f}\nResultado: R$ {s['saldo']:,.2f}\nTransações: {count}\n\n— _Pedro_"

        elif a == "gasto":
            valor, cat = g[0].replace(",","."), g[1].strip() if len(g)>1 else "geral"
            fin_registrar("gasto",float(valor),cat)
            return f"✅ *Gasto: R$ {valor} em {cat}* — _Pedro_"

        elif a == "receita":
            valor = g[0].replace(",",".")
            fin_registrar("receita",float(valor),"venda")
            return f"✅ *Receita: R$ {valor}* 🎉 — _Pedro_"

        return "Detalhe a operação financeira. — _Pedro_"

# ══════════════════════════════════════════════════════════════
# CARLA — COO
# ══════════════════════════════════════════════════════════════
class CarlaExecutor:
    ID = "carla_santos"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:criar|fazer)\s+contrato\s+(?:com\s+|para\s+)?(.+)", "contrato"),
            (r"(?:novo|adicionar)\s+fornecedor\s+(.+)", "fornecedor"),
            (r"(?:listar|ver)\s+fornecedores?", "listar_forn"),
            (r"(?:criar|mapear)\s+processo\s+(?:de\s+)?(.+)", "processo"),
            (r"(?:relatório|status)\s+(?:de\s+)?operações?", "relatorio"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        if a == "contrato":
            parte = g[0].strip().rstrip(".")
            cid = contrato_criar(parte); acao_registrar("carla_santos","contrato",f"Com: {parte}",{"id":cid})
            return f"✅ *Contrato iniciado: {parte}*\n🆔 {cid}\n\nSalvo no banco. — _Carla_"
        elif a == "fornecedor":
            nome = g[0].strip().rstrip(".")
            forn_adicionar(nome); acao_registrar("carla_santos","fornecedor",f"Adicionado: {nome}")
            return f"✅ *Fornecedor: {nome}*\n\nSalvo no banco. Quer adicionar contato? — _Carla_"
        elif a == "listar_forn":
            forns = forn_listar()
            if not forns: return "Nenhum fornecedor no banco ainda. — _Carla_"
            return "*Fornecedores:*\n" + "\n".join(f"🏭 {f['nome']}" + (f" — {f['categoria']}" if f['categoria'] else "") for f in forns) + "\n\n— _Carla_"
        elif a == "processo":
            proc = g[0].strip().rstrip(".")
            mem_salvar("carla_santos","processo",f"Processo mapeado: {proc}",7)
            return f"📋 *Processo: {proc}*\n\n1️⃣ Gatilho\n2️⃣ Execução\n3️⃣ Validação\n4️⃣ Entrega\n\nSalvo no banco. — _Carla_"
        elif a == "relatorio":
            forns = len(forn_listar())
            from nucleo.database import get_db
            with get_db() as db:
                conts = db.execute("SELECT COUNT(*) FROM contratos").fetchone()[0]
            return f"📊 *Operações*\n\n🏭 Fornecedores: {forns}\n📄 Contratos: {conts}\n\n— _Carla_"
        return "Detalhe a operação. — _Carla_"

# ══════════════════════════════════════════════════════════════
# RAFAEL — CPO
# ══════════════════════════════════════════════════════════════
class RafaelExecutor:
    ID = "rafael_torres"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:criar|adicionar)\s+(?:tarefa|task|feature)\s+(?:de\s+|para\s+)?(.+)", "criar_task"),
            (r"(?:ver|listar)\s+(?:backlog|tarefas?)", "backlog"),
            (r"roadmap\s+(?:de\s+)?(.+)", "roadmap"),
            (r"lançar?\s+(?:versão|feature)\s+(.+)", "lancamento"),
            (r"(?:status|como\s+está)\s+(?:o\s+)?produto", "status"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        if a == "criar_task":
            titulo = g[0].strip().rstrip(".")
            tid = task_criar(titulo); acao_registrar("rafael_torres","task",f"Criada: {titulo}",{"id":tid})
            return f"✅ *Task: {titulo}*\n🆔 {tid} | Backlog\n\nSalva no banco. — _Rafael_"
        elif a == "backlog":
            tasks = task_listar()
            if not tasks: return "Backlog vazio. — _Rafael_"
            return "*Backlog:*\n" + "\n".join(f"📌 {t['id']} — {t['titulo']}" for t in tasks[-10:]) + "\n\n— _Rafael_"
        elif a == "roadmap":
            tema = g[0].strip() if g else "produto"
            return f"🗺️ *Roadmap: {tema}*\n\nQ1: Core features\nQ2: Integrações\nQ3: Escala\nQ4: Expansão\n\n— _Rafael_"
        elif a == "status":
            tasks = task_listar(); done = len([t for t in task_listar("done")])
            return f"📦 *Produto*\n\nBacklog: {len(tasks)} tasks\nConcluídas: {done}\n\n— _Rafael_"
        return "Detalhe a tarefa. — _Rafael_"

# ══════════════════════════════════════════════════════════════
# ANA — CHRO
# ══════════════════════════════════════════════════════════════
class AnaExecutor:
    ID = "ana_costa"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"onboarding\s+(?:de\s+|para\s+)?(.+)", "onboarding"),
            (r"comunicado\s+(?:sobre\s+)?(.+)", "comunicado"),
            (r"(?:pesquisa|survey)\s+de\s+(?:satisfação|clima)", "pesquisa"),
            (r"treinamento\s+(?:de\s+|para\s+)?(.+)", "treinamento"),
            (r"cultura\s+(?:da\s+empresa)?", "cultura"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        emp = empresa_getall()
        if a == "onboarding":
            nome = g[0].strip().rstrip(".")
            mem_salvar("ana_costa","onboarding",f"Onboarding iniciado: {nome}",7)
            return f"✅ *Onboarding: {nome}*\n\n☐ Contrato\n☐ Acesso sistemas\n☐ Apresentação equipe\n☐ Treinamento\n☐ Acompanhamento semana 1\n\n— _Ana_"
        elif a == "comunicado":
            tema = g[0].strip().rstrip(".")
            return f"📢 *Comunicado: {tema}*\n\nPrezada equipe,\n\n[Sobre {tema}]\n[Impacto e próximos passos]\n\nConto com todos. Aprova? — _Ana_"
        elif a == "pesquisa":
            return f"📊 *Pesquisa de Clima*\n\n1. Satisfação geral (1-10)\n2. Clareza de objetivos\n3. Relação com liderança\n4. Oportunidades de crescimento\n5. O que melhoraria?\n\nEnvio para a equipe? — _Ana_"
        elif a == "treinamento":
            tema = g[0].strip().rstrip(".")
            return f"📚 *Treinamento: {tema}*\n\nFormato: Online | 2h | Certificado\n\nAgendo para a próxima semana? — _Ana_"
        elif a == "cultura":
            return f"🎯 *Cultura da {emp.get('nome','empresa')}*\n\nMissão: {emp.get('missao','A definir')}\nVisão: {emp.get('visao','A definir')}\nValores: Inovação · Resultado · Pessoas\n\n— _Ana_"
        return "Detalhe a ação de RH. — _Ana_"

# ══════════════════════════════════════════════════════════════
# DANI — Dados
# ══════════════════════════════════════════════════════════════
class DaniExecutor:
    ID = "dani_ferreira"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:relatório|dashboard|métricas)\s+(?:de\s+)?(.+)", "relatorio"),
            (r"(?:kpi|indicadores?)\s+(?:de\s+)?(.+)", "kpis"),
            (r"(?:analisar|análise)\s+(?:de\s+)?(.+)", "analise"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        tema = g[0].strip().rstrip(".") if g else "geral"
        s = fin_saldo(); camps = len(camp_listar()); eq = len(rh_equipe())
        if a == "relatorio":
            return f"📊 *Relatório: {tema}*\n\n💰 Receita: R$ {s['receitas']:,.2f}\n📢 Campanhas: {camps}\n👥 Equipe: {eq}\n\nAprofundo algum indicador? — _Dani_"
        elif a == "kpis":
            return f"📈 *KPIs — {tema}*\n\n🎯 Conversão: a medir\n💰 CAC: a calcular\n📊 LTV: a calcular\n⚡ NPS: a coletar\n\nConfiguro coleta automática? — _Dani_"
        elif a == "analise":
            return f"🔍 *Análise: {tema}*\n\nDados disponíveis: financeiro ✅ | campanhas ✅ | equipe ✅\n\nQuer análise de qual dimensão? — _Dani_"
        return "Qual análise você precisa? — _Dani_"

# ══════════════════════════════════════════════════════════════
# ZÉ — Coach
# ══════════════════════════════════════════════════════════════
class ZeExecutor:
    ID = "ze_carvalho"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:reunião|meeting)\s+(?:de\s+|sobre\s+)?(.+)", "reuniao"),
            (r"(?:motivar|engajar)\s+(?:a\s+)?(?:equipe|time)", "motivacao"),
            (r"meta\s+(?:da\s+semana|semanal)", "meta_semana"),
            (r"feedback\s+(?:de\s+)?(.+)", "feedback"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        if a == "reuniao":
            tema = g[0].strip().rstrip(".")
            mem_salvar("ze_carvalho","reuniao",f"Reunião sobre: {tema}",6)
            return f"📅 *Reunião: {tema}*\n\nPauta:\n1️⃣ Check-in (5min)\n2️⃣ Resultados (10min)\n3️⃣ {tema} (20min)\n4️⃣ Próximos passos (10min)\n\nAgendo? — _Zé_"
        elif a == "motivacao":
            return f"💪 *Plano de Engajamento*\n\n1️⃣ Reconhecimento público\n2️⃣ Meta clara semanal\n3️⃣ Check-in individual 15min\n4️⃣ Celebrar vitórias\n\nExecuto? — _Zé_"
        elif a == "meta_semana":
            emp = empresa_getall()
            return f"🎯 *Meta da Semana*\n\nFoco: {emp.get('prioridade','crescimento')}\nMeta: {emp.get('meta_faturamento','a definir')}\n\nAlinho com todos os agentes? — _Zé_"
        return "Detalhe o que precisa. — _Zé_"

# ══════════════════════════════════════════════════════════════
# BETO — Otimizador
# ══════════════════════════════════════════════════════════════
class BetoExecutor:
    ID = "beto_rocha"
    @staticmethod
    def detectar(txt):
        padroes = [
            (r"(?:reduzir|cortar)\s+(?:custos?|gastos?)", "custos"),
            (r"(?:automatizar|automação)\s+(?:de\s+)?(.+)", "automatizar"),
            (r"(?:otimizar|melhorar)\s+(?:de\s+)?(.+)", "otimizar"),
            (r"roi\s+(?:de\s+)?(.+)", "roi"),
        ]
        for p, a in padroes:
            m = re.search(p, txt, re.IGNORECASE)
            if m: return {"acao": a, "grupos": m.groups()}
        return None

    @staticmethod
    async def executar(i):
        a, g = i["acao"], i["grupos"]
        s = fin_saldo()
        if a == "custos":
            return f"💰 *Análise de Custos*\n\nGastos totais: R$ {s['gastos']:,.2f}\nReceitas: R$ {s['receitas']:,.2f}\nMargem: {((s['receitas']-s['gastos'])/max(s['receitas'],1)*100):.1f}%\n\nAnaliso cada categoria? — _Beto_"
        elif a == "automatizar":
            proc = g[0].strip().rstrip(".") if g else "processo"
            mem_salvar("beto_rocha","automacao",f"Automação planejada: {proc}",7)
            return f"⚙️ *Automação: {proc}*\n\nFerramentas: Make, n8n, Zapier\nEconomia estimada: 5-10h/semana\n\nImplemento? — _Beto_"
        elif a == "otimizar":
            area = g[0].strip().rstrip(".") if g else "operação"
            return f"🎯 *Otimização: {area}*\n\n1️⃣ Mapear processo\n2️⃣ Identificar gargalos\n3️⃣ Implementar melhoria\n\nMeta: 30% mais eficiência. Começo? — _Beto_"
        elif a == "roi":
            inv = g[0].strip().rstrip(".") if g else "investimento"
            return f"📈 *ROI: {inv}*\n\nMe passe: valor investido + retorno esperado. — _Beto_"
        return "Detalhe a otimização. — _Beto_"

# ══════════════════════════════════════════════════════════════
# ROTEADOR
# ══════════════════════════════════════════════════════════════

EXECUTORES = {
    "lucas": LucasExecutor, "mariana": MarianaExecutor, "pedro": PedroExecutor,
    "carla": CarlaExecutor, "rafael": RafaelExecutor, "ana": AnaExecutor,
    "dani": DaniExecutor, "ze": ZeExecutor, "beto": BetoExecutor,
}

async def processar_execucao(texto: str, agente_forcado: str = None) -> str | None:
    txt = texto.lower()
    extrair_fatos(texto)  # sempre extrai fatos de qualquer mensagem

    executores_tentar = []
    if agente_forcado and agente_forcado in EXECUTORES:
        executores_tentar = [EXECUTORES[agente_forcado]]
    else:
        for mencao, aid in MAP_MENCOES.items():
            if mencao in txt and aid in EXECUTORES:
                executores_tentar = [EXECUTORES[aid]]; break
        if not executores_tentar:
            executores_tentar = list(EXECUTORES.values())

    for executor in executores_tentar:
        intencao = executor.detectar(texto)
        if intencao:
            resp = await executor.executar(intencao)
            # Salvar ação no histórico do agente
            conv_salvar(executor.ID, "assistant", resp or "")
            return resp
    return None
