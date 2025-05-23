
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
        name = st.text_input("Prénom")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        user = supabase.table("users").select("*").eq("first_name", name).eq("password", password).execute()
        if user.data:
            st.session_state.user = user.data[0]
            st.success(f"Bienvenue {name} !")
            st.experimental_rerun()
        else:
            st.error("Utilisateur ou mot de passe incorrect.")

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
