# Guia de API Keys

Todas as integrações do Increase Team usam **suas próprias credenciais**. Nenhum dado trafega pelos servidores do Núcleo. Você tem controle total.

---

## Como obter cada chave

### 🧠 Google Gemini (LLM Principal)

**Obrigatório.** Motor de inteligência dos agentes.

1. Acesse [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Clique em **Create API Key**
3. Selecione um projeto Google Cloud (crie um novo se precisar)
4. Copie a chave gerada

```env
GOOGLE_API_KEY='AIzaSy...'
```

**Custo:** Gratuito até 1 milhão de tokens/dia. Além disso, US$0,075 por 1M tokens de entrada.

---

### ⚡ Groq API (LLM Rápido — fallback)

**Obrigatório.** Usado para respostas que precisam de velocidade máxima.

1. Acesse [console.groq.com](https://console.groq.com)
2. Crie uma conta → **API Keys** → **Create API Key**
3. Copie a chave (começa com `gsk_`)

```env
GROQ_API_KEY='gsk_...'
```

**Custo:** Gratuito no free tier (14.400 tokens/minuto).

---

### 📱 Twilio WhatsApp Business

**Obrigatório.** Comunicação dos agentes com clientes e com você.

1. Acesse [console.twilio.com](https://console.twilio.com)
2. Copie o **Account SID** e o **Auth Token** do painel principal
3. Vá em **Messaging → Senders → WhatsApp senders**
4. Para produção: solicite aprovação do número WhatsApp Business
5. Para testes: use o **Sandbox** (`whatsapp:+14155238886`)

```env
TWILIO_ACCOUNT_SID='ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_AUTH_TOKEN='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_WHATSAPP_NUMBER='whatsapp:+14155238886'
DONO_WHATSAPP_NUMBER='+5511999999999'
```

**Custo:** ~R$0,005 por mensagem enviada. Recebimento é gratuito.

> **Dica:** Comece com o Sandbox para testar sem custo. Para produção, solicite aprovação do número — leva 1 a 3 dias úteis.

---

### 💳 Mercado Pago

**Obrigatório.** Pagamentos via Pix, Boleto e Cartão.

1. Acesse [mercadopago.com.br/developers/panel](https://www.mercadopago.com.br/developers/panel)
2. Crie uma aplicação → **Suas integrações → Criar aplicação**
3. Vá em **Credenciais de produção**
4. Copie o **Access Token de produção**

```env
MERCADOPAGO_ACCESS_TOKEN='APP_USR-...'
```

**Custo:** Gratuito. Taxa sobre transações: Pix grátis, Boleto R$3,49, Cartão 3,99% + R$0,40.

---

### 📧 Gmail (e-mails dos agentes)

**Opcional.** Para agentes enviarem e-mails com suas assinaturas.

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um projeto → **APIs & Services → Credentials**
3. Crie **OAuth 2.0 Client ID** (tipo: Desktop App)
4. Baixe o JSON e gere o refresh token:

```bash
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', ['https://www.googleapis.com/auth/gmail.send'])
creds = flow.run_local_server(port=0)
print('REFRESH TOKEN:', creds.refresh_token)
"
```

```env
GMAIL_CLIENT_ID='xxx.apps.googleusercontent.com'
GMAIL_CLIENT_SECRET='GOCSPX-...'
GMAIL_REFRESH_TOKEN='1//...'
```

**Custo:** Gratuito.

---

### ✈️ Telegram Bot

**Opcional.** Comunicação interna da diretoria e alertas para você.

1. Abra o Telegram e busque **@BotFather**
2. Envie `/newbot` e siga as instruções
3. Copie o token do bot (formato: `123456:ABCdef...`)
4. Para obter seu Chat ID, envie uma mensagem para **@userinfobot**
5. Para o ID do grupo de diretoria: adicione o bot ao grupo e acesse `https://api.telegram.org/bot<TOKEN>/getUpdates`

```env
TELEGRAM_BOT_TOKEN='123456789:ABCdefGHI...'
TELEGRAM_CHAT_DONO='-1001234567890'
TELEGRAM_CHAT_DIRETORIA='-1009876543210'
```

**Custo:** Gratuito.

---

### 📊 Meta Ads (Facebook + Instagram)

**Opcional.** Criar e monitorar campanhas automaticamente.

1. Acesse [developers.facebook.com](https://developers.facebook.com)
2. Crie um App → tipo **Business**
3. Vá em **Tools → Graph API Explorer**
4. Gere um token com permissões: `ads_management`, `ads_read`, `pages_manage_posts`
5. Acesse [business.facebook.com](https://business.facebook.com) → Configurações → Contas de Anúncios para o ID

```env
META_ACCESS_TOKEN='EAAxxxx...'
META_APP_ID='123456789'
META_APP_SECRET='abcdef...'
META_AD_ACCOUNT_ID='1234567890'
META_PAGE_ID='9876543210'
```

**Custo:** Gratuito. Você paga apenas pelos anúncios veiculados.

> **Atenção:** O token de usuário expira em 60 dias. Para produção, converta para um **token de sistema** (não expira). Documentação: [developers.facebook.com/docs/facebook-login/access-tokens](https://developers.facebook.com/docs/facebook-login/access-tokens)

---

### 🎨 Leonardo.AI

**Opcional.** Geração de criativos e imagens para campanhas.

1. Acesse [app.leonardo.ai](https://app.leonardo.ai)
2. Vá em **Settings → API Key → Create new key**

```env
LEONARDO_API_KEY='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

**Custo:** US$10/mês (2.500 créditos/mês).

---

### 🔍 SEMrush

**Opcional.** Análise de concorrentes e palavras-chave.

1. Acesse [semrush.com/api-analytics](https://www.semrush.com/api-analytics)
2. Gere sua API Key

```env
SEMRUSH_API_KEY='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

**Custo:** API inclusa no plano Pro (US$119/mês).

---

### 📈 Google Analytics 4

**Opcional.** Métricas de tráfego e conversão do seu site.

1. Acesse [analytics.google.com](https://analytics.google.com)
2. **Admin → Property Settings → Property ID** (número de 9 dígitos)
3. Crie uma conta de serviço em [console.cloud.google.com](https://console.cloud.google.com) → IAM → Service Accounts
4. Baixe o JSON e defina o caminho:

```env
GA4_PROPERTY_ID='123456789'
GOOGLE_APPLICATION_CREDENTIALS='/home/ubuntu/nucleo-empreende/google-sa.json'
```

**Custo:** Gratuito.

---

### 🛒 Hotmart

**Opcional.** Gestão de vendas de infoprodutos.

1. Acesse [app.hotmart.com](https://app.hotmart.com)
2. Vá em **Ferramentas → Credenciais API → Criar credencial**
3. Gere o Basic Token: `echo -n "CLIENT_ID:CLIENT_SECRET" | base64`
4. Para o webhook token: **Ferramentas → Webhooks → chave secreta**

```env
HOTMART_CLIENT_ID='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
HOTMART_CLIENT_SECRET='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
HOTMART_BASIC_TOKEN='base64encodedstring=='
HOTMART_WEBHOOK_TOKEN='seu_webhook_secret'
HOTMART_PRODUTO_ID='1234567'
HOTMART_AMBIENTE='producao'
```

**Custo:** Gratuito. Taxa sobre vendas: ~9,9% + R$1,00 por transação.

---

### ✍️ ClickSign

**Opcional.** Contratos digitais com validade jurídica.

1. Acesse [app.clicksign.com](https://app.clicksign.com)
2. **Configurações → Integrações → API → Gerar token**

```env
CLICKSIGN_ACCESS_TOKEN='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

**Custo:** R$69/mês (10 docs) · R$149/mês (25 docs) · R$299/mês (50 docs).

---

### 🎙️ ElevenLabs

**Opcional.** Voz sintética para os agentes.

1. Acesse [elevenlabs.io](https://elevenlabs.io)
2. **Profile → API Key → Copy**

```env
ELEVENLABS_API_KEY='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

**Custo:** US$5/mês (30.000 caracteres).

---

### 🧬 Pinecone (Memória vetorial)

**Opcional.** Memória semântica de longo prazo dos agentes.

1. Acesse [app.pinecone.io](https://app.pinecone.io)
2. **API Keys → Create API Key**
3. Crie um index chamado `nucleo-agentes` com dimensão 768

```env
PINECONE_API_KEY='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

**Custo:** Gratuito até 100.000 vetores (1 index).

---

### 🗄️ Supabase (Banco de dados)

**Opcional.** Memória estruturada de médio prazo.

1. Acesse [app.supabase.com](https://app.supabase.com)
2. Crie um projeto
3. **Settings → API → Project URL e service_role key**
4. Execute o SQL de criação das tabelas (arquivo `docs/supabase-schema.sql`)

```env
SUPABASE_URL='https://xxxx.supabase.co'
SUPABASE_SERVICE_ROLE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

**Custo:** Gratuito até 500MB de banco e 2GB de bandwidth.

---

## Configuração mínima para começar

Se você quer testar hoje sem gastar nada:

```env
# Gratuito — suficiente para a Fase 1 funcionar
GOOGLE_API_KEY='AIzaSy...'         # obrigatório — free tier
GROQ_API_KEY='gsk_...'             # obrigatório — free tier
TWILIO_ACCOUNT_SID='ACxx...'       # sandbox gratuito
TWILIO_AUTH_TOKEN='xx...'
TWILIO_WHATSAPP_NUMBER='whatsapp:+14155238886'
DONO_WHATSAPP_NUMBER='+5511999999999'
MERCADOPAGO_ACCESS_TOKEN='APP_USR-...'
```

Com estas 7 variáveis, todos os outros conectores entram em **modo simulação** automaticamente — funcionam, mas sem chamadas reais às APIs externas.
