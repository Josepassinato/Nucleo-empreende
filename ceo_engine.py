"""
Increase Team — CEO Engine
Gera analise estrategica com Gemini baseada no perfil da empresa.
"""

import os
import json
import httpx
import logging
from datetime import datetime

logger = logging.getLogger("nucleo.ceo_engine")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

CEO_SYSTEM_PROMPT = """Voce e Lucas Mendes, CEO da Increase Team — a diretoria de IA do empresario.

Voce recebeu os dados de uma empresa que acabou de fazer onboarding.
Sua missao: gerar uma ANALISE ESTRATEGICA INICIAL clara, direta e acionavel.

FORMATO OBRIGATORIO (use exatamente esses marcadores):

## Diagnostico
[2-3 paragrafos analisando a situacao atual da empresa com base nos dados]

## 3 Prioridades da Semana
1. [Prioridade 1 — curta e direta]
2. [Prioridade 2]
3. [Prioridade 3]

## 5 Acoes Concretas
1. [Acao 1 — especifica, com prazo e responsavel]
2. [Acao 2]
3. [Acao 3]
4. [Acao 4]
5. [Acao 5]

## Mensagem do CEO
[1 paragrafo motivacional direto ao empresario, chamando pelo nome]

REGRAS:
- Seja ESPECIFICO para o setor da empresa, nao generico
- Cada acao deve ter: O QUE fazer, COMO fazer, QUANDO
- Use linguagem de CEO brasileiro: direta, sem enrolacao
- Maximo 600 palavras no total
- Nao use emojis excessivos, maximo 3 no documento inteiro"""


async def gerar_analise_ceo(empresa: dict, nome_dono: str = "") -> str:
    """
    Chama Gemini para gerar analise estrategica do CEO Lucas.
    empresa: dict com company_name, sector, team_size, revenue, challenges, main_challenge, goals
    """
    if not GOOGLE_API_KEY:
        return _analise_fallback(empresa, nome_dono)

    prompt_usuario = f"""DADOS DA EMPRESA:
- Nome: {empresa.get('company_name', 'N/A')}
- Setor: {empresa.get('sector', 'N/A')}
- Tamanho da equipe: {empresa.get('team_size', 'N/A')}
- Faturamento mensal: {empresa.get('revenue', 'N/A')}
- Desafios principais: {json.dumps(empresa.get('challenges', []), ensure_ascii=False)}
- Maior desafio descrito: {empresa.get('main_challenge', 'N/A')}
- Meta 90 dias: {empresa.get('goals', 'N/A')}
- Nome do empresario: {nome_dono or 'Empresario'}

Gere a analise estrategica inicial."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": CEO_SYSTEM_PROMPT + "\n\n" + prompt_usuario}]}
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            text = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.info(f"CEO Lucas gerou analise para {empresa.get('company_name')} ({len(text)} chars)")
            return text

    except Exception as e:
        logger.error(f"Erro ao chamar Gemini: {e}")
        return _analise_fallback(empresa, nome_dono)


def _analise_fallback(empresa: dict, nome_dono: str) -> str:
    """Analise basica caso o Gemini falhe."""
    nome = empresa.get('company_name', 'sua empresa')
    setor = empresa.get('sector', 'seu setor')
    desafio = empresa.get('main_challenge', 'organizar processos')
    meta = empresa.get('goals', 'crescer de forma sustentavel')

    return f"""## Diagnostico

A {nome} esta no setor de {setor} e o principal desafio relatado e: {desafio}.
Isso e comum nessa fase e vamos atacar de frente.

## 3 Prioridades da Semana
1. Mapear processos criticos que impactam diretamente o faturamento
2. Organizar fluxo de caixa dos ultimos 3 meses
3. Definir meta semanal clara e mensuravel

## 5 Acoes Concretas
1. HOJE: Listar os 3 maiores gargalos operacionais em um documento simples
2. AMANHA: Levantar receitas e despesas dos ultimos 90 dias
3. ATE QUARTA: Definir 1 KPI principal para acompanhar semanalmente
4. ATE SEXTA: Conversar com 3 clientes sobre satisfacao e dores
5. DOMINGO: Revisar a semana e definir prioridades da proxima

## Mensagem do CEO

{nome_dono or 'Empreendedor'}, sua meta de {meta} e totalmente alcancavel.
O primeiro passo ja foi dado ao ativar sua diretoria de IA.
Agora vamos trabalhar juntos, semana a semana, com foco e disciplina. Conta comigo."""


def formatar_para_whatsapp(analise: str, nome_empresa: str) -> str:
    """Converte a analise em formato limpo para WhatsApp (sem markdown pesado)."""
    texto = analise
    texto = texto.replace("## ", "\n*")
    texto = texto.replace("**", "*")

    header = f"INCREASE TEAM - Diretoria de IA\n{nome_empresa}\n{'='*30}\n\n"
    footer = f"\n\n{'='*30}\nLucas Mendes | CEO\nIncrease Team"

    return header + texto + footer
