# Getting the SMARD data

Download the three raw CSV files from SMARD.de (they are not in the repository) and save them in `data/raw/` under exactly these names:
- `Realisierte_Erzeugung_202306010000_202606020000_Viertelstunde.csv` (generation)
- `Actual_consumption_202306010000_202606020000_Quarterhour.csv` (consumption)
- `Gro_handelspreise_202306010000_202606020000_Viertelstunde.csv` (prices)

How these files were made, as far as the files and the loaders in `scripts/` confirm it:
1. Open <https://www.smard.de/en/downloadcenter/download-market-data/>.
2. **Generation** (menu name `Generation`): all sources (12 columns, `Biomasse` to `Sonstige Konventionelle`). Choose the **German** website language: the file has the columns `Datum von`, `Datum bis` and `<source> [MWh] Originalauflösungen`, German numbers (`1.026,00`) and dates like `01.06.2023 00:00`.
3. **Consumption** (menu name `Consumption`): 4 columns: `grid load`, `Grid load incl. hydro pumped storage`, `Hydro pumped storage`, `Residual load`. Choose the **English** website language: the file has the columns `Start date`, `End date` and `<name> [MWh] Original resolutions`, numbers like `11,053.00` and dates like `Jun 1, 2023 12:00 AM`.
4. **Prices** (menu name not verified): wholesale prices, all zones (17 columns, `Deutschland/Luxemburg` to `Ungarn`). Choose the **German** website language: the file has the columns `Datum von`, `Datum bis` and `<zone> [€/MWh] Originalauflösungen`, German numbers (`84,15`) and dates like `01.06.2023 00:00`.
5. For all three: region Germany (not verified: the CSV does not record the region), resolution quarter-hour (confirmed: 15-minute steps, columns marked "original resolutions"), period 01.06.2023 to 02.06.2026 (confirmed: the first row starts 01.06.2023 00:00 and the last row ends 02.06.2026 00:00), format CSV (confirmed: semicolon-separated, UTF-8 with a byte-order mark).
6. Each file was downloaded in one go: the download center lets you pick the start and end date, so the full range 01.06.2023 to 02.06.2026 comes as one file per dataset. No joining was needed.
7. Check each file: 105,312 data rows (`wc -l` prints 105313 with the header line), first row starting 1 June 2023 00:00.

The loaders expect these exact column names (`scripts/load_data.py`, `scripts/load_verbrauch.py`, `scripts/load_preise.py`), so a different website language needs a loader change.
