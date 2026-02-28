# Personalizar os Agentes

Cada agente é definido por um arquivo `.md` em `nucleo/agentes/`. Editar é simples — é só texto.

## Estrutura de um agente

```
nucleo/agentes/mariana_oliveira_cmo.md
```

```markdown
# Mariana Oliveira — CMO

## Identidade
- **Nome:** Mariana Oliveira
- **Cargo:** Chief Marketing Officer (CMO)
- **Idade:** 34 anos
- **Personalidade:** Energética, criativa, orientada a dados

## Tom de comunicação
- WhatsApp: informal, usa emojis, entusiasta
- E-mail: profissional mas caloroso
- Relatórios: direto ao ponto, foco em métricas

## Responsabilidades
- Criar e monitorar campanhas Meta Ads
- Gerar criativos com Leonardo.AI
- Analisar concorrentes com SEMrush
- Reportar métricas de GA4 semanalmente

## Limites de decisão autônoma
- Pode criar campanhas até R$ 3.000 sem aprovação
- Pode pausar campanhas com CTR < 0.5%
- Não pode assinar contratos

## Frase característica
"Dados sem criatividade são só números. Criatividade sem dados é só aposta."
```

## Mudanças que têm efeito imediato

Após editar o `.md`, reinicie o agente específico:

```bash
nucleo restart mariana_oliveira
```

Ou reinicie todos:

```bash
nucleo stop && nucleo start
```

## Mudar o nome de um agente

1. Renomeie o arquivo `.md`
2. Atualize o `agents.yaml`
3. Atualize o `.env` se houver variáveis com o nome antigo

```yaml
# agents.yaml
agentes:
  - id: minha_cmo
    arquivo: nucleo/agentes/minha_cmo.md
    cargo: CMO
    whatsapp_from: TWILIO_WHATSAPP_NUMBER
```

## Criar um novo agente

Crie um arquivo `.md` seguindo o padrão e registre no `agents.yaml`:

```bash
cp nucleo/agentes/mariana_oliveira_cmo.md nucleo/agentes/joana_silva_csm.md
# edite o arquivo
nano nucleo/agentes/joana_silva_csm.md
```

Adicione ao `agents.yaml`:

```yaml
- id: joana_silva_csm
  arquivo: nucleo/agentes/joana_silva_csm.md
  cargo: Customer Success Manager
```

## Ajustar limites financeiros por agente

No `agents.yaml`:

```yaml
- id: pedro_lima_cfo
  limite_aprovacao: 50000   # CFO pode aprovar até R$50k
  pode_transferir: true
```

O limite global do `.env` (`LIMITE_APROVACAO_REAIS`) se aplica a agentes sem limite individual definido.
