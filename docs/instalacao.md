# Guia de Instalação

## Pré-requisitos

| Requisito | Mínimo | Recomendado |
|-----------|--------|-------------|
| SO | Ubuntu 20.04 / macOS 12 | Ubuntu 22.04 LTS |
| CPU | 1 vCPU | 2 vCPUs |
| RAM | 2 GB | 4 GB |
| Disco | 10 GB | 20 GB |
| Python | 3.10 | 3.11+ |
| Rede | 10 Mbps | 100 Mbps |

> **Windows:** Use WSL2. Instale em: Configurações → Sistema → Recursos opcionais → WSL.

---

## VPS recomendadas

| Provedor | Plano | Custo | Link |
|----------|-------|-------|------|
| Hetzner | CX21 (2 vCPU / 4GB) | ~R$50/mês | hetzner.com |
| DigitalOcean | Basic Droplet (2GB) | ~R$60/mês | digitalocean.com |
| Contabo | VPS S | ~R$40/mês | contabo.com |
| AWS Lightsail | 2GB | ~R$55/mês | aws.amazon.com |

---

## Instalação em 3 passos

### Passo 1 — Conectar ao servidor

```bash
ssh ubuntu@SEU_IP_DO_SERVIDOR
```

Se for sua máquina local (macOS/Linux), pule este passo.

---

### Passo 2 — Executar o instalador

```bash
curl -fsSL https://install.nucleoempreende.com.br | bash -s SUA_CHAVE_DE_LICENCA
```

O instalador executa automaticamente:

```
[1/7] Verificando sistema operacional
[2/7] Verificando dependências
[3/7] Baixando Increase Team v1.0.0
[4/7] Instalando dependências Python
[5/7] Configurando API Keys         ← Setup Wizard abre aqui
[6/7] Criando atalhos e comandos
[7/7] Instalação concluída
```

**Onde o framework é instalado:** `~/nucleo-empreende/`

---

### Passo 3 — Configurar no Setup Wizard

O Setup Wizard abre automaticamente após a instalação.

**Modo CLI** (servidores sem interface gráfica):
```
[1/3] Informações da empresa
[2/3] API Keys (guiado campo a campo)
[3/3] Arquivo .env gerado
```

**Modo Web** (máquinas com navegador):
O wizard abre em `http://localhost:7317/setup` automaticamente.

---

## Instalação manual (sem o one-liner)

Se preferir instalar manualmente:

```bash
# 1. Clonar o repositório (ou descompactar o zip da licença)
git clone https://github.com/seu-usuario/nucleo-empreende.git
cd nucleo-empreende

# 2. Criar virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Copiar e preencher o .env
cp .env.example .env
nano .env

# 5. Testar conexões
python3 testar_tudo.py

# 6. Iniciar
python3 main_gemini.py
```

---

## Redis (memória de sessão)

O Redis é altamente recomendado. Sem ele, a memória de sessão funciona em arquivos locais.

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis

# Verificar
redis-cli ping  # deve retornar: PONG
```

---

## Serviço automático (systemd)

O instalador cria o serviço automaticamente no Linux. Para verificar:

```bash
# Status
sudo systemctl status nucleo-empreende

# Iniciar
sudo systemctl start nucleo-empreende

# Parar
sudo systemctl stop nucleo-empreende

# Reiniciar
sudo systemctl restart nucleo-empreende

# Ver logs em tempo real
journalctl -u nucleo-empreende -f
```

---

## Atualizar para nova versão

```bash
nucleo update
# ou
curl -fsSL https://install.nucleoempreende.com.br | bash -s SUA_CHAVE
```

O updater preserva seu `.env` e dados existentes.

---

## Desinstalar

```bash
sudo systemctl stop nucleo-empreende
sudo systemctl disable nucleo-empreende
rm -rf ~/nucleo-empreende
sudo rm /usr/local/bin/nucleo
```

---

## Solução de problemas

### "Python não encontrado"
```bash
sudo apt-get install python3 python3-pip python3-venv
```

### "Permissão negada no .env"
```bash
chmod 600 ~/nucleo-empreende/.env
```

### "Porta 8000 já em uso"
```bash
# Ver o que está usando a porta
lsof -i :8000

# Usar outra porta
nucleo dashboard --port 8080
```

### "Gemini API error: 429"
Você atingiu o limite gratuito. Adicione um método de pagamento no Google Cloud ou aguarde o reset às 00:00 UTC.

### "Twilio: Unable to create record"
Verifique se o número de destino está no formato `+5511999999999` (sem espaços, com código do país).

### Logs de erros
```bash
# Logs do sistema
nucleo logs

# Logs específicos
tail -f ~/nucleo-empreende/nucleo/logs/whatsapp_log.jsonl
tail -f ~/nucleo-empreende/nucleo/logs/transacoes.jsonl
```

---

## Portas utilizadas

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| Dashboard / API | 8000 | Interface web e API REST |
| Setup Wizard web | 7317 | Apenas durante o setup |
| Redis | 6379 | Memória de sessão (local) |
