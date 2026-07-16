---
name: churn-detector
description: >
  Detecta señales de riesgo de churn en clientes activos de StudioChat — analiza métricas
  de conversaciones, tendencias de volumen, degradación de deflección, y handoffs crecientes,
  y produce un reporte semafórico por cliente. Usar SIEMPRE que Nacho, Ivo o Cris quieran
  saber qué clientes están en riesgo, sospechen que un cliente podría no renovar, o quieran
  un chequeo proactivo de salud del portfolio. Frases exactas: "qué clientes están en riesgo",
  "quién podría no renovar", "churn alert", "cómo está la salud del portfolio",
  "hay algún cliente que me debería preocupar", "revisá si [cliente] está bien",
  "señales de riesgo esta semana", "qué clientes tienen tendencia negativa".
---

# Churn Detector

Runbook de detección de riesgo de churn para el portfolio de clientes activos de StudioChat.
Combina métricas de la Studio Chat Analytics API con la bitácora de Notion para producir un semáforo por cliente.

Llama a `customer-success:data-expert` para las métricas. Lee la bitácora de `account-management:account-manager` para el contexto relacional.

## Las cinco señales de riesgo

| Señal | Descripción | Umbral de alerta |
|-------|-------------|-----------------|
| **Caída de volumen** | Conversaciones este mes vs. mes anterior | < -20% MoM |
| **Deflección en baja** | Deflection rate tendiendo a bajar | < -5pp vs. baseline del cliente |
| **Handoffs en alza** | Las derivaciones a humanos suben | > +15% MoM |
| **Silencio relacional** | Sin contacto con el equipo SC | > 30 días sin entrada en bitácora |
| **Renovación próxima sin conversación** | Vencimiento < 45 días y no hubo check-in de renovación | Automático si fecha disponible |

Un cliente con 1 señal → 🟡 Atención. Con 2+ señales → 🔴 Riesgo activo.

## Workflow del runbook

### 1. Obtener lista de clientes activos

Leer el mapa de clientes de `account-management:account-manager` o hacer query al CRM de Notion:
- Status = `🟢 Cliente` en la base Empresas
- Excluir clientes en onboarding

### 2. Por cada cliente — verificar las 5 señales

**Señal 1 y 2: métricas de conversaciones (data-expert)**

```python
# Para cada STUDIO_PROJECT_ID de cliente activo:
GET /projects/{pid}/conversations/analytics
  params: start_date=hace_30_dias, end_date=hoy, group_by=day
→ calcular volumen total y comparar con mes anterior
→ calcular deflection rate y comparar con baseline del cliente

GET /projects/{pid}/conversations/analytics
  params: start_date=hace_30_dias, include_handoffs=true
→ calcular handoff rate y comparar con mes anterior
```

**Señal 4: silencio relacional (Notion)**
- Leer bitácora del cliente en Account Management
- Buscar la entrada más reciente
- Calcular días desde esa entrada

**Señal 5: renovación próxima (Notion CRM)**
- Leer campo `Fecha próximo paso` o `renovación` en Empresas
- Si < 45 días y no hay entrada de bitácora tipo "Expansión" o "Renovación" → alertar

### 3. Asignar semáforo

```
🟢 Verde: 0 señales activas
🟡 Amarillo: 1 señal activa → "Atención — monitorear"
🔴 Rojo: 2+ señales activas → "Riesgo activo — acción requerida"
```

### 4. Producir reporte

Formato de salida del reporte:

```
## Churn Report — [fecha]

### 🔴 Riesgo activo
**[Cliente]** — [X] señales
- Volumen: -25% MoM (100 convs → 75 convs)
- Handoffs: +20% MoM
- Acción sugerida: [ver abajo]

### 🟡 Atención
**[Cliente]** — [1] señal
- Sin contacto: 28 días
- Acción sugerida: [ver abajo]

### 🟢 Saludables
[Cliente A], [Cliente B] — sin señales
```

### 5. Sugerencias de acción por señal

| Señal | Acción sugerida |
|-------|----------------|
| Caída de volumen | Verificar si es estacional o si el cliente movió tráfico fuera del canal. Check-in urgente. |
| Deflección en baja | Revisar con `quality-engineer` si hay degradación en el asistente. Proponer sesión de mejora. |
| Handoffs en alza | Auditar las últimas 20 conversaciones con handoff para detectar el patrón. |
| Silencio relacional | Agendar check-in esta semana. |
| Renovación próxima | Preparar conversación de renovación con métricas de valor entregado (usar `case-study-generator`). |

## Output esperado

El reporte se produce en el chat (no como archivo). Es un insumo para la reunión semanal del equipo de StudioChat. No se envía directamente al cliente.

En el futuro, cuando exista un dashboard interno o super admin, este reporte puede alimentarlo. Por ahora, el output es texto estructurado en el chat.

## Gotchas

- **La caída de volumen puede ser buena.** Si un cliente redujo tráfico porque mejoró su proceso de calificación y ahora llegan menos leads pero mejor calificados, no es churn — es éxito. Siempre leer la bitácora para contexto antes de alarmar.
- **El baseline de deflección es por cliente, no global.** Un cliente con 60% de deflección "saludable" es diferente a otro que arrancó en 85%. Usar el promedio histórico del cliente, no el promedio del portfolio.
- **STUDIO_PROJECT_ID es obligatorio por cliente.** Si falta para algún cliente, no estimar — marcar ese cliente como "sin datos disponibles" y avisarle a Nacho.
- **No todos los clientes tienen CSAT habilitado.** No penalizar en el semáforo por ausencia de CSAT — es una métrica opcional, no una señal de riesgo en sí misma.
- **El silencio relacional no es siempre riesgo.** Clientes muy estables a veces no necesitan contacto frecuente. Usar el juicio: si el cliente está 🟢 en métricas y lleva 35 días sin contacto, es 🟡 leve, no 🔴.
- **Toribio Achaval está en onboarding — no aparece en este reporte** hasta que complete el go-live.

## Dependencias

- `customer-success:data-expert` — fuente principal de métricas (volumen, deflección, handoffs)
- `account-management:account-manager` — bitácora relacional (último contacto, contexto)
- `sales-marketing:case-study-generator` — para preparar el argumento de renovación cuando se detecta riesgo + renovación próxima
