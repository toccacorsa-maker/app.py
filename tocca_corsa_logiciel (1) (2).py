import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime, timedelta

# ==============================================================================
# 1. CONFIGURATION DE LA PAGE & STYLE ARTISANAL PREMIUM
# ==============================================================================
st.set_page_config(page_title="TOCCA CORSA — Logiciel de Gestion", layout="wide", page_icon="🪚")

# Palette écoresponsable : Vert Sauge, Bois Patiné, Lin Brut
st.markdown("""
    <style>
    .main { background-color: #f7f5f0; }
    h1, h2, h3 { color: #2c3e2b !important; font-family: 'Georgia', serif; }
    .stButton>button {
        background-color: #4a5d4e;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover { background-color: #354438; color: white; }
    div[data-testid="stMetricValue"] { color: #8e7355; font-family: 'Georgia', serif; font-size: 2rem; }
    .kpi-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .badge-ok { background-color: #d4edda; color: #155724; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-warning { background-color: #fff3cd; color: #856404; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-danger { background-color: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .invoice-box { background-color: white; padding: 30px; border: 1px solid #ddd; font-family: 'Courier New', Courier, monospace; color: #000000; }
    </style>
""", unsafe_allow_html=True)

# En-tête officiel
st.title("🪚 TOCCA CORSA — Système de Gestion Intégral")
st.markdown("*Atelier d'Upcycling & Éco-surcyclage de Mobilier d'Art — Afa (Corse-du-Sud)*")
st.caption("⚖️ Statut : Entreprise Individuelle (EI) — Régime : TVA non applicable, art. 293 B du CGI")

# ==============================================================================
# 2. INITIALISATION, SÉCURITÉ & SAUVEGARDE CLOUD AUTOMATIQUE
# ==============================================================================
DB_CHANTIERS = "chantiers_tocca_corsa.csv"
DB_STOCKS = "stocks_tocca_corsa.csv"
DIR_SAUVEGARDE = "sauvegardes_secours"

COLUMNS_CHANTIERS = [
    "ID", "Client", "Téléphone", "Meuble", "Type_Meuble", "Prestation", 
    "Complexite", "Statut", "Prix_HT", "Acompte", "Reste_A_Payer", "Date_Creation", "Heures_Passees"
]

if not os.path.exists(DIR_SAUVEGARDE):
    os.makedirs(DIR_SAUVEGARDE)

if not os.path.exists(DB_CHANTIERS):
    pd.DataFrame(columns=COLUMNS_CHANTIERS).to_csv(DB_CHANTIERS, index=False)
if not os.path.exists(DB_STOCKS):
    pd.DataFrame(columns=["Article", "Catégorie", "Quantité", "Unité", "Seuil_Alerte"]).to_csv(DB_STOCKS, index=False)

def sauvegarder_donnees(df, filename):
    df.to_csv(filename, index=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = os.path.join(DIR_SAUVEGARDE, f"backup_{timestamp}_{filename}")
    shutil.copyfile(filename, backup_name)

df_chantiers = pd.read_csv(DB_CHANTIERS)
df_stocks = pd.read_csv(DB_STOCKS)

if not df_chantiers.empty:
    df_chantiers["Prix_HT"] = pd.to_numeric(df_chantiers["Prix_HT"]).fillna(0.0).round(2)
    df_chantiers["Acompte"] = pd.to_numeric(df_chantiers["Acompte"]).fillna(0.0).round(2)
    df_chantiers["Reste_A_Payer"] = pd.to_numeric(df_chantiers["Reste_A_Payer"]).fillna(0.0).round(2)
    df_chantiers["Heures_Passees"] = pd.to_numeric(df_chantiers["Heures_Passees"]).fillna(0.0)

# ==============================================================================
# 3. RÉFÉRENTIEL MÉTIER (GRILLE TARIFAIRE DU LIVRET D'ACCUEIL)
# ==============================================================================
TARIFS_METIER = {
    "Chaise / Tabouret": {"Aérogommage Seul": 45.0, "Relooking & Finitions": 95.0},
    "Table de chevet / Petit meuble": {"Aérogommage Seul": 90.0, "Relooking & Finitions": 190.0},
    "Commode / Console (3 tiroirs)": {"Aérogommage Seul": 250.0, "Relooking & Finitions": 480.0},
    "Table de repas (4 à 6 personnes)": {"Aérogommage Seul": 320.0, "Relooking & Finitions": 650.0},
    "Buffet bas / Enfilade (3-4 portes)": {"Aérogommage Seul": 450.0, "Relooking & Finitions": 890.0},
    "Armoire ancienne / Grand Vaisselier": {"Aérogommage Seul": 650.0, "Relooking & Finitions": 1200.0}
}

# ==============================================================================
# 4. NAVIGATION PRINCIPALE
# ==============================================================================
st.sidebar.markdown("### 🛠️ Menu Principal")
menu = st.sidebar.radio(
    "Accéder aux espaces :",
    [
        "📊 Tableau de Bord & 48h", 
        "📋 Suivi Kanban Atelier", 
        "➕ Simulateur & Nouveau Devis", 
        "⏱️ Temps & Rentabilité Horaire",
        "🖨️ Facturation & Relances",
        "🌿 Stocks & Éco-Consommables",
        "📈 Statistiques Annuelles"
    ]
)

# MODULE 1 : TABLEAU DE BORD & SUIVI 48H
if menu == "📊 Tableau de Bord & 48h":
    st.header("📊 Tableau de Bord de l'Atelier")
    if not df_chantiers.empty:
        total_ca = float(df_chantiers["Prix_HT"].sum())
        total_encaisse = float(df_chantiers["Acompte"].sum() + df_chantiers[df_chantiers["Statut"] == "Facturé"]["Reste_A_Payer"].sum())
        total_reste = float(df_chantiers["Reste_A_Payer"].sum())
        chantiers_actifs = len(df_chantiers[df_chantiers["Statut"].isin(["En attente", "En cours"])])
        
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Chiffre d'Affaires Global (HT)", f"{total_ca:,.2f} €")
        with m2: st.metric("Fonds Encaissés", f"{total_encaisse:,.2f} €")
        with m3: st.metric("Reste à Encaisser", f"{total_reste:,.2f} €")
        with m4: st.metric("Projets Actifs", chantiers_actifs)
        
        st.write("---")
        st.subheader("⏳ Alerte Réactivité Client (Engagement Devis 48h)")
        devis_en_attente = df_chantiers[df_chantiers["Statut"] == "En attente"]
        
        if not devis_en_attente.empty:
            for idx, row in devis_en_attente.iterrows():
                try:
                    date_creation = datetime.strptime(str(row["Date_Creation"]), '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        date_creation = datetime.strptime(str(row["Date_Creation"]).split(), '%Y-%m-%d')
                    except Exception:
                        date_creation = datetime.now()
                
                date_limite = date_creation + timedelta(hours=48)
                temps_restant = date_limite - datetime.now()
                heures_restantes = temps_restant.total_seconds() / 3600
                
                if heures_restantes > 24:
                    badge = f'<span class="badge-ok">Délai OK ({int(heures_restantes)}h restantes)</span>'
                elif 0 <= heures_restantes <= 24:
                    badge = f'<span class="badge-warning">URGENT ({int(heures_restantes)}h restantes)</span>'
                else:
                    badge = f'<span class="badge-danger">RETARD (Dépassé de {abs(int(heures_restantes))}h)</span>'
                
                st.markdown(f"🔹 **Client :** {row['Client']} — **Meuble :** {row['Meuble']} | {badge}", unsafe_allow_html=True)
        else:
            st.success("🎉 Aucun devis en attente. Votre engagement qualité de 48h est parfaitement respecté !")
            
        st.write("---")
        st.subheader("📋 Liste Générale des Commandes")
        st.dataframe(df_chantiers, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun projet enregistré pour le moment.")

# MODULE 2 : VUE KANBAN
elif menu == "📋 Suivi Kanban Atelier":
    st.header("📋 Suivi Tactile des Postes de Travail")
    if not df_chantiers.empty:
        col_attente, col_encours, col_termine, col_facture = st.columns(4)
        
        with col_attente:
            st.markdown("### ⏳ En Attente")
            for _, r in df_chantiers[df_chantiers["Statut"] == "En attente"].iterrows():
                st.info(f"**ID {r['ID']} : {r['Client']}**\n\n*{r['Meuble']}*")
                
        with col_encours:
            st.markdown("### 🪵 À l'Atelier")
            for _, r in df_chantiers[df_chantiers["Statut"] == "En cours"].iterrows():
                st.warning(f"**ID {r['ID']} : {r['Client']}**\n\n*{r['Meuble']}*\n\n⏱️ {r['Heures_Passees']}h cumulées")
                
        with col_termine:
            st.markdown("### ✨ Prêt / Terminé")
            for _, r in df_chantiers[df_chantiers["Statut"] == "Terminé"].iterrows():
                st.success(f"**ID {r['ID']} : {r['Client']}**\n\n*{r['Meuble']}*")
                
        with col_facture:
            st.markdown("### 💶 Facturé")
            for _, r in df_chantiers[df_chantiers["Statut"] == "Facturé"].iterrows():
                st.markdown(f"✅ **ID {r['ID']} : {r['Client']}**\n\n*{r['Meuble']}*")
                
        st.write("---")
        st.subheader("⚙️ Déplacement de Projet")
        with st.form("quick_move"):
            id_m = st.selectbox("Sélectionner l'ID du meuble :", df_chantiers["ID"].tolist())
            stat_m = st.selectbox("Nouveau poste :", ["En attente", "En cours", "Terminé", "Facturé"])
            if st.form_submit_button("Actualiser la position"):
                idx = df_chantiers[df_chantiers["ID"] == id_m].index
                df_chantiers.loc[idx, "Statut"] = stat_m
                if stat_m == "Facturé":
                    df_chantiers.loc[idx, "Reste_A_Payer"] = 0.0
                sauvegarder_donnees(df_chantiers, DB_CHANTIERS)
                st.success("Position mise à jour, copie de sauvegarde générée.")
                st.rerun()

# MODULE 3 : SIMULATEUR DE DEVIS
elif menu == "➕ Simulateur & Nouveau Devis":
    st.header("➕ Création de Projet & Estimation Automatique")
    with st.form("form_devis"):
        c1, c2 = st.columns(2)
        with c1:
            client = st.text_input("Nom & Prénom du Client *")
            telephone = st.text_input("Téléphone")
        with c2:
            meuble = st.text_input("Désignation précise du meuble *")
            cat_meuble = st.selectbox("Type de meuble (Grille Tarifaire) :", list(TARIFS_METIER.keys()))
            
        type_prest = st.selectbox("Niveau d'intervention :", ["Aérogommage Seul", "Relooking & Finitions"])
        complexite = st.select_slider("Analyse technique de la pénibilité :", options=["Standard", "Moyen", "Complexe"])
        
        base_tarif = TARIFS_METIER[cat_meuble][type_prest]
        coef = 1.0 if complexite == "Standard" else (1.25 if complexite == "Moyen" else 1.50)
        prix_suggere = round(base_tarif * coef, 2)
        
        st.info(f"💡 Tarif théorique basé sur le livret d'accueil : {base_tarif} € HT | Prix ajusté à la pénibilité : {prix_suggere} € HT")
        
        final_ht = st.number_input("Prix final appliqué (€ HT)", min_value=0.0, value=float(prix_suggere))
        acompte = st.number_input("Acompte versé (30% préconisé)", min_value=0.0, value=round(final_ht * 0.3, 2))
        
        if st.form_submit_button("Enregistrer et Activer la surveillance 48h"):
            if client and meuble:
                nid = len(df_chantiers) + 1
                date_s = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_row = pd.DataFrame([[nid, client, telephone, meuble, cat_meuble, type_prest, complexite, "En attente", final_ht, acompte, round(final_ht-acompte, 2), date_s, 0.0]], columns=COLUMNS_CHANTIERS)
                df_chantiers = pd.concat([df_chantiers, new_row], ignore_index=True)
                sauvegarder_donnees(df_chantiers, DB_CHANTIERS)
                st.success("Chantier créé avec succès !")
                st.rerun()
            else:
                st.error("Veuillez remplir les champs obligatoires (*).")

# MODULE 4 : SUIVI DES HEURES & RENTABILITÉ RÉELLE
elif menu == "⏱️ Temps & Rentabilité Horaire":
    st.header("⏱️ Contrôle du Temps Passé & Analyse du Taux Horaire")
    chantiers_en_cours = df_chantiers[df_chantiers["Statut"] == "En cours"]
    if not chantiers_en_cours.empty:
        with st.form("ajout_temps"):
            id_t = st.selectbox("Sélectionner le chantier en cours :", chantiers_en_cours["ID"].tolist())
            heures_supp = st.number_input("Heures de travail à ajouter (ex: 2.5) :", min_value=0.1, max_value=15.0, step=0.5)
            if st.form_submit_button("Enregistrer le temps passé"):
                idx = df_chantiers[df_chantiers["ID"] == id_t].index
                df_chantiers.loc[idx, "Heures_Passees"] += heures_supp
                sauvegarder_donnees(df_chantiers, DB_CHANTIERS)
                st.success("Temps enregistré sur le meuble.")
                st.rerun()
    else:
        st.info("Aucun chantier n'est actuellement marqué 'En cours' à l'atelier.")
    st.write("---")
    st.subheader("📊 Rentabilité de vos projets d'artisanat")
    if not df_chantiers.empty:
        df_renta = df_chantiers.copy()
        df_renta["Taux_Horaire_Réel (€/h)"] = df_renta.apply(
            lambda r: round(r["Prix_HT"] / r["Heures_Passees"], 2) if r["Heures_Passees"] > 0 else 0.0, axis=1
        )
        st.dataframe(df_renta[["ID", "Client", "Meuble", "Prix_HT", "Heures_Passees", "Taux_Horaire_Réel (€/h)", "Statut"]], use_container_width=True, hide_index=True)

# MODULE 5 : FACTURATION & RELANCES COMMERCIALES
elif menu == "🖨️ Facturation & Relances":
    st.header("🖨️ Édition de Documents & Communication Client")
    if not df_chantiers.empty:
        id_doc = st.selectbox("Choisir un dossier client :", df_chantiers["ID"].tolist())
        row_doc = df_chantiers[df_chantiers["ID"] == id_doc].iloc[0]
        tab_fact, tab_relance = st.tabs(["📄 Aperçu du Document (Devis/Facture)", "💬 Messages de Relance Automatiques"])
        with tab_fact:
            is_facture = row_doc["Statut"] == "Facturé"
            st.markdown(f"""
            <div class="invoice-box">
                <h2 style='text-align: center; color: black;'>TOCCA CORSA EI</h2>
                <p style='text-align: center; color: black;'>Atelier d'Upcycling d'Art — Rénovation Écoresponsable<br>Afa (Corse-du-Sud) | contact@tocca-corsa.com</p>
                <hr>
                <p style='color: black;'><strong>Dossier N° :</strong> {row_doc['ID'] if is_facture else 'DEVIS_PROV_' + str(row_doc['ID'])}<br>
                <strong>Date :</strong> {row_doc['Date_Creation']}<br>
                <strong>Client :</strong> {row_doc['Client']}<br>
                <strong>Téléphone :</strong> {row_doc['Téléphone']}</p>
                <table style='width:100%; border-collapse: collapse; color: black;'>
                    <tr style='background:#f2f2f2;'>
                        <th style='text-align:left; padding:8px;'>Description des Prestations</th>
                        <th style='text-align:right; padding:8px;'>Montant HT</th>
                    </tr>
                    <tr>
                        <td style='padding:8px;'>{row_doc['Prestation']} sur {row_doc['Meuble']}<br><small>Finition éco-certifiée, traitement selon pénibilité : {row_doc['Complexite']}</small></td>
                        <td style='text-align:right; padding:8px;'>{row_doc['Prix_HT']:.2f} €</td>
                    </tr>
                </table>
                <hr style='margin-top:50px;'>
                <p style='text-align:right; color: black;'><strong>TOTAL NET À PAYER : {row_doc['Prix_HT']:.2f} €</strong><br>
                Acompte versé : {row_doc['Acompte']:.2f} €<br>
                <strong>Solde restant dû : {row_doc['Reste_A_Payer']:.2f} €</strong></p>
                <p style='font-size:11px; text-align:center; color:#555; margin-top:20px;'>TVA non applicable, article 293 B du CGI — Entreprise Individuelle bénéficiant de la franchise en base.</p>
            </div>
            """, unsafe_allow_html=True)
        with tab_relance:
            msg_48h = f"Bonjour {row_doc['Client']}, c'est l'atelier Tocca Corsa à Afa. Votre devis gratuit pour la rénovation de votre {row_doc['Meuble']} est prêt ! N'hésitez pas à me recontacter pour lancer votre projet écoresponsable. À bientôt !"
            msg_pret = f"Bonjour {row_doc['Client']}, bonne nouvelle ! Les sessions d'aérogommage et finitions sur votre {row_doc['Meuble']} sont achevées à l'atelier. Il est prêt à retrouver votre intérieur. À très vite chez Tocca Corsa !"
            st.text_area("1. Relance Devis (Engagement sous 48h) :", value=msg_48h, height=100)
            st.text_area("2. Notification de Fin de Chantier :", value=msg_pret, height=100)
    else:
        st.info("Aucune commande disponible.")

# MODULE 6 : INVENTAIRE DES STOCKS
elif menu == "🌿 Stocks & Éco-Consommables":
    st.header("🌿 Inventaire Permanent Éco-Artisanal")
    if not df_stocks.empty:
        df_stocks["Alerte"] = df_stocks["Quantité"] <= df_stocks["Seuil_Alerte"]
        alertes = df_stocks[df_stocks["Alerte"] == True]
        if not alertes.empty:
            for _, r in alertes.iterrows():
                st.markdown(f"⚠️ **Seuil critique atteint :** *{r['Article']}* — Reste seulement {r['Quantité']} {r['Unité']}.", unsafe_allow_html=True)
        st.dataframe(df_stocks, use_container_width=True, hide_index=True)
    else:
        st.info("Inventaire vide.")
    with st.form("ajout_stock"):
        c1, c2, c3 = st.columns(3)
        with c1: art = st.text_input("Désignation de la référence :")
        with c2: cat = st.selectbox("Type :", ["Peintures & Patines", "Vernis & Cires", "Abrasifs & Ponçage", "Produits de traitement"])
        with c3: qte = st.number_input("Quantité :", min_value=0.0)
        if st.form_submit_button("Actualiser le stock"):
            if art:
                mask = (df_stocks["Article"] == art) & (df_stocks["Catégorie"] == cat)
                if mask.any():
                    df_stocks.loc[mask, "Quantité"] += qte
                else:
                    new_art = pd.DataFrame([[art, cat, qte, "Unités", 2.0]], columns=["Article", "Catégorie", "Quantité", "Unité", "Seuil_Alerte"])
                    df_stocks = pd.concat([df_stocks, new_art], ignore_index=True)
                sauvegarder_donnees(df_stocks, DB_STOCKS)
                st.success("Mouvement de stock enregistré avec succès.")
                st.rerun()

# MODULE 7 : STATISTIQUES FINANCIÈRES ANNUELLES
elif menu == "📈 Statistiques Annuelles":
    st.header("📈 Performances Annuelles de l'Entreprise")
    if not df_chantiers.empty:
        def extraire_annee(val):
            try:
                return str(datetime.strptime(str(val), '%Y-%m-%d %H:%M:%S').year)
            except ValueError:
                try:
                    return str(str(val).split('-')[0])
                except Exception:
                    return str(datetime.now().year)
                
        df_stats = df_chantiers.copy()
        df_stats["Annee"] = df_stats["Date_Creation"].apply(extraire_annee)
        annees_dispo = sorted(df_stats["Annee"].unique().tolist())
        annee_select = st.selectbox("Sélectionner l'exercice comptable :", annees_dispo)
        df_annee = df_stats[df_stats["Annee"] == annee_select]
        
        ca_realise_annee = df_annee[df_annee["Statut"] == "Facturé"]["Prix_HT"].sum()
        ca_potentiel_annee = df_annee["Prix_HT"].sum()
        
        s1, s2 = st.columns(2)
        with s1: st.metric(f"Chiffre d'Affaires Encaissé en {annee_select}", f"{ca_realise_annee:,.2f} € HT")
        with s2: st.metric(f"Volume d'Affaires Global", f"{ca_potentiel_annee:,.2f} € HT")
        st.write("---")
        st.subheader("📊 Répartition du chiffre d'affaires par type de meuble")
        df_graph = df_annee.groupby("Type_Meuble")["Prix_HT"].sum().reset_index()
        st.bar_chart(data=df_graph, x="Type_Meuble", y="Prix_HT", color="#4a5d4e")
    else:
        st.info("Aucune donnée disponible.")
