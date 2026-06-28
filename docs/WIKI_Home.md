# SkosConnect QGIS Plugin Wiki

Welcome to the official Wiki for the **SkosConnect** QGIS Plugin. This guide is designed to help researchers, archaeologists, geographers, and database administrators of all skill levels (including complete beginners) understand, set up, and get the most out of SkosConnect.

---

## 📖 Table of Contents
1. [Introduction to Core Concepts](#-1-introduction-to-core-concepts)
   * [What is a Controlled Vocabulary?](#what-is-a-controlled-vocabulary)
   * [What is SKOS?](#what-is-skos-simple-knowledge-organization-system)
   * [What is Linked Open Data (LOD)?](#what-is-linked-open-data-lod)
   * [Relational Database Lookup Tables](#why-use-relational-database-lookup-tables)
2. [Installation & Requirements](#%EF%B8%8F-2-installation--requirements)
3. [Preparing your Database Target Layer](#-3-preparing-your-database-target-layer)
   * [Method A: Local GeoPackage (.gpkg) [Easiest]](#method-a-local-geopackage-gpkg-recommended-for-individuals)
   * [Method B: PostgreSQL/PostGIS [Recommended for Teams]](#method-b-postgresqlpostgis-recommended-for-collaborations)
4. [Step-by-Step Tutorial: Your First Import](#-4-step-by-step-tutorial-your-first-import)
5. [In-Depth Feature Guide](#-5-in-depth-feature-guide)
   * [Dynamic Language Mapping](#dynamic-language-mapping)
   * [The Setup Columns Dialog](#the-setup-columns-dialog)
   * [GND, Wikidata, and AAT Links](#gnd-wikidata-and-aat-links-mapping)
   * [Spatial Geometry Projection (WKT Coordinates)](#spatial-geometry-projection-wkt-coordinates)
   * [JSON Wikidata Descriptions](#json-wikidata-descriptions)
   * [Parent-Child Hierarchy Linkages (Foreign Keys)](#parent-child-hierarchy-linkages-foreign-keys)
   * [Update & Sync Mode](#update--sync-mode)
6. [QGIS Value Relation Form Setup](#-6-qgis-value-relation-form-setup)
7. [Troubleshooting & FAQs](#-7-troubleshooting--faqs)

---

## 🎓 1. Introduction to Core Concepts

Before pressing buttons in QGIS, let's understand *why* we use this plugin. If you are already familiar with SKOS and database normalization, you can skip to [Section 2](#%EF%B8%8F-2-installation--requirements).

### What is a Controlled Vocabulary?
Imagine you are building a database of archaeological sites, and you have a field named `period`.
* User A writes: `Bronze Age`
* User B writes: `bronze age`
* User C writes: `E. Bronze Age`
* User D writes: `Frühe Bronzezeit` (German)

For QGIS, these are four completely different values. If you try to filter sites dating to the Bronze Age, your queries will fail.
A **Controlled Vocabulary** is an authorized list of terms. Users must select a term from this list rather than typing it in manually. This ensures consistency.

### What is SKOS (Simple Knowledge Organization System)?
SKOS is a standard way to represent controlled vocabularies, thesauri, and taxonomies using the Resource Description Framework (RDF).
Under SKOS:
* Each term is called a **Concept**.
* Concepts are organized hierarchically: a concept can have parent concepts (**broader**) or child concepts (**narrower**).
* Each concept can have **preferred labels** (`prefLabel`) in multiple languages (e.g. `de` = "Bronzezeit", `en` = "Bronze Age").

### What is Linked Open Data (LOD)?
In SKOS, terms are not just plain text. Every concept has a unique, permanent web address called a **URI** (Uniform Resource Identifier).
For example, the Getty Art & Architecture Thesaurus (AAT) represents the concept "excavations" with this URI:
`http://vocab.getty.edu/aat/300054328`

By storing the URI in your database instead of a plain-text word:
1. The meaning is unambiguous.
2. It links directly to global knowledge bases (like Wikidata or GND).
3. If labels change or get translated, your database connections remain intact because the URI never changes.

### Why use Relational Database Lookup Tables?
Rather than copy-pasting the URI, English label, German label, and French label into every single site point on your map, we use a database technique called **normalization**:
1. We create a **Lookup Table** containing all vocabulary concepts, their URIs, and translations.
2. In our map layers, we store only the short `uri` link as a reference.
3. We tell QGIS to look up the labels dynamically. If you change a translation in the lookup table, every feature on your map is instantly updated!

---

## 🛠️ 2. Installation & Requirements

### Installing the Plugin
1. Locate your QGIS profiles folder:
   * **Windows:** Go to `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   * **macOS:** Go to `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   * **Linux:** Go to `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
2. Create a folder named `SkosConnect` inside the plugins folder, and copy the files of this repository into it (including `skosconnect_plugin.py`, `__init__.py`, and `metadata.txt`).
3. Restart QGIS.
4. Go to **Plugins** ➡️ **Manage and Install Plugins...**
5. Search for **SkosConnect**, check the box next to it, and close the dialog.
6. A new icon **🔌 SkosConnect** will appear in your database toolbar, and under the **Plugins ➡️ SkosConnect** menu.

### Python Dependencies (For Offline Mode)
* **Online Mode** requires no external libraries.
* **Offline Mode** reads standard XML files (`.rdf`, `.xml`) automatically.
* If you want to load **Turtle (`.ttl`)**, **JSON-LD (`.jsonld`)**, or **N-Triples (`.nt`)** files offline, you must install the `rdflib` library in your QGIS environment:
  * **Windows:** Open the **OSGeo4W Shell** as Administrator and run:
    ```bash
    pip3 install rdflib
    ```
  * **macOS / Linux:** Run `pip3 install rdflib` in your terminal.

---

## 🗄️ 3. Preparing your Database Target Layer

To import concepts using SkosConnect, you need a target table in QGIS.

### Method A: Local GeoPackage (.gpkg) [Recommended for Individuals]
A GeoPackage is a single file database stored on your computer. It is portable, simple, and requires no setup.
1. In QGIS, go to **Layer** ➡️ **Create Layer** ➡️ **New GeoPackage Layer...**
2. **Database:** Choose where to save your file and name it (e.g. `vocabulary.gpkg`).
3. **Table name:** Set to `vocab_lookup`.
4. **Geometry type:** Select **No Geometry** (this is a plain attribute table).
5. **New Field:** Create one column:
   * Name: `uri`
   * Type: `Text data`
6. Click **Add to Fields List** and click **OK**.

*Note: Do not create language columns manually! SkosConnect will create them automatically.*

### Method B: PostgreSQL/PostGIS [Recommended for Teams]
If you are collaborating on a shared database server:
1. Open QGIS database manager or PGAdmin.
2. Execute the following SQL to create a normalized lookup table:
   ```sql
   CREATE TABLE vocab_lookup (
       id SERIAL PRIMARY KEY,
       uri VARCHAR(255) UNIQUE NOT NULL
   );
   ```

---

## 🚀 4. Step-by-Step Tutorial: Your First Import

In this tutorial, we will load terms from the Bonn University's *Hector* project database and import them into a GeoPackage table.

### Step 1: Open SkosConnect
Click the **🔌 SkosConnect** icon in QGIS. The dialog window will open:

![SkosConnect Dialog](../artifacts/media__1782661143380.png)

### Step 2: Configure the Vocabulary Source
1. Select **Online: Skosmos API** (checked by default).
2. Leave the default API URL: `https://skosmos.dbprojects.uni-bonn.de/rest/v1/hector`

### Step 3: Select your Target Table
1. In section **1. Target Table**, choose your table (`vocab_lookup` in your GeoPackage).
2. Next to the combobox, click the **🔧 Setup Columns** button.
3. A configuration dialog will appear:
   * **Preferred Labels:** Check the translation columns you want to add (e.g., German, English, French).
   * **Linked Open Data & Enrichment:** Check **Wikidata URI**, **Wikidata Description**, **GND URI**, and **AAT URI**.
   * Click **Add Columns**. SkosConnect will add the columns directly to your database and update the interface.

### Step 4: Select Import Languages
In the **Language Import Options** section, you will see checkboxes for each language column detected in the database (e.g., `pref_ger`, `pref_eng`).
* Check the boxes for the languages you want to write.
* **Language Fallback:** In the dropdown, choose what should happen if a term doesn't have a label in your target language. We recommend choosing **English ('en')** or **First available label**.

### Step 5: Browse and Select Concepts
1. Click **Load Top Concepts**. The interactive tree will populate on the left.
2. Click any concept. Its URI, labels, and external LOD links (`exactMatch`) will display in the **Concept Preview** on the right.
3. To load sub-concepts, double-click/expand any concept in the tree.
4. Check the boxes next to the terms you want to import.
   * *Tip: If you check "Auto-select child concepts recursively", selecting a category will automatically select all of its children while keeping the database flat.*

### Step 6: Execute the Import
1. Choose whether you want to enable **Update/Sync mode** (to update coordinates/labels of existing records).
2. Click **3. Write Selected Concepts to Database**.
3. Once completed, a success message will show how many records were inserted or updated. Open your QGIS attribute table for `vocab_lookup` to see the results!

---

## 🔍 5. In-Depth Feature Guide

### Dynamic Language Mapping
Unlike hardcoded plugins, SkosConnect parses database schemas at runtime. Any database column starting with `pref_` (e.g., `pref_ger`, `pref_eng`, `pref_fre`, `pref_spa`, `pref_lat`) is recognized as a translation target. The plugin automatically generates checkbox options for them.

### The Setup Columns Dialog
This helper dialog lets users add structural fields to local files or remote databases without writing SQL commands. It supports:
* Language labels (varchar, 100 characters).
* External LOD URIs (varchar, 255 characters).
* Enrichment descriptions (varchar, 1000 characters).

### GND, Wikidata, and AAT Links Mapping
When importing concepts, SkosConnect extracts links declared as `skos:exactMatch` or `skos:closeMatch`.
* If a Wikidata entity link (`wikidata.org/entity/Q...`) is found, it queries the Wikidata API.
* Using Wikidata's structured claims, it fetches associated **GND ID (P227)** and **Getty AAT ID (P1014)**.
* It formats and stores them as official, clickable URIs in your database columns:
  * `http://d-nb.info/gnd/...`
  * `http://vocab.getty.edu/aat/...`

### Spatial Geometry Projection (WKT Coordinates)
If your target layer is spatial (contains points, lines, or polygons) and you are importing concepts with geographic connections:
1. SkosConnect fetches coordinates from the Lobid-GND API (using WKT formats) or Wikidata.
2. It automatically creates a point geometry.
3. If your target layer is projected in a coordinate reference system other than EPSG:4326 (e.g., UTM or Web Mercator), SkosConnect reprojects the coordinates on-the-fly using QGIS's coordinate transformation engine before writing it to the database.

### JSON Wikidata Descriptions
If the `wikidata_desc` column is present in your table, SkosConnect fetches descriptions for all selected languages from Wikidata. It serializes them as a single JSON text object in your database:
```json
{
  "de": "Epoche der Menschheitsgeschichte, die durch die Nutzung von Bronze geprägt ist.",
  "en": "Archaeological period characterized by the use of bronze."
}
```
This is highly useful for displaying tooltips or search listings in multi-language web maps.

### Parent-Child Hierarchy Linkages (Foreign Keys)
If you are importing a hierarchical tree (e.g. Periods ➡️ Epochs), you can assign a parent relation:
1. Check **Optional Hierarchy Link**.
2. Select your parent table and choose the parent concept.
3. Choose the Foreign Key column in your target table.
4. When importing, SkosConnect writes the parent identifier to every child concept imported.

### Update & Sync Mode
By default, the plugin skips concepts that are already present in the database to prevent duplicate key constraint crashes.
* If you check **Update/Sync existing concepts**, SkosConnect will locate existing rows matching on `uri` and update their labels, coordinate geometries, and description JSONs to the latest values from the API/LOD endpoints.

---

## 🔌 6. QGIS Value Relation Form Setup

Once your lookup table is populated, connect your map layer (e.g., `archaeological_sites`) to it to display lookup dropdowns instead of text fields.

1. Double-click your spatial map layer in QGIS to open **Layer Properties**.
2. Navigate to the **Attributes Form** tab.
3. Select your classification field in the column list (e.g., `period_uri`).
4. Under **Widget Type**, choose **Value Relation**:

![QGIS Value Relation Form Setup](../artifacts/media__1782660804744.png)

5. Configure:
   * **Layer:** Select your vocabulary lookup layer (`vocab_lookup`).
   * **Key column:** `uri` (this is the value stored in your spatial table).
   * **Value column:** Choose the language translation you want displayed on-screen (e.g., `pref_eng` or `pref_ger`).
6. Toggle **Allow NULL value** if classification is optional.
7. Click **OK**.
8. Start editing your map layer! When creating a new point, you will see a clean, sorted dropdown menu displaying the vocabulary labels.

---

## ❓ 7. Troubleshooting & FAQs

### Q: Why is the "Write Selected Concepts" button disabled?
* **A:** You must load a vocabulary (click "Load Top Concepts"), check at least one term in the tree, and select a valid target database table.

### Q: Why are my database updates failing with a constraint error?
* **A:** Check if your target database layer is editable. If using PostgreSQL, ensure your user profile has permission to `INSERT` and `UPDATE` on the table.

### Q: I imported a concept with coordinates, but it doesn't show up on my map.
* **A:** Make sure your target table was created as a spatial table (e.g. Point geometry type) and not as an attribute-only table.

### Q: Does the plugin support offline dictionaries?
* **A:** Yes. Switch the source to **Offline: Local SKOS File** and select your `.rdf`, `.xml`, or `.ttl` file.

---

*For further assistance, feature requests, or bug reports, please contact the BCDH development team at bcdh@uni-bonn.de.*
