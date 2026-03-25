# Setup Guide — Weekly Scorecard Dashboard

## 1. Vytvor Notion Integration Token

1. Choď na https://www.notion.so/my-integrations
2. Klikni **+ New integration**
3. Názov: `Scorecard Dashboard`
4. Associated workspace: tvoj workspace
5. Permissions: **Read content**, **Update content**, **Insert content**
6. Skopíruj **Internal Integration Token** (začína `secret_...`)

## 2. Daj integrácii prístup k stránke

1. Otvor stránku **🎯 MA-O1: Top of Mind Brand — Marketing Plan 2026** v Notion
2. Klikni `...` (hore vpravo) → **Connections**
3. Pridaj `Scorecard Dashboard`

## 3. Vytvor .env súbor

```bash
cp .env.example .env
```

Otvor `.env` a vyplň:
```
NOTION_TOKEN=secret_tvoj_token_tu
NOTION_DB_ID=37ef1c72a99d46ec9be372259c79c5a1
PORT=3000
```

## 4. Spusti dashboard

```bash
python3 server.py
```

Otvor prehliadač: **http://localhost:3000**

## 5. Každý týždeň

Buď:
- **Automaticky**: Každý piatok o 8:05 Claude Code automaticky vytvorí nový týždeň v Notion
- **Manuálne**: Klikni "**+ Nový týždeň**" v dashboarde

Potom vyplň hodnoty priamo v Notion databáze **📊 Weekly Scorecard DB** alebo cez API.

---

## Štruktúra projektu

```
DASHBOARD/
  server.py              # Flask backend (spúšťaj toto)
  config.py              # KR targets, baselines — uprav keď dostaneš baseline hodnoty
  requirements.txt       # Python závislosti
  .env                   # Tvoj Notion token (NECOMMITOVAŤ!)
  api/
    notion_client.py     # Notion API komunikácia
    compute_utils.py     # Auto-výpočty (%, trend, status, 4w avg)
  public/
    index.html           # Dashboard UI
    styles.css           # Štýly
    app.js               # Frontend logika + Chart.js grafy
```

## Budúce vylepšenia (v2)

- **GA4 integrácia**: Pridaj `google-analytics-data` a service account JSON
- **Baseline hodnoty**: Uprav `config.py` → KR1/KR3/KR6 dostanú správne % výpočty
- **Export do PDF/Excel**: Weekly report automation
