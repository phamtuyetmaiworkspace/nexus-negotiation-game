
# NEXUS Streamlit MVP

## What this MVP includes
- Public International Market + Team Directory
- Team Trader login with Team Number + Trader PIN
- Team inventory and pending offers
- Create / Accept / Reject trades
- Build items
- Sell assets to International Market
- Teacher dashboard
- Open / close market and advance period

## 1. Install
```bash
pip install -r requirements.txt
```

## 2. Configure secrets
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SERVICE_KEY = "YOUR_SERVER_SIDE_SECRET_KEY"
ADMIN_PIN = "choose-a-teacher-pin"
```

Never commit `.streamlit/secrets.toml`.

## 3. Run locally
```bash
streamlit run app.py
```

## Important
This version assumes the Supabase `nexus_*` tables and RPC functions have already been created.

MVP v0.1 supports one line per side in a trade. The database already supports package deals; the next UI version can allow multiple lines.
