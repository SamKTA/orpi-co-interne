
import streamlit as st
from supabase import create_client, Client
import uuid
from datetime import datetime

st.set_page_config(page_title="ORPI Reco Interne", layout="centered")

# Connexion Supabase
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

st.title("Connexion")

# Stockage session
if "user" not in st.session_state:
    st.session_state.user = None

# Connexion utilisateur
if st.session_state.user is None:
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
            st.error("Adresse e-mail ou mot de passe incorrect.")

# Formulaire de recommandation
if st.session_state.user:
    st.subheader("Faire une recommandation")

    # Récupération des utilisateurs pour le menu déroulant
    users = supabase.table("users").select("*").neq("id", st.session_state.user["id"]).execute().data

    # Organiser par point de vente
    users_by_point = {}
    for u in users:
        key = u["point_de_vente"] or "Autres"
        users_by_point.setdefault(key, []).append(u)

    point = st.selectbox("Choisissez un point de vente", list(users_by_point.keys()))
    selected_user = st.selectbox(
        "Destinataire de la recommandation",
        users_by_point[point],
        format_func=lambda x: f"{x['first_name']} {x['last_name']} ({x['poste']})"
    )

    # Formulaire client
    client_name = st.text_input("Nom du client")
    client_email = st.text_input("Email du client")
    client_phone = st.text_input("Téléphone du client")
    projet = st.selectbox("Projet concerné", [
        "vente", "achat", "location", "gestion", "syndic", "entreprise",
        "location + gestion", "recrutement", "CGI"
    ])
    details = st.text_area("Détail du projet")
    adresse = st.text_input("Adresse du projet")

    if st.button("Envoyer la recommandation"):
        new_id = str(uuid.uuid4())
        supabase.table("recommendations").insert({
            "id": new_id,
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
        st.success("Recommandation envoyée avec succès ✅")


# Tableau de bord d'accueil
st.subheader("🏠 Tableau de bord")

# Recommandations liées à l'utilisateur
sent = supabase.table("recommendations").select("*").eq("sender_id", st.session_state.user["id"]).execute().data
received = supabase.table("recommendations").select("*").eq("receiver_id", st.session_state.user["id"]).execute().data

# Recommandations transformées
transformed_status = ["Transformé", "Acté/Facturé", "Recruté"]
transformed = [r for r in received if r["statut"] in transformed_status]

# Chiffre d'affaires total
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
