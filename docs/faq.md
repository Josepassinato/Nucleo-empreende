# FAQ — Perguntas Frequentes

## Instalação

**Preciso saber programar para instalar?**
Não. O instalador é um único comando no terminal e o Setup Wizard guia você passo a passo. Se você sabe copiar e colar texto, consegue instalar.

**Funciona no Windows?**
Via WSL2 (Windows Subsystem for Linux). Abra o PowerShell como administrador e execute:
```powershell
wsl --install
```
Depois reinicie e use o Ubuntu pelo menu Iniciar. O processo de instalação é idêntico.

**Posso instalar no meu MacBook?**
Sim. macOS 12+ é totalmente suportado. O comando de instalação é o mesmo.

**Qual o servidor mais barato para rodar?**
Hetzner CX21: 2 vCPU, 4GB RAM por ~R$50/mês. É o suficiente para a Fase 1 completa com todos os agentes ativos.

**E se a minha VPS não tiver Python 3.10+?**
O instalador detecta e instala automaticamente via `apt-get`.

---

## Custos

**Quanto custa usar o framework depois de comprar?**
O framework em si não tem mensalidade. Você paga apenas pelas APIs que usar:
- Gemini API: gratuito no free tier (1M tokens/dia)
- Groq: gratuito no free tier
- Twilio WhatsApp: ~R$180–350/mês (varia com volume)
- Mercado Pago: grátis para Pix, 3.99% em cartões
- VPS: R$40–60/mês

Fase 1 completa custa tipicamente **R$400–800/mês**.

**Tem como testar sem gastar nada?**
Sim. Configure apenas Gemini API (gratuita) e Groq (gratuito). Todos os outros conectores entram em modo simulação automaticamente e funcionam normalmente para testes.

**O que é o "modo simulação"?**
Quando uma API key não está configurada, o conector simula as respostas localmente. Você vê o comportamento completo do sistema sem fazer chamadas reais ou gastar dinheiro. Ideal para testar e validar antes de ativar em produção.

---

## Funcionamento

**Os agentes ficam ligados o tempo todo?**
Sim, enquanto o servidor estiver rodando. O serviço systemd reinicia automaticamente se travar, e também inicia com o servidor no reboot.

**Posso pausar um agente específico?**
Sim, pelo dashboard ou pelo terminal:
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/agentes/mariana_oliveira/pausar

# Via terminal
nucleo stop mariana_oliveira
```

**Como funciona a memória dos agentes?**
Três camadas:
1. **Redis** — memória de sessão (últimas 24h)
2. **Supabase** — memória estruturada (decisões, tarefas, interações)
3. **Pinecone** — memória semântica vetorial (busca por significado)

Se Pinecone e Supabase não estiverem configurados, a memória funciona em arquivos locais.

**Os agentes podem acessar a internet?**
Sim, via Playwright (automação de navegador). O nível de acesso é configurável. Por padrão, os agentes podem navegar em sites públicos para pesquisa e coleta de dados.

**Como os agentes tomam decisões?**
Cada agente recebe seu contexto (tarefas ativas, memória recente, dados das APIs) e usa o LLM para raciocinar e agir. Decisões financeiras acima do limite definido são sempre enviadas para aprovação do Dono antes de serem executadas.

---

## Controle e segurança

**Como funciona a aprovação financeira?**
Qualquer ação que envolva gasto acima de `LIMITE_APROVACAO_REAIS` (padrão: R$10.000) é bloqueada e enviada para você via WhatsApp e Telegram. Você aprova ou rejeita direto do celular. O agente aguarda sua resposta.

**Posso mudar o limite financeiro?**
Sim, no `.env`:
```env
LIMITE_APROVACAO_REAIS=5000    # bloqueia acima de R$5.000
LIMITE_PERCENTUAL_CAIXA=0.03   # ou acima de 3% do saldo
```

**O que é o Kill Switch?**
Um script que para todos os agentes imediatamente:
```bash
bash kill_switch.sh
```
Útil em emergências. Todos os processos são encerrados e o serviço systemd é pausado.

**Meus dados ficam seguros?**
Você usa suas próprias credenciais de API. Nenhum dado trafega pelos servidores do Nucleo Empreende. O arquivo `.env` é armazenado localmente com permissão `600` (somente leitura pelo seu usuário).

---

## Personalização

**Posso mudar a personalidade dos agentes?**
Sim. Cada agente tem um arquivo `.md` em `nucleo/agentes/`. Edite o texto como quiser:
```bash
nano nucleo/agentes/mariana_oliveira_cmo.md
```
As mudanças têm efeito no próximo ciclo do agente (normalmente em minutos).

**Posso adicionar novos agentes?**
Sim. Crie um arquivo `.md` seguindo o padrão dos existentes e registre o agente no `agents.yaml`.

**Posso mudar o nome dos agentes?**
Sim. Edite o `.md` do agente e o `agents.yaml`. Os agentes se apresentarão com o novo nome no WhatsApp e e-mails.

**Posso conectar outras APIs além das 12 incluídas?**
Sim. O padrão de conector é bem documentado. Qualquer API com SDK Python pode ser integrada seguindo o mesmo padrão de `nucleo/conectores/`.

---

## Suporte e atualizações

**Como atualizo para uma versão nova?**
```bash
nucleo update
```
O updater preserva seu `.env` e todos os dados.

**Por quanto tempo recebo atualizações?**
- Starter: 3 meses
- Pro: 1 ano
- Enterprise: 2 anos

**Posso usar em mais de uma empresa?**
Cada licença autoriza uma instalação. Para múltiplas empresas, você precisa de licenças separadas ou do plano Enterprise (white-label).

**Posso revender o framework para clientes?**
Apenas com o plano Enterprise, que inclui licença de revenda e white-label.

---

## Técnico

**Qual LLM os agentes usam?**
Por padrão, Gemini 2.0 Flash para tarefas complexas e Llama 3.3 70B (via Groq) para tarefas que precisam de velocidade. Você pode configurar qualquer LLM compatível com a API OpenAI.

**Funciona com Claude ou GPT-4?**
Sim. Configure no `.env`:
```env
# Para usar Claude (Anthropic)
ANTHROPIC_API_KEY='sk-ant-...'

# Para usar GPT-4 (OpenAI)
OPENAI_API_KEY='sk-...'
```

**O framework é open-source?**
Não. É um produto comercial com licença proprietária. O código-fonte completo está disponível no plano Enterprise.

**Posso hospedar o dashboard publicamente?**
Sim, mas adicione autenticação. O dashboard expõe dados sensíveis da empresa. Configure um proxy reverso (Nginx + HTTPS) e o token de API antes de expor publicamente.

```nginx
# Exemplo Nginx
server {
    listen 443 ssl;
    server_name dashboard.suaempresa.com;
    
    location / {
        proxy_pass http://localhost:8000;
        auth_basic "Núcleo Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```
