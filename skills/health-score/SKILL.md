---
name: health-score
description: >
  Calcula un score de salud (1–10) por cliente activo de StudioChat basado en métricas
  reales: volumen de conversaciones, deflection rate, tendencia mensual, CSAT si existe,
  y frecuencia de contacto. Persiste el histórico en Notion para detectar tendencias.
  Usar SIEMPRE que Nacho quiera saber cómo está la salud del portfolio de clientes,
  quién mejoró o empeoró, o necesite un número que resuma el estado de un cliente.
  Frases exactas: "salud de [cliente]", "score de todos los clientes",
  "quién mejoró este mes", "health score del portfolio", "cómo está [cliente] en números",
  "dashboard de salud de clientes", "quién está mejor y quién peor".
---

# Health Score

Calcula y persiste un score de salud 1–10 por cliente activo de StudioChat, combinando
métricas cuantitativas de la API con señales cualitativas de la bitácora de Notion.

Llama a `customer-success:data-expert` para métricas. Lee/escribe en Notion vía MCP para
el histórico de scores.

## Modelo de scoring

El score es la suma ponderada de 5 componentes, cada uno de 0–2 puntos:

| Componente | Peso | Cómo se mide |
|------------|------|--------------|
| **Deflection rate** | 25% | vs. baseline del cliente y benchmark general |
| **Tendencia de volumen** | 20% | MoM: crecimiento / estabilidad / caída |
| **Calidad de respuesta** | 20% | deflection_quality + handoff_reason de métricas de conv |
| **CSAT** | 15% | si disponible; neutro (1.0) si no está habilitado |
| **Salud relacional** | 20% | días desde último contacto + ausencia de issues abiertos |

**Score final = suma de componentes escalada a 1–10.**

### Rubrica por componente

#### Deflection rate (0–2 pts)
```
2.0 pts — ≥ 80% (o ≥ 10pp sobre baseline histórico del cliente)
1.5 pts — 65–79%
1.0 pts — 50–64%
0.5 pts — 35–49%
0.0 pts — < 35% o sin datos suficientes (< 50 convs en el período)
```

#### Tendencia de volumen MoM (0–2 pts)
```
2.0 pts — crecimiento ≥ 10% MoM
1.5 pts — crecimiento 0–9% MoM (estable-positivo)
1.0 pts — caída 1–9% MoM (estable-negativo leve)
0.5 pts — caída 10–19% MoM
0.0 pts — caída ≥ 20% MoM
```

#### Calidad de respuesta (0–2 pts)
Calcular sobre las últimas 30 conversaciones con métricas disponibles:
```
2.0 pts — deflection_quality "resolved" ≥ 70%, handoff_reason "policy/user_request" (handoffs justificados)
1.5 pts — resolved 50–69% o mix de handoffs justificados/bot_limitation
1.0 pts — resolved 35–49% o presencia de handoffs por "frustration"
0.5 pts — resolved < 35% o handoffs por "bot_limitation" dominantes
0.0 pts — sin métricas disponibles o scored_at null en > 80% de convs
```

#### CSAT (0–2 pts)
```
2.0 pts — CSAT ≥ 4.0/5 (o ≥ 80% positivo)
1.5 pts — CSAT 3.5–3.9
1.0 pts — CSAT 3.0–3.4 (o no habilitado → valor neutro)
0.5 pts — CSAT 2.5–2.9
0.0 pts — CSAT < 2.5
```
Si CSAT no está habilitado para el cliente: asignar 1.0 (neutro) — no penalizar por ausencia.

#### Salud relacional (0–2 pts)
Leer de la bitácora del cliente en `account-management:account-manager`:
```
2.0 pts — contacto en los últimos 14 días + sin issues abiertos
1.5 pts — contacto en los últimos 30 días + sin issues críticos
1.0 pts — contacto en los últimos 45 días o issue menor abierto
0.5 pts — sin contacto en > 45 días o issue abierto sin seguimiento
0.0 pts — sin contacto en > 60 días o issue crítico sin respuesta
```

### Escala de interpretación

| Score | Semáforo | Significado |
|-------|----------|-------------|
| 8.0–10.0 | 🟢 Saludable | Cliente estable y creciendo. Candidato a expansión. |
| 6.0–7.9 | 🟡 Atención | Alguna señal débil. Monitorear. Check-in en los próximos 15 días. |
| 4.0–5.9 | 🟠 En riesgo | Múltiples señales negativas. Acción requerida esta semana. |
| 1.0–3.9 | 🔴 Crítico | Riesgo alto de churn. Escalada inmediata. |

## Workflow de cálculo

### Para un cliente individual

1. Obtener `STUDIO_PROJECT_ID` del cliente
2. Llamar a `data-expert` para los 5 componentes:
   ```python
   # Deflection + volumen
   GET /projects/{pid}/conversations/analytics
     params: start_date=hace_30_dias, end_date=hoy
   GET /projects/{pid}/conversations/analytics
     params: start_date=hace_60_dias, end_date=hace_30_dias  # mes anterior para tendencia

   # Calidad de respuesta
   GET /projects/{pid}/conversations
     params: limit=30, start_date=hace_30_dias
   → para cada conv: GET /projects/{pid}/conversations/{id}/metrics

   # CSAT
   GET /projects/{pid}/csat/analytics
     params: start_date=hace_30_dias
   ```
3. Leer bitácora de `account-management:account-manager` en Notion (último contacto, issues)
4. Calcular score por componente → score final
5. Persistir en Notion (ver abajo)

### Para el portfolio completo

Iterar sobre todos los clientes activos. Calcular en paralelo donde sea posible.
Producir tabla resumen ordenada por score ascendente (peores primero).

## Persistencia en Notion

Guardar en la página del cliente en `account-management:account-manager`:

```markdown
## Health Score — Histórico
| Fecha | Score | 🚦 | Deflec. | Volumen | Calidad | CSAT | Relacional | Notas |
|-------|-------|----|---------|---------|---------|------|------------|-------|
| 2026-07-16 | 7.2 | 🟡 | 1.5 | 1.5 | 1.5 | 1.0 | 1.5 | — |
```

Agregar siempre al final de la tabla (orden cronológico). No modificar entradas anteriores.

## Output del reporte de portfolio

```
## Health Score — Portfolio StudioChat — [fecha]

| Cliente | Score | 🚦 | vs. mes anterior | Acción sugerida |
|---------|-------|----|-----------------|-----------------|
| Coderhouse | 8.4 | 🟢 | +0.3 | Explorar expansión |
| Avera | 7.1 | 🟡 | -0.5 | Check-in esta semana |
| Takenos | 6.2 | 🟡 | = | Monitorear |
| Mudafy | 5.1 | 🟠 | -1.2 | Acción urgente |
| Rebill | 4.8 | 🟠 | nuevo | Revisar onboarding |
| Belo | 7.8 | 🟢 | nuevo | — |

### Alertas
- **Mudafy** score cayó 1.2 puntos MoM → ver churn-detector para análisis profundo
```

## Gotchas

- **El score no reemplaza el juicio.** Un cliente con score 6 que acaba de firmar expansión es distinto a uno con score 6 que está en silencio hace 40 días. El score es un resumen, no un veredicto.
- **Baseline de deflección es por cliente, no global.** Coderhouse tiene tres agentes (Preventa, Students, Staff) con deflection rates distintos — calcular el score por asistente si hay diferencias grandes, y reportar el peor.
- **CSAT ausente = neutro, no negativo.** Si el cliente no lo habilitó, 1.0 pts. No penalizar.
- **Volumen bajo → deflection rate poco confiable.** < 50 conversaciones en el período → asignar 0.0 en deflection y notar "volumen insuficiente" en lugar de calcular un rate engañoso.
- **Los scores históricos en Notion son solo para tendencias.** No recalcular scores pasados — la lógica puede cambiar. Solo agregar entradas nuevas.
- **Toribio Achaval no tiene score todavía** — en onboarding, sin datos suficientes. Calcular a partir de la primera semana post go-live.

## Dependencias

- `customer-success:data-expert` — métricas de conversaciones, deflección, CSAT
- `account-management:account-manager` — salud relacional (último contacto, issues), persistencia del histórico
- `customer-success:churn-detector` — para profundizar cuando el score baja a 🟠/🔴
