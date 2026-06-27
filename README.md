# SkosConnect: Multilingual LOD Importer for QGIS

**SkosConnect** is a user-friendly QGIS plugin that allows you to import controlled vocabularies directly from a Skosmos online API or an offline SKOS/RDF file into a relational database layer (like PostgreSQL or a local **GeoPackage**).

---

## 💡 Why this Plugin Matters: A Guide for Beginners

When working with geographic data, you often need to classify features (e.g., archaeology sites by "Time Period" or buildings by "Usage"). 

### 1. The Problem with Free-Text Fields
If multiple people type period names manually, they will write them differently:
* `"Early Bronze Age"`
* `"E. Bronze Age"`
* `"early bronze age"`
* `"Frühe Bronzezeit"` (in German)

This makes it impossible to search, filter, or style your map consistently because QGIS treats these as completely different categories.

### 2. The Solution: Controlled Vocabularies & Linked Open Data (LOD)
Instead of typing labels manually, we use a **controlled vocabulary** hosted on a web server (like Skosmos) or in a local file. Each concept (e.g., "Early Bronze Age") has a unique identifier called a **URI** (Universal Resource Identifier), which looks like a web link: `http://example.org/vocab/EarlyBronzeAge`. 

Even if you translate the label to German ("Frühe Bronzezeit") or English ("Early Bronze Age"), the **URI stays exactly the same**. 

### 3. Relational Database Design
Instead of copy-pasting the URI and labels into every single point, line, or polygon in your map:
1. We import the concepts into a **Lookup Table** (a dictionary table containing `uri`, `pref_ger`, and `pref_eng`).
2. In our map layer, we only store the short `uri` link.
3. QGIS automatically connects the two and displays the beautiful, translated labels to the user!

---

## 📦 Why GeoPackage (.gpkg) is Perfect for this Workflow

If you don't have a central PostgreSQL database server, a **GeoPackage (.gpkg)** is the best choice:
* It is a single, portable file (easy to email or share).
* Unlike Shapefiles (which truncate column names to 10 characters and fail on long strings), a GeoPackage is a full SQLite database that easily handles long URI strings and relations.
* You can store both your map layers (spatial) and your vocabulary lookup tables (non-spatial) in the **same** file.

---

## 🚀 Step-by-Step Beginner Tutorial (Using GeoPackage)

### Step 1: Create a Vocabulary Lookup Table in QGIS
1. In QGIS, go to the top menu: **Layer ➡️ Create Layer ➡️ New GeoPackage Layer...**
2. **Database:** Choose a save location and name your file (e.g., `archaeology_data.gpkg`).
3. **Table name:** Name the table `vocab_periods`.
4. **Geometry type:** Select **No Geometry** (this is a pure table containing text, not map shapes).
5. **New Field:** Add the following text columns:
   * Name: `uri`, Type: `Text data`
   * Name: `pref_ger`, Type: `Text data` (for German labels)
   * Name: `pref_eng`, Type: `Text data` (for English labels)
6. Click **Add to Fields List** for each, then click **OK**. You will see the new table in your layers panel.

### Step 2: Use SkosConnect to Import Concepts
1. Click the database plug icon **🔌 SkosConnect** in QGIS (located in the database toolbar or under **Plugins ➡️ SkosConnect**).
2. **SKOS Source Configuration:**
   * **Online:** Keep selected and use the default URL (`https://skosmos.dbprojects.uni-bonn.de/rest/v1/hector`) or enter your own Skosmos server.
   * **Offline:** Select this if you have a local SKOS file (e.g., `.rdf`, `.xml`, or `.ttl`).
3. **1. Target Table:** Select your newly created `vocab_periods` table.
4. **Language Import Options:** Ensure both German and English checkboxes are checked (the plugin automatically detects that these columns exist in your table!).
5. **2. Browse Vocabulary:** Click **Load Top Concepts**. Click the arrow keys to expand concepts (like expanding folders). Check the items you want to import.
6. **3. Write Selected Concepts to Database:** Click this button. The plugin will write the selected URIs and their translations into your GeoPackage table.

### Step 3: Link your Map Layer to the Vocabulary
Now, when you draw a point on your map, you want a dropdown menu showing the periods we just imported.
1. Double-click your spatial map layer (e.g., `excavation_sites`) and open **Attributes Form**.
2. Select your period attribute column (e.g., `period_uri`).
3. Under **Widget Type**, choose **Value Relation**.
4. Configure it as follows:
   * **Layer:** `vocab_periods`
   * **Key column:** `uri` (what QGIS saves in the background)
   * **Value column:** `pref_eng` or `pref_ger` (what you see on screen)
5. Click **OK**. 

🎉 **Done!** When you add or edit features in your map layer, you will now see a clean dropdown menu showing the correct period terms. QGIS saves the stable URI in the background, keeping your database clean and database-compliant!

---

## 🛠️ Installation & Requirements

### 1. Copying the Plugin
Copy this folder (`SkosConnect`) into your QGIS plugin directory:
* **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\SkosConnect`
* **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/SkosConnect`
* **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/SkosConnect`

Restart QGIS, then activate it in **Plugins ➡️ Manage and Install Plugins**.

### 2. Offline Mode Requirements
* The built-in XML parser handles **RDF/XML (`.rdf`, `.xml`)** files automatically.
* To read **Turtle (`.ttl`)**, **JSON-LD (`.jsonld`)**, or **N-Triples (`.nt`)** files, you need the Python library `rdflib` installed in your QGIS environment.
  * **Windows (Open OSGeo4W Shell as Admin):**
    ```bash
    pip3 install rdflib
    ```

---

## 📄 License
This project is licensed under the MIT License.
