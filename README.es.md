# claude-mls-wordpress-sync

Motor de sync diff-based. Trae listings de MLS (RESO Web API / Bridge
Interactive / Spark / IDX Broker) y empuja a WordPress (Custom Post
Type) vía WP REST API solamente los listings que **cambiaron**.

Hecho para sitios de brokerages que estaban quemando la cuota de su API
de MLS haciendo re-syncs completos, o perdiendo los custom fields cada
vez que corría el cron.

> Data de demo sintética (`Acme Realty`, `+1555...`). Conectás
> credenciales reales de MLS en `.env` para sincronizar un feed vivo.

## Por qué existe

La mayoría de las integraciones "MLS → WordPress" que me tocó tocar
hacen overwrite total en cada cron. Eso quema cuota de la API de MLS
(Spark/Bridge te rate-limitean por hora), re-crea los posts de WP
(mata permalinks SEO y pisa los custom fields que el staff editó a
mano) y re-baja cada imagen cada vez (el sync pasa de minutos a horas).

Este proyecto hace diff sync:

1. Trae listings del MLS (paginado, con filtro `ModificationTimestamp` cuando el provider lo soporta)
2. Carga el snapshot local (`state/listings.json`) — `listing_id → content_hash`
3. Calcula diff: `created | updated | unchanged | removed`
4. Empuja a WordPress vía REST solo `created + updated`
5. Marca los `removed` como `status=draft` (nunca hard-delete — primero que el broker revise)
6. Persiste el nuevo snapshot atómicamente

Resultado: un MLS de 1.200 listings corriendo cada 15 minutos
típicamente toca <20 listings por ciclo.

## Features

- **Patrón adapter para providers de MLS.** `src/mls_adapters/` tiene un
  archivo por provider (`reso.py`, `bridge.py`, `spark.py`, `mock.py`).
  Cambiar de provider = cambio de config, no de código.
- **Field mapping configurable.** `config/field_mapping.yaml` declara
  cómo los campos de MLS mapean a post fields + meta keys de WP. Se
  cambia de vendor editando YAML.
- **Idempotente.** Correr el sync dos veces seguidas sobre un MLS que
  no cambió = cero writes a WordPress.
- **Retry exponencial + dead-letter log.** Las fallas de red reintentan
  3 veces con backoff; las fallas permanentes quedan en
  `logs/dead-letter.jsonl` para revisión humana.
- **Async con `httpx.AsyncClient`.** Pulls + pushes concurrentes con
  paralelismo acotado por semáforo.
- **Endpoint de health sin costo.** `python -m src.health` imprime
  último timestamp de sync, success rate de las últimas 24h, y count
  de dead-letter — piped a Slack / Uptime Kuma.

## Quickstart

```bash
git clone https://github.com/sarteta/claude-mls-wordpress-sync.git
cd claude-mls-wordpress-sync
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # editar creds
python -m src.sync --provider mock --dry-run          # preview del diff
python -m src.sync --provider mock                    # sync real
```

`--provider mock` usa el feed sintético bundleado para que veas el
motor funcionando antes de conectar un MLS real.

## Scheduling

Cron en Linux:
```
*/15 * * * * cd /srv/claude-mls-sync && /srv/claude-mls-sync/.venv/bin/python -m src.sync >> logs/cron.log 2>&1
```

Task Scheduler en Windows: `scripts/run-sync.ps1`.

Docker: `docker compose up -d` corre el loop internamente cada
`SYNC_INTERVAL_MINUTES`.

## Estado

- [x] Motor de diff
- [x] Adapter mock (feed sintético para demos/tests)
- [x] Adapter RESO Web API
- [x] Cliente WordPress REST con app-password
- [x] Field mapping vía YAML
- [x] Retry exponencial + dead-letter
- [ ] Adapter Spark API (planeado — próxima release)
- [ ] Adapter Bridge Interactive (planeado)
- [ ] Diff de imágenes + lazy download (planeado)

## Licencia

MIT — ver [LICENSE](./LICENSE).

Armado por [Santiago Arteta](https://github.com/sarteta) a partir de
trabajo de integración en real-estate. Forks e issues bienvenidos;
disponible para consultoría sobre feeds de MLS a medida.
