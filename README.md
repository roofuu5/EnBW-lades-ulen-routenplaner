# EnBW Ladestopp

Web-App: Ziel eingeben, Ladestopp nach X Minuten wählen, passende EnBW-Säule an der Strecke finden und in Google Maps mit Zwischenstopp navigieren.

- Nur EnBW-eigene Säulen (EnBW, EnBW ODR), optional EnBW-Töchter (SMATRICS, naturenergie, PRE). Keine Roaming-Partner.
- Säulenliste (ab 50 kW, Stand 23.10.2026) aus dem Projekt github.com/theomega/enbw-charging-routing.
- Routing: OSRM (routing.openstreetmap.de), Adresssuche: Photon (photon.komoot.io), Restaurants: Overpass API, Karte: OpenStreetMap.
- Schrift Barlow (SIL Open Font License, `fonts/`) und Leaflet 1.9.4 (BSD-2-Clause, `vendor/leaflet/`) liegen im Repo, es wird nichts von Google oder CDNs geladen.
- Privates Werkzeug, nicht für Suchmaschinen freigegeben (noindex). Keine Verbindung zu EnBW.
