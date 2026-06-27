# SkosConnect: Multilingual LOD Importer for QGIS

**SkosConnect** ist ein QGIS-Plugin, das den Import von multilingualen kontrollierten Vokabularen aus Skosmos-Instanzen (über die REST-API) sowie aus lokalen SKOS-Dateien direkt in relationale Datenbanken (z. B. PostgreSQL-Tabellen) in QGIS ermöglicht.

---

## 🌟 Features

* **Zwei Datenquellen:**
  * **Online (Skosmos API):** Direktes Laden über eine konfigurierbare API-Schnittstelle (z. B. die Hector-Datenbank der Universität Bonn).
  * **Offline (Lokale Datei):** Laden lokaler Vokabulare in den Formaten RDF/XML (`.rdf`, `.xml`) sowie Turtle (`.ttl`), JSON-LD (`.jsonld`) und N-Triples (`.nt`).
* **Multilingualer Import:** Importiert bevorzugte Bezeichnungen (Labels) auf Deutsch (`pref_ger`) und Englisch (`pref_eng`).
* **Relationale Verknüpfung (Fremdschlüssel):** Optionale hierarchische Verlinkung importierter Begriffe an übergeordnete Tabellen (z. B. Zuweisung von Perioden zu Epochen).
* **Flexibles Tree-UI:** Navigierbare hierarchische Darstellung der Vokabular-Konzepte mit Lazy-Loading (Unterbegriffe werden erst beim Aufklappen geladen).
* **Auswahlassistent:** Option zum automatischen rekursiven Auswählen aller untergeordneten Begriffe.
* **Transaktionssicher:** Detaillierte Fehlerberichterstattung direkt aus den Datenbank-Constraint-Verletzungen mit automatischem Rollback bei Fehlern.

---

## 🛠️ Installation & Anforderungen

### 1. Plugin-Ordner kopieren
Kopieren Sie diesen Ordner (`SkosConnect`) in das QGIS-Plugin-Verzeichnis Ihres Systems:
* **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\SkosConnect`
* **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/SkosConnect`
* **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/SkosConnect`

Aktivieren Sie das Plugin anschließend in QGIS über **Erweiterungen -> Erweiterungen verwalten und installieren**.

### 2. Voraussetzungen / Abhängigkeiten
* Für den **Online-Modus** und den **Offline-RDF/XML-Import** werden keine externen Python-Bibliotheken benötigt (reines Python / QGIS-Standard).
* Für den Import von **Turtle (`.ttl`)** und anderen RDF-Formaten im Offline-Modus wird die Python-Bibliothek `rdflib` benötigt.
  * **Unter Windows (OSGeo4W-Shell als Administrator ausführen):**
    ```bash
    pip3 install rdflib
    ```

---

## 📂 Datenbank-Schema-Anforderungen

Das Ziel-Layer in QGIS muss ein Vektor-Layer (z. B. PostgreSQL/PostGIS) sein und folgende Spaltenstruktur aufweisen:

| Spaltenname | Typ | Beschreibung |
| :--- | :--- | :--- |
| `uri` | Text | Eindeutige Kennung des SKOS-Konzepts (z. B. `http://...`). **Erforderlich.** |
| `pref_ger` | Text | Bevorzugtes Label in deutscher Sprache (Optional). |
| `pref_eng` | Text | Bevorzugtes Label in englischer Sprache (Optional). |

Falls Sie die **hierarchische Verknüpfung** nutzen möchten, muss das Ziel-Layer eine Fremdschlüsselspalte enthalten (z. B. `parent_id`), die auf die ID-Spalte einer Eltern-Tabelle verweist.

---

## 📄 Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert.
