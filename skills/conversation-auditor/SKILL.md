---
name: conversation-auditor
description: >
  Audita lotes de conversaciones del asistente de Studio Chat — evalúa calidad de respuesta,
  tono, precisión, handoffs justificados, y produce un resumen de issues por categoría con
  ejemplos. Usar SIEMPRE que Nacho, Ivo o Cris quieran revisar si el asistente respondió bien
  en un período, investigar por qué hubo handoffs, auditar conversaciones específicas, o hacer
  QA periódico antes de una renovación o expansión. Frases exactas: "auditá estas
  conversaciones", "revisá si el bot respondió bien en [fecha]", "por qué hubo tantos
  handoffs", "qué pasó con las conversaciones de [cliente] esta semana", "hacé un QA
  rápido del asistente", "hay conversaciones donde el bot la cagó", "revisá los handoffs
  de los últimos 7 días", "cómo respondió el bot en Hot Sale".
---

# Conversation Auditor

Audita lotes de conversaciones de Studio Chat para detectar patrones de comportamiento
incorrecto del asistente. Distinto del `quality-engineer` (que arranca de un conversation_id
específico de un bug reportado), este skill arranca de un período o un filtro y detecta
problemas en forma exploratoria.

Usa `customer-success:data-expert` para la mecánica de llamadas a la API.

## Cuándo usar este skill vs. quality-engineer

| | conversation-auditor | quality-engineer |
|---|---|---|
| **Punto de entrada** | Un período, un cliente, un filtro | Un conversation_id concreto donde el bot falló |
| **Modo** | Exploración — encontrar problemas que no se reportaron | Investigación — root cause de un bug conocido |
| **Output** | Resumen de issues por categoría con ejemplos | Fix validado + eval de regresión |
| **Trigger** | "auditá las conversaciones de esta semana" | "esta conversación está mal, arreglala" |

## Fuentes de datos

**Conversaciones (lista + metadata):**
```
GET /projects/{pid}/conversations
  params: start_date, end_date, playbook_base_id, has_handoff, sentiment
  → lista paginada con metadata básica de cada conversación
```

**Métricas de calidad por conversación:**
```
GET /projects/{pid}/conversations/{conversation_id}/metrics
  → sentiment_label, deflection_quality, handoff_reason, recontact_risk
```

**Detalle completo (mensajes + citas):**
```
GET /projects/{pid}/conversations/{conversation_id}
  → full transcript, tool_calls, KB citations, metadata
```

**Batch de conversaciones (hasta 50):**
```
POST /projects/{pid}/conversations/batch
  body: { "conversation_ids": ["id1", "id2", ...] }
  → detalle completo de múltiples conversaciones en un solo request
```

## Workflow de auditoría

### 1. Definir el scope

Si no está especificado, preguntar:
- ¿Qué cliente / asistente? (si hay varios en el proyecto)
- ¿Qué período? (default: últimos 7 días)
- ¿Algún filtro específico? (solo handoffs, solo sentiment negativo, etc.)

### 2. Obtener la lista de conversaciones

```python
GET /projects/{pid}/conversations
  params:
    start_date = periodo_inicio
    end_date   = periodo_fin
    limit      = 100  # paginar si hay más
    # filtros opcionales según el scope:
    has_handoff   = true   # si solo interesan handoffs
    sentiment     = "negative"  # si solo interesa sentiment negativo
```

### 3. Priorizar cuáles auditar en profundidad

Con la metadata de la lista, identificar las conversaciones de mayor riesgo:

**Señales de prioridad (ordenar por)**:
1. `handoff = true` — el asistente derivó a humano
2. `sentiment_label = "negative"` — el usuario salió frustrado
3. `recontact_risk = "high"` — el problema probablemente no quedó resuelto
4. `deflection_quality = "partial"` o `"no_response"` — no resolvió

Auditar en profundidad las top ~20 conversaciones más riesgosas. Para el resto, usar solo las métricas de calidad (sin leer el transcript completo).

### 4. Auditar en profundidad con batch

```python
POST /projects/{pid}/conversations/batch
  body: { "conversation_ids": [top_20_ids] }
→ leer transcript completo de cada una
```

Para cada conversación, evaluar:

| Dimensión | Qué mirar |
|-----------|-----------|
| **Precisión** | ¿La información que dio era correcta? ¿Inventó algo que no estaba en la KB? |
| **Handoff justificado** | Si derivó, ¿era necesario? ¿O podría haberlo resuelto? |
| **Tone** | ¿Fue apropiado para el contexto? ¿Demasiado frío, demasiado informal? |
| **Calificación** | Si el rol del asistente es calificar leads, ¿hizo las preguntas correctas? |
| **KB usage** | ¿Consultó las bases correctas? ¿Las citas tenían sentido con la respuesta? |
| **Límites** | ¿Respondió algo que no debería haber respondido? |

### 5. Producir el reporte

```
## Auditoría de Conversaciones — [Cliente] — [Período]

### Resumen
- Conversaciones auditadas: X total / Y en profundidad
- Handoffs: X (Y% del total) — [alto/normal/bajo para este cliente]
- Sentiment negativo: X (Y%)
- Issues detectados: X

### Issues por categoría

#### 🔴 Críticos (comportamiento incorrecto)
**[Categoría]** — X casos
Ejemplo: conv_id XYZ — "[fragmento del mensaje problemático]"
Causa probable: [descripción]
Acción: escalar a quality-engineer para fix

#### 🟡 Mejorables (subóptimos pero no incorrectos)
**[Categoría]** — X casos
Ejemplo: conv_id XYZ — "[fragmento]"
Acción: [sugerencia de mejora]

#### ℹ️ Observaciones
[patrones interesantes sin issue claro]

### Handoffs — análisis
- Motivo más frecuente: [policy / user_request / frustration / bot_limitation]
- Handoffs evitables: X (~Y%) — el asistente podría haberlos resuelto
- Handoffs justificados: X

### Conversaciones destacadas para revisión manual
1. conv_id XYZ — [por qué vale la pena leerla]
2. ...
```

## Gotchas

- **`conversation_id` es el ID externo de plataforma** (Chatwoot, Intercom, PROA), no un UUID interno. Es el mismo que aparece visible en la UI del cliente.
- **Las métricas se calculan asincrónicamente.** Una conversación muy reciente (< 1 hora) puede no tener métricas todavía. Si `scored_at` es null, skipear o triggerear análisis manual con `POST .../metrics/analyze`.
- **No todas las dimensiones aplican a todos los asistentes.** Un asistente de calificación de leads (Toribio) se audita distinto que uno de soporte (Avera). Ajustar el criterio al rol del asistente.
- **El batch endpoint tiene límite de 50 conversation_ids.** Para auditorías grandes, paginar en lotes de 50.
- **No escalar a quality-engineer automáticamente.** Presentar los issues al equipo primero — ellos deciden cuáles merecen un fix y cuáles son comportamiento aceptable en contexto.
- **La auditoría no cambia nada en el asistente.** Este skill es solo lectura + análisis. Los fixes van por `continuous-improvement` o `quality-engineer`.

## Dependencias

- `customer-success:data-expert` — mecánica de llamadas a la API y scripts de autenticación
- `customer-success:quality-engineer` — para el fix de issues críticos detectados en la auditoría
- `customer-success:continuous-improvement` — para cambios de política que emergen de patrones recurrentes
