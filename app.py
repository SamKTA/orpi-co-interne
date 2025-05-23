
import streamlit as st
from supabase import create_client, Client
import uuid

st.set_page_config(page_title="ORPI Reco Interne", layout="centered")

# Connexion Supabase
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

st.title("Connexion")

# Formulaire de connexion
with st.form("login_form"):
    name = st.text_input("Prénom")
    password = st.text_input("Mot de passe", type="password")
    submitted = st.form_submit_button("Se connecter")

if submitted:
    user = supabase.table("users").select("*").eq("first_name", name).eq("password", password).execute()
    if user.data:
        st.success(f"Bienvenue {name} !")
        st.write("⚙️ Interface de recommandation à venir ici…")
    else:
        st.error("Utilisateur ou mot de passe incorrect.")
