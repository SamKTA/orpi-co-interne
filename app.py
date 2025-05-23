
import streamlit as st
from supabase import create_client, Client
from streamlit_option_menu import option_menu
import uuid
from datetime import datetime
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="ORPI Reco", layout="wide")

# Connexion Supabase
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

# Mail setup
MAIL_HOST = st.secrets["mail"]["smtp_host"]
MAIL_PORT = st.secrets["mail"]["smtp_port"]
MAIL_USER = st.secrets["mail"]["smtp_user"]
MAIL_PASS = st.secrets["mail"]["smtp_password"]

def envoyer_mail(to, sujet, corps):
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = MAIL_USER
    msg["To"] = to
    msg.set_content(corps)
    with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
        server.starttls()
        server.login(MAIL_USER, MAIL_PASS)
        server.send_message(msg)

# Authentification utilisateur
if "user" not in st.session_state:
    st.session_state.user = None
if st.session_state.user is None:
    st.title("Connexion")
    with st.form("login_form"):
        email = st.text_input("Adresse e-mail")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")
    if submitted:
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            st.session_state.user = user.data[0]
            st.success(f"Bienvenue {st.session_state.user['first_name']} !")
            st.stop()
        else:
            st.error("Identifiants incorrects")
    st.stop()

# Menu latéral
with st.sidebar:
    selected = option_menu(
        menu_title="Menu",
        options=["🏠 Accueil", "📝 Nouvelle recommandation", "📂 Mes recommandations"],
        icons=["house", "plus-square", "list-ul"],
        menu_icon="cast",
        default_index=0,
    )

st.title(f"{selected}")

# Accueil
if selected == "🏠 Accueil":
    sent = supabase.table("recommendations").select("*").eq("sender_id", st.session_state.user["id"]).execute().data
    received = supabase.table("recommendations").select("*").eq("receiver_id", st.session_state.user["id"]).execute().data
    transformed_status = ["Transformé", "Acté/Facturé", "Recruté"]
    transformed = [r for r in received if r["statut"] in transformed_status]
    ca_instant = sum([r["chiffre_affaire_instant"] or 0 for r in transformed])
    ca_annuel = sum([r["chiffre_affaire_annuel"] or 0 for r in transformed])

    col1, col2, col3 = st.columns(3)
    col1.metric("📤 Envoyées", len(sent))
    col2.metric("📥 Reçues", len(received))
    col3.metric("✅ Transformées", len(transformed))
    st.markdown("---")
    col4, col5 = st.columns(2)
    col4.metric("💶 CA généré (€)", f"{ca_instant:,.0f}".replace(",", " "))
    col5.metric("📈 CA annuel projeté (€)", f"{ca_annuel:,.0f}".replace(",", " "))

# Nouvelle recommandation
elif selected == "📝 Nouvelle recommandation":
    users = supabase.table("users").select("*").neq("id", st.session_state.user["id"]).execute().data
    users_by_point = {}
    for u in users:
        key = u["point_de_vente"] or "Autres"
        users_by_point.setdefault(key, []).append(u)
    point = st.selectbox("Point de vente", list(users_by_point.keys()))
    selected_user = st.selectbox("Destinataire", users_by_point[point], format_func=lambda x: f"{x['first_name']} {x['last_name']} ({x['poste']})")
    client_name = st.text_input("Nom du client")
    client_email = st.text_input("Email client")
    client_phone = st.text_input("Téléphone client")
    projet = st.selectbox("Projet", ["vente", "achat", "location", "gestion", "syndic", "entreprise", "location + gestion", "recrutement", "CGI"])
    details = st.text_area("Détails du projet")
    adresse = st.text_input("Adresse du projet")

    if st.button("Envoyer la recommandation"):
        reco_id = str(uuid.uuid4())
        supabase.table("recommendations").insert({
            "id": reco_id,
            "sender_id": st.session_state.user["id"],
            "receiver_id": selected_user["id"],
            "client_name": client_name,
            "client_email": client_email,
            "client_phone": client_phone,
            "projet": projet,
            "details": details,
            "adresse": adresse,
            "statut": "Contacté",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        
        # Email
        lien = f"https://orpi-co-interne.streamlit.app/?reco_id={reco_id}"
        corps = f"""Nouvelle recommandation reçue de {st.session_state.user["first_name"]} {st.session_state.user["last_name"]}.

Client : {client_name}
Projet : {projet}

Accéder à la reco : {lien}
"""
        envoyer_mail(selected_user["email"], "Nouvelle recommandation reçue", corps)

        st.success("Recommandation envoyée !")


# Mes recommandations
elif selected == "📂 Mes recommandations":
    recs_env = supabase.table("recommendations").select("*").eq("sender_id", st.session_state.user["id"]).order("created_at", desc=True).execute().data
    recs_rec = supabase.table("recommendations").select("*").eq("receiver_id", st.session_state.user["id"]).order("created_at", desc=True).execute().data
    tab_env, tab_rec = st.tabs(["📤 Envoyées", "📥 Reçues"])

    def afficher_reco(r):
        with st.expander(f"👁 {r['client_name']} - {r['projet']} ({r['statut']})"):
            st.write(f"📅 Envoyée le : {r['created_at'][:10]}")
            st.write(f"📌 Adresse : {r['adresse']}")
            st.write(f"📨 Email : {r['client_email']}")
            st.write(f"📞 Téléphone : {r['client_phone']}")
            st.write(f"📝 Détails : {r['details']}")
            if st.session_state.user["id"] == r["receiver_id"]:
                new_statut = st.selectbox("Modifier le statut", ["Contacté", "Messagerie", "Injoignable", "Rdv pris", "Estimé", "Sous offre", "En cours", "Transformé", "Acté/Facturé", "Recruté", "Sans suite"], index=["Contacté", "Messagerie", "Injoignable", "Rdv pris", "Estimé", "Sous offre", "En cours", "Transformé", "Acté/Facturé", "Recruté", "Sans suite"].index(r["statut"]))
                ca_instant = None
                ca_annuel = None
                if new_statut in ["Transformé", "Acté/Facturé", "Recruté"]:
                    ca_instant = st.number_input("CA généré instantané (€)", min_value=0.0)
                    ca_annuel = st.number_input("CA annuel projeté (€)", min_value=0.0)
                if st.button("Enregistrer les modifications", key=r["id"]):
                    update = {"statut": new_statut}
                    if ca_instant is not None: update["chiffre_affaire_instant"] = ca_instant
                    if ca_annuel is not None: update["chiffre_affaire_annuel"] = ca_annuel
                    supabase.table("recommendations").update(update).eq("id", r["id"]).execute()
                    st.success("Recommandation mise à jour")

    with tab_env:
        for r in recs_env:
            afficher_reco(r)
    with tab_rec:
        for r in recs_rec:
            afficher_reco(r)
