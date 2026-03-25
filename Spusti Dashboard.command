#!/bin/bash

# --- Ableneo Marketing Dashboard Launcher ---

DASHBOARD_DIR="/Users/peter/CLAUDE CODE/DASHBOARD"
PORT=3000
URL="http://localhost:$PORT"

echo "🚀 Spúšťam Ableneo Marketing Dashboard..."
cd "$DASHBOARD_DIR"

# Nainštaluj závislosti ak chýbajú
if [ ! -d "node_modules" ]; then
  echo "📦 Inštalujem závislosti (npm install)..."
  npm install
  echo "✅ Závislosti nainštalované"
fi

# Zabij prípadný starý proces na porte 3000
OLD_PID=$(lsof -ti tcp:$PORT)
if [ -n "$OLD_PID" ]; then
  echo "⚠️  Port $PORT obsadený, restartujem..."
  kill -9 $OLD_PID
  sleep 1
fi

# Spusti server na pozadí
node server.js &
SERVER_PID=$!
echo "✅ Server beží (PID: $SERVER_PID)"

# Počkaj kým server naštartuje
sleep 2

# Otvor v prehliadači
echo "🌐 Otváram $URL..."
open "$URL"

echo ""
echo "Dashboard beží na $URL"
echo "Pre zastavenie zavri toto okno alebo stlač Ctrl+C"
echo ""

# Drž terminal otvorený
wait $SERVER_PID
