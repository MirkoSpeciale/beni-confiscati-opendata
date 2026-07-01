"""
utils.py — Funzioni di supporto per il progetto "Beni Confiscati alla Mafia"
"""

import pandas as pd
import numpy as np
import json
import os
import folium
from folium.plugins import MarkerCluster
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# 1. ISPEZIONE DATI
# ============================================================

def printInfo(df: pd.DataFrame, name: str = "DataFrame") -> None:
    """Stampa un riepilogo sintetico del DataFrame: shape, tipi, valori nulli."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Righe: {len(df):,}  |  Colonne: {len(df.columns)}")
    print(f"\n  {'Colonna':<30} {'Tipo':<12} {'Non-null':>8}  {'% null':>7}  {'Unici':>7}")
    print(f"  {'-'*70}")
    for col in df.columns:
        n_null = df[col].isna().sum()
        pct    = n_null / len(df) * 100
        uniq   = df[col].nunique()
        print(f"  {col:<30} {str(df[col].dtype):<12} {len(df)-n_null:>8}  {pct:>6.1f}%  {uniq:>7}")
    print()


# ============================================================
# 2. MAPPING REGIONI → NUTS2 (per Plotly choropleth)
# ============================================================

REGIONI_NUTS2 = {
    "Piemonte":              "ITC1",
    "Valle d'Aosta":         "ITC2",
    "Lombardia":             "ITC4",
    "Liguria":               "ITC3",
    "Trentino-Alto Adige":   "ITH2",
    "Veneto":                "ITH3",
    "Friuli-Venezia Giulia": "ITH4",
    "Emilia-Romagna":        "ITH5",
    "Toscana":               "ITI1",
    "Umbria":                "ITI2",
    "Marche":                "ITI3",
    "Lazio":                 "ITI4",
    "Abruzzo":               "ITF1",
    "Molise":                "ITF2",
    "Campania":              "ITF3",
    "Puglia":                "ITF4",
    "Basilicata":            "ITF5",
    "Calabria":              "ITF6",
    "Sicilia":               "ITG1",
    "Sardegna":              "ITG2",
}


# ============================================================
# 3. MAPPA FOLIUM — punti aggregati per provincia
# ============================================================

def genera_mappa_province(df: pd.DataFrame, output_path: str) -> folium.Map:
    """
    Genera una mappa Folium con CircleMarker per ogni provincia.
    La dimensione del cerchio è proporzionale al numero di beni.
    Salva l'HTML nella cartella output_path.

    Parametri:
        df           : DataFrame unificato con colonne 'lat', 'lon', 'NomeProvinciaValidato'
        output_path  : cartella dove salvare la mappa HTML
    """
    m = folium.Map(location=[41.87, 12.56], zoom_start=6, tiles="CartoDB positron")

    # Raggruppa per provincia calcolando il centroide medio dei comuni
    agg = (
        df.dropna(subset=["lat", "lon"])
          .groupby("NomeProvinciaValidato")
          .agg(lat=("lat", "mean"), lon=("lon", "mean"), n_beni=("s_bene", "count"))
          .reset_index()
    )

    max_n = agg["n_beni"].max()

    for _, row in agg.iterrows():
        radius = 5 + (row["n_beni"] / max_n) * 25
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color="#c0392b",
            fill=True,
            fill_color="#e74c3c",
            fill_opacity=0.6,
            popup=folium.Popup(
                f"<b>{row['NomeProvinciaValidato']}</b><br>Beni: {row['n_beni']:,}",
                max_width=200
            ),
            tooltip=f"{row['NomeProvinciaValidato']}: {row['n_beni']:,} beni"
        ).add_to(m)

    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, "mappa-beni-confiscati.html")
    m.save(out_file)
    print(f"Mappa salvata in: {out_file}")
    return m


# ============================================================
# 5. EXPORT DATASET PROCESSATO
# ============================================================

def esporta_csv_e_frictionless(df: pd.DataFrame, output_path: str, filename: str = "beni-confiscati") -> None:
    """
    Esporta il DataFrame processato in CSV e genera il datapackage.json
    (standard Frictionless Data).

    Parametri:
        df          : DataFrame pulito
        output_path : cartella di destinazione
        filename    : nome base del file (senza estensione)
    """
    os.makedirs(output_path, exist_ok=True)
    csv_path = os.path.join(output_path, f"{filename}.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"CSV salvato: {csv_path}")

    # Costruisce lo schema dei campi per il datapackage
    fields = []
    type_map = {
        "int64":   "integer",
        "Int64":   "integer",
        "float64": "number",
        "object":  "string",
        "bool":    "boolean",
    }
    for col in df.columns:
        dtype = str(df[col].dtype)
        fields.append({
            "name": col,
            "type": type_map.get(dtype, "string"),
        })

    datapackage = {
        "name": filename,
        "title": "Beni Confiscati alla Mafia in Italia",
        "description": (
            "Dataset unificato dei beni (immobili e aziende) confiscati alle organizzazioni criminali "
            "in Italia, distinti tra beni già destinati e beni ancora in gestione giudiziaria. "
            "Fonte: Agenzia Nazionale per l'Amministrazione e la Destinazione dei Beni Sequestrati "
            "e Confiscati alla Criminalità Organizzata (ANBSC)."
        ),
        "version": "1.0.0",
        "keywords": ["beni confiscati", "mafia", "criminalità organizzata", "ANBSC", "open data", "Italia"],
        "licenses": [{"name": "CC-BY-4.0", "title": "Creative Commons Attribution 4.0"}],
        "sources": [
            {
                "title": "ANBSC – Beni destinati",
                "path": "https://dati.gov.it/view-dataset/dataset?id=beni-confiscati-destinati"
            },
            {
                "title": "ANBSC – Beni in gestione",
                "path": "https://dati.gov.it/view-dataset/dataset?id=beni-confiscati-in-gestione"
            }
        ],
        "spatial": {"location": "Italia"},
        "resources": [
            {
                "name": filename,
                "path": f"{filename}.csv",
                "format": "csv",
                "encoding": "utf-8",
                "schema": {"fields": fields},
            }
        ],
    }

    pkg_path = os.path.join(output_path, "datapackage.json")
    with open(pkg_path, "w", encoding="utf-8") as f:
        json.dump(datapackage, f, ensure_ascii=False, indent=2)
    print(f"datapackage.json salvato: {pkg_path}")
