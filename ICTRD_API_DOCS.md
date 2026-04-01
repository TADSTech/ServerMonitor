# Centaur Trading API Docs

## Overview

Centaur Trading API exposes market intelligence, data download, model lifecycle, and strategy backtesting behind API-key authentication.

Base URL (local):

- `http://localhost:8080`

Base URL (live):

- `https://ictrd.onrender.com`

Interactive API docs:

- `http://localhost:8080/docs`
- `http://localhost:8080/redoc`
- `https://ictrd.onrender.com/docs`
- `https://ictrd.onrender.com/redoc`

## Security Model

The API now supports private owner-only mode for pre-launch security.

Set these environment variables on live API server:

- `ENABLE_PUBLIC_API=0` (default secure mode)
- `OWNER_ACCESS_SECRET=<strong_secret>`
- `ALLOWED_IPS=<optional_comma_separated_ip_allowlist>`
- `ADMIN_API_KEY=<strong_secret_for_admin_endpoints>`

### Consumer Key

All `/v1/*` business endpoints require:

- Header: `X-API-Key: <your_key>`

In private mode (`ENABLE_PUBLIC_API=0`), requests also require one of:

- Header: `X-Owner-Secret: <owner_secret>`
- Caller IP present in `ALLOWED_IPS`

### Admin Key

Administrative key management endpoints require:

- Header: `X-Admin-Key: <admin_key>`
- Header: `X-Owner-Secret: <owner_secret>` (or allowlisted IP)

Set admin key in environment:

- `ADMIN_API_KEY=change_this_to_strong_secret`

## API Key Lifecycle

### 1) Generate key from CLI (owner protected)

```bash
export KEYGEN_OWNER_SECRET='your_strong_owner_secret'
python generate_api_key.py --label mobile-app --scopes '*' --expires-days 90
```

Notes:

- The CLI now refuses to generate keys unless `KEYGEN_OWNER_SECRET` is configured.
- You will be prompted for owner secret unless you pass `--owner-secret`.

### 2) Generate key via admin endpoint

```bash
curl -X POST http://localhost:8080/v1/auth/keys/generate \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -H "X-Owner-Secret: $OWNER_ACCESS_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "mobile-app",
    "scopes": ["*"],
    "expires_days": 90
  }'
```

### 3) List keys

```bash
curl -X GET http://localhost:8080/v1/auth/keys \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -H "X-Owner-Secret: $OWNER_ACCESS_SECRET"
```

### 4) Revoke key

```bash
curl -X POST http://localhost:8080/v1/auth/keys/revoke \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -H "X-Owner-Secret: $OWNER_ACCESS_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"key_prefix": "ctr_abcd1234"}'
```

## Live Server Endpoints

Assuming API host: `https://ictrd.onrender.com`

- Health: `GET /health`
- Swagger docs: `GET /docs`
- ReDoc docs: `GET /redoc`
- Identity: `GET /v1/me`
- Download history: `POST /v1/history/download`
- Train model: `POST /v1/model/train`
- Evaluate model: `POST /v1/model/evaluate`
- Predict model: `POST /v1/model/predict`
- Run backtest: `POST /v1/backtest/run`
- Key admin generate/list/revoke: `/v1/auth/keys/*`

## Endpoint Reference

### Health

- `GET /health`
- Auth: none
- Purpose: liveness check

### Identity

- `GET /v1/me`
- Auth: `X-API-Key`
- Purpose: return API-key metadata (label, scopes, dates)

### History Download

- `POST /v1/history/download`
- Auth: `X-API-Key`
- Purpose: download OANDA candles into CSV
- Request body:

```json
{
  "instrument": "GBP_JPY",
  "granularity": "M30",
  "days": 720,
  "chunk_size": 5000,
  "output_csv": "history_gbpjpy_m30.csv"
}
```

### Model Training

- `POST /v1/model/train`
- Auth: `X-API-Key`
- Purpose: train model artifact from historical data
- Request body:

```json
{
  "history_csv": "history_gbpjpy_m30.csv",
  "output_path": "models/gbpjpy_direction_model.joblib",
  "horizon_bars": 12,
  "atr_target_ratio": 0.8,
  "epochs": 350,
  "lr": 0.08
}
```

### Model Evaluation

- `POST /v1/model/evaluate`
- Auth: `X-API-Key`
- Purpose: evaluate model on holdout and export prediction-vs-actual CSV
- Request body:

```json
{
  "history_csv": "history_gbpjpy_m30.csv",
  "model_path": "models/gbpjpy_direction_model.joblib",
  "output_csv": "model_predictions_vs_actual.csv",
  "split_ratio": 0.8,
  "horizon_bars": 12,
  "atr_target_ratio": 0.8
}
```

### Model Predict

- `POST /v1/model/predict`
- Auth: `X-API-Key`
- Purpose: infer latest directional bias from recent candles
- Request body:

```json
{
  "model_path": "models/gbpjpy_direction_model.joblib",
  "history_csv": "history_gbpjpy_m30.csv",
  "lookback_rows": 500
}
```

### Backtest Run

- `POST /v1/backtest/run`
- Auth: `X-API-Key`
- Purpose: run strict-confluence backtest and return summary + trade preview
- Request body supports all major strategy params:

```json
{
  "history_csv": "history_gbpjpy_m30.csv",
  "instrument": "GBP_JPY",
  "granularity": "M30",
  "candle_count": 3500,
  "vol_spike_ratio": 1.8,
  "min_expansion_atr": 1.1,
  "pullback_atr_ratio": 0.35,
  "min_rr": 2.2,
  "sl_atr_multiplier": 1.3,
  "max_hold_bars": 16,
  "min_session_hour_utc": 7,
  "max_session_hour_utc": 20,
  "debug": false
}
```

## Example Integration (Python)

```python
import requests

BASE = "http://localhost:8080"
API_KEY = "your_api_key"

headers = {"X-API-Key": API_KEY}

pred = requests.post(
    f"{BASE}/v1/model/predict",
    headers={**headers, "Content-Type": "application/json"},
    json={"history_csv": "history_gbpjpy_m30.csv", "lookback_rows": 500},
    timeout=30,
)
print(pred.json())
```

## Example Integration (Node.js)

```javascript
const base = "http://localhost:8080";
const apiKey = process.env.CENTAUR_API_KEY;

const res = await fetch(`${base}/v1/backtest/run`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": apiKey,
    "X-Owner-Secret": process.env.CENTAUR_OWNER_SECRET,
  },
  body: JSON.stringify({
    history_csv: "history_gbpjpy_m30.csv",
    candle_count: 2000,
    vol_spike_ratio: 1.4,
    min_expansion_atr: 0.8,
  }),
});

console.log(await res.json());
```

## Error Conventions

- `401`: missing or invalid `X-API-Key`
- `403`: denied by owner-only access policy or invalid admin key
- `404`: missing model/history file
- `500`: server-side or environment configuration issue

## Recommended Deployment Hardening

1. Use HTTPS behind reverse proxy.
2. Restrict CORS to known domains.
3. Keep `ENABLE_PUBLIC_API=0` until launch.
4. Require `X-Owner-Secret` and set strict `ALLOWED_IPS`.
5. Rotate API keys periodically and enforce expiry.
6. Set `ADMIN_API_KEY` and `OWNER_ACCESS_SECRET` to strong random secrets.
7. Persist `api_keys.json` securely (backups + restricted permissions).
