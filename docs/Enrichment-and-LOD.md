# Enrichment & Linked Open Data (LOD) Features

One of SkosConnect's most powerful capabilities is its ability to dynamically query global authorities (Wikidata and Lobid-GND) at import time to enrich your database with spatial coordinates, multilingual descriptions, and unified mappings.

---

## 🔗 Wikidata, GND, and AAT Links Mapping
Controlled vocabulary concepts often contain `skos:exactMatch` or `skos:closeMatch` elements pointing to Wikidata identifiers (Q-IDs).
When importing:
1. SkosConnect extracts these mappings from the SKOS API or offline file.
2. If a Wikidata mapping exists, the plugin queries the Wikidata API in the background.
3. Using Wikidata claims, it retrieves linked authority IDs:
   * **GND ID (German National Library):** Property `P227`
   * **AAT ID (Getty Art & Architecture Thesaurus):** Property `P1014`
4. If your target database table contains `gnd` or `aat` columns, SkosConnect automatically stores their official URIs:
   * `http://d-nb.info/gnd/{gnd_id}`
   * `http://vocab.getty.edu/aat/{aat_id}`

This connects your local QGIS lookup table directly to international authority records!

---

## 🗺️ Spatial Coordinate Plotting (On-the-Fly Reprojection)
If your target lookup layer is spatial (contains geometries, like a PostGIS Point table or a spatial GeoPackage layer) and you import concepts that refer to geographical entities:
1. SkosConnect fetches coordinates from the Lobid-GND API (which stores high-precision geometries) or Wikidata (Property `P625`).
2. If coordinate points are found, the plugin creates a geometry representation (`QgsPointXY`).
3. If your QGIS target layer is set to a projected system (like UTM, EPSG:25832, or Web Mercator) instead of WGS 84 (EPSG:4326), SkosConnect reprojects the coordinates dynamically on-the-fly using the QGIS Coordinate Transformation Engine.
4. The concept is plotted as a point on your QGIS map!

---

## 📝 Multilingual JSON Descriptions
If your target table contains the `wikidata_desc` column:
1. SkosConnect queries the Wikidata entity data for description translations in common languages (`de`, `en`, `fr`, `es`, `la`).
2. It aggregates these descriptions into a single JSON object:
   ```json
   {
     "de": "Epoche der Menschheitsgeschichte, die durch die Nutzung von Bronze geprägt ist.",
     "en": "Archaeological period characterized by the use of bronze.",
     "fr": "Période de la Protohistoire caractérisée par l'usage du bronze."
   }
   ```
3. It writes this string directly to the `wikidata_desc` column. This enables multi-language tooltip rendering, descriptive listings, or searchable cards in web-mapping frontends.
