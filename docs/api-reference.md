# API Reference

Base URL: `http://localhost:8000`

Autenticação: `Authorization: Bearer SEU_SECRET_KEY`

> Em desenvolvimento (`NUCLEO_ENV=development`) a autenticação é desativada.

---

## GET /

Health check.

**Resposta:**
```json
{
  "sistema": "Increase Team",
  "versao": "1.0.0",
  "status": "online",
  "empresa": "Sua Empresa",
  "ts": "2026-02-28T10:00:00"
}
```

---

## GET /api/v1/status

Status geral do sistema.

```json
{
  "sistema": { "ligado": true, "uptime_segundos": 3600 },
  "agentes": { "total": 9, "ativos": 7, "em_alerta": 2, "score_medio": 8.4 },
  "aprovacoes_pendentes": 2,
  "conectores": { "configurados": 8, "total": 12 }
}
```

---

## GET /api/v1/agentes

Lista todos os agentes com métricas.

```json
{
  "agentes": [
    {
      "id": "lucas_mendes",
      "nome": "Lucas Mendes",
      "cargo": "CEO",
      "status": "ativo",
      "score": 8.7,
      "estresse": 0.32,
      "energia": 0.88,
      "tarefa": "Revisando relatório semanal"
    }
  ]
}
```

---

## GET /api/v1/dashboard

Dados completos para o dashboard (agentes + métricas + aprovações + atividade + APIs).

---

## POST /api/v1/aprovacoes/{id}

Aprovar ou rejeitar uma solicitação financeira.

**Body:**
```json
{
  "decisao": "aprovar",
  "comentario": "OK, prosseguir"
}
```

**decisao:** `"aprovar"` | `"rejeitar"`

---

## POST /api/v1/agentes/{id}/pausar

Pausa um agente específico.

---

## POST /webhook/hotmart

Recebe eventos de venda do Hotmart.

**Headers:** `x-hotmart-signature: sha1_hash`

O endpoint valida a assinatura, processa o evento e dispara a entrega automática em caso de `PURCHASE_APPROVED`.

---

## GET /api/v1/license/validate?key=NF-XXXX

Valida uma chave de licença. Usado pelo instalador.

```json
{
  "valid": true,
  "plano": "pro",
  "nome": "Carlos Mendonça",
  "expira_em": "2027-02-28"
}
```

---

## WS /ws/dashboard

WebSocket para atualizações em tempo real.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/dashboard');
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  // data.tipo === "update" → atualização periódica dos agentes
  // data.tipo === "aprovacao_resolvida" → aprovação processada
};
```

Atualização enviada a cada **5 segundos** com o estado de todos os agentes.
