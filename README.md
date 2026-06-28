# SkosConnect: Multilingual LOD Importer for QGIS

[![QGIS Version](https://img.shields.io/badge/QGIS-3.0%2B-blue)](https://qgis.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**SkosConnect** is a lightweight QGIS plugin that bridges the gap between controlled vocabularies and geospatial databases. It allows you to import hierarchical concepts directly from an online Skosmos REST API or a local SKOS file into database layers (like **PostgreSQL/PostGIS** or **GeoPackage**).

---

## 🌟 Key Features

* **Dynamic Multilingual Support:** Automatically scans target lookup tables for language fields starting with `pref_` and maps translations dynamically.
* **On-the-Fly Column Setup:** Helper utility to instantly create database columns for languages and Linked Open Data (LOD) authorities.
* **Linked Open Data Enrichment:** Automatically resolves Wikidata entities to fetch, link, and store Getty AAT and German GND URIs.
* **Spatial Geometry Plotting:** Extracts WKT geometries from Lobid-GND and Wikidata APIs, transforms coordinates, and plots them as map features.
* **Multi-Language Descriptions:** Aggregates Wikidata translation summaries as a structured JSON object.
* **Update & Sync Mode:** Keeps database schemas up-to-date by synchronizing coordinates, labels, and links.
* **Hierarchical Nesting:** Links parent-child concept relationships using relational Foreign Keys.

---

## 📖 Wiki & Documentation

For detailed, beginner-friendly instructions, refer to the project Wiki:

1. [**Wiki Home**](docs/Home.md) — Core concepts of controlled vocabularies, SKOS, and lookup normalization.
2. [**Installation & Requirements**](docs/Installation.md) — Step-by-step plugin installation and library dependencies (like `rdflib`).
3. [**Database Setup**](docs/Database-Setup.md) — How to configure target tables in local GeoPackages or PostGIS databases.
4. [**Import Tutorial**](docs/Import-Tutorial.md) — Walkthrough of the user interface and importing vocabulary terms.
5. [**Enrichment & LOD**](docs/Enrichment-and-LOD.md) — Learn about Wikidata, Lobid, spatial transformations, and JSON serialization.
6. [**QGIS Attribute Forms**](docs/QGIS-Integration.md) — How to set up QGIS Value Relation widgets for clean user editing.

---

## ⚡ Quick Start

1. Copy the `SkosConnect` directory into your QGIS plugins path:
   * **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   * **macOS / Linux:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Enable **SkosConnect** in QGIS under **Plugins** ➡️ **Manage and Install Plugins...**
3. Create a target database table containing at least a `uri` column.
4. Open the plugin **🔌 SkosConnect**, select your table, load your vocabulary, select terms, and import!

---

## 📄 License
This project is licensed under the MIT License.
