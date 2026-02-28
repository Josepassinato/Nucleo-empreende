# 🧠 Nucleo Empreende

**Diretoria autônoma de IA para empresários brasileiros.**

9 agentes com cargo, personalidade e memória — CEO, CMO, CFO, COO e mais — trabalhando pela sua empresa 24h/dia. Instale em 20 minutos. Configure uma vez.

```bash
curl -fsSL https://install.nucleoempreende.com.br | bash -s SUA_LICENCA
```

---

## O que é o Nucleo Empreende

A maioria das ferramentas de IA são chatbots. O Núcleo é diferente: é uma **organização de agentes** que opera de forma autônoma, toma decisões, executa tarefas e reporta para você — exatamente como uma diretoria real, mas disponível 24h e a uma fração do custo.

Cada agente tem:
- **Cargo e responsabilidades** definidos
- **Personalidade e tom** únicos (o Pedro é formal, a Mariana é energética)
- **Memória persistente** — lembram do que aconteceu semanas atrás
- **Limites financeiros** — nenhum gasto acima do seu limite sem aprovação
- **Comportamento humano** no WhatsApp — delay de digitação, typos, emojis certos

---

## Agentes

| Agente | Cargo | Responsabilidades |
|--------|-------|-------------------|
| 🧠 **Lucas Mendes** | CEO | Estratégia, decisões, reunião semanal |
| 📣 **Mariana Oliveira** | CMO | Campanhas, criativos, Meta Ads |
| 💰 **Pedro Lima** | CFO | Finanças, aprovações, fluxo de caixa |
| ⚙️ **Carla Santos** | COO | Operações, processos, logística |
| 🚀 **Rafael Torres** | CPO | Produto, roadmap, backlog |
| 👥 **Ana Costa** | CHRO | Pessoas, onboarding de clientes |
| 📊 **Dani Ferreira** | Dados | Analytics, SEMrush, GA4 |
| 🧘 **Zé Carvalho** | Coach | Cultura, retenção, bem-estar |
| 🔧 **Beto Rocha** | Otimizador | Custos, eficiência, infra |

---

## Integrações incluídas

```
Comunicação    WhatsApp Business · Gmail · Telegram
Pagamentos     Mercado Pago (Pix/Boleto) · Stripe
Marketing      Meta Ads · Leonardo.AI · SEMrush · Google Analytics 4
Vendas         Hotmart · Mercado Livre
Contratos      ClickSign
Voz            ElevenLabs
Memória        Pinecone · Supabase · Redis
```

---

## Instalação rápida

### Pré-requisitos

- Linux (Ubuntu 20+) ou macOS
- Python 3.10+
- Acesso ao terminal (local ou SSH)

> **VPS recomendada:** DigitalOcean, Hetzner, Contabo ou AWS. Mínimo 2 vCPU / 4GB RAM.

### 1. Instalar

```bash
curl -fsSL https://install.nucleoempreende.com.br | bash -s SUA_CHAVE_DE_LICENCA
```

O instalador faz automaticamente:
- Verifica Python e dependências
- Instala todos os pacotes necessários
- Valida sua licença
- Abre o Setup Wizard

### 2. Configurar

O **Setup Wizard** guia você campo a campo para configurar cada API key com:
- Link direto para onde criar a chave
- Custo estimado de cada serviço
- Dica do formato esperado
- Validação em tempo real

Você pode usar o wizard no terminal (CLI) ou no navegador (interface web).

### 3. Iniciar

```bash
nucleo start      # inicia todos os agentes
nucleo dashboard  # abre o painel de controle na porta 8000
nucleo status     # verifica status do sistema
```

---

## Estrutura do projeto

```
nucleo-empreende/
├── nucleo/
│   ├── agentes/          # Personalidade de cada agente (.md)
│   ├── conectores/       # 12 integrações com APIs externas
│   │   ├── whatsapp.py
│   │   ├── pagamentos.py
│   │   ├── memoria.py
│   │   ├── gmail.py
│   │   ├── telegram.py
│   │   ├── meta_ads.py
│   │   ├── hotmart.py
│   │   ├── clicksign.py
│   │   ├── elevenlabs.py
│   │   └── criativos_dados.py
│   ├── mecanismos/
│   │   ├── alma.py       # Sistema de estresse/energia dos agentes
│   │   └── reuniao_semanal.py
│   ├── api.py            # Backend FastAPI
│   └── entrega.py        # Fluxo pós-compra automático
├── setup_wizard.py       # Wizard de configuração interativo
├── testar_tudo.py        # Teste de todos os conectores
├── main_gemini.py        # Ponto de entrada principal
├── install.sh            # Instalador one-liner
├── .env.example          # Template de variáveis de ambiente
└── agents.yaml           # Configuração dos agentes
```

---

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```bash
cp .env.example .env
```

### Obrigatórias (Fase 1 — MVP)

```env
# LLM
GOOGLE_API_KEY=''          # aistudio.google.com/app/apikey
GROQ_API_KEY=''            # console.groq.com

# WhatsApp
TWILIO_ACCOUNT_SID=''      # console.twilio.com
TWILIO_AUTH_TOKEN=''
TWILIO_WHATSAPP_NUMBER=''  # formato: whatsapp:+14155238886
DONO_WHATSAPP_NUMBER=''    # seu número: +5511999999999

# Pagamentos
MERCADOPAGO_ACCESS_TOKEN=''
```

### Opcionais (Fases 2 e 3)

```env
# Marketing
META_ACCESS_TOKEN=''
LEONARDO_API_KEY=''
SEMRUSH_API_KEY=''
GA4_PROPERTY_ID=''

# Vendas e contratos
HOTMART_CLIENT_ID=''
HOTMART_CLIENT_SECRET=''
CLICKSIGN_ACCESS_TOKEN=''

# Memória avançada
PINECONE_API_KEY=''
SUPABASE_URL=''
SUPABASE_SERVICE_ROLE_KEY=''
```

---

## Comandos disponíveis

```bash
nucleo start       # Inicia todos os agentes
nucleo stop        # Para o sistema
nucleo dashboard   # Abre painel web (porta 8000)
nucleo setup       # Reconfigura API keys
nucleo test        # Testa todos os conectores
nucleo logs        # Logs em tempo real
nucleo status      # Status do sistema
nucleo update      # Atualiza para versão mais recente
```

---

## Testando os conectores

Antes de iniciar em produção, teste todas as conexões:

```bash
python3 testar_tudo.py
```

Saída esperada:
```
✅ WhatsApp        produção
✅ Pagamentos      produção
✅ Gmail           produção
✅ Meta Ads        simulação   ← configure META_ACCESS_TOKEN
⚠️  ElevenLabs     simulação   ← opcional
...
11/11 conectores OK
```

Conectores sem API key configurada rodam em **modo simulação** — funcionam normalmente mas não fazem chamadas reais.

---

## Controle financeiro

Nenhum agente pode gastar acima do limite sem sua aprovação explícita:

```env
LIMITE_APROVACAO_REAIS=10000   # acima disso → aprovação obrigatória
LIMITE_PERCENTUAL_CAIXA=0.05   # ou > 5% do saldo → aprovação obrigatória
```

Quando um limite é atingido, você recebe uma notificação no **WhatsApp e Telegram** com a descrição, valor e botão para aprovar/rejeitar direto do celular.

---

## Mecanismo ALMA

O sistema ALMA monitora o estado interno de cada agente:

```python
{
  "estresse":  0.0 – 1.0,   # > 0.75 → agente entra em modo crítico
  "energia":   0.0 – 1.0,   # < 0.20 → agente reduz cadência
  "score":     0.0 – 10.0,  # performance histórica
  "humor":     "focado" | "sobrecarregado" | "motivado" | ...
}
```

O Zé Carvalho (Coach) monitora o ALMA de todos os agentes e aciona o Dono quando necessário.

---

## Deploy em produção

### Ubuntu / Debian (VPS)

```bash
# 1. Instalar com licença
curl -fsSL https://install.nucleoempreende.com.br | bash -s SUA_LICENCA

# 2. O instalador cria o serviço systemd automaticamente
sudo systemctl status nucleo-empreende

# 3. Verificar logs
journalctl -u nucleo-empreende -f
```

### Docker

```bash
docker run -d \
  --name nucleo \
  --env-file .env \
  -p 8000:8000 \
  nucleoai/framework:latest
```

### PM2 (alternativa ao systemd)

```bash
npm install -g pm2
pm2 start "python3 main_gemini.py" --name nucleo
pm2 save && pm2 startup
```

---

## Segurança

- Arquivo `.env` com permissão `600` (somente leitura pelo proprietário)
- Nenhum dado trafega pelos servidores do Núcleo — você usa suas próprias APIs
- Kill switch disponível: `bash kill_switch.sh` para parar tudo imediatamente
- Logs de transações financeiras com hash SHA-256 dos dados sensíveis

---

## Custo estimado de operação

| Fase | Serviços incluídos | Custo mensal estimado |
|------|-------------------|----------------------|
| Fase 1 (MVP) | Gemini + WhatsApp + Pagamentos | R$ 400 – 800 |
| Fase 2 (+Marketing) | + Meta Ads + Leonardo + SEMrush | R$ 800 – 1.500 |
| Fase 3 (Completo) | Todas as 12 integrações | R$ 1.200 – 2.500 |

> Os custos variam conforme o volume de uso. Gemini e Groq têm tiers gratuitos generosos.

---

## Documentação completa

- **[Guia de instalação](docs/instalacao.md)**
- **[Configuração de API keys](docs/api-keys.md)**
- **[Personalizar agentes](docs/agentes.md)**
- **[Integrações](docs/integracoes.md)**
- **[API Reference](docs/api-reference.md)**
- **[FAQ](docs/faq.md)**

---

## Suporte

| Canal | Plano | Tempo de resposta |
|-------|-------|-------------------|
| E-mail: suporte@nucleoempreende.com.br | Starter | 48h |
| WhatsApp: +55 11 XXXX-XXXX | Pro | 4h |
| SLA dedicado | Enterprise | 1h |

---

## Licença

Distribuído sob licença comercial. Cada licença autoriza instalação em **um servidor/empresa**. Para uso em múltiplos clientes (revenda ou agências), consulte o plano Enterprise.

---

<p align="center">
  Feito com ⚡ por <a href="https://nucleoempreende.com.br">Nucleo Empreende</a>
</p>
