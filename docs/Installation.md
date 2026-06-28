# Installation & Requirements

Getting SkosConnect running in your QGIS environment is simple. Follow the instructions below to install the plugin and set up its requirements.

---

## 🔌 1. Copying the Plugin files

1. Download the plugin folder (`SkosConnect`) from the repository.
2. Locate the QGIS active profile folder on your operating system:
   * **Windows:** Go to `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   * **macOS:** Go to `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   * **Linux:** Go to `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
3. Copy the entire `SkosConnect` folder into that directory.

---

## ⚙️ 2. Activating the Plugin in QGIS

1. Open (or restart) QGIS.
2. Go to the top menu bar: **Plugins** ➡️ **Manage and Install Plugins...**
3. Select the **Installed** tab on the left sidebar.
4. Search for **SkosConnect**.
5. Check the box next to it to enable it.
6. Click **Close**.

The **🔌 SkosConnect** icon should now be visible in your **Database Toolbar** and under the **Plugins** drop-down menu.

---

## 📦 3. Library Dependencies (For Offline Mode)

* **Online Mode** (fetching vocabularies directly from a Skosmos API endpoint over the web) does not require any external dependencies.
* **Offline Mode** reads standard XML files (`.rdf`, `.xml`) automatically.
* To read **Turtle (`.ttl`)**, **JSON-LD (`.jsonld`)**, or **N-Triples (`.nt`)** files offline, QGIS's Python environment needs the `rdflib` library:

### Windows installation (OSGeo4W Shell):
1. Search for **OSGeo4W Shell** in your Windows start menu.
2. Right-click it and select **Run as Administrator**.
3. Run the following command:
   ```bash
   pip3 install rdflib
   ```

### macOS / Linux installation:
1. Open your system Terminal.
2. Run the command:
   ```bash
   pip3 install rdflib
   ```
