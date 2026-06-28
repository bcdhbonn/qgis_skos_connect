# Welcome to the SkosConnect Wiki

**SkosConnect** is a user-friendly QGIS plugin designed to import controlled vocabularies directly from a Skosmos online API or an offline SKOS/RDF file into database layers (like PostgreSQL/PostGIS or a local **GeoPackage**).

This wiki provides comprehensive, step-by-step guides for users of all skill levels, from absolute beginners to database administrators.

---

## 💡 Core Concepts: A Guide for Beginners

### What is a Controlled Vocabulary?
When classifying geographical features (e.g., archaeological sites by "Time Period" or buildings by "Function"), free-text fields lead to inconsistent data:
* User A enters: `Bronze Age`
* User B enters: `bronze age`
* User C enters: `E. Bronze Age`
* User D enters: `Frühe Bronzezeit` (German)

For QGIS, these are four completely different categories. This makes searching, styling, or filtering your map impossible.
A **Controlled Vocabulary** is an authorized list of terms. Users must choose from this list, ensuring absolute consistency across the project.

### What is SKOS?
SKOS (Simple Knowledge Organization System) is a standard way to represent classification schemes, thesauri, and taxonomies.
* Each entry is a **Concept**.
* Concepts are organized hierarchically: they can have parent concepts (**broader**) or child concepts (**narrower**).
* Each concept can have **preferred labels** (`prefLabel`) in multiple languages (e.g., German "Bronzezeit" and English "Bronze Age").

### What is Linked Open Data (LOD)?
In SKOS, terms are associated with a permanent, unique web link called a **URI** (Uniform Resource Identifier).
For example, the Art & Architecture Thesaurus (AAT) URI for "excavations" is:
`http://vocab.getty.edu/aat/300054328`

Storing the URI in your dataset instead of the text string ensures:
1. The classification is globally unambiguous.
2. It links directly to international authorities (like Wikidata or GND).
3. Even if a label is translated or modified, the URI stays the same, keeping your data connected.

### Why Use Relational Lookup Tables?
Instead of copying the URI, English label, and German label into every single point on your map, we use a database technique called **normalization**:
1. We import the concepts into a **Lookup Table** (containing `uri` and language label columns).
2. In our map layer, we store only the short `uri` reference.
3. QGIS automatically connects the two tables, displaying the clean translated labels to the user. If you edit a translation in the lookup table, every site on your map updates instantly!

---

## 📖 Wiki Navigation
* [Installation Guide](Installation.md)
* [Database Setup (PostgreSQL vs. GeoPackage)](Database-Setup.md)
* [Your First Import Tutorial](Import-Tutorial.md)
* [Enrichment & LOD (Wikidata, GND, AAT)](Enrichment-and-LOD.md)
* [QGIS Form Widget Integration](QGIS-Integration.md)
