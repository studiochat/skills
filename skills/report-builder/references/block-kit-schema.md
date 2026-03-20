# Block Kit Schema

Reports produce a JSON document with `metadata` and `blocks`. The rendering engine (PDF and web UI) only supports these block types.

## Document Structure

```json
{
  "metadata": {
    "time_window_days": 7,
    "conversations_analyzed": 150,
    "playbook_names": ["Cotizador", "Soporte"],
    "generated_at": "2026-03-20T12:00:00Z"
  },
  "blocks": [ ... ]
}
```

## Block Types

### heading
```json
{ "type": "heading", "level": 1, "text": "Section Title" }
```
Levels: 1 (main section), 2 (subsection), 3 (minor heading).

### text
```json
{ "type": "text", "text": "Paragraph content." }
```

### divider
```json
{ "type": "divider" }
```

### fact_cards
Key metrics displayed as cards in a row.
```json
{
  "type": "fact_cards",
  "items": [
    {
      "label": "Total Conversations",
      "value": "1,234",
      "change": "+12%",
      "sentiment": "positive"
    }
  ]
}
```
- `label`: metric name (uppercase in rendering)
- `value`: formatted string (use commas for thousands)
- `change`: optional, e.g. "+12%", "-5%"
- `sentiment`: optional, `positive` (green), `negative` (red), `neutral` (gray)

### table
```json
{
  "type": "table",
  "title": "Optional Table Title",
  "headers": ["Column A", "Column B"],
  "rows": [
    ["cell 1", "cell 2"],
    ["cell 3", "cell 4"]
  ]
}
```

### list
```json
{ "type": "list", "ordered": false, "items": ["Item one", "Item two"] }
{ "type": "list", "ordered": true, "items": ["Step one", "Step two"] }
```

### callout
```json
{ "type": "callout", "style": "warning", "text": "Important note." }
```
Styles: `info` (blue), `warning` (amber), `success` (green), `error` (red).
