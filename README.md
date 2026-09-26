[tocca_corsa_atelier_premium_v4.py](https://github.com/user-attachments/files/32691122/tocca_corsa_atelier_premium_v4.py)
"""
TOCCA CORSA — Logiciel de gestion métier PRO
V3 — construit à partir de la base fournie par TOCCA CORSA.

Fonctions ajoutées :
- CRM clients
- calendrier / planning des chantiers
- génération PDF de devis/factures
- numérotation commerciale
- recherche globale
- gestion des acomptes / soldes
- journal d'activité
- import automatique des anciennes données CSV
- sauvegarde / export
"""

import io
import sqlite3
from pathlib import Path
from html import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

TARIFS_METIER = {
    "Chaise / Tabouret": {"Aérogommage Seul": 45.0, "Relooking & Finitions": 95.0},
    "Table de chevet / Petit meuble": {"Aérogommage Seul": 90.0, "Relooking & Finitions": 190.0},
    "Commode / Console (3 tiroirs)": {"Aérogommage Seul": 250.0, "Relooking & Finitions": 480.0},
    "Table de repas (4 à 6 personnes)": {"Aérogommage Seul": 320.0, "Relooking & Finitions": 650.0},
    "Buffet bas / Enfilade (3-4 portes)": {"Aérogommage Seul": 450.0, "Relooking & Finitions": 890.0},
    "Armoire ancienne / Grand Vaisselier": {"Aérogommage Seul": 650.0, "Relooking & Finitions": 1200.0},
}

import streamlit as st
import pandas as pd
import os, shutil, re
from datetime import datetime, timedelta, date

st.set_page_config(
    page_title="TOCCA CORSA PRO",
    page_icon="🪚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# DESIGN SYSTEM
# ============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap');
:root{--forest:#294236;--forest2:#3f5d4d;--cream:#f6f2e9;--paper:#fffdf8;--wood:#a17c59;--ink:#24302a;--muted:#748078;--line:#e7e1d5;--danger:#a95151;--warning:#a8792f;--success:#48765a}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.stApp{background:var(--cream)}
.block-container{max-width:1550px;padding-top:1.1rem;padding-bottom:3rem}
h1,h2,h3{font-family:'Playfair Display',Georgia,serif!important;color:var(--forest)!important}
h1{font-size:2.3rem!important} h2{font-size:1.65rem!important}
[data-testid="stSidebar"]{background:#20362b;border-right:1px solid #183026}
[data-testid="stSidebar"] *{color:#f7f3ea!important}
.stButton>button{border-radius:10px;border:1px solid transparent;background:var(--forest);color:#fff;font-weight:600;min-height:42px}
.stButton>button:hover{background:var(--forest2);color:#fff}
[data-testid="stMetric"]{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:15px 17px;box-shadow:0 5px 18px rgba(44,55,47,.05)}
[data-testid="stMetricValue"]{color:var(--forest)!important;font-family:'Playfair Display',Georgia,serif}
div[data-testid="stForm"]{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:1rem}
.tc-hero{background:linear-gradient(135deg,#294236,#3e5c4b);color:white;border-radius:20px;padding:28px 32px;margin-bottom:20px;box-shadow:0 12px 30px rgba(32,54,43,.16)}
.tc-hero h1,.tc-hero p{color:#fff!important}
.tc-kicker{text-transform:uppercase;letter-spacing:.13em;font-size:.72rem;opacity:.72;font-weight:700}
.tc-card{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 5px 18px rgba(44,55,47,.045);margin-bottom:12px}
.tc-muted{color:var(--muted);font-size:.9rem}.tc-price{color:var(--wood);font-family:'Playfair Display',Georgia,serif;font-size:1.3rem;font-weight:700}
.badge{display:inline-block;border-radius:999px;padding:4px 9px;font-size:.73rem;font-weight:700}
.green{background:#e4f0e6;color:#376347}.orange{background:#f7ecd3;color:#8a6322}.red{background:#f5dddd;color:#8d3f3f}.neutral{background:#ecebe7;color:#5f665f}
.smallcaps{text-transform:uppercase;letter-spacing:.08em;font-size:.72rem;color:var(--muted);font-weight:700}
.timeline{border-left:3px solid #d8d0c2;padding-left:15px;margin-left:6px}
.timeline-item{padding-bottom:15px}
.timeline-date{font-size:.75rem;color:var(--muted)}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTES / DONNÉES
# ============================================================================
DB = "tocca_corsa_pro.db"
DB_CHANTIERS = "chantiers_tocca_corsa.csv"
DB_STOCKS = "stocks_tocca_corsa.csv"
BACKUP_DIR = Path("sauvegardes_secours")
BACKUP_DIR.mkdir(exist_ok=True)

COLUMNS = [
    "ID","Client","Téléphone","Meuble","Type_Meuble","Prestation","Complexite",
    "Statut","Prix_HT","Acompte","Reste_A_Payer","Date_Creation","Heures_Passees"
]
STATUTS = ["En attente","En cours","Terminé","Facturé"]

def euro(v):
    return f"{float(v):,.2f} €".replace(",", " ").replace(".", ",")

def nowstr():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================================================
# SQLITE — CRM, PLANNING, HISTORIQUE
# ============================================================================
def db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL,
        telephone TEXT, email TEXT, adresse TEXT, notes TEXT,
        created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS planning(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chantier_id INTEGER NOT NULL,
        date_debut TEXT, date_fin TEXT, lieu TEXT, notes TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS journal(
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
        type TEXT, message TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sequence(
        id INTEGER PRIMARY KEY CHECK(id=1), devis INTEGER DEFAULT 0,
        factures INTEGER DEFAULT 0)""")
    conn.execute("INSERT OR IGNORE INTO sequence(id) VALUES(1)")
    conn.commit()
    return conn

CONN = db()

def log_event(kind, message):
    CONN.execute("INSERT INTO journal(date,type,message) VALUES(?,?,?)",
                 (nowstr(), kind, message))
    CONN.commit()

def clients_df():
    return pd.read_sql_query("SELECT * FROM clients ORDER BY nom", CONN)

def planning_df():
    return pd.read_sql_query("""
        SELECT p.*, c.Client, c.Meuble, c.Statut
        FROM planning p LEFT JOIN (
            SELECT ID, Client, Meuble, Statut FROM chantiers_cache
        ) c ON c.ID=p.chantier_id
        ORDER BY p.date_debut
    """, CONN) if False else pd.read_sql_query(
        "SELECT * FROM planning ORDER BY date_debut", CONN)

# Cache métier dans SQLite pour enrichir planning sans casser les CSV existants.
def sync_chantiers_cache(df):
    CONN.execute("""CREATE TABLE IF NOT EXISTS chantiers_cache(
        ID INTEGER PRIMARY KEY, Client TEXT, Meuble TEXT, Statut TEXT)""")
    CONN.execute("DELETE FROM chantiers_cache")
    for _, r in df.iterrows():
        CONN.execute("INSERT INTO chantiers_cache VALUES(?,?,?,?)",
                     (int(r.ID), str(r.Client), str(r.Meuble), str(r.Statut)))
    CONN.commit()

# ============================================================================
# MIGRATION / CHARGEMENT DES DONNÉES EXISTANTES
# ============================================================================
if not Path(DB_CHANTIERS).exists():
    pd.DataFrame(columns=COLUMNS).to_csv(DB_CHANTIERS,index=False)
if not Path(DB_STOCKS).exists():
    pd.DataFrame(columns=["Article","Catégorie","Quantité","Unité","Seuil_Alerte"]).to_csv(DB_STOCKS,index=False)

df = pd.read_csv(DB_CHANTIERS)
for c in ["Prix_HT","Acompte","Reste_A_Payer","Heures_Passees"]:
    if c not in df.columns: df[c]=0.0
    df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
if "ID" in df.columns: df["ID"]=pd.to_numeric(df["ID"],errors="coerce").fillna(0).astype(int)
stocks = pd.read_csv(DB_STOCKS)
for c in ["Quantité","Seuil_Alerte"]:
    if c in stocks.columns: stocks[c]=pd.to_numeric(stocks[c],errors="coerce").fillna(0)
sync_chantiers_cache(df)

# ============================================================================
# DOCUMENTS PDF
# ============================================================================
def next_number(kind):
    col = "devis" if kind=="devis" else "factures"
    cur = CONN.execute(f"SELECT {col} FROM sequence WHERE id=1").fetchone()[0] or 0
    cur += 1
    CONN.execute(f"UPDATE sequence SET {col}=? WHERE id=1",(cur,))
    CONN.commit()
    prefix = "DEV" if kind=="devis" else "FAC"
    return f"{prefix}-{datetime.now():%Y}-{cur:04d}"

def make_pdf(row, kind="devis"):
    number = next_number(kind)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,
                            topMargin=18*mm,bottomMargin=18*mm)
    styles=getSampleStyleSheet()
    title=ParagraphStyle("title",parent=styles["Title"],fontName="Helvetica-Bold",
                         fontSize=20,textColor=colors.HexColor("#294236"),alignment=TA_LEFT)
    normal=ParagraphStyle("normal2",parent=styles["Normal"],fontSize=9.5,leading=13)
    small=ParagraphStyle("small2",parent=styles["Normal"],fontSize=8,textColor=colors.HexColor("#68736c"))
    story=[
        Paragraph("TOCCA CORSA EI",title),
        Paragraph("Atelier d’Upcycling d’Art — Rénovation écoresponsable",normal),
        Paragraph("Afa (Corse-du-Sud) · TVA non applicable, art. 293 B du CGI",small),
        Spacer(1,8),
        Paragraph(f"<b>{'FACTURE' if kind=='facture' else 'DEVIS'} {number}</b>",styles["Heading2"]),
        Paragraph(f"Date : {datetime.now():%d/%m/%Y}",normal),
        Spacer(1,8),
        Paragraph(f"<b>Client :</b> {escape(str(row['Client']))}<br/>"
                  f"<b>Téléphone :</b> {escape(str(row['Téléphone']))}",normal),
        Spacer(1,10)
    ]
    data=[["Prestation","Détails","Montant HT"],
          [str(row["Prestation"]),f"{row['Meuble']} · pénibilité {row['Complexite']}",euro(row["Prix_HT"])]]
    table=Table(data,colWidths=[45*mm,90*mm,35*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#294236")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#d9d4c9")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ALIGN",(-1,1),(-1,-1),"RIGHT"),
        ("PADDING",(0,0),(-1,-1),7)
    ]))
    story += [table,Spacer(1,18),
              Paragraph(f"<b>Total HT : {euro(row['Prix_HT'])}</b>",styles["Heading2"]),
              Paragraph(f"Acompte : {euro(row['Acompte'])}<br/>"
                        f"Solde restant dû : {euro(row['Reste_A_Payer'])}",normal),
              Spacer(1,20),
              Paragraph("Merci pour votre confiance et pour votre choix en faveur de la rénovation écoresponsable.",small)]
    doc.build(story)
    return buffer.getvalue(), number

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("## 🪚 TOCCA CORSA")
    st.caption("Logiciel de gestion métier PRO")
    st.markdown("---")
    menu=st.radio("Navigation",[
        "🏠 Tableau de bord","🪵 Atelier Premium","👥 Clients (CRM)","➕ Nouveau projet",
        "📅 Planning","💶 Devis & factures","⏱️ Temps & rentabilité",
        "🌿 Stocks","📈 Statistiques","⚙️ Paramètres"
    ],label_visibility="collapsed")
    st.markdown("---")
    actifs=int(df.Statut.isin(["En attente","En cours"]).sum()) if not df.empty else 0
    reste=float(df.Reste_A_Payer.sum()) if not df.empty else 0
    st.caption("SYNTHÈSE")
    st.markdown(f"**{actifs}** projets actifs")
    st.markdown(f"**{euro(reste)}** à encaisser")
    st.caption("Données locales + sauvegardes")

# ============================================================================
# TABLEAU DE BORD
# ============================================================================
if menu=="🏠 Tableau de bord":
    st.markdown("""<div class="tc-hero"><div class="tc-kicker">Pilotage quotidien</div>
    <h1>TOCCA CORSA — votre atelier, en un coup d’œil.</h1>
    <p>Clients, projets, trésorerie et planning réunis dans un seul espace.</p></div>""",unsafe_allow_html=True)

    ca=float(df.Prix_HT.sum()) if not df.empty else 0
    enc=float(df.Acompte.sum()) if not df.empty else 0
    reste=float(df.Reste_A_Payer.sum()) if not df.empty else 0
    term=int((df.Statut=="Terminé").sum()) if not df.empty else 0
    a,b,c,d=st.columns(4)
    a.metric("CA potentiel",euro(ca)); b.metric("Encaissé",euro(enc))
    c.metric("À encaisser",euro(reste)); d.metric("Prêts à livrer",term)

    st.markdown("### 🎯 Priorités")
    waiting=df[df.Statut=="En attente"].copy()
    if waiting.empty:
        st.success("Aucun devis en attente.")
    else:
        for _,r in waiting.sort_values("Date_Creation").head(6).iterrows():
            created=pd.to_datetime(r.Date_Creation,errors="coerce")
            h=(created+timedelta(hours=48)-datetime.now()).total_seconds()/3600 if pd.notna(created) else 0
            badge="green" if h>24 else ("orange" if h>=0 else "red")
            txt=f"**#{r.ID} · {r.Client}** — {r.Meuble}  <span class='badge {badge}'>{'OK' if h>24 else ('URGENT' if h>=0 else 'RETARD')}</span>"
            st.markdown(txt,unsafe_allow_html=True)

    st.markdown("### 📊 Activité")
    left,right=st.columns(2)
    with left:
        st.markdown("**Répartition des projets**")
        counts=df.Statut.value_counts().reindex(STATUTS,fill_value=0) if not df.empty else pd.Series()
        st.bar_chart(counts,height=250)
    with right:
        st.markdown("**CA par catégorie de meuble**")
        g=df.groupby("Type_Meuble").Prix_HT.sum().sort_values(ascending=False) if not df.empty else pd.Series()
        st.bar_chart(g,height=250)

# ============================================================================
# ATELIER
# ============================================================================
elif menu=="🪵 Atelier Premium":
    st.title("🪵 Atelier Premium")
    st.caption("Le cockpit visuel de l’atelier : chaque pièce, son histoire, son avancement et sa valeur.")

    # Mini dashboard métier
    ca_atelier = float(df.Prix_HT.sum()) if not df.empty else 0
    heures = float(df.Heures_Passees.sum()) if not df.empty else 0
    projets = len(df)
    pret = int((df.Statut=="Terminé").sum()) if not df.empty else 0
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Pièces suivies", projets)
    k2.metric("Heures atelier", f"{heures:.1f} h")
    k3.metric("Valeur des projets", euro(ca_atelier))
    k4.metric("Pièces prêtes", pret)

    search=st.text_input("🔎 Rechercher une pièce, un client ou un dossier",placeholder="Ex. commode, Dupont, #12")
    view_mode = st.radio("Affichage", ["Kanban","Liste détaillée"], horizontal=True)

    if view_mode == "Liste détaillée" and not df.empty:
        st.dataframe(
            df[["ID","Client","Meuble","Type_Meuble","Prestation","Statut","Prix_HT","Heures_Passees"]],
            hide_index=True, use_container_width=True,
            column_config={
                "Prix_HT": st.column_config.NumberColumn("Valeur",format="%.2f €"),
                "Heures_Passees": st.column_config.NumberColumn("Temps",format="%.1f h")
            }
        )
        st.divider()

    # Galerie visuelle : les photos sont enregistrées localement dans galerie_tocca.
    st.markdown("### 📸 Fiche visuelle")
    photo_dir = Path("galerie_tocca")
    photo_dir.mkdir(exist_ok=True)
    if not df.empty:
        photo_id = st.selectbox(
            "Choisir une pièce",
            df.ID.tolist(),
            format_func=lambda x: f"#{x} · {df.loc[df.ID==x,'Client'].iloc[0]} · {df.loc[df.ID==x,'Meuble'].iloc[0]}"
        )
        selected = df[df.ID==photo_id].iloc[0]
        img_files = sorted([p for p in photo_dir.glob(f"{int(photo_id)}_*") if p.suffix.lower() in [".jpg",".jpeg",".png",".webp"]])
        if img_files:
            img_cols = st.columns(min(3,len(img_files)))
            for col,p in zip(img_cols,img_files):
                col.image(str(p), caption=p.stem, use_container_width=True)
        else:
            st.info("Aucune photo pour cette pièce. Déposez des photos avec le module ci-dessous.")
        uploaded = st.file_uploader(
            "Ajouter des photos avant / pendant / après",
            type=["jpg","jpeg","png","webp"],
            accept_multiple_files=True,
            key=f"photos_{photo_id}"
        )
        if uploaded and st.button("Enregistrer les photos", use_container_width=True):
            saved=0
            for up in uploaded:
                safe = re.sub(r"[^a-zA-Z0-9_-]","_",Path(up.name).stem)
                dest = photo_dir / f"{int(photo_id)}_{safe}{Path(up.name).suffix.lower()}"
                dest.write_bytes(up.getbuffer())
                saved += 1
            log_event("Galerie",f"{saved} photo(s) ajoutée(s) au projet #{photo_id}")
            st.success(f"{saved} photo(s) enregistrée(s).")
            st.rerun()

    st.divider()
    st.markdown("### 📋 Flux de production")

    f=df.copy()
    if search:
        mask=pd.Series(False,index=f.index)
        for col in ["ID","Client","Téléphone","Meuble","Type_Meuble"]:
            mask |= f[col].astype(str).str.contains(search,case=False,na=False)
        f=f[mask]
    cols=st.columns(4)
    icons={"En attente":"⏳","En cours":"🪵","Terminé":"✨","Facturé":"💶"}
    for col,status in zip(cols,STATUTS):
        with col:
            items=f[f.Statut==status]
            st.markdown(f"### {icons[status]} {status} · {len(items)}")
            for _,r in items.iterrows():
                st.markdown(f"""<div class="tc-card"><b>#{int(r.ID)} · {escape(str(r.Client))}</b>
                <div class="tc-muted">{escape(str(r.Meuble))}</div>
                <div class="smallcaps">{escape(str(r.Type_Meuble))}</div>
                <div class="tc-price">{euro(r.Prix_HT)}</div>
                <div class="tc-muted">⏱ {float(r.Heures_Passees):.1f} h · {escape(str(r.Prestation))}</div>
                </div>""",unsafe_allow_html=True)


    st.divider()
    with st.form("move"):
        ids=df.ID.tolist()
        if ids:
            x,y,z=st.columns(3)
            sid=x.selectbox("Dossier",ids)
            row=df[df.ID==sid].iloc[0]
            y.write(f"**{row.Client}**\n\n{row.Meuble}")
            ns=z.selectbox("Nouveau statut",STATUTS,index=STATUTS.index(row.Statut))
            if st.form_submit_button("Déplacer le dossier",use_container_width=True):
                i=df.index[df.ID==sid][0]; df.loc[i,"Statut"]=ns
                if ns=="Facturé": df.loc[i,"Reste_A_Payer"]=0
                df.to_csv(DB_CHANTIERS,index=False); sync_chantiers_cache(df)
                log_event("Atelier",f"Dossier #{sid} déplacé vers {ns}")
                st.success("Dossier mis à jour."); st.rerun()

# ============================================================================
# CRM
# ============================================================================
elif menu=="👥 Clients (CRM)":
    st.title("👥 Clients")
    clients=clients_df()
    tab1,tab2=st.tabs(["Annuaire","Nouveau client"])
    with tab1:
        q=st.text_input("🔎 Rechercher un client")
        view=clients.copy()
        if q and not view.empty:
            view=view[view.nom.str.contains(q,case=False,na=False) |
                      view.telephone.fillna("").str.contains(q,case=False,na=False) |
                      view.email.fillna("").str.contains(q,case=False,na=False)]
        st.dataframe(view,hide_index=True,use_container_width=True)
        if not view.empty:
            st.caption("Les projets historiques restent dans le module Atelier ; le CRM ajoute les coordonnées et notes.")
    with tab2:
        with st.form("new_client"):
            nom=st.text_input("Nom & prénom *"); tel=st.text_input("Téléphone")
            email=st.text_input("Email"); adresse=st.text_area("Adresse")
            notes=st.text_area("Notes client")
            if st.form_submit_button("Créer le client",use_container_width=True):
                if nom.strip():
                    CONN.execute("INSERT INTO clients(nom,telephone,email,adresse,notes,created_at) VALUES(?,?,?,?,?,?)",
                                 (nom.strip(),tel,email,adresse,notes,nowstr())); CONN.commit()
                    log_event("CRM",f"Client créé : {nom.strip()}")
                    st.success("Client créé."); st.rerun()
                else: st.error("Le nom est obligatoire.")

# ============================================================================
# NOUVEAU PROJET
# ============================================================================
elif menu=="➕ Nouveau projet":
    st.title("➕ Nouveau projet")
    st.caption("Création rapide + estimation métier + suivi 48 h.")
    with st.form("new_project"):
        a,b=st.columns(2)
        client=a.text_input("Nom & prénom *"); tel=b.text_input("Téléphone")
        meuble=a.text_input("Désignation du meuble *")
        cat=b.selectbox("Type de meuble",list(TARIFS_METIER.keys()))
        prestation=a.selectbox("Prestation",["Aérogommage Seul","Relooking & Finitions"])
        complexite=b.select_slider("Pénibilité",["Standard","Moyen","Complexe"],value="Standard")
        base=TARIFS_METIER[cat][prestation]
        coef={"Standard":1,"Moyen":1.25,"Complexe":1.5}[complexite]
        suggestion=round(base*coef,2)
        st.info(f"Tarif de référence **{euro(base)}** · suggestion **{euro(suggestion)} HT**")
        prix=a.number_input("Prix final HT",min_value=0.,value=float(suggestion),step=10.)
        acompte=b.number_input("Acompte",min_value=0.,value=round(suggestion*.3,2),step=10.)
        if st.form_submit_button("Créer le projet",use_container_width=True):
            if client.strip() and meuble.strip():
                nid=int(df.ID.max()+1) if not df.empty else 1
                row=[nid,client.strip(),tel.strip(),meuble.strip(),cat,prestation,complexite,"En attente",
                     round(prix,2),round(acompte,2),round(max(prix-acompte,0),2),nowstr(),0.]
                df=pd.concat([df,pd.DataFrame([row],columns=COLUMNS)],ignore_index=True)
                df.to_csv(DB_CHANTIERS,index=False); sync_chantiers_cache(df)
                log_event("Projet",f"Projet #{nid} créé pour {client.strip()}")
                st.success(f"Projet #{nid} créé."); st.rerun()
            else: st.error("Client et meuble sont obligatoires.")

# ============================================================================
# PLANNING
# ============================================================================
elif menu=="📅 Planning":
    st.title("📅 Planning atelier")
    if df.empty:
        st.info("Créez d'abord un projet.")
    else:
        with st.form("schedule"):
            ids=df.ID.tolist()
            sid=st.selectbox("Projet",ids,format_func=lambda x:f"#{x} · {df.loc[df.ID==x,'Client'].iloc[0]} · {df.loc[df.ID==x,'Meuble'].iloc[0]}")
            a,b=st.columns(2)
            start=a.date_input("Début",date.today())
            end=b.date_input("Fin",date.today()+timedelta(days=1))
            place=st.text_input("Lieu",value="Atelier TOCCA CORSA")
            notes=st.text_area("Notes planning")
            if st.form_submit_button("Ajouter au planning",use_container_width=True):
                CONN.execute("INSERT INTO planning(chantier_id,date_debut,date_fin,lieu,notes) VALUES(?,?,?,?,?)",
                             (sid,str(start),str(end),place,notes)); CONN.commit()
                log_event("Planning",f"Projet #{sid} planifié du {start} au {end}")
                st.success("Créneau ajouté."); st.rerun()
        st.divider()
        plan=pd.read_sql_query("SELECT * FROM planning ORDER BY date_debut",CONN)
        if plan.empty: st.info("Aucun créneau planifié.")
        else:
            for _,p in plan.iterrows():
                r=df[df.ID==p.chantier_id]
                label=f"#{int(p.chantier_id)}"
                if not r.empty: label+=f" · {r.iloc[0].Client} · {r.iloc[0].Meuble}"
                st.markdown(f"""<div class="tc-card"><b>📆 {p.date_debut} → {p.date_fin}</b>
                <div>{escape(label)}</div><div class="tc-muted">📍 {escape(str(p.lieu or ''))} · {escape(str(p.notes or ''))}</div></div>""",
                            unsafe_allow_html=True)

# ============================================================================
# DEVIS & FACTURES
# ============================================================================
elif menu=="💶 Devis & factures":
    st.title("💶 Devis & factures")
    if df.empty: st.info("Aucun projet.")
    else:
        sid=st.selectbox("Dossier",df.ID.tolist(),format_func=lambda x:f"#{x} · {df.loc[df.ID==x,'Client'].iloc[0]} · {df.loc[df.ID==x,'Meuble'].iloc[0]}")
        row=df[df.ID==sid].iloc[0]
        st.markdown(f"""<div class="tc-card"><div class="smallcaps">DOSSIER</div>
        <h3>#{int(row.ID)} · {escape(str(row.Client))}</h3>
        <div class="tc-muted">{escape(str(row.Meuble))} · {escape(str(row.Prestation))}</div>
        </div>""",unsafe_allow_html=True)
        a,b,c=st.columns(3)
        a.metric("Total",euro(row.Prix_HT)); b.metric("Acompte",euro(row.Acompte)); c.metric("Solde",euro(row.Reste_A_Payer))
        pdf1,num1=make_pdf(row,"devis")
        pdf2,num2=make_pdf(row,"facture")
        st.download_button("📄 Télécharger le devis PDF",pdf1,file_name=f"{num1}.pdf",mime="application/pdf",use_container_width=True)
        if row.Statut=="Facturé" or row.Reste_A_Payer<=0:
            st.download_button("🧾 Télécharger la facture PDF",pdf2,file_name=f"{num2}.pdf",mime="application/pdf",use_container_width=True)
        else:
            st.info("La facture peut être générée après passage du dossier en « Facturé ».")
        st.divider()
        st.subheader("Modification commerciale")
        with st.form("commercial"):
            a,b=st.columns(2)
            price=a.number_input("Prix HT",min_value=0.,value=float(row.Prix_HT))
            deposit=b.number_input("Acompte",min_value=0.,value=float(row.Acompte))
            status=a.selectbox("Statut",STATUTS,index=STATUTS.index(row.Statut))
            if st.form_submit_button("Mettre à jour",use_container_width=True):
                i=df.index[df.ID==sid][0]
                df.loc[i,"Prix_HT"]=price; df.loc[i,"Acompte"]=deposit
                df.loc[i,"Reste_A_Payer"]=0 if status=="Facturé" else max(price-deposit,0)
                df.loc[i,"Statut"]=status
                df.to_csv(DB_CHANTIERS,index=False); sync_chantiers_cache(df)
                log_event("Facturation",f"Dossier #{sid} mis à jour : {status}")
                st.success("Enregistré."); st.rerun()

# ============================================================================
# TEMPS
# ============================================================================
elif menu=="⏱️ Temps & rentabilité":
    st.title("⏱️ Temps & rentabilité")
    active=df[df.Statut=="En cours"]
    if not active.empty:
        with st.form("hours"):
            sid=st.selectbox("Chantier",active.ID.tolist(),format_func=lambda x:f"#{x} · {active.loc[active.ID==x,'Client'].iloc[0]}")
            h=st.number_input("Heures à ajouter",min_value=.1,max_value=20.,value=1.,step=.5)
            if st.form_submit_button("Enregistrer",use_container_width=True):
                i=df.index[df.ID==sid][0]; df.loc[i,"Heures_Passees"]+=h
                df.to_csv(DB_CHANTIERS,index=False); sync_chantiers_cache(df)
                log_event("Temps",f"{h:g} h ajoutées au projet #{sid}")
                st.success("Temps enregistré."); st.rerun()
    else: st.info("Aucun chantier en cours.")
    st.divider()
    r=df.copy()
    r["Taux horaire réel"]=r.apply(lambda x:x.Prix_HT/x.Heures_Passees if x.Heures_Passees>0 else 0,axis=1)
    st.dataframe(r[["ID","Client","Meuble","Prix_HT","Heures_Passees","Taux horaire réel","Statut"]],
                 hide_index=True,use_container_width=True,
                 column_config={"Prix_HT":st.column_config.NumberColumn("Prix HT",format="%.2f €"),
                                "Heures_Passees":st.column_config.NumberColumn("Heures",format="%.1f h"),
                                "Taux horaire réel":st.column_config.NumberColumn("Taux réel",format="%.2f €/h")})

# ============================================================================
# STOCKS
# ============================================================================
elif menu=="🌿 Stocks":
    st.title("🌿 Stocks & consommables")
    if stocks.empty: st.info("Inventaire vide.")
    else:
        stocks["Alerte"]=stocks.Quantité<=stocks.Seuil_Alerte
        alert=stocks[stocks.Alerte]
        a,b=st.columns(2); a.metric("Références",len(stocks)); b.metric("Alertes",len(alert))
        for _,r in alert.iterrows(): st.warning(f"Stock faible · **{r.Article}** : {r.Quantité:g} {r.Unité}.")
        st.dataframe(stocks.drop(columns=["Alerte"]),hide_index=True,use_container_width=True)
    with st.form("stock"):
        a,b,c=st.columns(3)
        art=a.text_input("Article"); cat=b.selectbox("Catégorie",["Peintures & Patines","Vernis & Cires","Abrasifs & Ponçage","Produits de traitement"])
        q=c.number_input("Quantité",min_value=0.,step=1.)
        unit=a.text_input("Unité",value="Unités"); threshold=b.number_input("Seuil",min_value=0.,value=2.,step=1.)
        if st.form_submit_button("Mettre à jour",use_container_width=True) and art.strip():
            mask=(stocks.Article==art.strip())&(stocks["Catégorie"]==cat)
            if mask.any(): stocks.loc[mask,"Quantité"]+=q
            else: stocks=pd.concat([stocks,pd.DataFrame([[art.strip(),cat,q,unit,threshold]],columns=["Article","Catégorie","Quantité","Unité","Seuil_Alerte"])],ignore_index=True)
            stocks.to_csv(DB_STOCKS,index=False); log_event("Stock",f"Stock mis à jour : {art.strip()}"); st.success("Stock enregistré."); st.rerun()

# ============================================================================
# STATS
# ============================================================================
elif menu=="📈 Statistiques":
    st.title("📈 Statistiques")
    if df.empty: st.info("Aucune donnée.")
    else:
        d=df.copy(); d["Date"]=pd.to_datetime(d.Date_Creation,errors="coerce"); d["Année"]=d.Date.dt.year.fillna(datetime.now().year).astype(int)
        years=sorted(d.Année.unique()); year=st.selectbox("Exercice",years,index=len(years)-1); d=d[d.Année==year]
        a,b,c,d4=st.columns(4)
        a.metric("CA potentiel",euro(d.Prix_HT.sum())); b.metric("CA facturé",euro(d.loc[d.Statut=="Facturé","Prix_HT"].sum()))
        c.metric("Panier moyen",euro(d.Prix_HT.mean() if len(d) else 0)); d4.metric("Projets",len(d))
        left,right=st.columns(2)
        with left: st.subheader("CA par type"); st.bar_chart(d.groupby("Type_Meuble").Prix_HT.sum(),height=300)
        with right: st.subheader("Statuts"); st.bar_chart(d.Statut.value_counts().reindex(STATUTS,fill_value=0),height=300)
        d["Mois"]=d.Date.dt.to_period("M").astype(str); st.subheader("CA mensuel"); st.line_chart(d.groupby("Mois").Prix_HT.sum(),height=280)

# ============================================================================
# PARAMÈTRES / JOURNAL / EXPORT
# ============================================================================
elif menu=="⚙️ Paramètres":
    st.title("⚙️ Paramètres & sécurité")
    tab1,tab2,tab3=st.tabs(["Exports","Journal d'activité","Tarifs métier"])
    with tab1:
        st.download_button("⬇️ Export projets CSV",df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"tocca_projets_{datetime.now():%Y%m%d}.csv",mime="text/csv",use_container_width=True)
        st.download_button("⬇️ Export stocks CSV",stocks.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"tocca_stocks_{datetime.now():%Y%m%d}.csv",mime="text/csv",use_container_width=True)
        if st.button("💾 Sauvegarder la base",use_container_width=True):
            stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(DB, BACKUP_DIR/f"backup_{stamp}_tocca.db")
            shutil.copy2(DB_CHANTIERS, BACKUP_DIR/f"backup_{stamp}_chantiers.csv")
            shutil.copy2(DB_STOCKS, BACKUP_DIR/f"backup_{stamp}_stocks.csv")
            st.success("Sauvegarde complète créée.")
    with tab2:
        journal=pd.read_sql_query("SELECT * FROM journal ORDER BY id DESC LIMIT 100",CONN)
        st.dataframe(journal,hide_index=True,use_container_width=True)
    with tab3:
        st.dataframe(pd.DataFrame(TARIFS_METIER).T,use_container_width=True)

st.caption("TOCCA CORSA EI · Atelier d’Upcycling d’Art · Afa (Corse-du-Sud) · Logiciel PRO V3")
