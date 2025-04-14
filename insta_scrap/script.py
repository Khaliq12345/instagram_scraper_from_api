import json
import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


def charger_fichier_excel(nom_fichier):
    chemin_fichier = os.path.join(os.getcwd(), nom_fichier)
    try:
        df = pd.read_excel(chemin_fichier)
        return df
    except FileNotFoundError:
        print(
            f"Erreur: Le fichier '{nom_fichier}' n'a pas été trouvé dans le répertoire courant."
        )
        return None
    except Exception as e:
        print(f"Une erreur s'est produite lors du chargement du fichier: {e}")
        return None


def ecrire_ligne_resultat(file_name: str, df: pd.DataFrame):
    if os.path.exists(file_name):
        df.to_csv(file_name, mode="a", header=False, index=False)
    else:
        df.to_csv(file_name, index=False)


def get_followers(username, start_from):
    rapidapi_key = os.getenv("rapidapi_key")
    try:
        url = "https://social-api4.p.rapidapi.com/v1/followers"
        querystring = {"username_or_id_or_url": username}
        if start_from:
            querystring["pagination_token"] = start_from
        headers = {
            "x-rapidapi-key": rapidapi_key,
            "x-rapidapi-host": "social-api4.p.rapidapi.com",
        }
        response = requests.get(url, headers=headers, params=querystring)
        json_data = response.json()
        items = json_data.get("data", {})
        token = json_data.get("pagination_token", None)
        items = items.get("items", []) if items else []
        return items, token
    except Exception as e:
        print(f"Error while getting folowers : {e}")
        return None, None


def get_gender(username):
    gender_key = os.getenv("gender_key")
    try:
        url = "https://api.genderapi.io/api/"
        payload = {"name": username, "key": gender_key}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, data=payload, headers=headers)
        return json.loads(response.text)
    except Exception as e:
        print(f"Error while getting gender : {e}")
        return None


def process_input_dataframe(df_source: pd.DataFrame):
    already_got = 0
    total_results = 5
    file_name = f"{str(int(datetime.now().timestamp()))}.csv"
    if df_source.empty:
        return None
    for index, row in df_source.iterrows():
        username = row["username_or_url"]
        next_start_from = None
        while total_results > already_got:
            print(
                f"Username_url: {username} | total_results: {total_results} | already_got: {already_got} | start_from: {next_start_from}"
            )
            followers_res, next_start_from = get_followers(username, next_start_from)
            if not followers_res:
                break
            print(f"Total users: {len(followers_res)}, already got: {already_got}")
            for user in followers_res:
                if not user.get("full_name"):
                    continue
                gender_res = get_gender(user["full_name"])
                if (
                    (gender_res)
                    and ("gender" in gender_res)
                    and ("country" in gender_res)
                ):
                    if (gender_res["gender"] == "male") and (
                        gender_res["country"] == "US"
                    ):
                        result = {
                            "username": user["username"],
                            "full name": user["full_name"],
                            "gender": gender_res["gender"],
                            "country": gender_res["country"],
                        }
                        df = pd.DataFrame(result, index=[0])
                        ecrire_ligne_resultat(file_name, df)
                        already_got = already_got + 1
                        print(
                            f"Total : {already_got} -- Une ligne Ajoutee pour le lien {index + 1}"
                        )
    print("DONE!")
    return file_name


# def start_insta_bot() -> str:
# process_inpuern_dataframe(input_df)
