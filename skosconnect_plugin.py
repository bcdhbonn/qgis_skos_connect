from qgis.PyQt.QtWidgets import (QAction, QDialog, QVBoxLayout, QPushButton, 
                                QTreeWidget, QTreeWidgetItem, QMessageBox, 
                                QApplication, QLabel, QComboBox, QGroupBox, 
                                QFormLayout, QCheckBox, QHBoxLayout, QWidget, 
                                QRadioButton, QLineEdit, QFileDialog, QTextBrowser, QGridLayout)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.core import (QgsProject, QgsFeature, QgsApplication, QgsMapLayerType, 
                       QgsMessageLog, Qgis, QgsWkbTypes, QgsCoordinateReferenceSystem, 
                       QgsCoordinateTransform, QgsPointXY, QgsGeometry)
import requests
import os
import xml.etree.ElementTree as ET
import re
import json

# Try to import rdflib for advanced RDF parsing (e.g. Turtle)
try:
    import rdflib
    from rdflib.namespace import RDF, SKOS
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False


def parse_skos_with_rdflib(file_path):
    """Parse SKOS vocabulary using rdflib (supports Turtle, RDF/XML, JSON-LD, etc.)."""
    if not RDFLIB_AVAILABLE:
        return None
        
    g = rdflib.Graph()
    # Auto-detect format from file extension
    ext = os.path.splitext(file_path)[-1].lower()
    fmt = 'xml'
    if ext in ['.ttl', '.n3']:
        fmt = 'turtle'
    elif ext in ['.jsonld', '.json']:
        fmt = 'json-ld'
    elif ext in ['.nt']:
        fmt = 'nt'
        
    try:
        g.parse(file_path, format=fmt)
    except Exception as e:
        QgsMessageLog.logMessage(f"rdflib failed parsing {file_path}: {e}", "Plugins", Qgis.Warning)
        return None
        
    concepts = {}
    
    for s in g.subjects(rdflib.RDF.type, SKOS.Concept):
        uri = str(s)
        concepts[uri] = {
            'uri': uri,
            'labels': {}, # Map of lang_code -> label string
            'narrower': [],
            'broader': [],
            'exactMatch': [],
            'closeMatch': []
        }
        
        # Extract all preferred labels
        for label in g.objects(s, SKOS.prefLabel):
            lang = getattr(label, 'language', '') or ''
            lang = lang.lower() or 'default'
            concepts[uri]['labels'][lang] = str(label)
                
        # Extract direct hierarchical relationships
        for child in g.objects(s, SKOS.narrower):
            concepts[uri]['narrower'].append(str(child))
        for parent in g.objects(s, SKOS.broader):
            concepts[uri]['broader'].append(str(parent))
            
        # Extract matches
        for m in g.objects(s, SKOS.exactMatch):
            concepts[uri]['exactMatch'].append(str(m))
        for m in g.objects(s, SKOS.closeMatch):
            concepts[uri]['closeMatch'].append(str(m))
            
    # Ensure all relationships are bidirectional in our model
    for uri, concept in concepts.items():
        for parent_uri in concept['broader']:
            if parent_uri in concepts and uri not in concepts[parent_uri]['narrower']:
                concepts[parent_uri]['narrower'].append(uri)
        for child_uri in concept['narrower']:
            if child_uri in concepts and uri not in concepts[child_uri]['broader']:
                concepts[child_uri]['broader'].append(uri)
                
    return concepts


def parse_skos_rdf_xml(file_path):
    """Fallback XML parser for SKOS/RDF XML format if rdflib is not installed."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        QgsMessageLog.logMessage(f"XML parsing error: {e}", "Plugins", Qgis.Warning)
        return {}

    # RDF/XML Namespace definitions
    RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    RDF_ABOUT = f"{{{RDF_NS}}}about"
    RDF_RESOURCE = f"{{{RDF_NS}}}resource"

    concepts = {}
    
    # Iterate over Concept elements in the RDF document
    for elem in root:
        local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local_name == 'Concept':
            uri = elem.attrib.get(RDF_ABOUT)
            if not uri:
                continue
                
            if uri not in concepts:
                concepts[uri] = {
                    'uri': uri,
                    'labels': {},
                    'narrower': [],
                    'broader': [],
                    'exactMatch': [],
                    'closeMatch': []
                }
            
            concept = concepts[uri]
            
            # Read properties
            for child in elem:
                local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                
                if local_name == 'prefLabel':
                    lang = "default"
                    for attr_name, attr_val in child.attrib.items():
                        if attr_name.endswith("}lang"):
                            lang = attr_val.lower()
                            break
                    text = child.text or ''
                    concept['labels'][lang] = text
                elif local_name == 'narrower':
                    child_uri = child.attrib.get(RDF_RESOURCE)
                    if child_uri:
                        concept['narrower'].append(child_uri)
                elif local_name == 'broader':
                    parent_uri = child.attrib.get(RDF_RESOURCE)
                    if parent_uri:
                        concept['broader'].append(parent_uri)
                elif local_name == 'exactMatch':
                    match_uri = child.attrib.get(RDF_RESOURCE)
                    if match_uri:
                        concept['exactMatch'].append(match_uri)
                elif local_name == 'closeMatch':
                    match_uri = child.attrib.get(RDF_RESOURCE)
                    if match_uri:
                        concept['closeMatch'].append(match_uri)
                        
    # Ensure all relationships are bidirectional in our model
    for uri, concept in concepts.items():
        for parent_uri in concept['broader']:
            if parent_uri in concepts and uri not in concepts[parent_uri]['narrower']:
                concepts[parent_uri]['narrower'].append(uri)
        for child_uri in concept['narrower']:
            if child_uri in concepts and uri not in concepts[child_uri]['broader']:
                concepts[child_uri]['broader'].append(uri)

    return concepts


def find_roots(concepts):
    """Find root concepts (those that have no parent/broader concepts)."""
    all_narrower = set()
    for c in concepts.values():
        for child in c['narrower']:
            all_narrower.add(child)
            
    roots = []
    for uri, c in concepts.items():
        if uri not in all_narrower and not c['broader']:
            roots.append(uri)
            
    # Fallback: if cyclical or no roots found, use all concepts
    if not roots and concepts:
        roots = list(concepts.keys())
    return roots


def get_concept_label(concept, lang_code, fallback_uri, fallback_mode="en"):
    """Extract preferred label from concept dict matching the given language code, with fallbacks."""
    if not concept:
        return fallback_uri
    labels = concept.get('labels', {})
    if lang_code in labels:
        return labels[lang_code]
    # Check partial matches (e.g. 'de' matches 'de-de')
    for l, val in labels.items():
        if l.startswith(lang_code) or lang_code.startswith(l):
            return val
    # Fallback mode check
    if fallback_mode == "uri":
        return fallback_uri
    elif fallback_mode == "first":
        if labels:
            return list(labels.values())[0]
        return fallback_uri
    else:
        # Specific language fallback (e.g. 'en', 'de', etc.)
        if fallback_mode in labels:
            return labels[fallback_mode]
        # Fallback to default/english if selected fallback is missing
        for l in [fallback_mode, 'en', 'de', 'default']:
            if l in labels:
                return labels[l]
        if labels:
            return list(labels.values())[0]
        return fallback_uri


# ---------------------------------------------------------
# DIALOG WINDOW IMPLEMENTATION
# ---------------------------------------------------------
class SchemaSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔧 Setup Database Columns for LOD")
        self.resize(450, 320)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Select columns to add to your target table:"))
        
        # Group for languages
        self.gp_langs = QGroupBox("Preferred Labels (Languages)")
        langs_layout = QGridLayout(self.gp_langs)
        self.chk_de = QCheckBox("German (pref_ger)")
        self.chk_en = QCheckBox("English (pref_eng)")
        self.chk_fr = QCheckBox("French (pref_fre)")
        self.chk_es = QCheckBox("Spanish (pref_spa)")
        self.chk_la = QCheckBox("Latin (pref_lat)")
        
        self.chk_de.setChecked(True)
        self.chk_en.setChecked(True)
        
        langs_layout.addWidget(self.chk_de, 0, 0)
        langs_layout.addWidget(self.chk_en, 0, 1)
        langs_layout.addWidget(self.chk_fr, 1, 0)
        langs_layout.addWidget(self.chk_es, 1, 1)
        langs_layout.addWidget(self.chk_la, 2, 0)
        layout.addWidget(self.gp_langs)
        
        # Group for LOD
        self.gp_lod = QGroupBox("Linked Open Data & Enrichment")
        lod_layout = QVBoxLayout(self.gp_lod)
        self.chk_wiki = QCheckBox("Wikidata URI (wikidata)")
        self.chk_wiki_desc = QCheckBox("Wikidata Description (wikidata_desc)")
        self.chk_gnd = QCheckBox("GND URI (gnd)")
        self.chk_aat = QCheckBox("AAT URI (aat)")
        
        self.chk_wiki.setChecked(True)
        self.chk_gnd.setChecked(True)
        self.chk_aat.setChecked(True)
        
        lod_layout.addWidget(self.chk_wiki)
        lod_layout.addWidget(self.chk_wiki_desc)
        lod_layout.addWidget(self.chk_gnd)
        lod_layout.addWidget(self.chk_aat)
        layout.addWidget(self.gp_lod)
        
        # Buttons
        btns_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Add Columns")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btns_layout.addWidget(self.btn_ok)
        btns_layout.addWidget(self.btn_cancel)
        layout.addLayout(btns_layout)


class SkosConnectMultilingualImporter(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔌 SkosConnect: Multilingual LOD Import")
        self.resize(950, 850)
        self.layout = QVBoxLayout()

        # 0. Source Configuration
        self.group_source = QGroupBox("0. SKOS Source Configuration")
        source_layout = QVBoxLayout()
        
        self.radio_online = QRadioButton("Online: Skosmos API")
        self.radio_offline = QRadioButton("Offline: Local SKOS File")
        self.radio_online.setChecked(True)
        
        self.radio_online.toggled.connect(self.on_source_mode_changed)
        self.radio_offline.toggled.connect(self.on_source_mode_changed)
        
        source_radio_layout = QHBoxLayout()
        source_radio_layout.addWidget(self.radio_online)
        source_radio_layout.addWidget(self.radio_offline)
        source_layout.addLayout(source_radio_layout)
        
        # Online config widgets
        self.widget_online = QWidget()
        online_form = QFormLayout(self.widget_online)
        self.txt_api_url = QLineEdit("https://skosmos.dbprojects.uni-bonn.de/rest/v1/hector")
        online_form.addRow("Skosmos API URL:", self.txt_api_url)
        source_layout.addWidget(self.widget_online)
        
        # Offline config widgets
        self.widget_offline = QWidget()
        offline_form = QHBoxLayout(self.widget_offline)
        self.txt_file_path = QLineEdit()
        self.txt_file_path.setReadOnly(True)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self.browse_offline_file)
        offline_form.addWidget(QLabel("SKOS File:"))
        offline_form.addWidget(self.txt_file_path)
        offline_form.addWidget(self.btn_browse)
        source_layout.addWidget(self.widget_offline)
        self.widget_offline.setVisible(False) # Starts hidden
        
        self.group_source.setLayout(source_layout)
        self.layout.addWidget(self.group_source)

        # 1. Target Table Selection
        self.layout.addWidget(QLabel("1. Target Table (Requires 'uri' column):"))
        target_layout = QHBoxLayout()
        self.combo_target_layer = QComboBox()
        self.combo_target_layer.currentIndexChanged.connect(self.on_target_layer_changed)
        target_layout.addWidget(self.combo_target_layer, 4)
        
        self.btn_setup_schema = QPushButton("🔧 Setup Columns")
        self.btn_setup_schema.clicked.connect(self.setup_table_schema)
        target_layout.addWidget(self.btn_setup_schema, 1)
        
        self.layout.addLayout(target_layout)

        # Dynamic Language Selection (Populated dynamically based on database columns)
        self.group_lang = QGroupBox("Language Import Options (Detected from Table Columns)")
        group_lang_layout = QVBoxLayout()
        self.lang_layout = QHBoxLayout()
        group_lang_layout.addLayout(self.lang_layout)
        
        # Fallback configuration
        fallback_layout = QHBoxLayout()
        fallback_layout.addWidget(QLabel("When preferred language is missing, fallback to:"))
        self.combo_fallback_lang = QComboBox()
        self.combo_fallback_lang.addItem("URI (No label fallback)", "uri")
        self.combo_fallback_lang.addItem("English ('en')", "en")
        self.combo_fallback_lang.addItem("German ('de')", "de")
        self.combo_fallback_lang.addItem("French ('fr')", "fr")
        self.combo_fallback_lang.addItem("Spanish ('es')", "es")
        self.combo_fallback_lang.addItem("Latin ('la')", "la")
        self.combo_fallback_lang.addItem("First available label", "first")
        self.combo_fallback_lang.setCurrentIndex(1) # Default to English 'en'
        fallback_layout.addWidget(self.combo_fallback_lang)
        fallback_layout.addStretch()
        
        group_lang_layout.addLayout(fallback_layout)
        self.group_lang.setLayout(group_lang_layout)
        self.layout.addWidget(self.group_lang)

        # Optional Foreign Key Link
        self.group_fk = QGroupBox("Optional Hierarchy Link (e.g., link Periods to Epochs)")
        self.group_fk.setCheckable(True)
        self.group_fk.setChecked(False) 
        fk_layout = QFormLayout()

        self.combo_parent_layer = QComboBox()
        self.combo_parent_layer.currentIndexChanged.connect(self.populate_parent_concepts)
        fk_layout.addRow("1. Parent Table:", self.combo_parent_layer)

        self.combo_parent_term = QComboBox()
        fk_layout.addRow("2. Parent Concept:", self.combo_parent_term)

        self.combo_fk_col = QComboBox()
        fk_layout.addRow("3. Foreign Key Column:", self.combo_fk_col)

        self.group_fk.setLayout(fk_layout)
        self.layout.addWidget(self.group_fk)

        # 2. Browse Vocabulary
        self.layout.addWidget(QLabel("\n2. Browse Vocabulary:"))
        
        # Horizontal widget split for tree and preview
        browse_widget = QWidget()
        browse_layout = QHBoxLayout(browse_widget)
        browse_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left container
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Option to select sub-concepts recursively
        self.chk_auto_select_children = QCheckBox("Auto-select child concepts recursively (deselects parent)")
        self.chk_auto_select_children.setChecked(False)
        left_layout.addWidget(self.chk_auto_select_children)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Skosmos Concepts"])
        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.tree.itemChanged.connect(self.on_item_changed) 
        self.tree.currentItemChanged.connect(self.on_current_item_changed)
        left_layout.addWidget(self.tree)

        self.btn_load = QPushButton("Load Top Concepts")
        self.btn_load.clicked.connect(self.load_top_concepts)
        left_layout.addWidget(self.btn_load)
        
        browse_layout.addWidget(left_container, 3)
        
        # Right container (Preview Panel)
        self.preview_box = QGroupBox("Concept Preview")
        preview_layout = QVBoxLayout(self.preview_box)
        self.txt_preview = QTextBrowser()
        self.txt_preview.setOpenExternalLinks(True)
        preview_layout.addWidget(self.txt_preview)
        
        browse_layout.addWidget(self.preview_box, 2)
        
        self.layout.addWidget(browse_widget)

        # 3. Import Options & Button
        self.chk_update_existing = QCheckBox("Update/Sync existing concepts in database (match by URI)")
        self.chk_update_existing.setChecked(False)
        self.layout.addWidget(self.chk_update_existing)

        self.btn_import = QPushButton("3. Write Selected Concepts to Database")
        self.btn_import.clicked.connect(self.import_to_qgis)
        self.btn_import.setEnabled(False)
        self.layout.addWidget(self.btn_import)

        self.setLayout(self.layout)
        
        self.base_url = "https://skosmos.dbprojects.uni-bonn.de/rest/v1/hector"
        self.offline_concepts = {}
        self.label_cache = {}
        self.concept_details_cache = {}
        self.lang_checkboxes = {} # Mapping: column_name -> (QCheckBox, lang_code)
        
        self.populate_layers()

    def on_source_mode_changed(self):
        is_online = self.radio_online.isChecked()
        self.widget_online.setVisible(is_online)
        self.widget_offline.setVisible(not is_online)
        
        self.tree.blockSignals(True)
        self.tree.clear()
        self.tree.blockSignals(False)
        
        if is_online:
            self.btn_load.setText("Load Top Concepts")
            self.btn_load.setEnabled(True)
        else:
            if self.txt_file_path.text():
                self.btn_load.setText("Load Offline Concepts")
                self.btn_load.setEnabled(True)
            else:
                self.btn_load.setText("Select a SKOS File first")
                self.btn_load.setEnabled(False)

    def browse_offline_file(self):
        file_filter = "SKOS/RDF Files (*.rdf *.xml *.ttl *.jsonld *.nt);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SKOS File", "", file_filter)
        if file_path:
            self.txt_file_path.setText(file_path)
            self.btn_load.setText("Load Offline Concepts")
            self.btn_load.setEnabled(True)

    def populate_layers(self):
        self.combo_target_layer.clear()
        self.combo_parent_layer.clear()
        
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            # Bugfix: Filter for vector layers only to avoid crashes with raster/mesh layers
            if layer.type() == QgsMapLayerType.VectorLayer:
                self.combo_target_layer.addItem(layer.name(), layer.id())
                self.combo_parent_layer.addItem(layer.name(), layer.id())
            
        self.on_target_layer_changed()

    def on_target_layer_changed(self):
        self.combo_fk_col.clear()
        
        # Clear dynamically generated checkboxes in self.lang_layout
        layout = self.lang_layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.lang_checkboxes = {}

        layer_id = self.combo_target_layer.currentData()
        if not layer_id: return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer: return
            
        fields = layer.fields().names()
        
        # Standard mappings for common suffixes to ISO language codes
        LANG_MAP = {
            'ger': 'de', 'deu': 'de', 'de': 'de',
            'eng': 'en', 'en': 'en',
            'fre': 'fr', 'fra': 'fr', 'fr': 'fr',
            'spa': 'es', 'es': 'es',
            'ita': 'it', 'it': 'it',
            'dut': 'nl', 'nld': 'nl', 'nl': 'nl',
            'rus': 'ru', 'ru': 'ru',
            'lat': 'la', 'la': 'la'
        }
        
        # Identify foreign key columns (exclude id, uri, and columns starting with pref_)
        for field in fields:
            if field not in ['id', 'uri'] and not field.startswith('pref_'):
                self.combo_fk_col.addItem(field)

        # Dynamically generate language check boxes based on database columns matching 'pref_XXX'
        pref_fields = [f for f in fields if f.startswith('pref_')]
        for col in pref_fields:
            lang_suffix = col.split('_')[-1]
            lang_code = LANG_MAP.get(lang_suffix, lang_suffix) # Fallback to suffix as API language code
            
            chk = QCheckBox(f"Import {col} ('{lang_code}')")
            chk.setChecked(True)
            layout.addWidget(chk)
            self.lang_checkboxes[col] = (chk, lang_code)

    def setup_table_schema(self):
        layer_id = self.combo_target_layer.currentData()
        if not layer_id:
            QMessageBox.warning(self, "Warning", "Please select a target table first.")
            return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            QMessageBox.warning(self, "Warning", "Selected layer not found.")
            return
            
        dlg = SchemaSetupDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # We want to add fields
            field_configs = []
            if dlg.chk_de.isChecked(): field_configs.append(('pref_ger', QVariant.String, 100))
            if dlg.chk_en.isChecked(): field_configs.append(('pref_eng', QVariant.String, 100))
            if dlg.chk_fr.isChecked(): field_configs.append(('pref_fre', QVariant.String, 100))
            if dlg.chk_es.isChecked(): field_configs.append(('pref_spa', QVariant.String, 100))
            if dlg.chk_la.isChecked(): field_configs.append(('pref_lat', QVariant.String, 100))
            
            if dlg.chk_wiki.isChecked(): field_configs.append(('wikidata', QVariant.String, 255))
            if dlg.chk_wiki_desc.isChecked(): field_configs.append(('wikidata_desc', QVariant.String, 1000))
            if dlg.chk_gnd.isChecked(): field_configs.append(('gnd', QVariant.String, 255))
            if dlg.chk_aat.isChecked(): field_configs.append(('aat', QVariant.String, 255))
                
            # Check what fields already exist
            existing = layer.fields().names()
            
            # Start editing session
            if not layer.isEditable() and not layer.startEditing():
                QMessageBox.critical(self, "Edit Error", f"Could not start editing on layer '{layer.name()}'. Is it read-only?")
                return
                
            from qgis.core import QgsField
            added_count = 0
            for name, ftype, length in field_configs:
                if name not in existing:
                    field = QgsField(name, ftype, "varchar", length)
                    if layer.addAttribute(field):
                        added_count += 1
                        
            if added_count > 0:
                if layer.commitChanges():
                    QMessageBox.information(self, "Success", f"Successfully added {added_count} columns to '{layer.name()}'!")
                    self.on_target_layer_changed() # Refresh fields mapping
                else:
                    layer.rollBack()
                    QMessageBox.critical(self, "Error", f"Failed to commit column changes to database.")
            else:
                layer.rollBack()
                QMessageBox.information(self, "Information", "All selected columns already exist in the table.")

    def fetch_wikidata_details(self, wikidata_id):
        """Fetch details (descriptions in various languages, coordinates, GND, AAT) from Wikidata API."""
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
        headers = {"User-Agent": "SkosConnectQgisPlugin/1.0 (contact: bcdh@uni-bonn.de)"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                entity = data.get("entities", {}).get(wikidata_id, {})
                
                # Fetch descriptions in common languages
                descriptions = {}
                for lang in ["de", "en", "fr", "es", "la"]:
                    descriptions[lang] = entity.get("descriptions", {}).get(lang, {}).get("value", "")
                
                # Coordinates (P625)
                lat, lon = None, None
                claims = entity.get("claims", {})
                p625 = claims.get("P625", [])
                if p625:
                    mainsnak = p625[0].get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    value = datavalue.get("value", {})
                    lat = value.get("latitude")
                    lon = value.get("longitude")
                    
                # GND ID (P227)
                gnd_val = None
                p227 = claims.get("P227", [])
                if p227:
                    gnd_val = p227[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    
                # AAT ID (P1014)
                aat_val = None
                p1014 = claims.get("P1014", [])
                if p1014:
                    aat_val = p1014[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    
                return {
                    "descriptions": descriptions,
                    "latitude": lat,
                    "longitude": lon,
                    "gnd_id": gnd_val,
                    "aat_id": aat_val
                }
        except Exception as e:
            QgsMessageLog.logMessage(f"SkosConnect: Wikidata API error for {wikidata_id}: {e}", "Plugins", Qgis.Warning)
        return {}

    def fetch_gnd_details(self, gnd_id):
        """Fetch details (coordinates) from Lobid GND API."""
        url = f"https://lobid.org/gnd/{gnd_id}.json"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                
                lat, lon = None, None
                # Check hasGeometry
                has_geometry = data.get("hasGeometry", [])
                if has_geometry:
                    as_wkt_list = has_geometry[0].get("asWKT", [])
                    if as_wkt_list:
                        wkt = as_wkt_list[0]
                        m = re.search(r'Point\s*\(\s*([+-]?\d+\.?\d*)\s+([+-]?\d+\.?\d*)\s*\)', wkt, re.IGNORECASE)
                        if m:
                            lon = float(m.group(1))
                            lat = float(m.group(2))
                            
                return {
                    "latitude": lat,
                    "longitude": lon
                }
        except Exception as e:
            QgsMessageLog.logMessage(f"SkosConnect: Lobid GND API error for {gnd_id}: {e}", "Plugins", Qgis.Warning)
        return {}

    def on_current_item_changed(self, current, previous):
        if not current:
            self.txt_preview.clear()
            return
            
        uri = current.data(0, Qt.UserRole)
        if not uri or uri in ["...loading sub-concepts...", "(No sub-concepts)"]:
            self.txt_preview.clear()
            return
            
        self.show_concept_preview(uri)

    def show_concept_preview(self, uri):
        self.txt_preview.setHtml(f"<h4>Concept Details</h4><p>URI: <code>{uri}</code></p><p><i>Loading details...</i></p>")
        QApplication.processEvents()
        
        # 1. Fetch details (either from cache or API/file)
        details = self.get_concept_details(uri)
        if not details:
            self.txt_preview.setHtml(f"<h4>Concept Details</h4><p>URI: <code>{uri}</code></p><p><i>No details found.</i></p>")
            return
            
        # 2. Build nice HTML
        html = "<div style='font-family: sans-serif; font-size: 11px;'>"
        html += f"<h3>{details.get('pref_label', 'Concept Details')}</h3>"
        html += f"<p><b>URI:</b><br/><a href='{uri}'>{uri}</a></p>"
        
        # Labels in different languages
        labels = details.get("labels", {})
        if labels:
            html += "<p><b>Labels:</b><br/>"
            for lang, val in labels.items():
                html += f"• <code>{lang}</code>: {val}<br/>"
            html += "</p>"
            
        # Matches
        exact_matches = details.get("exactMatch", [])
        close_matches = details.get("closeMatch", [])
        
        if exact_matches:
            html += "<p><b>exactMatch (LOD):</b><br/>"
            for m in exact_matches:
                html += f"• <a href='{m}'>{m}</a><br/>"
            html += "</p>"
            
        if close_matches:
            html += "<p><b>closeMatch (LOD):</b><br/>"
            for m in close_matches:
                html += f"• <a href='{m}'>{m}</a><br/>"
            html += "</p>"
            
        html += "</div>"
        self.txt_preview.setHtml(html)

    def get_concept_details(self, uri):
        # Use cache if present
        if hasattr(self, 'concept_details_cache') and uri in self.concept_details_cache:
            return self.concept_details_cache[uri]
            
        if not hasattr(self, 'concept_details_cache'):
            self.concept_details_cache = {}
            
        details = {
            "uri": uri,
            "pref_label": "",
            "labels": {},
            "exactMatch": [],
            "closeMatch": []
        }
        
        if not self.radio_online.isChecked():
            # Offline mode: extract from self.offline_concepts
            concept = self.offline_concepts.get(uri)
            if concept:
                details["labels"] = concept.get("labels", {})
                details["exactMatch"] = concept.get("exactMatch", [])
                details["closeMatch"] = concept.get("closeMatch", [])
                details["pref_label"] = get_concept_label(concept, self.get_tree_language(), uri)
        else:
            # Online mode: fetch from Skosmos /data
            try:
                resp = requests.get(f"{self.base_url}/data", params={"uri": uri}, headers={"Accept": "application/json"}, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    graph = data.get("graph", [])
                    
                    # Look for our concept node
                    concept_node = None
                    for node in graph:
                        if node.get("uri") == uri or node.get("id") == uri:
                            concept_node = node
                            break
                            
                    if concept_node:
                        # Extract prefLabels
                        pref_labels = concept_node.get("prefLabel")
                        if pref_labels:
                            if isinstance(pref_labels, list):
                                for pl in pref_labels:
                                    if isinstance(pl, dict):
                                        lang = pl.get("lang") or pl.get("@language") or "default"
                                        val = pl.get("value") or pl.get("@value")
                                        if val: details["labels"][lang.lower()] = val
                                    elif isinstance(pl, str):
                                        details["labels"]["default"] = pl
                            elif isinstance(pref_labels, dict):
                                lang = pref_labels.get("lang") or pref_labels.get("@language") or "default"
                                val = pref_labels.get("value") or pref_labels.get("@value")
                                if val: details["labels"][lang.lower()] = val
                            elif isinstance(pref_labels, str):
                                details["labels"]["default"] = pref_labels
                                
                        # Set preferred label for preview title
                        details["pref_label"] = get_concept_label(details, self.get_tree_language(), uri)
                        
                        # Extract matches
                        details["exactMatch"] = self.extract_property_uris(concept_node, "exactMatch")
                        details["closeMatch"] = self.extract_property_uris(concept_node, "closeMatch")
            except Exception as e:
                QgsMessageLog.logMessage(f"SkosConnect: Error getting concept details for {uri}: {e}", "Plugins", Qgis.Warning)
                details["pref_label"] = uri
                
        self.concept_details_cache[uri] = details
        return details

    def extract_property_uris(self, item, key):
        uris = []
        for k in [key, f"skos:{key}", f"http://www.w3.org/2004/02/skos/core#{key}"]:
            val = item.get(k)
            if val:
                if isinstance(val, list):
                    for v in val:
                        if isinstance(v, dict):
                            uris.append(v.get("uri") or v.get("value") or v.get("@id"))
                        elif isinstance(v, str):
                            uris.append(v)
                elif isinstance(val, dict):
                    uris.append(val.get("uri") or val.get("value") or val.get("@id"))
                elif isinstance(val, str):
                    uris.append(val)
        return [u for u in uris if u]

    def populate_parent_concepts(self):
        self.combo_parent_term.clear()
        layer_id = self.combo_parent_layer.currentData()
        if not layer_id: return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer: return
        
        # Populate parent concept terms
        for f in layer.getFeatures():
            uri = f['uri']
            if uri:
                label = f.attribute('pref_ger') or f.attribute('pref_eng') or uri
                self.combo_parent_term.addItem(label, uri)

    def get_tree_language(self):
        """Determine what language to load concepts inside the tree widget."""
        # Use first checked language, fallback to 'de' or 'en'
        for col, (chk, lang_code) in self.lang_checkboxes.items():
            if chk.isChecked():
                return lang_code
        return 'de'

    def load_top_concepts(self):
        self.tree.blockSignals(True) 
        self.tree.clear()
        
        tree_lang = self.get_tree_language()
        
        if self.radio_online.isChecked():
            self.btn_load.setText("Loading...")
            self.btn_load.setEnabled(False)
            QApplication.processEvents()
            
            # Use dynamic URL from the text input field
            self.base_url = self.txt_api_url.text().strip().rstrip('/')
            
            try:
                # Bugfix: Added 10s timeout to prevent infinite blocks if server hangs
                resp = requests.get(f"{self.base_url}/topConcepts", params={'lang': tree_lang}, timeout=10)
                resp.raise_for_status()
                tops = resp.json().get('topconcepts', [])
                
                for top in tops:
                    item = QTreeWidgetItem([top.get('label')])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                    item.setData(0, Qt.UserRole, top.get('uri'))
                    
                    dummy = QTreeWidgetItem(["...loading sub-concepts..."])
                    item.addChild(dummy)
                    self.tree.addTopLevelItem(item)
                            
                self.btn_load.setText("Top Concepts Loaded!")
                self.btn_import.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load:\n{str(e)}")
                self.btn_load.setText("Error. Try again.")
                self.btn_load.setEnabled(True)
                # Log error details to QGIS log
                QgsMessageLog.logMessage(f"SkosConnect: API error loading top concepts: {e}", "Plugins", Qgis.Warning)
            finally:
                self.tree.blockSignals(False)
        else:
            # Offline mode
            file_path = self.txt_file_path.text()
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "Warning", "Please select a valid SKOS file first.")
                self.tree.blockSignals(False)
                return
                
            self.btn_load.setText("Parsing File...")
            self.btn_load.setEnabled(False)
            QApplication.processEvents()
            
            try:
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext == '.ttl' and not RDFLIB_AVAILABLE:
                    QMessageBox.warning(self, "Library Missing", 
                                        "Turtle (.ttl) files require the 'rdflib' library.\n"
                                        "Please install 'rdflib' (e.g. via OSGeo4W Shell: pip3 install rdflib) "
                                        "or load an RDF/XML (.rdf, .xml) file instead.")
                    self.btn_load.setText("Load Offline Concepts")
                    self.btn_load.setEnabled(True)
                    self.tree.blockSignals(False)
                    return
                
                # Parse depending on rdflib availability
                if RDFLIB_AVAILABLE:
                    self.offline_concepts = parse_skos_with_rdflib(file_path)
                else:
                    self.offline_concepts = parse_skos_rdf_xml(file_path)
                
                if not self.offline_concepts:
                    QMessageBox.warning(self, "No Concepts Found", "No SKOS Concepts were found in the file.")
                    self.btn_load.setText("Load Offline Concepts")
                    self.btn_load.setEnabled(True)
                    self.tree.blockSignals(False)
                    return
                
                # Find root concepts
                roots = find_roots(self.offline_concepts)
                
                for r_uri in roots:
                    concept = self.offline_concepts[r_uri]
                    label = get_concept_label(concept, tree_lang, r_uri)
                    
                    item = QTreeWidgetItem([label])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                    item.setData(0, Qt.UserRole, r_uri)
                    
                    if concept['narrower']:
                        dummy = QTreeWidgetItem(["...loading sub-concepts..."])
                        item.addChild(dummy)
                    self.tree.addTopLevelItem(item)
                    
                self.btn_load.setText("Offline Concepts Loaded!")
                self.btn_import.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Parsing Error", f"Failed to parse SKOS file:\n{str(e)}")
                self.btn_load.setText("Load Offline Concepts")
                self.btn_load.setEnabled(True)
                QgsMessageLog.logMessage(f"SkosConnect: File parsing error: {e}", "Plugins", Qgis.Warning)
            finally:
                self.tree.blockSignals(False)

    def fetch_children_for_item(self, item):
        uri = item.data(0, Qt.UserRole)
        item.removeChild(item.child(0)) 
        
        tree_lang = self.get_tree_language()
        
        if self.radio_online.isChecked():
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                # Bugfix: Added 10s timeout
                c_resp = requests.get(f"{self.base_url}/children", params={'uri': uri, 'lang': tree_lang}, timeout=10)
                if c_resp.status_code == 200:
                    children = c_resp.json().get('narrower', [])
                    if not children:
                        item.addChild(QTreeWidgetItem(["(No sub-concepts)"]))
                    else:
                        for child in children:
                            c_item = QTreeWidgetItem([child.get('prefLabel')])
                            c_item.setFlags(c_item.flags() | Qt.ItemIsUserCheckable)
                            c_item.setCheckState(0, Qt.Unchecked)
                            c_item.setData(0, Qt.UserRole, child.get('uri'))
                            
                            if child.get('hasChildren', False):
                                c_item.addChild(QTreeWidgetItem(["...loading sub-concepts..."]))
                            item.addChild(c_item)
            except Exception as e:
                item.addChild(QTreeWidgetItem([f"Error: {str(e)}"]))
                QgsMessageLog.logMessage(f"SkosConnect: API error fetching children: {e}", "Plugins", Qgis.Warning)
            finally:
                QApplication.restoreOverrideCursor()
        else:
            # Offline mode
            if not self.offline_concepts or uri not in self.offline_concepts:
                item.addChild(QTreeWidgetItem(["(No sub-concepts)"]))
                return
                
            concept = self.offline_concepts[uri]
            children_uris = concept['narrower']
            
            if not children_uris:
                item.addChild(QTreeWidgetItem(["(No sub-concepts)"]))
            else:
                for c_uri in children_uris:
                    if c_uri in self.offline_concepts:
                        child = self.offline_concepts[c_uri]
                        label = get_concept_label(child, tree_lang, c_uri)
                        
                        c_item = QTreeWidgetItem([label])
                        c_item.setFlags(c_item.flags() | Qt.ItemIsUserCheckable)
                        c_item.setCheckState(0, Qt.Unchecked)
                        c_item.setData(0, Qt.UserRole, c_uri)
                        
                        if child['narrower']:
                            c_item.addChild(QTreeWidgetItem(["...loading sub-concepts..."]))
                        item.addChild(c_item)
                    else:
                        c_item = QTreeWidgetItem([c_uri])
                        c_item.setFlags(c_item.flags() | Qt.ItemIsUserCheckable)
                        c_item.setCheckState(0, Qt.Unchecked)
                        c_item.setData(0, Qt.UserRole, c_uri)
                        item.addChild(c_item)

    def on_item_expanded(self, item):
        self.tree.blockSignals(True)
        if item.childCount() == 1 and item.child(0).text(0) == "...loading sub-concepts...":
            self.fetch_children_for_item(item)
        self.tree.blockSignals(False)

    def on_item_changed(self, item, column):
        self.tree.blockSignals(True) 
        
        is_checked = (item.checkState(0) == Qt.Checked)
        
        # Bugfix: Use decoupled checkbox instead of linking tree check behavior to foreign key checkbox
        if self.chk_auto_select_children.isChecked():
            if is_checked:
                if item.childCount() == 1 and item.child(0).text(0) == "...loading sub-concepts...":
                    self.fetch_children_for_item(item)
                
                has_real_children = False
                
                for i in range(item.childCount()):
                    child = item.child(i)
                    if child.text(0) not in ["(No sub-concepts)", "...loading sub-concepts..."]:
                        child.setCheckState(0, Qt.Checked)
                        has_real_children = True
                
                if has_real_children:
                    item.setCheckState(0, Qt.Unchecked)
                    
            else:
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, Qt.Unchecked)
                    
        self.tree.blockSignals(False)

    def fetch_label_from_api(self, uri, lang):
        cache_key = f"{uri}_{lang}"
        if cache_key in self.label_cache:
            return self.label_cache[cache_key]
            
        try:
            # Bugfix: Added 5s timeout and proper logging
            resp = requests.get(f"{self.base_url}/label", params={'uri': uri, 'lang': lang}, timeout=5)
            if resp.status_code == 200:
                label = resp.json().get('prefLabel', '')
                self.label_cache[cache_key] = label
                return label
        except Exception as e:
            QgsMessageLog.logMessage(f"SkosConnect: Error fetching label for {uri} ({lang}): {e}", "Plugins", Qgis.Warning)
        return ''

    def import_to_qgis(self):
        target_layer_id = self.combo_target_layer.currentData()
        if not target_layer_id: return
        layer = QgsProject.instance().mapLayer(target_layer_id)
        if not layer: return
        fields = layer.fields().names()

        if 'uri' not in fields:
            QMessageBox.critical(self, "Security Halt", f"Target table '{layer.name()}' must have a 'uri' column!")
            return
            
        # Check if any language is selected
        any_selected = any(chk.isChecked() for chk, _ in self.lang_checkboxes.values())
        if not any_selected and self.lang_checkboxes:
            QMessageBox.warning(self, "No Language Selected", "Please select at least one language to import.")
            return

        fk_col = None
        parent_id = None
        if self.group_fk.isChecked():
            fk_col = self.combo_fk_col.currentText()
            parent_id = self.combo_parent_term.currentData()
            if not fk_col or parent_id is None:
                QMessageBox.critical(self, "Error", "Foreign Key configuration is incomplete.")
                return

        checked_uris = set()
        checked_items = []
        
        def collect_checked(item):
            if item.checkState(0) == Qt.Checked:
                term = item.text(0)
                uri = item.data(0, Qt.UserRole)
                if term not in ["...loading sub-concepts...", "(No sub-concepts)"]:
                    if uri not in checked_uris: 
                        checked_uris.add(uri)
                        checked_items.append({"ui_term": term, "uri": uri})
            for i in range(item.childCount()):
                collect_checked(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            collect_checked(self.tree.topLevelItem(i))

        total_items = len(checked_items)
        if total_items == 0:
            QMessageBox.warning(self, "Empty Selection", "No concepts selected!")
            return

        existing_features = {f['uri']: f for f in layer.getFeatures() if f['uri']}
        
        features_to_add = []
        features_to_update = []
        skipped_count = 0
        updated_count = 0

        self.btn_import.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        is_spatial = layer.isSpatial()

        try:
            for index, item in enumerate(checked_items, 1):
                self.btn_import.setText(f"Processing Concept {index} of {total_items}...")
                QApplication.processEvents() 

                is_update = item['uri'] in existing_features
                if is_update:
                    if not self.chk_update_existing.isChecked():
                        skipped_count += 1
                        continue
                    feat = existing_features[item['uri']]
                else:
                    feat = QgsFeature(layer.fields())
                    feat.setAttribute('uri', item['uri'])
                
                # Fetch details for matches & labels
                details = self.get_concept_details(item['uri'])
                exact_matches = details.get("exactMatch", [])
                close_matches = details.get("closeMatch", [])
                all_matches = exact_matches + close_matches
                
                # Identify external IDs
                wikidata_id = None
                for m in all_matches:
                    if "wikidata.org" in m:
                        qid_match = re.search(r'Q\d+', m)
                        if qid_match:
                            wikidata_id = qid_match.group(0)
                            break
                            
                gnd_id = None
                for m in all_matches:
                    if "d-nb.info/gnd" in m:
                        parts = m.rstrip('/').split('/')
                        if parts:
                            gnd_id = parts[-1]
                            break
                
                # Fetch rich LOD info if columns exist or layer is spatial
                wiki_details = {}
                gnd_details = {}
                
                need_wikidata = ('wikidata_desc' in fields) or ('aat' in fields) or ('gnd' in fields) or (is_spatial)
                
                if wikidata_id and need_wikidata:
                    wiki_details = self.fetch_wikidata_details(wikidata_id)
                if gnd_id and is_spatial:
                    gnd_details = self.fetch_gnd_details(gnd_id)
                    
                # Extract coordinates
                lat, lon = None, None
                if gnd_details.get("latitude") is not None:
                    lat = gnd_details["latitude"]
                    lon = gnd_details["longitude"]
                elif wiki_details.get("latitude") is not None:
                    lat = wiki_details["latitude"]
                    lon = wiki_details["longitude"]
                    
                # Create geometry if spatial
                geom = None
                if is_spatial and lat is not None and lon is not None:
                    point = QgsPointXY(lon, lat)
                    if layer.crs().authid() != "EPSG:4326":
                        try:
                            source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                            transform = QgsCoordinateTransform(source_crs, layer.crs(), QgsProject.instance())
                            point = transform.transform(point)
                        except Exception as tr_err:
                            QgsMessageLog.logMessage(f"SkosConnect: CRS transform error: {tr_err}", "Plugins", Qgis.Warning)
                    geom = QgsGeometry.fromPointXY(point)

                # Set labels dynamically for checked languages
                fallback_mode = self.combo_fallback_lang.currentData()
                for col, (chk, lang_code) in self.lang_checkboxes.items():
                    if chk.isChecked() and col in fields:
                        val = details.get("labels", {}).get(lang_code, "")
                        if not val:
                            val = get_concept_label(details, lang_code, item['ui_term'], fallback_mode)
                        feat.setAttribute(col, val)
                    
                # Set matches fields
                if 'wikidata' in fields:
                    wiki_uri = next((m for m in all_matches if "wikidata.org" in m), "")
                    if not wiki_uri and wikidata_id:
                        wiki_uri = f"http://www.wikidata.org/entity/{wikidata_id}"
                    feat.setAttribute('wikidata', wiki_uri)
                    
                if 'gnd' in fields:
                    gnd_uri = next((m for m in all_matches if "d-nb.info/gnd" in m), "")
                    if not gnd_uri and wiki_details.get("gnd_id"):
                        gnd_uri = f"http://d-nb.info/gnd/{wiki_details['gnd_id']}"
                    feat.setAttribute('gnd', gnd_uri)
                    
                if 'aat' in fields:
                    aat_uri = next((m for m in all_matches if "vocab.getty.edu/aat" in m), "")
                    if not aat_uri and wiki_details.get("aat_id"):
                        aat_uri = f"http://vocab.getty.edu/aat/{wiki_details['aat_id']}"
                    feat.setAttribute('aat', aat_uri)
                    
                # Set enrichment columns
                if 'wikidata_desc' in fields:
                    desc_dict = {}
                    for col, (chk, lang_code) in self.lang_checkboxes.items():
                        if chk.isChecked():
                            desc_val = wiki_details.get("descriptions", {}).get(lang_code, "")
                            if desc_val:
                                desc_dict[lang_code] = desc_val
                    # Fallback to English description if empty
                    if not desc_dict and wiki_details.get("descriptions", {}).get("en"):
                        desc_dict["en"] = wiki_details["descriptions"]["en"]
                    feat.setAttribute('wikidata_desc', json.dumps(desc_dict, ensure_ascii=False))
                    
                if self.group_fk.isChecked() and fk_col:
                    feat.setAttribute(fk_col, parent_id)
                    
                if is_spatial and geom:
                    feat.setGeometry(geom)
                    
                if is_update:
                    features_to_update.append(feat)
                else:
                    features_to_add.append(feat)

            if features_to_add or features_to_update:
                self.btn_import.setText("Writing to Database...")
                QApplication.processEvents()
                
                if not layer.isEditable() and not layer.startEditing():
                    QMessageBox.critical(self, "Edit Error", f"Could not start editing on layer '{layer.name()}'. Is it read-only?")
                    return
                
                # Update existing
                if features_to_update:
                    for f in features_to_update:
                        layer.updateFeature(f)
                    updated_count = len(features_to_update)
                    
                # Add new
                added_count = 0
                if features_to_add:
                    success = layer.addFeatures(features_to_add)
                    if success:
                        added_count = len(features_to_add)
                
                if layer.commitChanges():
                    msg = "✅ Concept Import completed!"
                    if added_count > 0:
                        msg += f"\n- {added_count} concepts imported."
                    if updated_count > 0:
                        msg += f"\n- {updated_count} concepts updated."
                    if skipped_count > 0:
                        msg += f"\n⚠️ {skipped_count} concepts skipped."
                    QMessageBox.information(self, "Success", msg)
                else:
                    commit_errs = layer.commitErrors()
                    layer.rollBack()
                    err_msg = "\n".join(commit_errs) if commit_errs else "Database rejected the updates."
                    QMessageBox.critical(self, "Database Error", f"Failed to save changes:\n{err_msg}")
            else:
                QMessageBox.warning(self, "Nothing to do", "All selected concepts already exist in this table!")
                
        finally:
            self.btn_import.setText("3. Write Selected Concepts to Database")
            self.btn_import.setEnabled(True)
            QApplication.restoreOverrideCursor()


# ---------------------------------------------------------
# QGIS PLUGIN-WRAPPER
# ---------------------------------------------------------
class SkosConnectPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = None
        self.action = None
        self.dialog = None

    def initGui(self):
        # Retrieve custom SVG icon from plugin directory
        icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")
        icon = QIcon(icon_path)
        
        self.action = QAction(icon, "SkosConnect LOD Importer", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        
        # Add to the "Database" Toolbar
        self.iface.addToolBarIcon(self.action)
        # Add to the "Plugins" menu
        self.iface.addPluginToMenu("SkosConnect", self.action)

    def unload(self):
        # Clean up GUI actions when plugin is deactivated
        self.iface.removePluginMenu("SkosConnect", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        # Open dialog window
        if not self.dialog:
            self.dialog = SkosConnectMultilingualImporter(self.iface.mainWindow())
        
        # Refresh the target layers lists on every dialog show
        self.dialog.populate_layers()
        self.dialog.show()
