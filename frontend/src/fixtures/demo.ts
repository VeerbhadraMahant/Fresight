// AUTO-GENERATED demo fixture — a pre-computed Hay Point -> Paradip scenario.
// Regenerate:  python backend/../capture (see scripts) while the API is running.
// Shown instantly on load so the dashboard is always populated, then replaced
// by live data when the API responds (handles Render free-tier cold starts).
export const DEMO = {
 "capturedAt": "2026-09-01T09:46:21.731527Z",
 "scenarioRequest": {
  "origin": "AUHPT",
  "destination": "INPRT",
  "commodity": "Thermal Coal",
  "cargo_volume_t": 600000,
  "contract_duration_months": 6,
  "laycan_month": 11,
  "vessel": null,
  "forecast_horizon_days": 120
 },
 "ports": {
  "discharge_ports": [
   {
    "code": "INPRT",
    "name": "Paradip",
    "country": "India",
    "region": "India-EastCoast",
    "role": "discharge",
    "lat": 20.26,
    "lon": 86.67,
    "max_draft_m": 16.5,
    "max_loa_m": 300,
    "max_beam_m": 46,
    "max_dwt": 175000,
    "berth_handling_tph": 1600,
    "congestion_base_days": 2.2,
    "transload": false,
    "notes": "Mechanised coal berths; PPA handles Capesize (draft-limited to ~150k t intake at 16.5 m).",
    "source": "paradipport.gov.in/berth_spec",
    "handling_tpd": 38400
   },
   {
    "code": "INVTZ",
    "name": "Visakhapatnam (Outer Harbour)",
    "country": "India",
    "region": "India-EastCoast",
    "role": "both",
    "lat": 17.68,
    "lon": 83.28,
    "max_draft_m": 17.0,
    "max_loa_m": 390,
    "max_beam_m": 50,
    "max_dwt": 200000,
    "berth_handling_tph": 1400,
    "congestion_base_days": 2.6,
    "transload": false,
    "notes": "Outer Harbour + SPM; super-Cape up to 200k DWT, draft to ~18.1 m at SPM.",
    "source": "vizagport.com allowable LOA/Beam/Draft",
    "handling_tpd": 33600
   },
   {
    "code": "INGVR",
    "name": "Gangavaram",
    "country": "India",
    "region": "India-EastCoast",
    "role": "discharge",
    "lat": 17.63,
    "lon": 83.23,
    "max_draft_m": 18.0,
    "max_loa_m": 325,
    "max_beam_m": 55,
    "max_dwt": 200000,
    "berth_handling_tph": 1600,
    "congestion_base_days": 1.8,
    "transload": false,
    "notes": "Water depth to 21 m; fully-laden super-Cape capable.",
    "source": "en.wikipedia.org/wiki/Gangavaram_Port",
    "handling_tpd": 38400
   },
   {
    "code": "INGPR",
    "name": "Gopalpur",
    "country": "India",
    "region": "India-EastCoast",
    "role": "discharge",
    "lat": 19.27,
    "lon": 84.92,
    "max_draft_m": 14.2,
    "max_loa_m": 290,
    "max_beam_m": 45,
    "max_dwt": 100000,
    "berth_handling_tph": 950,
    "congestion_base_days": 1.5,
    "transload": false,
    "notes": "Cape geared self-dischargers to ~14.5 m; berths GCB1-3 at 14.2 m.",
    "source": "gopalpurports.in max permissible LOA/Beam/Draft",
    "handling_tpd": 22800
   },
   {
    "code": "INDHA",
    "name": "Dhamra",
    "country": "India",
    "region": "India-EastCoast",
    "role": "discharge",
    "lat": 20.78,
    "lon": 87.0,
    "max_draft_m": 18.0,
    "max_loa_m": 290,
    "max_beam_m": 47,
    "max_dwt": 180000,
    "berth_handling_tph": 1500,
    "congestion_base_days": 1.6,
    "transload": false,
    "notes": "18 m draught, 180k DWT Capesize.",
    "source": "en.wikipedia.org/wiki/Dhamra_Port ; shipnext.com",
    "handling_tpd": 36000
   },
   {
    "code": "INSAN",
    "name": "Sagar / Sandheads",
    "country": "India",
    "region": "India-EastCoast",
    "role": "discharge",
    "lat": 21.15,
    "lon": 88.05,
    "max_draft_m": 10.5,
    "max_loa_m": 260,
    "max_beam_m": 40,
    "max_dwt": 90000,
    "berth_handling_tph": 650,
    "congestion_base_days": 3.0,
    "transload": true,
    "notes": "Anchorage transloading point for the Hooghly; floating-crane lighterage to Haldia/Kolkata.",
    "source": "assumed from Hooghly estuary pilotage practice",
    "handling_tpd": 15600
   },
   {
    "code": "INHAL",
    "name": "Haldia",
    "country": "India",
    "region": "India-EastCoast",
    "role": "discharge",
    "lat": 22.03,
    "lon": 88.09,
    "max_draft_m": 9.1,
    "max_loa_m": 230,
    "max_beam_m": 32.5,
    "max_dwt": 60000,
    "berth_handling_tph": 650,
    "congestion_base_days": 3.4,
    "transload": false,
    "notes": "Tidal riverine dock; Panamax part-laden only, max ~8.5 m sustained sailing draft.",
    "source": "en.wikipedia.org/wiki/Haldia_Dock_Complex",
    "handling_tpd": 15600
   }
  ],
  "load_ports": [
   {
    "code": "AUHPT",
    "name": "Hay Point",
    "country": "Australia",
    "region": "Australia",
    "role": "load",
    "lat": -21.28,
    "lon": 149.3,
    "max_draft_m": 17.4,
    "max_loa_m": 300,
    "max_beam_m": 50,
    "max_dwt": 200000,
    "berth_handling_tph": 5800,
    "congestion_base_days": 1.4,
    "transload": false,
    "notes": "Metallurgical + thermal coal; two of the world's largest coal terminals (DBCT + HPCT).",
    "source": "nqbp.com.au ; ballastmarkets.com/ports/hay-point",
    "handling_tpd": 139200
   },
   {
    "code": "AUNTL",
    "name": "Newcastle",
    "country": "Australia",
    "region": "Australia",
    "role": "load",
    "lat": -32.92,
    "lon": 151.79,
    "max_draft_m": 16.2,
    "max_loa_m": 300,
    "max_beam_m": 50,
    "max_dwt": 200000,
    "berth_handling_tph": 5200,
    "congestion_base_days": 1.8,
    "transload": false,
    "notes": "World's largest coal export port (thermal); Hunter Valley Coal Chain.",
    "source": "en.wikipedia.org/wiki/Port_of_Newcastle",
    "handling_tpd": 124800
   },
   {
    "code": "AUDBY",
    "name": "Dalrymple Bay",
    "country": "Australia",
    "region": "Australia",
    "role": "load",
    "lat": -21.25,
    "lon": 149.32,
    "max_draft_m": 18.1,
    "max_loa_m": 305,
    "max_beam_m": 50,
    "max_dwt": 210000,
    "berth_handling_tph": 5500,
    "congestion_base_days": 1.6,
    "transload": false,
    "notes": "Deepwater Capesize coal terminal adjacent to Hay Point.",
    "source": "assumed from NQBP declared depths",
    "handling_tpd": 132000
   },
   {
    "code": "USORF",
    "name": "Hampton Roads (Norfolk)",
    "country": "USA",
    "region": "USA",
    "role": "load",
    "lat": 36.92,
    "lon": -76.33,
    "max_draft_m": 15.2,
    "max_loa_m": 300,
    "max_beam_m": 48,
    "max_dwt": 175000,
    "berth_handling_tph": 2500,
    "congestion_base_days": 2.0,
    "transload": false,
    "notes": "Lamberts Point / Pier IX coal piers; ~50 ft channel.",
    "source": "assumed from USACE Norfolk Harbor 50 ft project",
    "handling_tpd": 60000
   },
   {
    "code": "USBAL",
    "name": "Baltimore (Curtis Bay)",
    "country": "USA",
    "region": "USA",
    "role": "load",
    "lat": 39.22,
    "lon": -76.58,
    "max_draft_m": 15.2,
    "max_loa_m": 290,
    "max_beam_m": 46,
    "max_dwt": 150000,
    "berth_handling_tph": 1900,
    "congestion_base_days": 2.2,
    "transload": false,
    "notes": "CSX Curtis Bay + CNX Marine coal terminals.",
    "source": "assumed from Baltimore Harbor 50 ft channel",
    "handling_tpd": 45600
   },
   {
    "code": "MZMPM",
    "name": "Maputo",
    "country": "Mozambique",
    "region": "Mozambique",
    "role": "load",
    "lat": -25.97,
    "lon": 32.57,
    "max_draft_m": 14.2,
    "max_loa_m": 280,
    "max_beam_m": 44,
    "max_dwt": 120000,
    "berth_handling_tph": 1100,
    "congestion_base_days": 2.4,
    "transload": false,
    "notes": "Coal + chrome + ferro; channel dredged to ~14.2-14.7 m, Panamax / part-laden Cape.",
    "source": "assumed from Port of Maputo declared depth",
    "handling_tpd": 26400
   },
   {
    "code": "MZBEW",
    "name": "Beira",
    "country": "Mozambique",
    "region": "Mozambique",
    "role": "load",
    "lat": -19.83,
    "lon": 34.84,
    "max_draft_m": 12.0,
    "max_loa_m": 240,
    "max_beam_m": 40,
    "max_dwt": 80000,
    "berth_handling_tph": 850,
    "congestion_base_days": 3.0,
    "transload": false,
    "notes": "Access channel siltation-constrained; Handy/Supramax coal from Moatize via Sena line.",
    "source": "assumed from Cornelder de Mocambique channel notices",
    "handling_tpd": 20400
   },
   {
    "code": "IDMBR",
    "name": "Muara Berau (East Kalimantan)",
    "country": "Indonesia",
    "region": "Indonesia",
    "role": "load",
    "lat": -0.33,
    "lon": 117.42,
    "max_draft_m": 17.5,
    "max_loa_m": 300,
    "max_beam_m": 50,
    "max_dwt": 200000,
    "berth_handling_tph": 1300,
    "congestion_base_days": 2.8,
    "transload": true,
    "notes": "Anchorage transloading: mother vessels loaded by floating cranes / barges.",
    "source": "16marine.co.id guidance to loading coal in Kalimantan",
    "handling_tpd": 31200
   },
   {
    "code": "IDTBN",
    "name": "Taboneo (South Kalimantan)",
    "country": "Indonesia",
    "region": "Indonesia",
    "role": "load",
    "lat": -3.68,
    "lon": 114.42,
    "max_draft_m": 16.5,
    "max_loa_m": 300,
    "max_beam_m": 50,
    "max_dwt": 190000,
    "berth_handling_tph": 1150,
    "congestion_base_days": 3.0,
    "transload": true,
    "notes": "Banjarmasin/Taboneo anchorage STS coal loading.",
    "source": "gem.wiki Banjamarsin Port",
    "handling_tpd": 27600
   },
   {
    "code": "RUVYP",
    "name": "Vostochny",
    "country": "Russia",
    "region": "Russia",
    "role": "load",
    "lat": 42.75,
    "lon": 133.08,
    "max_draft_m": 16.5,
    "max_loa_m": 300,
    "max_beam_m": 48,
    "max_dwt": 170000,
    "berth_handling_tph": 3000,
    "congestion_base_days": 2.0,
    "transload": false,
    "notes": "Far East mechanised coal terminal (Nakhodka).",
    "source": "assumed from Port Vostochny coal complex declared depth",
    "handling_tpd": 72000
   },
   {
    "code": "RUULU",
    "name": "Ust-Luga",
    "country": "Russia",
    "region": "Russia",
    "role": "load",
    "lat": 59.67,
    "lon": 28.4,
    "max_draft_m": 14.4,
    "max_loa_m": 260,
    "max_beam_m": 42,
    "max_dwt": 120000,
    "berth_handling_tph": 2200,
    "congestion_base_days": 2.4,
    "transload": false,
    "notes": "Baltic coal terminal; Suez routing to East Coast India.",
    "source": "assumed from Ust-Luga declared depth",
    "handling_tpd": 52800
   }
  ]
 },
 "vessels": [
  {
   "name": "Handysize",
   "dwt": 32000,
   "loa": 180,
   "beam": 28.0,
   "scantling_draft": 10.0,
   "laden_speed_kn": 12.5,
   "ballast_speed_kn": 13.0,
   "bunker_sea_tpd": 18.0,
   "bunker_port_tpd": 3.0,
   "geared": true,
   "typical_tce_usd_day": 11500
  },
  {
   "name": "Supramax",
   "dwt": 58000,
   "loa": 199,
   "beam": 32.3,
   "scantling_draft": 12.8,
   "laden_speed_kn": 13.0,
   "ballast_speed_kn": 13.5,
   "bunker_sea_tpd": 26.0,
   "bunker_port_tpd": 4.0,
   "geared": true,
   "typical_tce_usd_day": 14500
  },
  {
   "name": "Panamax",
   "dwt": 76000,
   "loa": 229,
   "beam": 32.2,
   "scantling_draft": 14.1,
   "laden_speed_kn": 13.0,
   "ballast_speed_kn": 13.5,
   "bunker_sea_tpd": 30.0,
   "bunker_port_tpd": 4.5,
   "geared": false,
   "typical_tce_usd_day": 15500
  },
  {
   "name": "Kamsarmax",
   "dwt": 82000,
   "loa": 229,
   "beam": 32.3,
   "scantling_draft": 14.4,
   "laden_speed_kn": 13.0,
   "ballast_speed_kn": 13.5,
   "bunker_sea_tpd": 31.0,
   "bunker_port_tpd": 4.5,
   "geared": false,
   "typical_tce_usd_day": 16500
  },
  {
   "name": "Capesize",
   "dwt": 180000,
   "loa": 292,
   "beam": 45.0,
   "scantling_draft": 18.2,
   "laden_speed_kn": 12.8,
   "ballast_speed_kn": 13.2,
   "bunker_sea_tpd": 42.0,
   "bunker_port_tpd": 6.0,
   "geared": false,
   "typical_tce_usd_day": 22000
  }
 ],
 "routes": [
  {
   "id": "AUHPT-INPRT",
   "lane": "Hay Point -> Paradip",
   "origin": {
    "code": "AUHPT",
    "name": "Hay Point",
    "country": "Australia",
    "region": "Australia"
   },
   "destination": {
    "code": "INPRT",
    "name": "Paradip",
    "region": "India-EastCoast"
   },
   "distance_nm": 6300,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "AUHPT-INVTZ",
   "lane": "Hay Point -> Visakhapatnam",
   "origin": {
    "code": "AUHPT",
    "name": "Hay Point",
    "country": "Australia",
    "region": "Australia"
   },
   "destination": {
    "code": "INVTZ",
    "name": "Visakhapatnam (Outer Harbour)",
    "region": "India-EastCoast"
   },
   "distance_nm": 6150,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "AUNTL-INPRT",
   "lane": "Newcastle -> Paradip",
   "origin": {
    "code": "AUNTL",
    "name": "Newcastle",
    "country": "Australia",
    "region": "Australia"
   },
   "destination": {
    "code": "INPRT",
    "name": "Paradip",
    "region": "India-EastCoast"
   },
   "distance_nm": 7050,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "AUNTL-INGVR",
   "lane": "Newcastle -> Gangavaram",
   "origin": {
    "code": "AUNTL",
    "name": "Newcastle",
    "country": "Australia",
    "region": "Australia"
   },
   "destination": {
    "code": "INGVR",
    "name": "Gangavaram",
    "region": "India-EastCoast"
   },
   "distance_nm": 6900,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "AUDBY-INDHA",
   "lane": "Dalrymple Bay -> Dhamra",
   "origin": {
    "code": "AUDBY",
    "name": "Dalrymple Bay",
    "country": "Australia",
    "region": "Australia"
   },
   "destination": {
    "code": "INDHA",
    "name": "Dhamra",
    "region": "India-EastCoast"
   },
   "distance_nm": 6350,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "USORF-INPRT",
   "lane": "Hampton Roads -> Paradip",
   "origin": {
    "code": "USORF",
    "name": "Hampton Roads (Norfolk)",
    "country": "USA",
    "region": "USA"
   },
   "destination": {
    "code": "INPRT",
    "name": "Paradip",
    "region": "India-EastCoast"
   },
   "distance_nm": 12500,
   "canal": "good-hope",
   "seasonality_profile": "atlantic"
  },
  {
   "id": "USBAL-INVTZ",
   "lane": "Baltimore -> Visakhapatnam",
   "origin": {
    "code": "USBAL",
    "name": "Baltimore (Curtis Bay)",
    "country": "USA",
    "region": "USA"
   },
   "destination": {
    "code": "INVTZ",
    "name": "Visakhapatnam (Outer Harbour)",
    "region": "India-EastCoast"
   },
   "distance_nm": 12650,
   "canal": "good-hope",
   "seasonality_profile": "atlantic"
  },
  {
   "id": "MZMPM-INPRT",
   "lane": "Maputo -> Paradip",
   "origin": {
    "code": "MZMPM",
    "name": "Maputo",
    "country": "Mozambique",
    "region": "Mozambique"
   },
   "destination": {
    "code": "INPRT",
    "name": "Paradip",
    "region": "India-EastCoast"
   },
   "distance_nm": 5250,
   "canal": "none",
   "seasonality_profile": "indian-ocean"
  },
  {
   "id": "MZBEW-INVTZ",
   "lane": "Beira -> Visakhapatnam",
   "origin": {
    "code": "MZBEW",
    "name": "Beira",
    "country": "Mozambique",
    "region": "Mozambique"
   },
   "destination": {
    "code": "INVTZ",
    "name": "Visakhapatnam (Outer Harbour)",
    "region": "India-EastCoast"
   },
   "distance_nm": 5050,
   "canal": "none",
   "seasonality_profile": "indian-ocean"
  },
  {
   "id": "IDMBR-INPRT",
   "lane": "Muara Berau -> Paradip",
   "origin": {
    "code": "IDMBR",
    "name": "Muara Berau (East Kalimantan)",
    "country": "Indonesia",
    "region": "Indonesia"
   },
   "destination": {
    "code": "INPRT",
    "name": "Paradip",
    "region": "India-EastCoast"
   },
   "distance_nm": 3250,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "IDMBR-INVTZ",
   "lane": "Muara Berau -> Visakhapatnam",
   "origin": {
    "code": "IDMBR",
    "name": "Muara Berau (East Kalimantan)",
    "country": "Indonesia",
    "region": "Indonesia"
   },
   "destination": {
    "code": "INVTZ",
    "name": "Visakhapatnam (Outer Harbour)",
    "region": "India-EastCoast"
   },
   "distance_nm": 3050,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "IDMBR-INHAL",
   "lane": "Muara Berau -> Haldia",
   "origin": {
    "code": "IDMBR",
    "name": "Muara Berau (East Kalimantan)",
    "country": "Indonesia",
    "region": "Indonesia"
   },
   "destination": {
    "code": "INHAL",
    "name": "Haldia",
    "region": "India-EastCoast"
   },
   "distance_nm": 3450,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "IDTBN-INGPR",
   "lane": "Taboneo -> Gopalpur",
   "origin": {
    "code": "IDTBN",
    "name": "Taboneo (South Kalimantan)",
    "country": "Indonesia",
    "region": "Indonesia"
   },
   "destination": {
    "code": "INGPR",
    "name": "Gopalpur",
    "region": "India-EastCoast"
   },
   "distance_nm": 3150,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "IDMBR-INSAN",
   "lane": "Muara Berau -> Sagar/Sandheads",
   "origin": {
    "code": "IDMBR",
    "name": "Muara Berau (East Kalimantan)",
    "country": "Indonesia",
    "region": "Indonesia"
   },
   "destination": {
    "code": "INSAN",
    "name": "Sagar / Sandheads",
    "region": "India-EastCoast"
   },
   "distance_nm": 3400,
   "canal": "none",
   "seasonality_profile": "monsoon"
  },
  {
   "id": "RUVYP-INVTZ",
   "lane": "Vostochny -> Visakhapatnam",
   "origin": {
    "code": "RUVYP",
    "name": "Vostochny",
    "country": "Russia",
    "region": "Russia"
   },
   "destination": {
    "code": "INVTZ",
    "name": "Visakhapatnam (Outer Harbour)",
    "region": "India-EastCoast"
   },
   "distance_nm": 5600,
   "canal": "none",
   "seasonality_profile": "pacific"
  },
  {
   "id": "RUULU-INPRT",
   "lane": "Ust-Luga -> Paradip",
   "origin": {
    "code": "RUULU",
    "name": "Ust-Luga",
    "country": "Russia",
    "region": "Russia"
   },
   "destination": {
    "code": "INPRT",
    "name": "Paradip",
    "region": "India-EastCoast"
   },
   "distance_nm": 8200,
   "canal": "suez",
   "seasonality_profile": "atlantic"
  }
 ],
 "provenance": {
  "mode": "hybrid",
  "note": "Freight rates follow the real Breakwave dry-bulk index; bunkers track Brent; port congestion comes from IMF PortWatch daily port-activity data; weather-delay risk uses live Open-Meteo forecasts. A voyage-economics model plus a stochastic overlay turns these drivers into a per route x vessel history calibrated to published 2024-25 route rates and real port constraints.",
  "data_sources": {
   "freight_index": "snapshot 2026-09-01",
   "bunker": "snapshot 2026-09-01",
   "port_activity": "snapshot 2026-09-01 - 7 ports",
   "weather": "snapshot 2026-09-01 - 7 ports"
  },
  "snapshot_date": "2026-09-01",
  "refreshing": false,
  "weather_ports": [
   "INDHA",
   "INGPR",
   "INGVR",
   "INHAL",
   "INPRT",
   "INSAN",
   "INVTZ"
  ],
  "generated_at": "2026-09-01T09:03:46.636526+00:00",
  "history_start": "2023-03-02",
  "history_end": "2026-08-31",
  "series_count": 79,
  "daily_rows": 1279
 },
 "snapshot": {
  "as_of": "2026-08-31",
  "vlsfo_usd_t": 656.7,
  "vlsfo_change_30d_pct": 3.7,
  "tce_usd_day": {
   "Handysize": 10273,
   "Supramax": 10297,
   "Panamax": 15987,
   "Kamsarmax": 16299,
   "Capesize": 16998
  },
  "congestion_days": {
   "Paradip": 2.12,
   "Visakhapatnam (Outer Harbour)": 2.86,
   "Gangavaram": 2.7,
   "Gopalpur": 1.23,
   "Dhamra": 2.03,
   "Sagar / Sandheads": 5.03,
   "Haldia": 5.21
  },
  "rates": [
   {
    "route_id": "AUDBY-INDHA",
    "lane": "Dalrymple Bay -> Dhamra",
    "vessel": "Handysize",
    "rate_usd_t": 33.59,
    "change_30d_pct": -4.9
   },
   {
    "route_id": "AUDBY-INDHA",
    "lane": "Dalrymple Bay -> Dhamra",
    "vessel": "Supramax",
    "rate_usd_t": 21.72,
    "change_30d_pct": -8.1
   },
   {
    "route_id": "AUDBY-INDHA",
    "lane": "Dalrymple Bay -> Dhamra",
    "vessel": "Panamax",
    "rate_usd_t": 22.24,
    "change_30d_pct": 0.9
   },
   {
    "route_id": "AUDBY-INDHA",
    "lane": "Dalrymple Bay -> Dhamra",
    "vessel": "Kamsarmax",
    "rate_usd_t": 22.03,
    "change_30d_pct": 7.6
   },
   {
    "route_id": "AUDBY-INDHA",
    "lane": "Dalrymple Bay -> Dhamra",
    "vessel": "Capesize",
    "rate_usd_t": 12.92,
    "change_30d_pct": 11.3
   },
   {
    "route_id": "AUHPT-INPRT",
    "lane": "Hay Point -> Paradip",
    "vessel": "Handysize",
    "rate_usd_t": 35.99,
    "change_30d_pct": 4.5
   },
   {
    "route_id": "AUHPT-INPRT",
    "lane": "Hay Point -> Paradip",
    "vessel": "Supramax",
    "rate_usd_t": 24.35,
    "change_30d_pct": 5.0
   },
   {
    "route_id": "AUHPT-INPRT",
    "lane": "Hay Point -> Paradip",
    "vessel": "Panamax",
    "rate_usd_t": 24.37,
    "change_30d_pct": 14.1
   },
   {
    "route_id": "AUHPT-INPRT",
    "lane": "Hay Point -> Paradip",
    "vessel": "Kamsarmax",
    "rate_usd_t": 22.75,
    "change_30d_pct": 11.5
   },
   {
    "route_id": "AUHPT-INPRT",
    "lane": "Hay Point -> Paradip",
    "vessel": "Capesize",
    "rate_usd_t": 14.36,
    "change_30d_pct": 17.2
   },
   {
    "route_id": "AUHPT-INVTZ",
    "lane": "Hay Point -> Visakhapatnam",
    "vessel": "Handysize",
    "rate_usd_t": 34.77,
    "change_30d_pct": 5.4
   },
   {
    "route_id": "AUHPT-INVTZ",
    "lane": "Hay Point -> Visakhapatnam",
    "vessel": "Supramax",
    "rate_usd_t": 22.87,
    "change_30d_pct": 2.4
   },
   {
    "route_id": "AUHPT-INVTZ",
    "lane": "Hay Point -> Visakhapatnam",
    "vessel": "Panamax",
    "rate_usd_t": 21.83,
    "change_30d_pct": 4.4
   },
   {
    "route_id": "AUHPT-INVTZ",
    "lane": "Hay Point -> Visakhapatnam",
    "vessel": "Kamsarmax",
    "rate_usd_t": 22.53,
    "change_30d_pct": 17.7
   },
   {
    "route_id": "AUHPT-INVTZ",
    "lane": "Hay Point -> Visakhapatnam",
    "vessel": "Capesize",
    "rate_usd_t": 13.77,
    "change_30d_pct": 18.7
   },
   {
    "route_id": "AUNTL-INGVR",
    "lane": "Newcastle -> Gangavaram",
    "vessel": "Handysize",
    "rate_usd_t": 36.81,
    "change_30d_pct": 2.7
   },
   {
    "route_id": "AUNTL-INGVR",
    "lane": "Newcastle -> Gangavaram",
    "vessel": "Supramax",
    "rate_usd_t": 25.79,
    "change_30d_pct": 4.7
   },
   {
    "route_id": "AUNTL-INGVR",
    "lane": "Newcastle -> Gangavaram",
    "vessel": "Panamax",
    "rate_usd_t": 24.76,
    "change_30d_pct": 7.0
   },
   {
    "route_id": "AUNTL-INGVR",
    "lane": "Newcastle -> Gangavaram",
    "vessel": "Kamsarmax",
    "rate_usd_t": 24.13,
    "change_30d_pct": 12.7
   },
   {
    "route_id": "AUNTL-INGVR",
    "lane": "Newcastle -> Gangavaram",
    "vessel": "Capesize",
    "rate_usd_t": 15.3,
    "change_30d_pct": 13.1
   },
   {
    "route_id": "AUNTL-INPRT",
    "lane": "Newcastle -> Paradip",
    "vessel": "Handysize",
    "rate_usd_t": 39.38,
    "change_30d_pct": -2.9
   },
   {
    "route_id": "AUNTL-INPRT",
    "lane": "Newcastle -> Paradip",
    "vessel": "Supramax",
    "rate_usd_t": 26.14,
    "change_30d_pct": -4.4
   },
   {
    "route_id": "AUNTL-INPRT",
    "lane": "Newcastle -> Paradip",
    "vessel": "Panamax",
    "rate_usd_t": 25.88,
    "change_30d_pct": 2.0
   },
   {
    "route_id": "AUNTL-INPRT",
    "lane": "Newcastle -> Paradip",
    "vessel": "Kamsarmax",
    "rate_usd_t": 26.0,
    "change_30d_pct": 11.6
   },
   {
    "route_id": "AUNTL-INPRT",
    "lane": "Newcastle -> Paradip",
    "vessel": "Capesize",
    "rate_usd_t": 16.29,
    "change_30d_pct": 12.4
   },
   {
    "route_id": "IDMBR-INHAL",
    "lane": "Muara Berau -> Haldia",
    "vessel": "Handysize",
    "rate_usd_t": 24.81,
    "change_30d_pct": 14.4
   },
   {
    "route_id": "IDMBR-INHAL",
    "lane": "Muara Berau -> Haldia",
    "vessel": "Supramax",
    "rate_usd_t": 20.28,
    "change_30d_pct": 6.2
   },
   {
    "route_id": "IDMBR-INHAL",
    "lane": "Muara Berau -> Haldia",
    "vessel": "Panamax",
    "rate_usd_t": 22.85,
    "change_30d_pct": 18.3
   },
   {
    "route_id": "IDMBR-INHAL",
    "lane": "Muara Berau -> Haldia",
    "vessel": "Kamsarmax",
    "rate_usd_t": 22.4,
    "change_30d_pct": 21.1
   },
   {
    "route_id": "IDMBR-INHAL",
    "lane": "Muara Berau -> Haldia",
    "vessel": "Capesize",
    "rate_usd_t": 16.25,
    "change_30d_pct": 23.6
   },
   {
    "route_id": "IDMBR-INPRT",
    "lane": "Muara Berau -> Paradip",
    "vessel": "Handysize",
    "rate_usd_t": 19.76,
    "change_30d_pct": 7.7
   },
   {
    "route_id": "IDMBR-INPRT",
    "lane": "Muara Berau -> Paradip",
    "vessel": "Supramax",
    "rate_usd_t": 12.68,
    "change_30d_pct": 0.8
   },
   {
    "route_id": "IDMBR-INPRT",
    "lane": "Muara Berau -> Paradip",
    "vessel": "Panamax",
    "rate_usd_t": 12.76,
    "change_30d_pct": 8.6
   },
   {
    "route_id": "IDMBR-INPRT",
    "lane": "Muara Berau -> Paradip",
    "vessel": "Kamsarmax",
    "rate_usd_t": 12.06,
    "change_30d_pct": 9.9
   },
   {
    "route_id": "IDMBR-INPRT",
    "lane": "Muara Berau -> Paradip",
    "vessel": "Capesize",
    "rate_usd_t": 8.22,
    "change_30d_pct": 20.0
   },
   {
    "route_id": "IDMBR-INSAN",
    "lane": "Muara Berau -> Sagar/Sandheads",
    "vessel": "Handysize",
    "rate_usd_t": 22.09,
    "change_30d_pct": -0.6
   },
   {
    "route_id": "IDMBR-INSAN",
    "lane": "Muara Berau -> Sagar/Sandheads",
    "vessel": "Supramax",
    "rate_usd_t": 17.69,
    "change_30d_pct": -2.9
   },
   {
    "route_id": "IDMBR-INSAN",
    "lane": "Muara Berau -> Sagar/Sandheads",
    "vessel": "Panamax",
    "rate_usd_t": 19.11,
    "change_30d_pct": 1.7
   },
   {
    "route_id": "IDMBR-INSAN",
    "lane": "Muara Berau -> Sagar/Sandheads",
    "vessel": "Kamsarmax",
    "rate_usd_t": 19.19,
    "change_30d_pct": 7.3
   },
   {
    "route_id": "IDMBR-INSAN",
    "lane": "Muara Berau -> Sagar/Sandheads",
    "vessel": "Capesize",
    "rate_usd_t": 14.13,
    "change_30d_pct": 10.1
   },
   {
    "route_id": "IDMBR-INVTZ",
    "lane": "Muara Berau -> Visakhapatnam",
    "vessel": "Handysize",
    "rate_usd_t": 16.97,
    "change_30d_pct": 3.3
   },
   {
    "route_id": "IDMBR-INVTZ",
    "lane": "Muara Berau -> Visakhapatnam",
    "vessel": "Supramax",
    "rate_usd_t": 11.33,
    "change_30d_pct": -0.1
   },
   {
    "route_id": "IDMBR-INVTZ",
    "lane": "Muara Berau -> Visakhapatnam",
    "vessel": "Panamax",
    "rate_usd_t": 12.02,
    "change_30d_pct": 12.6
   },
   {
    "route_id": "IDMBR-INVTZ",
    "lane": "Muara Berau -> Visakhapatnam",
    "vessel": "Kamsarmax",
    "rate_usd_t": 10.85,
    "change_30d_pct": 9.3
   },
   {
    "route_id": "IDMBR-INVTZ",
    "lane": "Muara Berau -> Visakhapatnam",
    "vessel": "Capesize",
    "rate_usd_t": 7.19,
    "change_30d_pct": 16.3
   },
   {
    "route_id": "IDTBN-INGPR",
    "lane": "Taboneo -> Gopalpur",
    "vessel": "Handysize",
    "rate_usd_t": 19.18,
    "change_30d_pct": 4.9
   },
   {
    "route_id": "IDTBN-INGPR",
    "lane": "Taboneo -> Gopalpur",
    "vessel": "Supramax",
    "rate_usd_t": 12.85,
    "change_30d_pct": -0.5
   },
   {
    "route_id": "IDTBN-INGPR",
    "lane": "Taboneo -> Gopalpur",
    "vessel": "Panamax",
    "rate_usd_t": 12.39,
    "change_30d_pct": 0.8
   },
   {
    "route_id": "IDTBN-INGPR",
    "lane": "Taboneo -> Gopalpur",
    "vessel": "Kamsarmax",
    "rate_usd_t": 12.76,
    "change_30d_pct": 9.6
   },
   {
    "route_id": "IDTBN-INGPR",
    "lane": "Taboneo -> Gopalpur",
    "vessel": "Capesize",
    "rate_usd_t": 9.69,
    "change_30d_pct": 15.8
   },
   {
    "route_id": "MZBEW-INVTZ",
    "lane": "Beira -> Visakhapatnam",
    "vessel": "Handysize",
    "rate_usd_t": 31.82,
    "change_30d_pct": 0.1
   },
   {
    "route_id": "MZBEW-INVTZ",
    "lane": "Beira -> Visakhapatnam",
    "vessel": "Supramax",
    "rate_usd_t": 21.52,
    "change_30d_pct": -7.2
   },
   {
    "route_id": "MZBEW-INVTZ",
    "lane": "Beira -> Visakhapatnam",
    "vessel": "Panamax",
    "rate_usd_t": 24.46,
    "change_30d_pct": 1.9
   },
   {
    "route_id": "MZBEW-INVTZ",
    "lane": "Beira -> Visakhapatnam",
    "vessel": "Kamsarmax",
    "rate_usd_t": 24.04,
    "change_30d_pct": 7.1
   },
   {
    "route_id": "MZMPM-INPRT",
    "lane": "Maputo -> Paradip",
    "vessel": "Handysize",
    "rate_usd_t": 31.16,
    "change_30d_pct": -0.2
   },
   {
    "route_id": "MZMPM-INPRT",
    "lane": "Maputo -> Paradip",
    "vessel": "Supramax",
    "rate_usd_t": 22.33,
    "change_30d_pct": 2.1
   },
   {
    "route_id": "MZMPM-INPRT",
    "lane": "Maputo -> Paradip",
    "vessel": "Panamax",
    "rate_usd_t": 21.65,
    "change_30d_pct": 5.6
   },
   {
    "route_id": "MZMPM-INPRT",
    "lane": "Maputo -> Paradip",
    "vessel": "Kamsarmax",
    "rate_usd_t": 21.73,
    "change_30d_pct": 11.7
   },
   {
    "route_id": "MZMPM-INPRT",
    "lane": "Maputo -> Paradip",
    "vessel": "Capesize",
    "rate_usd_t": 15.42,
    "change_30d_pct": 11.7
   },
   {
    "route_id": "RUULU-INPRT",
    "lane": "Ust-Luga -> Paradip",
    "vessel": "Handysize",
    "rate_usd_t": 67.63,
    "change_30d_pct": 5.1
   },
   {
    "route_id": "RUULU-INPRT",
    "lane": "Ust-Luga -> Paradip",
    "vessel": "Supramax",
    "rate_usd_t": 48.22,
    "change_30d_pct": 2.2
   },
   {
    "route_id": "RUULU-INPRT",
    "lane": "Ust-Luga -> Paradip",
    "vessel": "Panamax",
    "rate_usd_t": 46.19,
    "change_30d_pct": 4.3
   },
   {
    "route_id": "RUULU-INPRT",
    "lane": "Ust-Luga -> Paradip",
    "vessel": "Kamsarmax",
    "rate_usd_t": 46.12,
    "change_30d_pct": 10.6
   },
   {
    "route_id": "RUULU-INPRT",
    "lane": "Ust-Luga -> Paradip",
    "vessel": "Capesize",
    "rate_usd_t": 37.02,
    "change_30d_pct": 11.4
   },
   {
    "route_id": "RUVYP-INVTZ",
    "lane": "Vostochny -> Visakhapatnam",
    "vessel": "Handysize",
    "rate_usd_t": 37.06,
    "change_30d_pct": 5.1
   },
   {
    "route_id": "RUVYP-INVTZ",
    "lane": "Vostochny -> Visakhapatnam",
    "vessel": "Supramax",
    "rate_usd_t": 24.43,
    "change_30d_pct": 1.7
   },
   {
    "route_id": "RUVYP-INVTZ",
    "lane": "Vostochny -> Visakhapatnam",
    "vessel": "Panamax",
    "rate_usd_t": 25.26,
    "change_30d_pct": 9.7
   },
   {
    "route_id": "RUVYP-INVTZ",
    "lane": "Vostochny -> Visakhapatnam",
    "vessel": "Kamsarmax",
    "rate_usd_t": 24.47,
    "change_30d_pct": 19.1
   },
   {
    "route_id": "RUVYP-INVTZ",
    "lane": "Vostochny -> Visakhapatnam",
    "vessel": "Capesize",
    "rate_usd_t": 15.35,
    "change_30d_pct": 19.2
   },
   {
    "route_id": "USBAL-INVTZ",
    "lane": "Baltimore -> Visakhapatnam",
    "vessel": "Handysize",
    "rate_usd_t": 79.24,
    "change_30d_pct": 1.2
   },
   {
    "route_id": "USBAL-INVTZ",
    "lane": "Baltimore -> Visakhapatnam",
    "vessel": "Supramax",
    "rate_usd_t": 54.67,
    "change_30d_pct": -0.8
   },
   {
    "route_id": "USBAL-INVTZ",
    "lane": "Baltimore -> Visakhapatnam",
    "vessel": "Panamax",
    "rate_usd_t": 51.63,
    "change_30d_pct": 4.9
   },
   {
    "route_id": "USBAL-INVTZ",
    "lane": "Baltimore -> Visakhapatnam",
    "vessel": "Kamsarmax",
    "rate_usd_t": 50.52,
    "change_30d_pct": 10.6
   },
   {
    "route_id": "USBAL-INVTZ",
    "lane": "Baltimore -> Visakhapatnam",
    "vessel": "Capesize",
    "rate_usd_t": 34.64,
    "change_30d_pct": 17.6
   },
   {
    "route_id": "USORF-INPRT",
    "lane": "Hampton Roads -> Paradip",
    "vessel": "Handysize",
    "rate_usd_t": 83.38,
    "change_30d_pct": 10.0
   },
   {
    "route_id": "USORF-INPRT",
    "lane": "Hampton Roads -> Paradip",
    "vessel": "Supramax",
    "rate_usd_t": 53.27,
    "change_30d_pct": 3.8
   },
   {
    "route_id": "USORF-INPRT",
    "lane": "Hampton Roads -> Paradip",
    "vessel": "Panamax",
    "rate_usd_t": 53.57,
    "change_30d_pct": 10.0
   },
   {
    "route_id": "USORF-INPRT",
    "lane": "Hampton Roads -> Paradip",
    "vessel": "Kamsarmax",
    "rate_usd_t": 51.78,
    "change_30d_pct": 15.2
   },
   {
    "route_id": "USORF-INPRT",
    "lane": "Hampton Roads -> Paradip",
    "vessel": "Capesize",
    "rate_usd_t": 33.22,
    "change_30d_pct": 9.5
   }
  ]
 },
 "scenario": {
  "request": {
   "origin": "AUHPT",
   "destination": "INPRT",
   "commodity": "Thermal Coal",
   "cargo_volume_t": 600000.0,
   "contract_duration_months": 6,
   "laycan_month": 11,
   "vessel": null,
   "forecast_horizon_days": 120
  },
  "resolved": {
   "route_id": "AUHPT-INPRT",
   "vessel": "Capesize",
   "lane": "Hay Point -> Paradip",
   "has_market_series": true
  },
  "vessel_optimisation": {
   "route": {
    "id": "AUHPT-INPRT",
    "lane": "Hay Point -> Paradip",
    "origin": {
     "code": "AUHPT",
     "name": "Hay Point",
     "country": "Australia",
     "region": "Australia"
    },
    "destination": {
     "code": "INPRT",
     "name": "Paradip",
     "region": "India-EastCoast"
    },
    "distance_nm": 6300,
    "canal": "none",
    "seasonality_profile": "monsoon"
   },
   "cargo": {
    "commodity": "Thermal Coal",
    "volume_t": 600000.0,
    "laycan_month": 11
   },
   "constraints": {
    "load_port": {
     "code": "AUHPT",
     "name": "Hay Point",
     "country": "Australia",
     "region": "Australia",
     "role": "load",
     "lat": -21.28,
     "lon": 149.3,
     "max_draft_m": 17.4,
     "max_loa_m": 300,
     "max_beam_m": 50,
     "max_dwt": 200000,
     "berth_handling_tph": 5800,
     "congestion_base_days": 1.4,
     "transload": false,
     "notes": "Metallurgical + thermal coal; two of the world's largest coal terminals (DBCT + HPCT).",
     "source": "nqbp.com.au ; ballastmarkets.com/ports/hay-point",
     "handling_tpd": 139200
    },
    "discharge_port": {
     "code": "INPRT",
     "name": "Paradip",
     "country": "India",
     "region": "India-EastCoast",
     "role": "discharge",
     "lat": 20.26,
     "lon": 86.67,
     "max_draft_m": 16.5,
     "max_loa_m": 300,
     "max_beam_m": 46,
     "max_dwt": 175000,
     "berth_handling_tph": 1600,
     "congestion_base_days": 2.2,
     "transload": false,
     "notes": "Mechanised coal berths; PPA handles Capesize (draft-limited to ~150k t intake at 16.5 m).",
     "source": "paradipport.gov.in/berth_spec",
     "handling_tpd": 38400
    }
   },
   "recommendation": {
    "vessel": "Capesize",
    "why": "Capesize lifts 153,396 t/parcel at 16.5 m governing draft (91% deadweight utilisation); lowest delivered cost/t among feasible classes after pricing expected port waiting time.",
    "delivered_cost_usd_per_t": 14.6,
    "shipments_required": 4,
    "estimated_campaign_cost_usd": 8761878,
    "potential_saving_vs_worst_feasible_usd": 13288285
   },
   "options": [
    {
     "vessel": "Capesize",
     "feasible": true,
     "reasons": [],
     "intake_t": 153396,
     "shipments_required": 4,
     "governing_draft_m": 16.5,
     "draft_utilisation_pct": 90.7,
     "voyage_days_roundtrip": 47.5,
     "load_days": 1.1,
     "disch_days": 3.99,
     "freight_usd_per_t": 14.36,
     "expected_wait_days": 3.73,
     "weather_delay_days": 0.0,
     "demurrage_risk_usd_per_t": 0.41,
     "delivered_cost_usd_per_t": 14.6,
     "total_campaign_cost_usd": 8761878,
     "campaign_lead_time_days": 101.1,
     "co2_kt_campaign": 21.7,
     "co2_g_per_t_nm": 5.6,
     "score": 18.784
    },
    {
     "vessel": "Kamsarmax",
     "feasible": true,
     "reasons": [],
     "intake_t": 77080,
     "shipments_required": 8,
     "governing_draft_m": 14.4,
     "draft_utilisation_pct": 100.0,
     "voyage_days_roundtrip": 44.2,
     "load_days": 0.55,
     "disch_days": 2.01,
     "freight_usd_per_t": 22.75,
     "expected_wait_days": 3.73,
     "weather_delay_days": 0.0,
     "demurrage_risk_usd_per_t": 0.79,
     "delivered_cost_usd_per_t": 23.22,
     "total_campaign_cost_usd": 13933448,
     "campaign_lead_time_days": 156.2,
     "co2_kt_campaign": 31.1,
     "co2_g_per_t_nm": 8.0,
     "score": 30.106
    },
    {
     "vessel": "Panamax",
     "feasible": true,
     "reasons": [],
     "intake_t": 71440,
     "shipments_required": 9,
     "governing_draft_m": 14.1,
     "draft_utilisation_pct": 100.0,
     "voyage_days_roundtrip": 44.0,
     "load_days": 0.51,
     "disch_days": 1.86,
     "freight_usd_per_t": 24.37,
     "expected_wait_days": 3.73,
     "weather_delay_days": 0.0,
     "demurrage_risk_usd_per_t": 0.83,
     "delivered_cost_usd_per_t": 24.87,
     "total_campaign_cost_usd": 14919884,
     "campaign_lead_time_days": 171.0,
     "co2_kt_campaign": 33.9,
     "co2_g_per_t_nm": 8.4,
     "score": 32.445
    },
    {
     "vessel": "Supramax",
     "feasible": true,
     "reasons": [],
     "intake_t": 54520,
     "shipments_required": 12,
     "governing_draft_m": 12.8,
     "draft_utilisation_pct": 100.0,
     "voyage_days_roundtrip": 43.4,
     "load_days": 0.39,
     "disch_days": 1.42,
     "freight_usd_per_t": 24.35,
     "expected_wait_days": 3.73,
     "weather_delay_days": 0.0,
     "demurrage_risk_usd_per_t": 0.7,
     "delivered_cost_usd_per_t": 24.77,
     "total_campaign_cost_usd": 14862455,
     "campaign_lead_time_days": 214.5,
     "co2_kt_campaign": 39.1,
     "co2_g_per_t_nm": 9.5,
     "score": 34.419
    },
    {
     "vessel": "Handysize",
     "feasible": true,
     "reasons": [],
     "intake_t": 30080,
     "shipments_required": 20,
     "governing_draft_m": 10.0,
     "draft_utilisation_pct": 100.0,
     "voyage_days_roundtrip": 44.2,
     "load_days": 0.22,
     "disch_days": 0.78,
     "freight_usd_per_t": 35.99,
     "expected_wait_days": 3.73,
     "weather_delay_days": 0.0,
     "demurrage_risk_usd_per_t": 1.27,
     "delivered_cost_usd_per_t": 36.75,
     "total_campaign_cost_usd": 22050163,
     "campaign_lead_time_days": 341.8,
     "co2_kt_campaign": 46.7,
     "co2_g_per_t_nm": 12.3,
     "score": 52.146
    }
   ],
   "robustness": {
    "Capesize": 0.935,
    "Kamsarmax": 0.045,
    "Panamax": 0.013,
    "Supramax": 0.007,
    "Handysize": 0.0
   },
   "emissions": {
    "recommended_kt": 21.7,
    "recommended_g_per_t_nm": 5.6,
    "greenest_feasible": "Capesize",
    "recommended_vs_greenest_pct": 0.0
   },
   "bunker_used_usd_t": 656.7
  },
  "forecast": {
   "route_id": "AUHPT-INPRT",
   "vessel": "Capesize",
   "as_of": "2026-08-31",
   "latest_rate": 14.23,
   "horizon_days": 240,
   "model": "HoltWinters(damped) + SeasonalNaiveDrift ensemble",
   "history": [
    {
     "date": "2024-11-04",
     "rate": 13.81
    },
    {
     "date": "2024-11-11",
     "rate": 14.49
    },
    {
     "date": "2024-11-18",
     "rate": 15.02
    },
    {
     "date": "2024-11-25",
     "rate": 14.69
    },
    {
     "date": "2024-12-02",
     "rate": 14.26
    },
    {
     "date": "2024-12-09",
     "rate": 14.08
    },
    {
     "date": "2024-12-16",
     "rate": 13.74
    },
    {
     "date": "2024-12-23",
     "rate": 12.98
    },
    {
     "date": "2024-12-30",
     "rate": 12.77
    },
    {
     "date": "2025-01-06",
     "rate": 12.13
    },
    {
     "date": "2025-01-13",
     "rate": 11.69
    },
    {
     "date": "2025-01-20",
     "rate": 11.6
    },
    {
     "date": "2025-01-27",
     "rate": 11.72
    },
    {
     "date": "2025-02-03",
     "rate": 11.64
    },
    {
     "date": "2025-02-10",
     "rate": 11.42
    },
    {
     "date": "2025-02-17",
     "rate": 10.96
    },
    {
     "date": "2025-02-24",
     "rate": 10.48
    },
    {
     "date": "2025-03-03",
     "rate": 10.78
    },
    {
     "date": "2025-03-10",
     "rate": 11.39
    },
    {
     "date": "2025-03-17",
     "rate": 11.47
    },
    {
     "date": "2025-03-24",
     "rate": 11.39
    },
    {
     "date": "2025-03-31",
     "rate": 10.84
    },
    {
     "date": "2025-04-07",
     "rate": 10.01
    },
    {
     "date": "2025-04-14",
     "rate": 10.0
    },
    {
     "date": "2025-04-21",
     "rate": 10.18
    },
    {
     "date": "2025-04-28",
     "rate": 10.2
    },
    {
     "date": "2025-05-05",
     "rate": 9.79
    },
    {
     "date": "2025-05-12",
     "rate": 9.59
    },
    {
     "date": "2025-05-19",
     "rate": 10.18
    },
    {
     "date": "2025-05-26",
     "rate": 10.17
    },
    {
     "date": "2025-06-02",
     "rate": 10.06
    },
    {
     "date": "2025-06-09",
     "rate": 9.66
    },
    {
     "date": "2025-06-16",
     "rate": 9.83
    },
    {
     "date": "2025-06-23",
     "rate": 9.22
    },
    {
     "date": "2025-06-30",
     "rate": 8.45
    },
    {
     "date": "2025-07-07",
     "rate": 8.17
    },
    {
     "date": "2025-07-14",
     "rate": 9.39
    },
    {
     "date": "2025-07-21",
     "rate": 10.13
    },
    {
     "date": "2025-07-28",
     "rate": 10.72
    },
    {
     "date": "2025-08-04",
     "rate": 10.58
    },
    {
     "date": "2025-08-11",
     "rate": 10.64
    },
    {
     "date": "2025-08-18",
     "rate": 11.95
    },
    {
     "date": "2025-08-25",
     "rate": 12.18
    },
    {
     "date": "2025-09-01",
     "rate": 12.46
    },
    {
     "date": "2025-09-08",
     "rate": 12.62
    },
    {
     "date": "2025-09-15",
     "rate": 12.54
    },
    {
     "date": "2025-09-22",
     "rate": 12.65
    },
    {
     "date": "2025-09-29",
     "rate": 12.06
    },
    {
     "date": "2025-10-06",
     "rate": 12.35
    },
    {
     "date": "2025-10-13",
     "rate": 13.61
    },
    {
     "date": "2025-10-20",
     "rate": 13.63
    },
    {
     "date": "2025-10-27",
     "rate": 13.36
    },
    {
     "date": "2025-11-03",
     "rate": 13.27
    },
    {
     "date": "2025-11-10",
     "rate": 14.04
    },
    {
     "date": "2025-11-17",
     "rate": 14.83
    },
    {
     "date": "2025-11-24",
     "rate": 15.03
    },
    {
     "date": "2025-12-01",
     "rate": 14.33
    },
    {
     "date": "2025-12-08",
     "rate": 14.0
    },
    {
     "date": "2025-12-15",
     "rate": 13.41
    },
    {
     "date": "2025-12-22",
     "rate": 13.64
    },
    {
     "date": "2025-12-29",
     "rate": 14.11
    },
    {
     "date": "2026-01-05",
     "rate": 13.78
    },
    {
     "date": "2026-01-12",
     "rate": 13.69
    },
    {
     "date": "2026-01-19",
     "rate": 13.91
    },
    {
     "date": "2026-01-26",
     "rate": 14.6
    },
    {
     "date": "2026-02-02",
     "rate": 15.37
    },
    {
     "date": "2026-02-09",
     "rate": 14.95
    },
    {
     "date": "2026-02-16",
     "rate": 15.74
    },
    {
     "date": "2026-02-23",
     "rate": 16.38
    },
    {
     "date": "2026-03-02",
     "rate": 17.45
    },
    {
     "date": "2026-03-09",
     "rate": 16.52
    },
    {
     "date": "2026-03-16",
     "rate": 15.29
    },
    {
     "date": "2026-03-23",
     "rate": 15.41
    },
    {
     "date": "2026-03-30",
     "rate": 16.46
    },
    {
     "date": "2026-04-06",
     "rate": 17.26
    },
    {
     "date": "2026-04-13",
     "rate": 17.58
    },
    {
     "date": "2026-04-20",
     "rate": 17.99
    },
    {
     "date": "2026-04-27",
     "rate": 19.15
    },
    {
     "date": "2026-05-04",
     "rate": 20.39
    },
    {
     "date": "2026-05-11",
     "rate": 20.39
    },
    {
     "date": "2026-05-18",
     "rate": 21.71
    },
    {
     "date": "2026-05-25",
     "rate": 19.94
    },
    {
     "date": "2026-06-01",
     "rate": 19.26
    },
    {
     "date": "2026-06-08",
     "rate": 15.36
    },
    {
     "date": "2026-06-15",
     "rate": 12.67
    },
    {
     "date": "2026-06-22",
     "rate": 11.15
    },
    {
     "date": "2026-06-29",
     "rate": 10.85
    },
    {
     "date": "2026-07-06",
     "rate": 10.91
    },
    {
     "date": "2026-07-13",
     "rate": 11.66
    },
    {
     "date": "2026-07-20",
     "rate": 11.43
    },
    {
     "date": "2026-07-27",
     "rate": 11.43
    },
    {
     "date": "2026-08-03",
     "rate": 12.14
    },
    {
     "date": "2026-08-10",
     "rate": 12.79
    },
    {
     "date": "2026-08-17",
     "rate": 13.26
    },
    {
     "date": "2026-08-24",
     "rate": 13.73
    },
    {
     "date": "2026-08-31",
     "rate": 14.23
    }
   ],
   "forecast": [
    {
     "date": "2026-09-07",
     "mean": 14.61,
     "lo": 12.16,
     "hi": 17.06
    },
    {
     "date": "2026-09-14",
     "mean": 14.87,
     "lo": 11.94,
     "hi": 17.81
    },
    {
     "date": "2026-09-21",
     "mean": 15.26,
     "lo": 11.95,
     "hi": 18.57
    },
    {
     "date": "2026-09-28",
     "mean": 15.16,
     "lo": 11.54,
     "hi": 18.79
    },
    {
     "date": "2026-10-05",
     "mean": 15.73,
     "lo": 11.82,
     "hi": 19.63
    },
    {
     "date": "2026-10-12",
     "mean": 16.61,
     "lo": 12.45,
     "hi": 20.76
    },
    {
     "date": "2026-10-19",
     "mean": 16.75,
     "lo": 12.37,
     "hi": 21.13
    },
    {
     "date": "2026-10-26",
     "mean": 16.64,
     "lo": 12.04,
     "hi": 21.23
    },
    {
     "date": "2026-11-02",
     "mean": 16.43,
     "lo": 11.63,
     "hi": 21.22
    },
    {
     "date": "2026-11-09",
     "mean": 17.14,
     "lo": 12.16,
     "hi": 22.13
    },
    {
     "date": "2026-11-16",
     "mean": 17.81,
     "lo": 12.64,
     "hi": 22.98
    },
    {
     "date": "2026-11-23",
     "mean": 18.03,
     "lo": 12.69,
     "hi": 23.37
    },
    {
     "date": "2026-11-30",
     "mean": 17.75,
     "lo": 12.24,
     "hi": 23.25
    },
    {
     "date": "2026-12-07",
     "mean": 17.23,
     "lo": 11.57,
     "hi": 22.9
    },
    {
     "date": "2026-12-14",
     "mean": 16.96,
     "lo": 11.14,
     "hi": 22.78
    },
    {
     "date": "2026-12-21",
     "mean": 17.08,
     "lo": 11.11,
     "hi": 23.05
    },
    {
     "date": "2026-12-28",
     "mean": 17.48,
     "lo": 11.37,
     "hi": 23.59
    },
    {
     "date": "2027-01-04",
     "mean": 16.75,
     "lo": 10.5,
     "hi": 23.01
    },
    {
     "date": "2027-01-11",
     "mean": 16.4,
     "lo": 10.01,
     "hi": 22.79
    },
    {
     "date": "2027-01-18",
     "mean": 16.65,
     "lo": 10.13,
     "hi": 23.17
    },
    {
     "date": "2027-01-25",
     "mean": 17.24,
     "lo": 10.59,
     "hi": 23.9
    },
    {
     "date": "2027-02-01",
     "mean": 17.81,
     "lo": 11.04,
     "hi": 24.59
    },
    {
     "date": "2027-02-08",
     "mean": 17.6,
     "lo": 10.7,
     "hi": 24.5
    },
    {
     "date": "2027-02-15",
     "mean": 17.98,
     "lo": 10.96,
     "hi": 25.0
    },
    {
     "date": "2027-02-22",
     "mean": 18.35,
     "lo": 11.21,
     "hi": 25.49
    },
    {
     "date": "2027-03-01",
     "mean": 19.35,
     "lo": 12.09,
     "hi": 26.61
    },
    {
     "date": "2027-03-08",
     "mean": 18.95,
     "lo": 11.58,
     "hi": 26.32
    },
    {
     "date": "2027-03-15",
     "mean": 18.24,
     "lo": 10.76,
     "hi": 25.73
    },
    {
     "date": "2027-03-22",
     "mean": 18.44,
     "lo": 10.85,
     "hi": 26.04
    },
    {
     "date": "2027-03-29",
     "mean": 18.94,
     "lo": 11.24,
     "hi": 26.65
    },
    {
     "date": "2027-04-05",
     "mean": 19.29,
     "lo": 11.49,
     "hi": 27.1
    },
    {
     "date": "2027-04-12",
     "mean": 19.37,
     "lo": 11.46,
     "hi": 27.28
    },
    {
     "date": "2027-04-19",
     "mean": 19.56,
     "lo": 11.54,
     "hi": 27.57
    },
    {
     "date": "2027-04-26",
     "mean": 20.09,
     "lo": 11.97,
     "hi": 28.2
    }
   ],
   "monthly": [
    {
     "month": "2026-09",
     "mean": 14.98,
     "lo": 11.9,
     "hi": 18.06
    },
    {
     "month": "2026-10",
     "mean": 16.43,
     "lo": 12.17,
     "hi": 20.69
    },
    {
     "month": "2026-11",
     "mean": 17.43,
     "lo": 12.27,
     "hi": 22.59
    },
    {
     "month": "2026-12",
     "mean": 17.19,
     "lo": 11.3,
     "hi": 23.08
    },
    {
     "month": "2027-01",
     "mean": 16.76,
     "lo": 10.31,
     "hi": 23.22
    },
    {
     "month": "2027-02",
     "mean": 17.94,
     "lo": 10.98,
     "hi": 24.9
    },
    {
     "month": "2027-03",
     "mean": 18.79,
     "lo": 11.31,
     "hi": 26.27
    },
    {
     "month": "2027-04",
     "mean": 19.58,
     "lo": 11.61,
     "hi": 27.54
    }
   ],
   "expected_rate": {
    "next_30d": 14.98,
    "next_60d": 15.78,
    "next_90d": 16.37
   },
   "current_percentile_12m": 54.0,
   "seasonal_factor_now": 0.97,
   "backtest": {
    "folds": 1,
    "fold_horizon_weeks": 34,
    "ensemble": {
     "mape": 19.61,
     "rmse": 2.73,
     "bias": 2.16
    },
    "ensemble_weight_holt_winters": 0.62,
    "models": {
     "holt_winters": {
      "mape": 17.95,
      "rmse": 2.49,
      "bias": 2.1
     },
     "seasonal_naive": {
      "mape": 23.03,
      "rmse": 3.24,
      "bias": 2.26
     }
    },
    "baselines": {
     "random_walk": {
      "mape": 22.89,
      "rmse": 3.39,
      "bias": 2.81
     },
     "seasonal_naive": {
      "mape": 16.26,
      "rmse": 2.49,
      "bias": -0.4
     }
    },
    "skill_vs_random_walk_pct": 14.3
   },
   "drivers": {
    "bunker_corr": 0.6,
    "tce_corr": 0.5,
    "congestion_load_corr": 0.2,
    "congestion_disch_corr": 0.35,
    "commodity_index_corr": -0.17,
    "trend_pct_last_30d": 17.2
   }
  },
  "timing": {
   "route_id": "AUHPT-INPRT",
   "vessel": "Capesize",
   "as_of": "2026-08-31",
   "current_rate_usd_t": 14.36,
   "annualised_volatility_pct": 36.1,
   "forecast_slope_over_contract_pct": 32.4,
   "entry_timing": {
    "action": "FIX_NOW",
    "window": {
     "from": "2026-09-07",
     "to": "2026-09-14",
     "weeks_out": 0
    },
    "expected_saving_usd": 0,
    "rationale": "Forecast offers no material near-term dip (or the downside risk of waiting outweighs it); securing tonnage now is preferable."
   },
   "charter_structure": {
    "recommendation": "PERIOD",
    "contract_duration_months": 6,
    "spot": {
     "expected_rate_usd_t": 16.91,
     "expected_cost_usd": 10146231,
     "cost_std_usd": 556401
    },
    "period": {
     "indicative_rate_usd_t": 16.23,
     "expected_cost_usd": 9740268,
     "cost_std_usd": 83460,
     "liquidity_premium_pct": 3.0
    },
    "rationale": "A 6-month period charter at ~$16.2/t has a lower risk-adjusted cost than rolling spot (exp. $16.9/t but \u00b1$0.9/t). Upward-sloping forecast favours locking in. Removes exposure to freight spikes over the cover period."
   },
   "vs_reactive_spot_approach": {
    "reactive_expected_cost_usd": 10146231,
    "reactive_cost_std_usd": 556401,
    "recommended_expected_cost_usd": 9740268,
    "recommended_cost_std_usd": 83460,
    "expected_saving_usd": 405962,
    "expected_saving_pct": 4.0,
    "risk_reduction_usd": 472941,
    "flat_rate_reference_cost_usd": 8613079,
    "note": "Reactive = rolling single spot voyages over the cover period (exposed to the forecast path). 'flat_rate_reference' is only what today's rate held constant would cost -- shown for context, not an achievable plan."
   },
   "forecast_preview": [
    {
     "month": "2026-09",
     "mean": 14.98,
     "lo": 11.9,
     "hi": 18.06
    },
    {
     "month": "2026-10",
     "mean": 16.43,
     "lo": 12.17,
     "hi": 20.69
    },
    {
     "month": "2026-11",
     "mean": 17.43,
     "lo": 12.27,
     "hi": 22.59
    },
    {
     "month": "2026-12",
     "mean": 17.19,
     "lo": 11.3,
     "hi": 23.08
    },
    {
     "month": "2027-01",
     "mean": 16.76,
     "lo": 10.31,
     "hi": 23.22
    },
    {
     "month": "2027-02",
     "mean": 17.94,
     "lo": 10.98,
     "hi": 24.9
    },
    {
     "month": "2027-03",
     "mean": 18.79,
     "lo": 11.31,
     "hi": 26.27
    },
    {
     "month": "2027-04",
     "mean": 19.58,
     "lo": 11.61,
     "hi": 27.54
    }
   ],
   "backtest": {
    "folds": 1,
    "fold_horizon_weeks": 34,
    "ensemble": {
     "mape": 19.61,
     "rmse": 2.73,
     "bias": 2.16
    },
    "ensemble_weight_holt_winters": 0.62,
    "models": {
     "holt_winters": {
      "mape": 17.95,
      "rmse": 2.49,
      "bias": 2.1
     },
     "seasonal_naive": {
      "mape": 23.03,
      "rmse": 3.24,
      "bias": 2.26
     }
    },
    "baselines": {
     "random_walk": {
      "mape": 22.89,
      "rmse": 3.39,
      "bias": 2.81
     },
     "seasonal_naive": {
      "mape": 16.26,
      "rmse": 2.49,
      "bias": -0.4
     }
    },
    "skill_vs_random_walk_pct": 14.3
   }
  },
  "idle_outlook": {
   "route_id": "AUHPT-INPRT",
   "vessel": "Capesize",
   "lane": "Hay Point -> Paradip",
   "idle_risk_index": 12.0,
   "estimated_idle_days_next_12w": 7.8,
   "components": {
    "demand_pressure": 3.0,
    "congestion_pressure": 0.0,
    "monsoon_pressure": 42.0
   },
   "soft_demand_weeks": [
    {
     "week": "2026-09-01",
     "seasonal_factor": 0.97
    },
    {
     "week": "2026-09-08",
     "seasonal_factor": 0.97
    },
    {
     "week": "2026-09-15",
     "seasonal_factor": 0.97
    },
    {
     "week": "2026-09-22",
     "seasonal_factor": 0.97
    },
    {
     "week": "2026-09-29",
     "seasonal_factor": 0.97
    }
   ],
   "discharge_wait_days_now": 2.13,
   "discharge_wait_days_year_avg": 2.55,
   "alternative_lanes": [
    {
     "route_id": "IDTBN-INGPR",
     "lane": "Taboneo -> Gopalpur",
     "near_term_demand_factor": 0.996,
     "discharge_wait_days": 1.24,
     "demand_weight": 1.0
    },
    {
     "route_id": "AUDBY-INDHA",
     "lane": "Dalrymple Bay -> Dhamra",
     "near_term_demand_factor": 0.996,
     "discharge_wait_days": 2.01,
     "demand_weight": 1.0
    },
    {
     "route_id": "AUNTL-INGVR",
     "lane": "Newcastle -> Gangavaram",
     "near_term_demand_factor": 0.996,
     "discharge_wait_days": 2.74,
     "demand_weight": 1.0
    },
    {
     "route_id": "AUHPT-INVTZ",
     "lane": "Hay Point -> Visakhapatnam",
     "near_term_demand_factor": 0.996,
     "discharge_wait_days": 2.87,
     "demand_weight": 1.2
    }
   ],
   "mitigation": [
    "5 soft-demand week(s) ahead on this lane -- avoid ballasting open into Paradip; delay positioning or pre-fix a period cargo.",
    "5 of the next 12 weeks fall in the SW monsoon -- build +1-2 weather days into laycans for East Coast discharge and prefer geared tonnage where berths congest."
   ]
  },
  "decision_backtest": {
   "strategies": {
    "always_spot": {
     "avg_usd_t": 12.93,
     "volatility_usd_t": 1.92,
     "worst_usd_t": 15.99
    },
    "always_period": {
     "avg_usd_t": 12.36,
     "volatility_usd_t": 1.61,
     "worst_usd_t": 14.33
    },
    "timed_cover": {
     "avg_usd_t": 12.59,
     "volatility_usd_t": 1.71,
     "worst_usd_t": 15.99
    }
   },
   "summary": {
    "timed_vs_spot_cost_pct": 2.6,
    "timed_vs_spot_volatility_pct": 11.1,
    "period_vs_spot_volatility_pct": 16.2,
    "worst_period_spot_usd_t": 15.99,
    "worst_period_timed_usd_t": 15.99,
    "max_spike_avoided_usd_t": 2.35,
    "period_locks": 1,
    "spot_periods": 6,
    "timely_locks": 1
   },
   "decision_points": 7
  },
  "weather": {
   "expected_delay_days_16d": 0.0,
   "high_wind_days": 0,
   "heavy_rain_days": 0
  },
  "risk_alerts": {
   "scoped": [],
   "all_count": 1,
   "severity_counts": {
    "medium": 1
   }
  }
 }
};
