import csv
import sys
from datetime import datetime

import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # Python < 3.9

API_URL = "https://worldcup26.ir/get/games"
OUTPUT_FILE = "worldcup2026_games.csv"
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

# Fuso horário de cada estádio pelo stadium_id da API
STADIUM_TIMEZONES = {
    "1":  "America/Mexico_City",   # Estadio Azteca — Cidade do México
    "2":  "America/Mexico_City",   # Estadio Akron — Guadalajara
    "3":  "America/Monterrey",     # Estadio BBVA — Monterrey
    "4":  "America/Chicago",       # AT&T Stadium — Dallas
    "5":  "America/Chicago",       # NRG Stadium — Houston
    "6":  "America/Chicago",       # Arrowhead Stadium — Kansas City
    "7":  "America/New_York",      # Mercedes-Benz Stadium — Atlanta
    "8":  "America/New_York",      # Hard Rock Stadium — Miami
    "9":  "America/New_York",      # Gillette Stadium — Boston
    "10": "America/New_York",      # Lincoln Financial Field — Filadélfia
    "11": "America/New_York",      # MetLife Stadium — Nova York/NJ
    "12": "America/Toronto",       # BMO Field — Toronto
    "13": "America/Vancouver",     # BC Place — Vancouver
    "14": "America/Los_Angeles",   # Lumen Field — Seattle
    "15": "America/Los_Angeles",   # Levi's Stadium — San Francisco
    "16": "America/Los_Angeles",   # SoFi Stadium — Los Angeles
}


def to_brazil_time(local_date_str: str, stadium_id: str) -> str:
    tz_name = STADIUM_TIMEZONES.get(str(stadium_id), "UTC")
    local_tz = ZoneInfo(tz_name)
    dt = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M").replace(tzinfo=local_tz)
    return dt.astimezone(BRAZIL_TZ).strftime("%d/%m/%Y %H:%M")


def fetch_games() -> list[dict]:
    print(f"Buscando jogos em {API_URL} ...")
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    if isinstance(payload, list):
        return payload
    for key in ("data", "games", "matches", "results"):
        if key in payload:
            return payload[key]
    raise ValueError(f"Formato de resposta inesperado: {list(payload.keys())}")


def build_rows(games: list[dict]) -> list[dict]:
    rows = []
    for g in games:
        stadium_id = str(g.get("stadium_id", ""))
        local_date = g.get("local_date", "")

        try:
            brazil_time = to_brazil_time(local_date, stadium_id) if local_date else ""
        except (ValueError, KeyError) as exc:
            print(f"  Aviso: não foi possível converter horário do jogo {g.get('id')} — {exc}")
            brazil_time = ""

        rows.append({
            "id":               g.get("id"),
            "tipo":             g.get("type", ""),
            "grupo":            g.get("group", ""),
            "rodada":           g.get("matchday", ""),
            "time_casa":        g.get("home_team_name_en", ""),
            "time_visitante":   g.get("away_team_name_en", ""),
            "data_hora_brasil": brazil_time,
            "data_hora_local":  local_date,
            "estadio_id":       stadium_id,
            "placar_casa":      g.get("home_score", ""),
            "placar_visitante": g.get("away_score", ""),
            "encerrado":        g.get("finished", ""),
            "status":           g.get("time_elapsed", ""),
        })

    rows.sort(
        key=lambda r: datetime.strptime(r["data_hora_brasil"], "%d/%m/%Y %H:%M")
        if r["data_hora_brasil"]
        else datetime.max,
    )
    return rows


def save_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    games = fetch_games()
    rows = build_rows(games)
    save_csv(rows, OUTPUT_FILE)
    print(f"{len(rows)} jogos salvos em '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()
