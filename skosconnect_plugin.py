from qgis.PyQt.QtWidgets import (QAction, QDialog, QVBoxLayout, QPushButton, 
                                QTreeWidget, QTreeWidgetItem, QMessageBox, 
                                QApplication, QLabel, QComboBox, QGroupBox, 
                                QFormLayout, QCheckBox, QHBoxLayout, QWidget, 
                                QRadioButton, QLineEdit, QFileDialog)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsFeature, QgsApplication, QgsMapLayerType, QgsMessageLog, Qgis
import requests
import os
import xml.etree.ElementTree as ET

# Try to import rdflib for advanced RDF parsing (e.g. Turtle)
try:
    import rdflib
    HAS_RDFLIB = True
except ImportError:
    HAS_RDFLIB = False

# ---------------------------------------------------------
# OFFLINE RDF/SKOS PARSERS
# ---------------------------------------------------------

def get_rdflib_format(file_path):
    """Map file extension to rdflib parser format name."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.ttl':
        return 'turtle'
    elif ext in ['.rdf', '.xml']:
        return 'xml'
    elif ext == '.jsonld':
        return 'json-ld'
    elif ext == '.nt':
        return 'nt'
    return 'xml'

def parse_skos_with_rdflib(file_path, file_format):
    """Parse SKOS concept hierarchy from file using rdflib."""
    import rdflib
    g = rdflib.Graph()
    g.parse(file_path, format=file_format)
    
    concepts = {}
    SKOS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    
    # Iterate over all subjects that are instances of skos:Concept
    for s in g.subjects(rdflib.RDF.type, SKOS.Concept):
        uri = str(s)
        concepts[uri] = {
            'uri': uri,
            'pref_de': '',
            'pref_en': '',
            'narrower': [],
            'broader': []
        }
        
        # Extract preferred labels
        for label in g.objects(s, SKOS.prefLabel):
            lang = getattr(label, 'language', '') or ''
            lang = lang.lower()
            text = str(label)
            if 'de' in lang:
                concepts[uri]['pref_de'] = text
            elif 'en' in lang or not concepts[uri]['pref_en']:
                concepts[uri]['pref_en'] = text
                
        # Extract direct hierarchical relationships
        for child in g.objects(s, SKOS.narrower):
            concepts[uri]['narrower'].append(str(child))
        for parent in g.objects(s, SKOS.broader):
            concepts[uri]['broader'].append(str(parent))
            
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
    """Fallback XML parser for standard RDF/XML SKOS files without rdflib dependency."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    concepts = {}
    
    RDF_ABOUT = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
    RDF_RESOURCE = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
    RDF_TYPE = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}type"
    SKOS_CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
    
    for elem in root.iter():
        is_concept = False
        if elem.tag.endswith("}Concept"):
            is_concept = True
        else:
            # Check children for rdf:type
            for child in elem:
                if child.tag == RDF_TYPE and child.attrib.get(RDF_RESOURCE) == SKOS_CONCEPT:
                    is_concept = True
                    break
        
        if is_concept:
            uri = elem.attrib.get(RDF_ABOUT)
            if not uri:
                continue
            
            if uri not in concepts:
                concepts[uri] = {
                    'uri': uri,
                    'pref_de': '',
                    'pref_en': '',
                    'narrower': [],
                    'broader': []
                }
            
            concept = concepts[uri]
            
            # Read properties
            for child in elem:
                local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                
                if local_name == 'prefLabel':
                    lang = ""
                    for attr_name, attr_val in child.attrib.items():
                        if attr_name.endswith("}lang"):
                            lang = attr_val.lower()
                            break
                    text = child.text or ''
                    if 'de' in lang:
                        concept['pref_de'] = text
                    elif 'en' in lang or not concept['pref_en']:
                        concept['pref_en'] = text
                elif local_name == 'narrower':
                    child_uri = child.attrib.get(RDF_RESOURCE)
                    if child_uri:
                        concept['narrower'].append(child_uri)
                elif local_name == 'broader':
                    parent_uri = child.attrib.get(RDF_RESOURCE)
                    if parent_uri:
                        concept['broader'].append(parent_uri)
                        
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


# ---------------------------------------------------------
# DIALOG WINDOW IMPLEMENTATION
# ---------------------------------------------------------
class SkosConnectMultilingualImporter(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔌 SkosConnect: Multilingual LOD Import")
        self.resize(700, 950)
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
        self.combo_target_layer = QComboBox()
        self.combo_target_layer.currentIndexChanged.connect(self.on_target_layer_changed)
        self.layout.addWidget(self.combo_target_layer)

        # Dynamic Language Selection
        self.group_lang = QGroupBox("Language Import Options (Detected from Table Columns)")
        lang_layout = QHBoxLayout()
        self.chk_ger = QCheckBox("Import German ('pref_ger')")
        self.chk_eng = QCheckBox("Import English ('pref_eng')")
        self.chk_ger.setEnabled(False)
        self.chk_eng.setEnabled(False)
        lang_layout.addWidget(self.chk_ger)
        lang_layout.addWidget(self.chk_eng)
        self.group_lang.setLayout(lang_layout)
        self.layout.addWidget(self.group_lang)

        # Optional Foreign Key Link
        self.group_fk = QGroupBox("Optional Hierarchy Link (e.g., link Periods to Epoche)")
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
        
        # Option to select sub-concepts recursively
        self.chk_auto_select_children = QCheckBox("Auto-select child concepts recursively (deselects parent)")
        self.chk_auto_select_children.setChecked(False)
        self.layout.addWidget(self.chk_auto_select_children)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Skosmos Concepts"])
        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.tree.itemChanged.connect(self.on_item_changed) 
        self.layout.addWidget(self.tree)

        self.btn_load = QPushButton("Load Top Concepts (German Base UI)")
        self.btn_load.clicked.connect(self.load_top_concepts)
        self.layout.addWidget(self.btn_load)

        # 3. Import Button
        self.btn_import = QPushButton("3. Write Selected Concepts to Database")
        self.btn_import.clicked.connect(self.import_to_qgis)
        self.btn_import.setEnabled(False)
        self.layout.addWidget(self.btn_import)

        self.setLayout(self.layout)
        
        self.base_url = "https://skosmos.dbprojects.uni-bonn.de/rest/v1/hector"
        self.offline_concepts = {}
        self.label_cache = {}
        
        self.populate_layers()

    def on_source_mode_changed(self):
        is_online = self.radio_online.isChecked()
        self.widget_online.setVisible(is_online)
        self.widget_offline.setVisible(not is_online)
        
        self.tree.blockSignals(True)
        self.tree.clear()
        self.tree.blockSignals(False)
        
        if is_online:
            self.btn_load.setText("Load Top Concepts (German Base UI)")
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
        self.chk_ger.setEnabled(False)
        self.chk_eng.setEnabled(False)
        self.chk_ger.setChecked(False)
        self.chk_eng.setChecked(False)

        layer_id = self.combo_target_layer.currentData()
        if not layer_id: return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer: return
            
        fields = layer.fields().names()
        
        for field in fields:
            if field not in ['id', 'pref_ger', 'pref_eng', 'uri']:
                self.combo_fk_col.addItem(field)

        if 'pref_ger' in fields:
            self.chk_ger.setEnabled(True)
            self.chk_ger.setChecked(True)
        if 'pref_eng' in fields:
            self.chk_eng.setEnabled(True)
            self.chk_eng.setChecked(True)

    def populate_parent_concepts(self):
        self.combo_parent_term.clear()
        layer_id = self.combo_parent_layer.currentData()
        if not layer_id: return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer: return
            
        fields = layer.fields().names()
        if 'id' not in fields or ('pref_ger' not in fields and 'term' not in fields):
            self.combo_parent_term.addItem("Invalid table (missing id or label)")
            return

        label_col = 'pref_ger' if 'pref_ger' in fields else 'term'
        for f in layer.getFeatures():
            val = f[label_col]
            label_str = str(val) if val is not None else "Unbenannt"
            self.combo_parent_term.addItem(label_str, f['id'])

    def load_top_concepts(self):
        self.tree.blockSignals(True) 
        self.tree.clear()
        
        if self.radio_online.isChecked():
            self.btn_load.setText("Loading...")
            self.btn_load.setEnabled(False)
            QApplication.processEvents()
            
            # Use dynamic URL from the text input field
            self.base_url = self.txt_api_url.text().strip().rstrip('/')
            
            try:
                # Bugfix: Added 10s timeout to prevent unendliche blocks if server hangs
                resp = requests.get(f"{self.base_url}/topConcepts", params={'lang': 'de'}, timeout=10)
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
                
                if ext == '.ttl' and not HAS_RDFLIB:
                    QMessageBox.warning(self, "Library Missing", 
                                        "Turtle (.ttl) files require the 'rdflib' library.\n"
                                        "Please install 'rdflib' (e.g. via OSGeo4W Shell: pip3 install rdflib) "
                                        "or load an RDF/XML (.rdf, .xml) file instead.")
                    self.btn_load.setText("Load Offline Concepts")
                    self.btn_load.setEnabled(True)
                    self.tree.blockSignals(False)
                    return
                
                # Parse depending on rdflib availability
                if HAS_RDFLIB:
                    fmt = get_rdflib_format(file_path)
                    self.offline_concepts = parse_skos_with_rdflib(file_path, fmt)
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
                    label = concept['pref_de'] or concept['pref_en'] or r_uri
                    
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
        
        if self.radio_online.isChecked():
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                # Bugfix: Added 10s timeout
                c_resp = requests.get(f"{self.base_url}/children", params={'uri': uri, 'lang': 'de'}, timeout=10)
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
                        label = child['pref_de'] or child['pref_en'] or c_uri
                        
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
            
        if not self.chk_ger.isChecked() and not self.chk_eng.isChecked():
            QMessageBox.warning(self, "No Language Selected", "Please select at least one language to import.")
            return

        fk_col = None
        parent_id = None
        if self.group_fk.isChecked():
            fk_col = self.combo_fk_col.currentText()
            parent_id = self.combo_parent_term.currentData()
            # parent_id might be 0, so compare with None
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

        existing_uris = [f['uri'] for f in layer.getFeatures() if f['uri']]
        
        features_to_add = []
        skipped_count = 0

        self.btn_import.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            for index, item in enumerate(checked_items, 1):
                self.btn_import.setText(f"Processing Concept {index} of {total_items}...")
                QApplication.processEvents() 

                if item['uri'] in existing_uris:
                    skipped_count += 1
                    continue
                    
                feat = QgsFeature(layer.fields())
                feat.setAttribute('uri', item['uri'])
                
                if self.chk_ger.isChecked() and 'pref_ger' in fields:
                    if not self.radio_online.isChecked():
                        ger_label = self.offline_concepts.get(item['uri'], {}).get('pref_de', item['ui_term'])
                    else:
                        ger_label = item['ui_term']
                    feat.setAttribute('pref_ger', ger_label)
                    
                if self.chk_eng.isChecked() and 'pref_eng' in fields:
                    if not self.radio_online.isChecked():
                        eng_label = self.offline_concepts.get(item['uri'], {}).get('pref_en', '')
                    else:
                        # Fetch from api (optimized using a cache)
                        eng_label = self.fetch_label_from_api(item['uri'], 'en')
                    feat.setAttribute('pref_eng', eng_label)
                    
                if self.group_fk.isChecked() and fk_col:
                    feat.setAttribute(fk_col, parent_id)
                    
                features_to_add.append(feat)

            if features_to_add:
                self.btn_import.setText("Writing to PostgreSQL Database...")
                QApplication.processEvents()
                
                # Bugfix: Start editing session safely
                if not layer.isEditable() and not layer.startEditing():
                    QMessageBox.critical(self, "Edit Error", f"Could not start editing on layer '{layer.name()}'. Is it read-only?")
                    return
                
                success = layer.addFeatures(features_to_add)
                
                # Bugfix: Validate both features added AND changes committed successfully
                if success and layer.commitChanges():
                    msg = f"✅ {len(features_to_add)} concepts imported to '{layer.name()}'!"
                    if skipped_count > 0:
                        msg += f"\n⚠️ {skipped_count} concepts skipped (already in database)."
                    QMessageBox.information(self, "Success", msg)
                else:
                    # Retrieve database commit errors
                    commit_errs = layer.commitErrors()
                    layer.rollBack()
                    err_msg = "\n".join(commit_errs) if commit_errs else "PostgreSQL rejected the insert (Constraint violation?)."
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
        # Elegant DB-Icon from QGIS system resources
        icon = QgsApplication.getThemeIcon("/mActionAddWfsLayer.svg")
        
        self.action = QAction(icon, "SkosConnect LOD Importer", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        
        # Add to Toolbar "Database"
        self.iface.addToolBarIcon(self.action)
        # Add to Menu "Plugins -> SkosConnect"
        self.iface.addPluginToMenu("SkosConnect", self.action)

    def unload(self):
        self.iface.removePluginMenu("SkosConnect", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        if not self.dialog:
            self.dialog = SkosConnectMultilingualImporter(self.iface.mainWindow())
        
        # Refresh layers list on show
        self.dialog.populate_layers()
        self.dialog.show()