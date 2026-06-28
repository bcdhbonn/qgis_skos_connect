# Database Target Layer Setup

To import concepts using SkosConnect, you must select an existing target layer inside QGIS. This layer will store the vocabulary terms and their URIs.

Here is a comparison and setup guide for the two most common configurations: **GeoPackage (.gpkg)** and **PostgreSQL/PostGIS**.

---

## 🏛️ GeoPackage vs. PostgreSQL/PostGIS

| Feature | GeoPackage (.gpkg) | PostgreSQL / PostGIS |
| :--- | :--- | :--- |
| **Hosting** | Local single file | Dedicated database server |
| **Setup Effort** | Zero configuration | Requires server installation & admin |
| **Best For** | Single researchers, offline work | Multi-user projects, institutions |
| **Multi-User Editing** | Not supported (file locking conflicts) | Fully supported (concurrency engine) |
| **Data Integrity** | Basic SQLite features | Advanced constraints, triggers, server rules |

---

## 📦 Option A: Local GeoPackage Layer [Easiest]

If you are working alone on your local computer, a GeoPackage is the easiest way to store your lookup tables.

### Step 1: Create the Lookup Table
1. In QGIS, go to **Layer** ➡️ **Create Layer** ➡️ **New GeoPackage Layer...**
2. **Database:** Click the `...` button, navigate to your folder, and name the file (e.g. `archaeological_vocab.gpkg`).
3. **Table name:** Set to `vocab_periods`.
4. **Geometry type:** Select **No Geometry** (this is a pure attribute lookup table, not a map shape).
5. **New Field:** Add the following column:
   * Name: `uri`
   * Type: `Text data`
6. Click **Add to Fields List**.
7. Click **OK**. The table will now appear in your QGIS Layers Panel.

*Note: You do not need to create language columns (like pref_ger, pref_eng) manually! The SkosConnect Schema Assistant will create them for you dynamically.*

---

## 🚀 Option B: PostgreSQL / PostGIS Setup [Advanced]

For multi-user institutional projects, database-enforced integrity and collaborative locks are crucial.

### Step 1: Create the Lookup Table in PostgreSQL
Connect to your database via pgAdmin or the QGIS Database Manager SQL window, and run the following command:

```sql
CREATE TABLE time_periods (
    id SERIAL PRIMARY KEY,
    uri VARCHAR(255) UNIQUE NOT NULL
);
```

### Step 2: Establish the Foreign Key Relationship on your Map Layer
To link your physical map features (e.g., excavation points) to your vocabulary terms, create a column referencing the lookup table:

```sql
CREATE TABLE excavation_sites (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    geom GEOMETRY(Point, 4326),
    period_id INTEGER REFERENCES time_periods(id)
);
```
Or, if you prefer using direct URI mapping:
```sql
CREATE TABLE excavation_sites (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    geom GEOMETRY(Point, 4326),
    period_uri VARCHAR(255) REFERENCES time_periods(uri)
);
```
Once these tables are added as layers in QGIS, SkosConnect can target them.
