# “””
Protégé-like Ontology Editor — Streamlit App

Install dependencies:
pip install streamlit rdflib networkx pyvis

Run:
streamlit run protege_app.py
“””

import json
import uuid
import io
import streamlit as st
from rdflib import Graph, Namespace, URIRef, Literal, OWL, RDF, RDFS, XSD
from rdflib.namespace import DC
import networkx as nx

# ─────────────────────────────────────────────

# Page config

# ─────────────────────────────────────────────

st.set_page_config(
page_title=“Protégé Lite — Ontology Editor”,
page_icon=“🦉”,
layout=“wide”,
initial_sidebar_state=“expanded”,
)

# ─────────────────────────────────────────────

# Custom CSS

# ─────────────────────────────────────────────

st.markdown(”””

<style>
    .main-header {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: white;
    }
    .section-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .class-item {
        background: #e3f2fd;
        border-left: 4px solid #1976d2;
        padding: 0.4rem 0.8rem;
        border-radius: 4px;
        margin: 2px 0;
        font-family: monospace;
    }
    .property-item {
        background: #e8f5e9;
        border-left: 4px solid #388e3c;
        padding: 0.4rem 0.8rem;
        border-radius: 4px;
        margin: 2px 0;
        font-family: monospace;
    }
    .individual-item {
        background: #fff3e0;
        border-left: 4px solid #f57c00;
        padding: 0.4rem 0.8rem;
        border-radius: 4px;
        margin: 2px 0;
        font-family: monospace;
    }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-class { background: #1976d2; color: white; }
    .badge-obj   { background: #388e3c; color: white; }
    .badge-data  { background: #7b1fa2; color: white; }
    .badge-ind   { background: #f57c00; color: white; }
    .stExpander { border: 1px solid #ccc; border-radius: 6px; }
</style>

“””, unsafe_allow_html=True)

# ─────────────────────────────────────────────

# Session-state initialisation

# ─────────────────────────────────────────────

def init_state():
if “ontology” not in st.session_state:
st.session_state.ontology = {
“iri”: “http://example.org/myOntology#”,
“label”: “My Ontology”,
“description”: “”,
“classes”: {},          # name -> {parent, comment, annotations}
“object_properties”: {},# name -> {domain, range, comment, char:[]}
“data_properties”: {},  # name -> {domain, range_xsd, comment}
“individuals”: {},      # name -> {class, obj_props:{}, data_props:{}, comment}
}

init_state()
ont = st.session_state.ontology

# ─────────────────────────────────────────────

# Helper utilities

# ─────────────────────────────────────────────

def all_class_names():
base = [“owl:Thing”] + sorted(ont[“classes”].keys())
return base

def uid():
return str(uuid.uuid4())[:8]

def build_class_tree():
“”“Return dict: parent -> [children]”””
tree = {“owl:Thing”: []}
for name, info in ont[“classes”].items():
parent = info.get(“parent”, “owl:Thing”) or “owl:Thing”
tree.setdefault(parent, []).append(name)
tree.setdefault(name, [])
return tree

def render_tree_node(name, tree, depth=0):
children = tree.get(name, [])
icon = “🔵” if name == “owl:Thing” else “📘”
indent = “ ” * (depth * 4)
st.markdown(
f”{indent}{icon} <span class='class-item'>{name}</span>”,
unsafe_allow_html=True,
)
for child in sorted(children):
render_tree_node(child, tree, depth + 1)

# ─────────────────────────────────────────────

# RDF/OWL export

# ─────────────────────────────────────────────

def build_rdf_graph() -> Graph:
g = Graph()
NS = Namespace(ont[“iri”])
g.bind(””, NS)
g.bind(“owl”, OWL)
g.bind(“rdfs”, RDFS)
g.bind(“xsd”, XSD)
g.bind(“dc”, DC)

```
onto_node = URIRef(ont["iri"].rstrip("#/"))
g.add((onto_node, RDF.type, OWL.Ontology))
if ont["label"]:
    g.add((onto_node, RDFS.label, Literal(ont["label"])))
if ont["description"]:
    g.add((onto_node, DC.description, Literal(ont["description"])))

# Classes
for name, info in ont["classes"].items():
    cls = NS[name]
    g.add((cls, RDF.type, OWL.Class))
    parent = info.get("parent", "owl:Thing")
    if parent and parent != "owl:Thing":
        g.add((cls, RDFS.subClassOf, NS[parent]))
    else:
        g.add((cls, RDFS.subClassOf, OWL.Thing))
    if info.get("comment"):
        g.add((cls, RDFS.comment, Literal(info["comment"])))

# Object Properties
for name, info in ont["object_properties"].items():
    prop = NS[name]
    g.add((prop, RDF.type, OWL.ObjectProperty))
    if info.get("domain") and info["domain"] != "—":
        g.add((prop, RDFS.domain, NS[info["domain"]]))
    if info.get("range") and info["range"] != "—":
        g.add((prop, RDFS.range, NS[info["range"]]))
    for char in info.get("characteristics", []):
        char_map = {
            "Functional":        OWL.FunctionalProperty,
            "InverseFunctional": OWL.InverseFunctionalProperty,
            "Transitive":        OWL.TransitiveProperty,
            "Symmetric":         OWL.SymmetricProperty,
            "Asymmetric":        OWL.AsymmetricProperty,
            "Reflexive":         OWL.ReflexiveProperty,
            "Irreflexive":       OWL.IrreflexiveProperty,
        }
        if char in char_map:
            g.add((prop, RDF.type, char_map[char]))
    if info.get("comment"):
        g.add((prop, RDFS.comment, Literal(info["comment"])))

# Data Properties
xsd_map = {
    "string": XSD.string, "integer": XSD.integer, "float": XSD.float,
    "boolean": XSD.boolean, "date": XSD.date, "dateTime": XSD.dateTime,
}
for name, info in ont["data_properties"].items():
    prop = NS[name]
    g.add((prop, RDF.type, OWL.DatatypeProperty))
    if info.get("domain") and info["domain"] != "—":
        g.add((prop, RDFS.domain, NS[info["domain"]]))
    rng = info.get("range_xsd", "string")
    g.add((prop, RDFS.range, xsd_map.get(rng, XSD.string)))
    if info.get("comment"):
        g.add((prop, RDFS.comment, Literal(info["comment"])))

# Individuals
for name, info in ont["individuals"].items():
    ind = NS[name]
    g.add((ind, RDF.type, OWL.NamedIndividual))
    cls = info.get("class")
    if cls and cls != "—":
        g.add((ind, RDF.type, NS[cls]))
    for prop_name, value in info.get("obj_props", {}).items():
        g.add((ind, NS[prop_name], NS[value]))
    for prop_name, value in info.get("data_props", {}).items():
        g.add((ind, NS[prop_name], Literal(value)))
    if info.get("comment"):
        g.add((ind, RDFS.comment, Literal(info["comment"])))

return g
```

# ─────────────────────────────────────────────

# Import OWL/RDF

# ─────────────────────────────────────────────

def import_rdf(content: bytes, fmt: str):
g = Graph()
g.parse(data=content, format=fmt)
NS_base = None

```
new_ont = {
    "iri": "http://example.org/imported#",
    "label": "Imported Ontology",
    "description": "",
    "classes": {},
    "object_properties": {},
    "data_properties": {},
    "individuals": {},
}

# Detect IRI
for s, p, o in g.triples((None, RDF.type, OWL.Ontology)):
    new_ont["iri"] = str(s) + "#"
    for _, _, lbl in g.triples((s, RDFS.label, None)):
        new_ont["label"] = str(lbl)

# Classes
for s, _, _ in g.triples((None, RDF.type, OWL.Class)):
    local = s.split("#")[-1].split("/")[-1]
    if not local or local.startswith("_"):
        continue
    parent_uri = None
    for _, _, parent in g.triples((s, RDFS.subClassOf, None)):
        parent_uri = parent
    parent_local = None
    if parent_uri and str(parent_uri) != str(OWL.Thing):
        parent_local = str(parent_uri).split("#")[-1].split("/")[-1]
    comment = ""
    for _, _, c in g.triples((s, RDFS.comment, None)):
        comment = str(c)
    new_ont["classes"][local] = {"parent": parent_local or "owl:Thing", "comment": comment}

# Object Properties
for s, _, _ in g.triples((None, RDF.type, OWL.ObjectProperty)):
    local = s.split("#")[-1].split("/")[-1]
    if not local:
        continue
    domain = range_ = ""
    for _, _, d in g.triples((s, RDFS.domain, None)):
        domain = str(d).split("#")[-1].split("/")[-1]
    for _, _, r in g.triples((s, RDFS.range, None)):
        range_ = str(r).split("#")[-1].split("/")[-1]
    new_ont["object_properties"][local] = {
        "domain": domain, "range": range_, "characteristics": [], "comment": ""
    }

# Data Properties
for s, _, _ in g.triples((None, RDF.type, OWL.DatatypeProperty)):
    local = s.split("#")[-1].split("/")[-1]
    if not local:
        continue
    domain = ""
    for _, _, d in g.triples((s, RDFS.domain, None)):
        domain = str(d).split("#")[-1].split("/")[-1]
    new_ont["data_properties"][local] = {"domain": domain, "range_xsd": "string", "comment": ""}

# Individuals
for s, _, _ in g.triples((None, RDF.type, OWL.NamedIndividual)):
    local = s.split("#")[-1].split("/")[-1]
    if not local:
        continue
    cls = ""
    for _, _, t in g.triples((s, RDF.type, None)):
        t_local = str(t).split("#")[-1].split("/")[-1]
        if t_local and t_local != "NamedIndividual" and t_local in new_ont["classes"]:
            cls = t_local
    new_ont["individuals"][local] = {"class": cls, "obj_props": {}, "data_props": {}, "comment": ""}

st.session_state.ontology = new_ont
st.rerun()
```

# ─────────────────────────────────────────────

# HEADER

# ─────────────────────────────────────────────

st.markdown(”””

<div class='main-header'>
  <h2 style='margin:0'>🦉 Protégé Lite — Ontology Editor</h2>
  <p style='margin:0;opacity:0.8;font-size:0.9rem'>
    Build OWL ontologies with classes, properties, and individuals — export to RDF/OWL
  </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────

# SIDEBAR — Ontology metadata + import/export

# ─────────────────────────────────────────────

with st.sidebar:
st.header(“📁 Ontology”)

```
with st.expander("⚙️ Metadata", expanded=True):
    ont["label"] = st.text_input("Label", value=ont["label"])
    ont["iri"] = st.text_input("IRI / Namespace", value=ont["iri"])
    ont["description"] = st.text_area("Description", value=ont["description"], height=80)

st.divider()

# Stats
st.markdown("### 📊 Statistics")
col1, col2 = st.columns(2)
col1.metric("Classes", len(ont["classes"]))
col2.metric("Obj Props", len(ont["object_properties"]))
col1.metric("Data Props", len(ont["data_properties"]))
col2.metric("Individuals", len(ont["individuals"]))

st.divider()

# Export
st.markdown("### 💾 Export")
export_fmt = st.selectbox("Format", ["xml", "turtle", "n3", "json-ld"], key="export_fmt")
g = build_rdf_graph()
ext_map = {"xml": "owl", "turtle": "ttl", "n3": "n3", "json-ld": "jsonld"}
rdf_bytes = g.serialize(format=export_fmt).encode()
st.download_button(
    label=f"⬇️ Download .{ext_map[export_fmt]}",
    data=rdf_bytes,
    file_name=f"{ont['label'].replace(' ','_')}.{ext_map[export_fmt]}",
    mime="text/plain",
)

# Export as JSON (project save)
st.download_button(
    label="💾 Save Project (.json)",
    data=json.dumps(ont, indent=2),
    file_name="ontology_project.json",
    mime="application/json",
)

st.divider()

# Import
st.markdown("### 📂 Import")
uploaded = st.file_uploader("Load OWL / RDF / JSON", type=["owl", "ttl", "xml", "n3", "json", "jsonld"])
if uploaded:
    raw = uploaded.read()
    name = uploaded.name.lower()
    if name.endswith(".json") and not name.endswith(".jsonld"):
        try:
            loaded = json.loads(raw)
            st.session_state.ontology = loaded
            st.rerun()
        except Exception as e:
            st.error(f"JSON parse error: {e}")
    else:
        fmt_guess = "xml"
        if name.endswith(".ttl"): fmt_guess = "turtle"
        elif name.endswith(".n3"): fmt_guess = "n3"
        elif name.endswith(".jsonld"): fmt_guess = "json-ld"
        try:
            import_rdf(raw, fmt_guess)
        except Exception as e:
            st.error(f"Import error: {e}")

if st.button("🗑️ Reset Ontology", type="secondary"):
    st.session_state.ontology = {
        "iri": "http://example.org/myOntology#",
        "label": "My Ontology", "description": "",
        "classes": {}, "object_properties": {},
        "data_properties": {}, "individuals": {},
    }
    st.rerun()
```

# ─────────────────────────────────────────────

# MAIN TABS

# ─────────────────────────────────────────────

tab_classes, tab_obj, tab_data, tab_ind, tab_graph, tab_sparql = st.tabs([
“📘 Classes”,
“🔗 Object Properties”,
“📊 Data Properties”,
“👤 Individuals”,
“🕸️ Graph View”,
“🔍 Query (SPARQL)”,
])

# ═══════════════════════════════════════════════

# TAB 1 — CLASSES

# ═══════════════════════════════════════════════

with tab_classes:
col_tree, col_editor = st.columns([1, 2])

```
with col_tree:
    st.subheader("Class Hierarchy")
    tree = build_class_tree()
    render_tree_node("owl:Thing", tree)

with col_editor:
    st.subheader("Add / Edit Class")
    with st.form("add_class_form", clear_on_submit=True):
        cls_name = st.text_input("Class name *", placeholder="e.g. Person")
        cls_parent = st.selectbox("Subclass of", all_class_names())
        cls_comment = st.text_area("Comment / Description", height=70)
        submitted = st.form_submit_button("➕ Add Class", type="primary")
        if submitted:
            if not cls_name.strip():
                st.error("Class name is required.")
            elif cls_name in ont["classes"]:
                st.warning(f"Class '{cls_name}' already exists.")
            else:
                ont["classes"][cls_name] = {
                    "parent": cls_parent,
                    "comment": cls_comment,
                }
                st.success(f"✅ Class '{cls_name}' added.")
                st.rerun()

    st.divider()
    st.subheader("Existing Classes")
    if not ont["classes"]:
        st.info("No classes defined yet.")
    for name in sorted(ont["classes"]):
        info = ont["classes"][name]
        with st.expander(f"📘 {name}  ←  {info.get('parent','owl:Thing')}"):
            new_parent = st.selectbox(
                "Parent", all_class_names(),
                index=all_class_names().index(info.get("parent", "owl:Thing")),
                key=f"cls_parent_{name}",
            )
            new_comment = st.text_area("Comment", value=info.get("comment", ""), key=f"cls_comment_{name}", height=60)
            c1, c2 = st.columns(2)
            if c1.button("💾 Save", key=f"cls_save_{name}"):
                ont["classes"][name]["parent"] = new_parent
                ont["classes"][name]["comment"] = new_comment
                st.success("Saved.")
                st.rerun()
            if c2.button("🗑️ Delete", key=f"cls_del_{name}"):
                del ont["classes"][name]
                st.rerun()
```

# ═══════════════════════════════════════════════

# TAB 2 — OBJECT PROPERTIES

# ═══════════════════════════════════════════════

with tab_obj:
col_list, col_edit = st.columns([1, 2])

```
with col_list:
    st.subheader("Object Properties")
    if not ont["object_properties"]:
        st.info("No object properties yet.")
    for name in sorted(ont["object_properties"]):
        info = ont["object_properties"][name]
        st.markdown(
            f"<div class='property-item'>🔗 <b>{name}</b><br>"
            f"<small>{info.get('domain','?')} → {info.get('range','?')}</small></div>",
            unsafe_allow_html=True,
        )

with col_edit:
    st.subheader("Add / Edit Object Property")
    class_options = ["—"] + sorted(ont["classes"].keys())
    CHARACTERISTICS = [
        "Functional", "InverseFunctional", "Transitive",
        "Symmetric", "Asymmetric", "Reflexive", "Irreflexive",
    ]
    with st.form("add_obj_form", clear_on_submit=True):
        op_name = st.text_input("Property name *", placeholder="e.g. hasParent")
        op_domain = st.selectbox("Domain", class_options)
        op_range = st.selectbox("Range", class_options)
        op_chars = st.multiselect("Characteristics", CHARACTERISTICS)
        op_comment = st.text_area("Comment", height=60)
        if st.form_submit_button("➕ Add Property", type="primary"):
            if not op_name.strip():
                st.error("Name required.")
            else:
                ont["object_properties"][op_name] = {
                    "domain": op_domain, "range": op_range,
                    "characteristics": op_chars, "comment": op_comment,
                }
                st.success(f"✅ '{op_name}' added.")
                st.rerun()

    st.divider()
    for name in sorted(ont["object_properties"]):
        info = ont["object_properties"][name]
        with st.expander(f"🔗 {name}"):
            d = st.selectbox("Domain", class_options, index=class_options.index(info.get("domain","—")) if info.get("domain","—") in class_options else 0, key=f"op_d_{name}")
            r = st.selectbox("Range", class_options, index=class_options.index(info.get("range","—")) if info.get("range","—") in class_options else 0, key=f"op_r_{name}")
            ch = st.multiselect("Characteristics", CHARACTERISTICS, default=info.get("characteristics",[]), key=f"op_ch_{name}")
            cm = st.text_area("Comment", value=info.get("comment",""), key=f"op_cm_{name}", height=55)
            c1, c2 = st.columns(2)
            if c1.button("💾 Save", key=f"op_sv_{name}"):
                ont["object_properties"][name].update({"domain": d, "range": r, "characteristics": ch, "comment": cm})
                st.success("Saved."); st.rerun()
            if c2.button("🗑️ Delete", key=f"op_dl_{name}"):
                del ont["object_properties"][name]; st.rerun()
```

# ═══════════════════════════════════════════════

# TAB 3 — DATA PROPERTIES

# ═══════════════════════════════════════════════

with tab_data:
col_list, col_edit = st.columns([1, 2])
XSD_TYPES = [“string”, “integer”, “float”, “boolean”, “date”, “dateTime”]
class_options = [”—”] + sorted(ont[“classes”].keys())

```
with col_list:
    st.subheader("Data Properties")
    if not ont["data_properties"]:
        st.info("No data properties yet.")
    for name in sorted(ont["data_properties"]):
        info = ont["data_properties"][name]
        st.markdown(
            f"<div class='property-item'>📊 <b>{name}</b><br>"
            f"<small>{info.get('domain','?')} → xsd:{info.get('range_xsd','string')}</small></div>",
            unsafe_allow_html=True,
        )

with col_edit:
    st.subheader("Add / Edit Data Property")
    with st.form("add_dp_form", clear_on_submit=True):
        dp_name = st.text_input("Property name *", placeholder="e.g. hasAge")
        dp_domain = st.selectbox("Domain", class_options)
        dp_range = st.selectbox("XSD Range type", XSD_TYPES)
        dp_comment = st.text_area("Comment", height=60)
        if st.form_submit_button("➕ Add Property", type="primary"):
            if not dp_name.strip():
                st.error("Name required.")
            else:
                ont["data_properties"][dp_name] = {
                    "domain": dp_domain, "range_xsd": dp_range, "comment": dp_comment,
                }
                st.success(f"✅ '{dp_name}' added.")
                st.rerun()

    st.divider()
    for name in sorted(ont["data_properties"]):
        info = ont["data_properties"][name]
        with st.expander(f"📊 {name}"):
            d = st.selectbox("Domain", class_options, index=class_options.index(info.get("domain","—")) if info.get("domain","—") in class_options else 0, key=f"dp_d_{name}")
            r = st.selectbox("XSD Range", XSD_TYPES, index=XSD_TYPES.index(info.get("range_xsd","string")), key=f"dp_r_{name}")
            cm = st.text_area("Comment", value=info.get("comment",""), key=f"dp_cm_{name}", height=55)
            c1, c2 = st.columns(2)
            if c1.button("💾 Save", key=f"dp_sv_{name}"):
                ont["data_properties"][name].update({"domain": d, "range_xsd": r, "comment": cm})
                st.success("Saved."); st.rerun()
            if c2.button("🗑️ Delete", key=f"dp_dl_{name}"):
                del ont["data_properties"][name]; st.rerun()
```

# ═══════════════════════════════════════════════

# TAB 4 — INDIVIDUALS

# ═══════════════════════════════════════════════

with tab_ind:
col_list, col_edit = st.columns([1, 2])
class_opts = [”—”] + sorted(ont[“classes”].keys())

```
with col_list:
    st.subheader("Individuals")
    if not ont["individuals"]:
        st.info("No individuals yet.")
    for name in sorted(ont["individuals"]):
        info = ont["individuals"][name]
        st.markdown(
            f"<div class='individual-item'>👤 <b>{name}</b><br>"
            f"<small>type: {info.get('class','—')}</small></div>",
            unsafe_allow_html=True,
        )

with col_edit:
    st.subheader("Add Individual")
    with st.form("add_ind_form", clear_on_submit=True):
        ind_name = st.text_input("Individual name *", placeholder="e.g. john_doe")
        ind_class = st.selectbox("Instance of (class)", class_opts)
        ind_comment = st.text_area("Comment", height=55)
        if st.form_submit_button("➕ Add Individual", type="primary"):
            if not ind_name.strip():
                st.error("Name required.")
            elif ind_name in ont["individuals"]:
                st.warning("Already exists.")
            else:
                ont["individuals"][ind_name] = {
                    "class": ind_class, "obj_props": {}, "data_props": {}, "comment": ind_comment,
                }
                st.success(f"✅ '{ind_name}' added.")
                st.rerun()

    st.divider()
    st.subheader("Manage Individuals")
    for name in sorted(ont["individuals"]):
        info = ont["individuals"][name]
        with st.expander(f"👤 {name}  [{info.get('class','—')}]"):
            new_cls = st.selectbox("Class", class_opts, index=class_opts.index(info.get("class","—")) if info.get("class","—") in class_opts else 0, key=f"ind_cls_{name}")
            cm = st.text_area("Comment", value=info.get("comment",""), key=f"ind_cm_{name}", height=55)

            # Object property assertions
            if ont["object_properties"]:
                st.markdown("**Object Property Assertions**")
                op_keys = sorted(ont["object_properties"].keys())
                ind_opts = ["—"] + sorted(ont["individuals"].keys())
                for prop in op_keys:
                    current_val = info.get("obj_props", {}).get(prop, "—")
                    idx = ind_opts.index(current_val) if current_val in ind_opts else 0
                    chosen = st.selectbox(f"  {prop}", ind_opts, index=idx, key=f"ind_op_{name}_{prop}")
                    if chosen != "—":
                        info.setdefault("obj_props", {})[prop] = chosen
                    elif prop in info.get("obj_props", {}):
                        del info["obj_props"][prop]

            # Data property assertions
            if ont["data_properties"]:
                st.markdown("**Data Property Assertions**")
                for prop in sorted(ont["data_properties"].keys()):
                    current_val = info.get("data_props", {}).get(prop, "")
                    new_val = st.text_input(f"  {prop}", value=current_val, key=f"ind_dp_{name}_{prop}")
                    if new_val:
                        info.setdefault("data_props", {})[prop] = new_val
                    elif prop in info.get("data_props", {}):
                        del info["data_props"][prop]

            c1, c2 = st.columns(2)
            if c1.button("💾 Save", key=f"ind_sv_{name}"):
                ont["individuals"][name]["class"] = new_cls
                ont["individuals"][name]["comment"] = cm
                st.success("Saved."); st.rerun()
            if c2.button("🗑️ Delete", key=f"ind_dl_{name}"):
                del ont["individuals"][name]; st.rerun()
```

# ═══════════════════════════════════════════════

# TAB 5 — GRAPH VIEW (networkx / pyvis)

# ═══════════════════════════════════════════════

with tab_graph:
st.subheader(“🕸️ Ontology Graph”)

```
try:
    from pyvis.network import Network
    import tempfile, os

    net = Network(height="600px", width="100%", bgcolor="#1a1a2e", font_color="white", directed=True)
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150)

    # owl:Thing root
    net.add_node("owl:Thing", label="owl:Thing", color="#aaaaaa", size=20, shape="ellipse", title="Root Class")

    # Classes
    for name, info in ont["classes"].items():
        net.add_node(name, label=name, color="#1976d2", size=16, shape="box", title=f"Class: {name}\n{info.get('comment','')}")
        parent = info.get("parent", "owl:Thing")
        net.add_edge(name, parent, color="#555555", title="subClassOf", dashes=True)

    # Object Properties
    for prop, info in ont["object_properties"].items():
        d = info.get("domain","")
        r = info.get("range","")
        if d and d != "—" and r and r != "—":
            if d in ont["classes"] and r in ont["classes"]:
                net.add_edge(d, r, label=prop, color="#43a047", title=prop)

    # Individuals
    for name, info in ont["individuals"].items():
        net.add_node(name, label=name, color="#f57c00", size=12, shape="dot", title=f"Individual: {name}\nClass: {info.get('class','')}")
        cls = info.get("class","")
        if cls and cls != "—" and cls in ont["classes"]:
            net.add_edge(name, cls, color="#ff9800", title="instanceOf", dashes=True)
        for prop, val in info.get("obj_props",{}).items():
            if val in ont["individuals"]:
                net.add_edge(name, val, label=prop, color="#ab47bc", title=prop)

    if not ont["classes"] and not ont["individuals"]:
        st.info("Add some classes or individuals to see the graph.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
            net.save_graph(f.name)
            html_content = open(f.name).read()
        os.unlink(f.name)
        st.components.v1.html(html_content, height=620, scrolling=False)

except ImportError:
    # Fallback: matplotlib-based graph
    st.warning("pyvis not installed — showing simplified graph. Install with: `pip install pyvis`")
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        G = nx.DiGraph()
        G.add_node("owl:Thing")
        for name, info in ont["classes"].items():
            G.add_node(name)
            parent = info.get("parent","owl:Thing")
            G.add_edge(name, parent)

        for name in ont["individuals"]:
            G.add_node(name)
            cls = ont["individuals"][name].get("class","")
            if cls and cls in ont["classes"]:
                G.add_edge(name, cls)

        if len(G.nodes) < 2:
            st.info("Add classes/individuals to see the graph.")
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
            pos = nx.spring_layout(G, seed=42)
            class_nodes = [n for n in G.nodes if n in ont["classes"] or n == "owl:Thing"]
            ind_nodes   = [n for n in G.nodes if n in ont["individuals"]]
            nx.draw_networkx_nodes(G, pos, nodelist=class_nodes, node_color="#1976d2", node_size=800, ax=ax)
            nx.draw_networkx_nodes(G, pos, nodelist=ind_nodes,   node_color="#f57c00", node_size=500, ax=ax)
            nx.draw_networkx_labels(G, pos, ax=ax, font_color="white", font_size=8)
            nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, arrowsize=15, edge_color="#aaaaaa")
            ax.set_facecolor("#1a1a2e"); fig.patch.set_facecolor("#1a1a2e")
            ax.axis("off")
            blue_patch = mpatches.Patch(color="#1976d2", label="Class")
            orange_patch = mpatches.Patch(color="#f57c00", label="Individual")
            ax.legend(handles=[blue_patch, orange_patch], loc="upper left", facecolor="#333", labelcolor="white")
            st.pyplot(fig)
    except Exception as e:
        st.error(f"Graph error: {e}")
```

# ═══════════════════════════════════════════════

# TAB 6 — SPARQL

# ═══════════════════════════════════════════════

with tab_sparql:
st.subheader(“🔍 SPARQL Query”)
st.caption(“Run SPARQL SELECT queries against your ontology.”)

```
default_query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
```

PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?class ?parent WHERE {
?class a owl:Class .
OPTIONAL { ?class rdfs:subClassOf ?parent }
}
ORDER BY ?class”””

```
query_presets = {
    "List all classes": "PREFIX owl: <http://www.w3.org/2002/07/owl#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\nSELECT ?class ?comment WHERE {\n  ?class a owl:Class .\n  OPTIONAL { ?class rdfs:comment ?comment }\n}\nORDER BY ?class",
    "List all individuals": "PREFIX owl: <http://www.w3.org/2002/07/owl#>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n\nSELECT ?individual ?type WHERE {\n  ?individual a owl:NamedIndividual .\n  OPTIONAL { ?individual a ?type . FILTER(?type != owl:NamedIndividual) }\n}",
    "List object properties": "PREFIX owl: <http://www.w3.org/2002/07/owl#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\nSELECT ?prop ?domain ?range WHERE {\n  ?prop a owl:ObjectProperty .\n  OPTIONAL { ?prop rdfs:domain ?domain }\n  OPTIONAL { ?prop rdfs:range ?range }\n}",
    "Custom query": default_query,
}

preset = st.selectbox("Preset queries", list(query_presets.keys()))
sparql_query = st.text_area("SPARQL Query", value=query_presets[preset], height=180)

if st.button("▶️ Run Query", type="primary"):
    try:
        g = build_rdf_graph()
        results = g.query(sparql_query)
        rows = [list(r) for r in results]
        if rows:
            import pandas as pd
            cols = [str(v) for v in results.vars]
            df = pd.DataFrame([[str(cell) if cell else "" for cell in row] for row in rows], columns=cols)
            st.dataframe(df, use_container_width=True)
            st.caption(f"✅ {len(df)} result(s).")
        else:
            st.info("Query returned no results.")
    except Exception as e:
        st.error(f"Query error: {e}")

st.divider()
st.subheader("📄 Raw RDF Triples")
if st.button("Show all triples"):
    g = build_rdf_graph()
    import pandas as pd
    triples = [(str(s), str(p), str(o)) for s, p, o in g]
    df = pd.DataFrame(triples, columns=["Subject", "Predicate", "Object"])
    st.dataframe(df, use_container_width=True)
    st.caption(f"{len(df)} triple(s) in the graph.")
```
