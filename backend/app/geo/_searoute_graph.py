"""A compact maritime waypoint graph for land-avoiding route estimation.

This is a deliberately small hand-built network (~90 nodes) covering the world's
canals, straits, capes and ocean crossings used by dry-bulk trades. Dijkstra
over it produces plausibly-kinked ocean routes through the *correct* chokepoints
(Suez, Panama, Malacca, Good Hope, Gibraltar, ...) without a heavy GIS
dependency.

It is an estimate: leg distances are within a few percent of routed distances on
the major lanes, less so on obscure ones. ``searoute-py`` (MIT, a ~100k-edge
network) is a drop-in precision upgrade -- see ``app/geo/searoute.py``.

Coordinates are (lat, lon).
"""

from __future__ import annotations

NODES: dict[str, tuple[float, float]] = {
    # --- Mediterranean / Black Sea / Suez ---
    "GIBRALTAR": (35.95, -5.60),
    "W_MED_WPT": (37.5, 4.0),
    "SICILY_WPT": (37.5, 12.0),
    "E_MED_WPT": (34.0, 24.0),
    "AEGEAN_WPT": (38.0, 25.0),
    "DARDANELLES": (40.2, 26.4),
    "BOSPHORUS": (41.2, 29.1),
    "BLACK_SEA_WPT": (43.5, 33.0),
    "SUEZ_N": (31.3, 32.35),
    "SUEZ_S": (29.2, 32.6),
    # --- Red Sea / Gulf of Aden / Arabian Sea / Gulf ---
    "RED_SEA_WPT": (20.0, 38.5),
    "BAB_EL_MANDEB": (12.6, 43.4),
    "GULF_OF_ADEN_WPT": (12.5, 47.5),
    "SOCOTRA_WPT": (12.0, 54.0),
    "ARABIAN_SEA_WPT": (14.0, 62.0),
    "HORMUZ": (26.0, 56.6),
    "GULF_WPT": (27.0, 51.5),
    # --- Indian Ocean / South Asia ---
    "MID_INDIAN_WPT": (8.0, 72.5),
    "SRI_LANKA_S": (5.4, 80.6),
    "BAY_OF_BENGAL_WPT": (10.0, 85.0),
    "ANDAMAN_WPT": (6.0, 92.0),
    "S_INDIAN_OCEAN_WPT": (-30.0, 65.0),
    "MADAGASCAR_E_WPT": (-25.0, 50.0),
    "MOZ_CHANNEL_N": (-12.0, 42.0),
    "MOZ_CHANNEL_S": (-26.0, 37.0),
    # --- SE Asia / Malacca / archipelago ---
    "MALACCA_NW": (5.6, 95.4),
    "MALACCA_SE": (1.3, 104.1),
    "SUNDA": (-6.0, 105.6),
    "LOMBOK": (-8.8, 115.8),
    "JAVA_SEA_WPT": (-5.0, 112.0),
    "SCS_S_WPT": (3.0, 106.0),
    "SCS_WPT": (14.0, 113.0),
    "CELEBES_WPT": (2.0, 122.5),
    "SULU_WPT": (8.0, 120.0),
    "MAKASSAR_WPT": (-3.0, 118.0),
    "ARAFURA_WPT": (-9.0, 133.0),
    "TORRES": (-10.4, 142.2),
    # --- East Asia ---
    "LUZON_STRAIT": (20.5, 121.2),
    "TAIWAN_STRAIT": (24.5, 119.6),
    "PHILIPPINE_SEA_WPT": (18.0, 129.0),
    "E_CHINA_SEA_WPT": (30.0, 124.0),
    "YELLOW_SEA_WPT": (34.0, 123.0),
    "BOHAI_WPT": (38.3, 120.6),
    "KOREA_STRAIT": (34.3, 129.2),
    "JAPAN_PACIFIC_WPT": (34.0, 141.5),
    "TSUGARU_WPT": (41.5, 142.0),
    # --- Pacific ---
    "N_PACIFIC_W_WPT": (36.0, 160.0),
    "N_PACIFIC_MID_WPT": (32.0, 180.0),
    "N_PACIFIC_E_WPT": (34.0, -150.0),
    "CENTRAL_PACIFIC_WPT": (2.0, 175.0),
    "HAWAII_WPT": (21.0, -158.0),
    "TAHITI_WPT": (-18.0, -149.0),
    "ALEUTIAN_WPT": (52.0, -172.0),
    "SAN_PEDRO_WPT": (32.5, -124.0),
    "JUAN_DE_FUCA_WPT": (48.2, -127.0),
    "GALAPAGOS_WPT": (-1.0, -92.0),
    "HUMBOLDT_WPT": (-20.0, -75.0),
    "S_PACIFIC_WPT": (-45.0, -95.0),
    "PANAMA_PAC": (7.9, -79.6),
    # --- South America / Cape Horn ---
    "PANAMA_ATL": (9.5, -79.9),
    "CARIBBEAN_WPT": (14.0, -70.0),
    "WINDWARD_PASSAGE": (20.0, -73.8),
    "MONA_PASSAGE": (18.5, -67.9),
    "YUCATAN_WPT": (21.5, -85.5),
    "GULF_OF_MEXICO_WPT": (25.5, -90.0),
    "FLORIDA_STRAIT": (24.5, -80.0),
    "NE_BRAZIL_WPT": (-3.0, -34.0),
    "SE_BRAZIL_WPT": (-24.0, -41.5),
    "PLATE_WPT": (-36.5, -52.0),
    "MAGELLAN_E": (-52.5, -67.5),
    "CAPE_HORN": (-56.5, -67.0),
    # --- Atlantic ---
    "S_ATLANTIC_MID_WPT": (-25.0, -8.0),
    "CAPE_AGULHAS": (-36.0, 20.0),
    "CAPE_TOWN_WPT": (-34.7, 16.5),
    "GULF_OF_GUINEA_WPT": (0.0, 2.0),
    "DAKAR_WPT": (12.0, -19.0),
    "CANARY_WPT": (27.0, -18.0),
    "N_ATLANTIC_MID_WPT": (43.0, -35.0),
    "CAPE_HATTERAS": (35.0, -73.5),
    "NY_APPROACH_WPT": (40.0, -69.5),
    "CABOT_STRAIT": (47.3, -59.8),
    "ST_LAWRENCE_WPT": (49.0, -63.5),
    "GREAT_LAKES_WPT": (45.0, -66.0),
    "FINISTERRE": (43.5, -11.5),
    "BISCAY_WPT": (45.5, -8.5),
    "USHANT": (48.4, -6.8),
    "DOVER": (51.0, 1.6),
    "N_SEA_WPT": (56.5, 2.5),
    "SKAGERRAK": (57.9, 9.3),
    "BALTIC_WPT": (56.5, 18.5),
}

# Undirected edges. Weight (nm) is filled in at import from great-circle distance.
EDGES: list[tuple[str, str]] = [
    # Mediterranean corridor
    ("GIBRALTAR", "W_MED_WPT"), ("W_MED_WPT", "SICILY_WPT"), ("SICILY_WPT", "E_MED_WPT"),
    ("E_MED_WPT", "AEGEAN_WPT"), ("E_MED_WPT", "SUEZ_N"), ("AEGEAN_WPT", "DARDANELLES"),
    ("DARDANELLES", "BOSPHORUS"), ("BOSPHORUS", "BLACK_SEA_WPT"),
    ("W_MED_WPT", "FINISTERRE"), ("GIBRALTAR", "CANARY_WPT"),
    # Suez -> Red Sea -> Indian Ocean
    ("SUEZ_N", "SUEZ_S"), ("SUEZ_S", "RED_SEA_WPT"), ("RED_SEA_WPT", "BAB_EL_MANDEB"),
    ("BAB_EL_MANDEB", "GULF_OF_ADEN_WPT"), ("GULF_OF_ADEN_WPT", "SOCOTRA_WPT"),
    ("SOCOTRA_WPT", "ARABIAN_SEA_WPT"), ("SOCOTRA_WPT", "GULF_OF_ADEN_WPT"),
    # Arabian Sea / Gulf
    ("ARABIAN_SEA_WPT", "HORMUZ"), ("HORMUZ", "GULF_WPT"),
    ("ARABIAN_SEA_WPT", "MID_INDIAN_WPT"), ("ARABIAN_SEA_WPT", "MOZ_CHANNEL_N"),
    # South Asia
    ("MID_INDIAN_WPT", "SRI_LANKA_S"), ("SRI_LANKA_S", "BAY_OF_BENGAL_WPT"),
    ("SRI_LANKA_S", "ANDAMAN_WPT"), ("BAY_OF_BENGAL_WPT", "ANDAMAN_WPT"),
    ("ANDAMAN_WPT", "MALACCA_NW"), ("MID_INDIAN_WPT", "S_INDIAN_OCEAN_WPT"),
    # Malacca / archipelago
    ("MALACCA_NW", "MALACCA_SE"), ("MALACCA_SE", "SCS_S_WPT"), ("MALACCA_SE", "SUNDA"),
    ("SCS_S_WPT", "SCS_WPT"), ("SCS_S_WPT", "JAVA_SEA_WPT"), ("SUNDA", "JAVA_SEA_WPT"),
    ("JAVA_SEA_WPT", "MAKASSAR_WPT"), ("JAVA_SEA_WPT", "LOMBOK"),
    ("MAKASSAR_WPT", "CELEBES_WPT"), ("MAKASSAR_WPT", "ARAFURA_WPT"),
    ("CELEBES_WPT", "SULU_WPT"), ("SULU_WPT", "SCS_WPT"),
    ("ARAFURA_WPT", "TORRES"), ("LOMBOK", "MAKASSAR_WPT"),
    # South China Sea -> East Asia
    ("SCS_WPT", "LUZON_STRAIT"), ("SCS_WPT", "TAIWAN_STRAIT"),
    ("TAIWAN_STRAIT", "E_CHINA_SEA_WPT"), ("LUZON_STRAIT", "PHILIPPINE_SEA_WPT"),
    ("E_CHINA_SEA_WPT", "YELLOW_SEA_WPT"), ("YELLOW_SEA_WPT", "BOHAI_WPT"),
    ("E_CHINA_SEA_WPT", "KOREA_STRAIT"), ("KOREA_STRAIT", "JAPAN_PACIFIC_WPT"),
    ("JAPAN_PACIFIC_WPT", "TSUGARU_WPT"), ("PHILIPPINE_SEA_WPT", "JAPAN_PACIFIC_WPT"),
    ("PHILIPPINE_SEA_WPT", "CELEBES_WPT"),
    # Pacific crossings
    ("JAPAN_PACIFIC_WPT", "N_PACIFIC_W_WPT"), ("TSUGARU_WPT", "N_PACIFIC_W_WPT"),
    ("N_PACIFIC_W_WPT", "N_PACIFIC_MID_WPT"), ("N_PACIFIC_MID_WPT", "N_PACIFIC_E_WPT"),
    ("N_PACIFIC_E_WPT", "SAN_PEDRO_WPT"), ("N_PACIFIC_E_WPT", "JUAN_DE_FUCA_WPT"),
    ("PHILIPPINE_SEA_WPT", "CENTRAL_PACIFIC_WPT"), ("CENTRAL_PACIFIC_WPT", "N_PACIFIC_MID_WPT"),
    ("CENTRAL_PACIFIC_WPT", "GALAPAGOS_WPT"), ("GALAPAGOS_WPT", "PANAMA_PAC"),
    ("GALAPAGOS_WPT", "HUMBOLDT_WPT"), ("SAN_PEDRO_WPT", "PANAMA_PAC"),
    ("HUMBOLDT_WPT", "S_PACIFIC_WPT"), ("S_PACIFIC_WPT", "CAPE_HORN"),
    ("HUMBOLDT_WPT", "MAGELLAN_E"),
    # Pacific: Panama <-> Asia via Hawaii; Chile/Peru <-> Oceania/Asia via the South Pacific
    ("PANAMA_PAC", "HAWAII_WPT"), ("HAWAII_WPT", "SAN_PEDRO_WPT"),
    ("HAWAII_WPT", "N_PACIFIC_E_WPT"), ("HAWAII_WPT", "N_PACIFIC_MID_WPT"),
    ("HAWAII_WPT", "N_PACIFIC_W_WPT"), ("HAWAII_WPT", "CENTRAL_PACIFIC_WPT"),
    ("JUAN_DE_FUCA_WPT", "ALEUTIAN_WPT"), ("ALEUTIAN_WPT", "N_PACIFIC_W_WPT"),
    ("ALEUTIAN_WPT", "TSUGARU_WPT"), ("ALEUTIAN_WPT", "N_PACIFIC_MID_WPT"),
    ("HUMBOLDT_WPT", "TAHITI_WPT"), ("TAHITI_WPT", "CENTRAL_PACIFIC_WPT"),
    ("TAHITI_WPT", "S_PACIFIC_WPT"), ("S_PACIFIC_WPT", "CENTRAL_PACIFIC_WPT"),
    # Panama + Caribbean + US Gulf/East
    ("PANAMA_PAC", "PANAMA_ATL"), ("PANAMA_ATL", "CARIBBEAN_WPT"),
    ("CARIBBEAN_WPT", "WINDWARD_PASSAGE"), ("CARIBBEAN_WPT", "MONA_PASSAGE"),
    ("CARIBBEAN_WPT", "YUCATAN_WPT"), ("WINDWARD_PASSAGE", "FLORIDA_STRAIT"),
    ("YUCATAN_WPT", "GULF_OF_MEXICO_WPT"), ("YUCATAN_WPT", "FLORIDA_STRAIT"),
    ("YUCATAN_WPT", "PANAMA_ATL"),
    ("FLORIDA_STRAIT", "CAPE_HATTERAS"), ("CAPE_HATTERAS", "NY_APPROACH_WPT"),
    ("NY_APPROACH_WPT", "CABOT_STRAIT"), ("CABOT_STRAIT", "ST_LAWRENCE_WPT"),
    ("ST_LAWRENCE_WPT", "GREAT_LAKES_WPT"), ("MONA_PASSAGE", "CARIBBEAN_WPT"),
    ("CARIBBEAN_WPT", "NE_BRAZIL_WPT"),
    # Atlantic
    ("NY_APPROACH_WPT", "N_ATLANTIC_MID_WPT"), ("N_ATLANTIC_MID_WPT", "FINISTERRE"),
    ("N_ATLANTIC_MID_WPT", "CANARY_WPT"), ("CAPE_HATTERAS", "N_ATLANTIC_MID_WPT"),
    ("CANARY_WPT", "FINISTERRE"), ("CANARY_WPT", "DAKAR_WPT"),
    ("DAKAR_WPT", "GULF_OF_GUINEA_WPT"),
    ("DAKAR_WPT", "NE_BRAZIL_WPT"), ("GULF_OF_GUINEA_WPT", "S_ATLANTIC_MID_WPT"),
    ("NE_BRAZIL_WPT", "SE_BRAZIL_WPT"), ("SE_BRAZIL_WPT", "PLATE_WPT"),
    ("SE_BRAZIL_WPT", "S_ATLANTIC_MID_WPT"), ("PLATE_WPT", "MAGELLAN_E"),
    ("PLATE_WPT", "S_ATLANTIC_MID_WPT"), ("MAGELLAN_E", "CAPE_HORN"),
    ("S_ATLANTIC_MID_WPT", "CAPE_TOWN_WPT"), ("CAPE_TOWN_WPT", "CAPE_AGULHAS"),
    ("GULF_OF_GUINEA_WPT", "CAPE_TOWN_WPT"),
    # Southern Africa -> Indian Ocean
    ("CAPE_AGULHAS", "MOZ_CHANNEL_S"), ("CAPE_AGULHAS", "S_INDIAN_OCEAN_WPT"),
    ("MOZ_CHANNEL_S", "MOZ_CHANNEL_N"), ("MOZ_CHANNEL_S", "MADAGASCAR_E_WPT"),
    ("MADAGASCAR_E_WPT", "S_INDIAN_OCEAN_WPT"), ("MADAGASCAR_E_WPT", "MOZ_CHANNEL_N"),
    ("S_INDIAN_OCEAN_WPT", "MID_INDIAN_WPT"),
    # NW Europe / Baltic
    ("FINISTERRE", "BISCAY_WPT"), ("BISCAY_WPT", "USHANT"), ("USHANT", "DOVER"),
    ("DOVER", "N_SEA_WPT"), ("N_SEA_WPT", "SKAGERRAK"), ("SKAGERRAK", "BALTIC_WPT"),
    ("USHANT", "N_ATLANTIC_MID_WPT"),
    # Australia
    ("S_INDIAN_OCEAN_WPT", "CAPE_AGULHAS"),
]

# Australian nodes + edges (added explicitly to keep the list readable)
NODES.update({
    "SW_AUSTRALIA_WPT": (-35.0, 112.0),
    "CAPE_LEEUWIN": (-35.5, 114.5),
    "NW_SHELF_WPT": (-18.0, 116.0),
    "GREAT_AUS_BIGHT_WPT": (-37.0, 132.0),
    "BASS_STRAIT_W": (-39.6, 143.5),
    "BASS_STRAIT_E": (-39.6, 148.5),
    "SE_AUSTRALIA_WPT": (-36.5, 151.5),
    "CORAL_SEA_WPT": (-18.0, 153.5),
    "TASMAN_WPT": (-40.0, 162.0),
    "NZ_N_WPT": (-34.5, 174.5),
    "NZ_S_WPT": (-48.0, 167.0),
})
EDGES += [
    ("S_INDIAN_OCEAN_WPT", "SW_AUSTRALIA_WPT"), ("SW_AUSTRALIA_WPT", "CAPE_LEEUWIN"),
    ("CAPE_LEEUWIN", "NW_SHELF_WPT"), ("NW_SHELF_WPT", "MALACCA_NW"),
    ("NW_SHELF_WPT", "SUNDA"), ("NW_SHELF_WPT", "LOMBOK"), ("NW_SHELF_WPT", "ARAFURA_WPT"),
    ("CAPE_LEEUWIN", "GREAT_AUS_BIGHT_WPT"), ("GREAT_AUS_BIGHT_WPT", "BASS_STRAIT_W"),
    ("BASS_STRAIT_W", "BASS_STRAIT_E"), ("BASS_STRAIT_E", "SE_AUSTRALIA_WPT"),
    ("SE_AUSTRALIA_WPT", "CORAL_SEA_WPT"), ("CORAL_SEA_WPT", "TORRES"),
    ("CORAL_SEA_WPT", "SULU_WPT"), ("CORAL_SEA_WPT", "PHILIPPINE_SEA_WPT"),
    ("SE_AUSTRALIA_WPT", "TASMAN_WPT"), ("TASMAN_WPT", "NZ_N_WPT"),
    ("BASS_STRAIT_E", "NZ_S_WPT"), ("NZ_S_WPT", "NZ_N_WPT"),
    ("TASMAN_WPT", "S_PACIFIC_WPT"), ("NZ_N_WPT", "CENTRAL_PACIFIC_WPT"),
    ("SW_AUSTRALIA_WPT", "S_INDIAN_OCEAN_WPT"),
]

# Each port basin connects to the network at this node.
BASIN_GATEWAY: dict[str, str] = {
    "NW_EUROPE": "N_SEA_WPT",
    "ATLANTIC_IBERIA": "FINISTERRE",
    "BALTIC": "BALTIC_WPT",
    "MEDITERRANEAN": "W_MED_WPT",
    "BLACK_SEA": "BLACK_SEA_WPT",
    "ARABIAN_GULF": "GULF_WPT",
    "ARABIAN_SEA": "ARABIAN_SEA_WPT",
    "RED_SEA": "RED_SEA_WPT",
    "BAY_OF_BENGAL": "BAY_OF_BENGAL_WPT",
    "SE_ASIA": "MALACCA_SE",
    "CHINA_SOUTH": "SCS_WPT",
    "CHINA_NORTH": "YELLOW_SEA_WPT",
    "JAPAN": "KOREA_STRAIT",
    "AUS_WEST": "NW_SHELF_WPT",
    "AUS_EAST": "CORAL_SEA_WPT",
    "NZ": "NZ_N_WPT",
    "SOUTH_AFRICA": "CAPE_TOWN_WPT",
    "EAST_AFRICA": "MOZ_CHANNEL_N",
    "WEST_AFRICA": "GULF_OF_GUINEA_WPT",
    "US_GULF": "GULF_OF_MEXICO_WPT",
    "US_EAST": "CAPE_HATTERAS",
    "GREAT_LAKES": "GREAT_LAKES_WPT",
    "US_WEST": "SAN_PEDRO_WPT",
    "US_NW": "JUAN_DE_FUCA_WPT",
    "CANADA_EAST": "CABOT_STRAIT",
    "CANADA_WEST": "JUAN_DE_FUCA_WPT",
    "BRAZIL_NORTH": "NE_BRAZIL_WPT",
    "BRAZIL_SOUTH": "SE_BRAZIL_WPT",
    "RIVER_PLATE": "PLATE_WPT",
    "LATAM_WEST": "HUMBOLDT_WPT",
    "CARIBBEAN": "CARIBBEAN_WPT",
}
