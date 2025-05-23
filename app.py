
import streamlit as st
from supabase import create_client, Client
import uuid
from datetime import datetime
from streamlit_option_menu import option_menu

st.set_page_config(page_title="ORPI Reco", layout="wide")

# Connexion Supabase
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

# Authentification
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

# Navigation principale
with st.sidebar:
    selected = option_menu(
        menu_title="Menu",
        options=["🏠 Accueil", "📝 Nouvelle recommandation", "📂 Mes recommandations"],
        icons=["house", "plus-square", "list-ul"],
        menu_icon="cast",
        default_index=0,
    )

st.title(f"{selected}")

# Page Accueil - KPI
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

# Page Nouvelle Recommandation
if selected == "📝 Nouvelle recommandation":
    users = supabase.table("users").select("*").neq("id", st.session_state.user["id"]).execute().data
    users_by_point = {}
    for u in users:
        key = u["point_de_vente"] or "Autres"
        users_by_point.setdefault(key, []).append(u)
    point = st.selectbox("Point de vente", list(users_by_point.keys()))
    selected_user = st.selectbox(
        "Destinataire", users_by_point[point],
        format_func=lambda x: f"{x['first_name']} {x['last_name']} ({x['poste']})"
    )
    client_name = st.text_input("Nom du client")
    client_email = st.text_input("Email client")
    client_phone = st.text_input("Téléphone client")
    projet = st.selectbox("Projet", [
        "vente", "achat", "location", "gestion", "syndic", "entreprise",
        "location + gestion", "recrutement", "CGI"
    ])
    details = st.text_area("Détails du projet")
    adresse = st.text_input("Adresse du projet")
    if st.button("Envoyer la recommandation"):
        supabase.table("recommendations").insert({
            "id": str(uuid.uuid4()),
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
        st.success("Recommandation envoyée !")

# Page Mes recommandations
if selected == "📂 Mes recommandations":
    recs_env = supabase.table("recommendations").select("*").eq("sender_id", st.session_state.user["id"]).order("created_at", desc=True).execute().data
    recs_rec = supabase.table("recommendations").select("*").eq("receiver_id", st.session_state.user["id"]).order("created_at", desc=True).execute().data
    tab1, tab2 = st.tabs(["📤 Envoyées", "📥 Reçues"])

    def afficher_reco(r):
        st.write(f"**Client :** {r['client_name']}")
        st.write(f"**Projet :** {r['projet']}")
        st.write(f"**Adresse :** {r['adresse']}")
        st.write(f"**Statut :** `{r['statut']}`")
        st.write(f"_Envoyée le {r['created_at'][:10]}_")
        st.markdown("---")

    with tab1:
        if not recs_env:
            st.info("Aucune recommandation envoyée.")
        else:
            for r in recs_env:
                afficher_reco(r)

    with tab2:
        if not recs_rec:
            st.info("Aucune recommandation reçue.")
        else:
            for r in recs_rec:
                afficher_reco(r)
