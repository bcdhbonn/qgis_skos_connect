# Step-by-Step Import Tutorial

This tutorial guides you through the process of loading vocabulary concepts from an online Skosmos API and writing them to your local QGIS database lookup layer.

---

## 🎯 Tutorial Requirements
Before beginning, make sure:
1. You have installed and activated **SkosConnect**.
2. You have a target lookup table loaded in your QGIS project containing at least a `uri` column.

---

## 🔌 Walkthrough

### Step 1: Open the Importer
Click the **🔌 SkosConnect** icon in QGIS (Database toolbar or under **Plugins ➡️ SkosConnect**). The main interface will appear.

---

### Step 2: Configure Vocabulary Source
Choose where the vocabulary resides:
* **Online: Skosmos API:** Enter the REST endpoint URL of your vocabulary server.
  * *Default:* `https://skosmos.dbprojects.uni-bonn.de/rest/v1/hector` (Hector Project Vocabulary).
* **Offline: Local SKOS File:** Check this if you have a file on your local machine. Click **Browse...** and select your `.rdf`, `.xml`, or `.ttl` file.

---

### Step 3: Setup Target Database Columns
1. Under **1. Target Table**, choose your database layer from the dropdown menu.
2. Click **🔧 Setup Columns** to open the schema creation assistant.
3. Check the columns you want to add:
   * Select languages: `German`, `English`, `French`, `Spanish`, `Latin`.
   * Select LOD options: `Wikidata URI`, `Wikidata Description`, `GND URI`, `AAT URI`.
4. Click **Add Columns**. SkosConnect will add the missing fields to your table.

---

### Step 4: Configure Language Import Options
After database columns are added, SkosConnect scans the target table for columns starting with `pref_` and populates the checkboxes:
1. Check the languages you wish to import (e.g. `pref_ger`, `pref_eng`).
2. **Missing Translation Fallback:** In the dropdown, choose what label should be inserted if the concept is missing your preferred language:
   * **URI:** Stash the raw URI link.
   * **English ('en') / German ('de'):** Try to find English/German translations.
   * **First available label:** Stash whatever translation is found first.

---

### Step 5: Browse and Select Terms
1. Click **Load Top Concepts**. The vocabulary hierarchy tree on the left will load.
2. Select any term. The **Concept Preview** on the right will display metadata, label translations, and matches.
3. Double-click parents to load sub-concepts dynamically.
4. Check the checkboxes next to concepts to select them for import.
   * *Tip: If "Auto-select child concepts recursively" is checked, selecting a parent automatically registers all nested sub-concepts instead.*

---

### Step 6: Select Update Mode & Import
1. If you are importing terms that might already exist in your database, choose whether to enable **Update/Sync Mode** (checks match by URI to update existing attributes and geometry, instead of skipping).
2. Click **3. Write Selected Concepts to Database**.
3. A progress bar will display. When finished, a confirmation dialog lists how many records were inserted, updated, or skipped.
