# SkosConnect: Multilingual LOD Importer for QGIS

**SkosConnect** is a user-friendly QGIS plugin that allows you to import controlled vocabularies directly from a Skosmos online API or an offline SKOS/RDF file into a relational database layer (like PostgreSQL/PostGIS or a local **GeoPackage**).

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

## 🏛️ Database Comparison: PostgreSQL vs. GeoPackage

When setting up your lookup tables, you have two main options. Here is why you might choose one over the other:

### 🚀 PostgreSQL/PostGIS (The Professional Enterprise Solution)
For production environments, team projects, or institutional databases, **PostgreSQL with the PostGIS extension** is the industry standard and the superior solution.
* **Multi-User Collaboration:** Dozens of users can view and edit the data at the same time. QGIS communicates with the database server, preventing lockouts or file corruption.
* **Robust Security & Permissions:** You can create individual user roles (e.g., digitizers can only select vocabulary terms, admins can update the vocabulary table, and public viewers can only read the data).
* **Data Integrity Rules:** PostgreSQL can strictly enforce relationships (Foreign Keys) directly on the database level. If a user tries to delete a vocabulary term that is still used on the map, the server will block the action and preserve database integrity.
* **Server-side Triggers & Functions:** You can automate tasks (e.g., logging who changed a value, or auto-generating timestamps).

### 📦 GeoPackage (.gpkg) (The Lightweight & Portable Alternative)
If you are a single researcher, don't have access to an IT department to host a server, or just want to quickly test the workflow:
* **Single File:** The entire database (map layers and lookup tables) is stored in a single `.gpkg` file on your computer.
* **Zero Setup:** No server configuration, usernames, passwords, or connection strings required.
* **Local limitations:** It is not designed for multiple users editing simultaneously. If two people write to the same file over a shared drive (like Dropbox/Sciebo), it can lead to synchronization conflicts and database corruption.

---

## 🚀 Tutorial 1: Setting up with PostgreSQL/PostGIS

### Step 1: Create your Lookup Table in PostgreSQL
Run the following SQL statement in your database management tool (like pgAdmin or the QGIS DB Manager SQL window) to create your vocabulary lookup table:

```sql
CREATE TABLE time_periods (
    id SERIAL PRIMARY KEY,
    uri VARCHAR(255) UNIQUE NOT NULL,
    pref_ger VARCHAR(100),
    pref_eng VARCHAR(100)
);
```

If you want to enforce a foreign key in your map layer, your map table should link to this lookup table:

```sql
CREATE TABLE excavation_sites (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    geom GEOMETRY(Point, 4326),
    period_id INTEGER REFERENCES time_periods(id)
);
```

### Step 2: Use SkosConnect to Import Concepts
1. In QGIS, connect to your PostgreSQL database.
2. Click the database plug icon **🔌 SkosConnect** in QGIS (located in the database toolbar or under **Plugins ➡️ SkosConnect**).
3. **SKOS Source Configuration:** Choose online or offline file.
4. **1. Target Table:** Select your PostgreSQL table (`time_periods`).
5. **Language Import Options:** Ensure both German and English checkboxes are checked (the plugin automatically detects that these columns exist in your table!).
6. **Optional Hierarchy Link:**
   * If you are importing sub-periods (e.g., "Early Bronze Age") and want to link them to an existing parent category in another table (e.g., "Bronze Age" in `epochs`), check this box and select the parent table, parent concept, and target foreign key column.
7. Click **Load Top Concepts**, check the items you want to import, and click **3. Write Selected Concepts to Database**.

---

## 🚀 Tutorial 2: Setting up with GeoPackage (.gpkg)

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
1. Click the database plug icon **🔌 SkosConnect** in QGIS.
2. **SKOS Source Configuration:** Choose online or offline file.
3. **1. Target Table:** Select your newly created `vocab_periods` table.
4. **Language Import Options:** Ensure both German and English checkboxes are checked.
5. Click **Load Top Concepts**. Click the arrow keys to expand concepts, check the items you want to import, and click **3. Write Selected Concepts to Database**.

---

## 🔗 Linking your Map Layer to the Vocabulary (QGIS Configuration)
Once your lookup table is populated (either in PostgreSQL or GeoPackage), you want a dropdown menu to appear in QGIS when editing features:

1. Double-click your spatial map layer (e.g., `excavation_sites`) and open the **Attributes Form** settings.
2. Select your period attribute column (e.g., `period_uri` or `period_id`).
3. Under **Widget Type**, choose **Value Relation**.
4. Configure it as follows:
   * **Layer:** `vocab_periods` or `time_periods`
   * **Key column:** `uri` (or `id` if you are using integer foreign keys in PostgreSQL)
   * **Value column:** `pref_eng` or `pref_ger` (the human-readable label you want to see on screen)
5. Click **OK**. 

🎉 **Done!** When you add or edit features in your map layer, you will now see a clean dropdown menu showing the correct period terms. QGIS saves the stable URI/ID in the background, keeping your database clean and database-compliant!

---

## 🛠️ Installation & Requirements

### 1. Copying the Plugin
Copy this folder (`SkosConnect`) into your QGIS plugin directory:
* **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\SkosConnect`
* **Linux:** `~/.local/share/QGIS/QGIS3/profiles\default\python\plugins\SkosConnect`
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
