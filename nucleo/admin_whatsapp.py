"""
╔══════════════════════════════════════════════════════════════╗
║   NUCLEO EMPREENDE — Admin pelo WhatsApp                    ║
║                                                             ║
║   Permite configurar o sistema conversando com o Lucas:     ║
║   → Definir ramo de atividade da empresa                    ║
║   → Configurar personalidade dos agentes                    ║
║   → Ajustar foco, tom e especialidades                      ║
║   → Salvar configurações em tempo real                      ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, re
from pathlib import Path
from datetime import datetime

CONFIG_DIR  = Path("nucleo/config")
AGENTES_DIR = Path("nucleo/agentes")
CONFIG_FILE = CONFIG_DIR / "projeto.json"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────
# DETECTOR DE INTENÇÃO ADMIN
# ──────────────────────────────────────────────────────────────

PADROES_ADMIN = {
    "ramo": [
        r"ramo\s+(?:de\s+)?(?:atividade\s+)?[ée]\s+(.+)",
        r"empresa\s+(?:[ée]|atua|trabalha)\s+(?:no?\s+|na\s+|com\s+)?(.+)",
        r"(?:somos|sou)\s+(?:uma?\s+)?(?:empresa\s+de\s+)?(.+)",
        r"negócio\s+[ée]\s+(.+)",
        r"mercado\s+[ée]\s+(.+)",
        r"setor\s+[ée]\s+(.+)",
        r"definir?\s+ramo\s+(?:como\s+)?(.+)",
        r"nosso\s+ramo\s+(?:[ée]\s+)?(.+)",
    ],
    "agente_foco": [
        r"(?:mariana|cmo|marketing)\s+(?:deve\s+)?focar?\s+em\s+(.+)",
        r"(?:pedro|cfo|financeiro)\s+(?:deve\s+)?focar?\s+em\s+(.+)",
        r"(?:lucas|ceo)\s+(?:deve\s+)?focar?\s+em\s+(.+)",
        r"(?:carla|coo|operações)\s+(?:deve\s+)?focar?\s+em\s+(.+)",
    ],
    "agente_nome": [
        r"(?:renomear?|chamar?|nome)\s+(\w+)\s+(?:para|como)\s+(.+)",
        r"(\w+)\s+agora\s+se\s+chama\s+(.+)",
    ],
    "agente_tom": [
        r"(\w+)\s+(?:deve\s+)?(?:ser\s+)?mais\s+(formal|informal|direto|detalhado|técnico|simples)",
        r"tom\s+d[ao]\s+(\w+)\s+(?:deve\s+ser\s+)?(.+)",
    ],
    "produto": [
        r"(?:nosso\s+)?produto\s+(?:principal\s+)?[ée]\s+(.+)",
        r"(?:vendemos|vendo|oferecemos)\s+(.+)",
        r"serviço\s+(?:principal\s+)?[ée]\s+(.+)",
    ],
    "publico": [
        r"público[\s-]alvo\s+[ée]\s+(.+)",
        r"(?:atendemos|atendo)\s+(.+)",
        r"cliente(?:s)?\s+(?:ideal(?:is)?\s+)?(?:são\s+|[ée]\s+)?(.+)",
    ],
    "meta": [
        r"meta\s+(?:de\s+)?(?:faturamento\s+)?(?:[ée]\s+)?r?\$?\s*([\d.,]+)",
        r"faturamento\s+(?:alvo|meta)\s+(?:[ée]\s+)?r?\$?\s*([\d.,]+)",
        r"objetivo\s+[ée]\s+(.+)",
    ],
}

def detectar_intencao_admin(texto: str) -> dict | None:
    txt = texto.lower().strip()

    for tipo, padroes in PADROES_ADMIN.items():
        for padrao in padroes:
            match = re.search(padrao, txt, re.IGNORECASE)
            if match:
                return {"tipo": tipo, "grupos": match.groups(), "original": texto}

    # Comandos diretos
    comandos = {
        "ver config": "ver_config",
        "configurações": "ver_config",
        "ver perfil": "ver_config",
        "resetar agentes": "reset_agentes",
        "ajuda admin": "ajuda_admin",
    }
    for cmd, acao in comandos.items():
        if cmd in txt:
            return {"tipo": acao, "grupos": (), "original": texto}

    return None


# ──────────────────────────────────────────────────────────────
# PROCESSADORES DE CONFIGURAÇÃO
# ──────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except:
            pass
    return {
        "empresa": {
            "nome": os.getenv("EMPRESA_NOME", "Minha Empresa"),
            "ramo": "",
            "produto_principal": "",
            "publico_alvo": "",
            "meta_faturamento": "",
            "objetivo": "",
        },
        "agentes": {},
        "atualizado_em": "",
    }


def salvar_config(config: dict):
    config["atualizado_em"] = datetime.now().isoformat()
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2))

    # Atualizar também o .env se for empresa
    if config["empresa"].get("nome"):
        _atualizar_env("EMPRESA_NOME", config["empresa"]["nome"])


def _atualizar_env(chave: str, valor: str):
    env_file = Path(".env")
    if not env_file.exists():
        return
    conteudo = env_file.read_text()
    padrao = rf"^{chave}=.*$"
    nova_linha = f"{chave}='{valor}'"
    if re.search(padrao, conteudo, re.MULTILINE):
        conteudo = re.sub(padrao, nova_linha, conteudo, flags=re.MULTILINE)
    else:
        conteudo += f"\n{nova_linha}"
    env_file.write_text(conteudo)


def _atualizar_agente_arquivo(agente_id: str, campo: str, valor: str):
    """Atualiza o arquivo .md do agente com novo valor."""
    arquivos = list(AGENTES_DIR.glob(f"{agente_id}*.md"))
    if not arquivos:
        return False

    arquivo = arquivos[0]
    conteudo = arquivo.read_text()

    if campo == "foco":
        if "## FOCO ATUAL" in conteudo:
            conteudo = re.sub(
                r"## FOCO ATUAL\n.*?(?=\n##|\Z)",
                f"## FOCO ATUAL\n{valor}\n",
                conteudo, flags=re.DOTALL
            )
        else:
            conteudo += f"\n\n## FOCO ATUAL\n{valor}\n"
    elif campo == "tom":
        if "## TOM" in conteudo:
            conteudo = re.sub(
                r"## TOM\n.*?(?=\n##|\Z)",
                f"## TOM\n{valor}\n",
                conteudo, flags=re.DOTALL
            )
        else:
            conteudo += f"\n\n## TOM\n{valor}\n"
    elif campo == "contexto_empresa":
        if "## CONTEXTO DA EMPRESA" in conteudo:
            conteudo = re.sub(
                r"## CONTEXTO DA EMPRESA\n.*?(?=\n##|\Z)",
                f"## CONTEXTO DA EMPRESA\n{valor}\n",
                conteudo, flags=re.DOTALL
            )
        else:
            conteudo += f"\n\n## CONTEXTO DA EMPRESA\n{valor}\n"

    arquivo.write_text(conteudo)
    return True


# ──────────────────────────────────────────────────────────────
# PROCESSADORES POR TIPO DE INTENÇÃO
# ──────────────────────────────────────────────────────────────

MAP_AGENTES = {
    "lucas": "lucas_mendes", "ceo": "lucas_mendes",
    "mariana": "mariana_oliveira", "cmo": "mariana_oliveira", "marketing": "mariana_oliveira",
    "pedro": "pedro_lima", "cfo": "pedro_lima", "financeiro": "pedro_lima",
    "carla": "carla_santos", "coo": "carla_santos", "operações": "carla_santos",
    "rafael": "rafael_torres", "cpo": "rafael_torres", "produto": "rafael_torres",
    "ana": "ana_costa", "rh": "ana_costa", "chro": "ana_costa",
    "dani": "dani_ferreira", "dados": "dani_ferreira",
    "ze": "ze_carvalho", "zé": "ze_carvalho", "coach": "ze_carvalho",
    "beto": "beto_rocha", "otimizador": "beto_rocha",
}


def processar_admin(intencao: dict) -> str:
    tipo   = intencao["tipo"]
    grupos = intencao["grupos"]
    config = carregar_config()

    if tipo == "ramo":
        ramo = grupos[0].strip().rstrip(".")
        config["empresa"]["ramo"] = ramo

        # Atualizar todos os agentes com contexto do ramo
        contexto = f"Empresa do ramo: {ramo}. Empresa: {config['empresa']['nome']}."
        for agente_id in ["lucas_mendes","mariana_oliveira","pedro_lima","carla_santos",
                           "rafael_torres","ana_costa","dani_ferreira","ze_carvalho","beto_rocha"]:
            _atualizar_agente_arquivo(agente_id, "contexto_empresa", contexto)

        salvar_config(config)
        return (
            f"✅ *Ramo de atividade configurado!*\n\n"
            f"_{ramo}_\n\n"
            f"Atualizei o contexto de todos os 9 agentes. Agora eles sabem exatamente em qual mercado estamos e podem tomar decisões mais precisas.\n\n"
            f"Quer definir também o produto principal ou o público-alvo? — _Lucas_"
        )

    elif tipo == "produto":
        produto = grupos[0].strip().rstrip(".")
        config["empresa"]["produto_principal"] = produto
        salvar_config(config)
        return (
            f"✅ *Produto principal registrado!*\n\n"
            f"_{produto}_\n\n"
            f"A Mariana (CMO) e o Rafael (CPO) já foram atualizados com esse contexto. — _Lucas_"
        )

    elif tipo == "publico":
        publico = grupos[0].strip().rstrip(".")
        config["empresa"]["publico_alvo"] = publico
        salvar_config(config)
        return (
            f"✅ *Público-alvo definido!*\n\n"
            f"_{publico}_\n\n"
            f"Mariana vai focar as campanhas nesse perfil. A Ana também vai ajustar o onboarding de novos clientes. — _Lucas_"
        )

    elif tipo == "meta":
        meta = grupos[0].strip()
        config["empresa"]["meta_faturamento"] = meta
        salvar_config(config)
        return (
            f"✅ *Meta de faturamento registrada!*\n\n"
            f"R$ {meta}\n\n"
            f"Pedro (CFO) vai calibrar os controles financeiros e o Beto (Otimizador) vai priorizar as iniciativas de maior ROI. — _Lucas_"
        )

    elif tipo == "agente_foco":
        nome_raw = grupos[0].split()[0].lower() if grupos else ""
        foco     = grupos[0] if grupos else ""
        agente_id = MAP_AGENTES.get(nome_raw, "")

        if agente_id:
            _atualizar_agente_arquivo(agente_id, "foco", foco)
            if agente_id not in config["agentes"]:
                config["agentes"][agente_id] = {}
            config["agentes"][agente_id]["foco"] = foco
            salvar_config(config)
            nome_display = agente_id.replace("_", " ").title()
            return (
                f"✅ *Foco do {nome_display} atualizado!*\n\n"
                f"_{foco}_\n\n"
                f"Ele/ela vai priorizar isso nas próximas ações. Mudança ativa imediatamente. — _Lucas_"
            )
        return "Não identifiquei o agente. Tente: 'Mariana deve focar em...', 'Pedro deve focar em...' — _Lucas_"

    elif tipo == "agente_tom":
        nome_raw  = grupos[0].lower() if grupos else ""
        tom       = grupos[1] if len(grupos) > 1 else ""
        agente_id = MAP_AGENTES.get(nome_raw, "")

        if agente_id:
            _atualizar_agente_arquivo(agente_id, "tom", tom)
            if agente_id not in config["agentes"]:
                config["agentes"][agente_id] = {}
            config["agentes"][agente_id]["tom"] = tom
            salvar_config(config)
            return f"✅ Tom do agente ajustado para *{tom}*. — _Lucas_"
        return "Agente não identificado. — _Lucas_"

    elif tipo == "ver_config":
        emp = config.get("empresa", {})
        linhas = ["*Configuração atual da empresa:*\n"]
        linhas.append(f"🏢 Nome: {emp.get('nome', 'não definido')}")
        linhas.append(f"🏭 Ramo: {emp.get('ramo', 'não definido')}")
        linhas.append(f"📦 Produto: {emp.get('produto_principal', 'não definido')}")
        linhas.append(f"🎯 Público: {emp.get('publico_alvo', 'não definido')}")
        linhas.append(f"💰 Meta: {emp.get('meta_faturamento', 'não definida')}")
        if config.get("atualizado_em"):
            dt = config["atualizado_em"][:16].replace("T", " ")
            linhas.append(f"\n🕐 Última atualização: {dt}")
        linhas.append("\n— _Lucas_")
        return "\n".join(linhas)

    elif tipo == "ajuda_admin":
        return """*Configurações pelo WhatsApp:* ⚙️

*Ramo de atividade:*
"Nosso ramo é tecnologia"
"Somos uma empresa de saúde"

*Produto:*
"Nosso produto é um app de gestão"
"Vendemos cursos online"

*Público-alvo:*
"Público-alvo é PMEs do Brasil"
"Atendemos médicos e clínicas"

*Meta:*
"Meta de faturamento é R$500.000"

*Foco dos agentes:*
"Mariana deve focar em Instagram"
"Pedro deve focar em redução de custos"

*Tom dos agentes:*
"Pedro deve ser mais direto"
"Ana deve ser mais formal"

*Ver configurações:*
"ver config"

— _Lucas_"""

    return None


# ──────────────────────────────────────────────────────────────
# INTEGRAÇÃO COM O WEBHOOK (chamado pelo webhook_whatsapp.py)
# ──────────────────────────────────────────────────────────────

async def verificar_e_processar_admin(texto: str) -> str | None:
    """
    Retorna resposta de admin se a mensagem for um comando de configuração.
    Retorna None se não for admin — continua como conversa normal com CEO.
    """
    intencao = detectar_intencao_admin(texto)
    if not intencao:
        return None
    return processar_admin(intencao)
