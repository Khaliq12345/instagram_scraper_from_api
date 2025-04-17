from dotenv import load_dotenv
from datetime import datetime
import hashlib
import json
import os
import requests
import time

load_dotenv()


def check_uri(url, querystring, headers, max_retries=3, timeout=30) -> dict | None:
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url=url, headers=headers, params=querystring, timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            # json.dumps(data, indent=2)
            return data.get("data", None)
        except requests.exceptions.RequestException as e:
            print(f"[Tentative {attempt + 1}] Échec : {e}")
            if attempt < max_retries - 1:
                print("Nouvelle tentative...\n")
    print("❌ Échec après plusieurs tentatives.")
    return None


def is_at_least(value, minimum) -> bool:
    return value >= minimum


def is_at_most(value, maximum) -> bool:
    return value <= maximum


def is_between(value, lower, upper) -> bool:
    return lower <= value <= upper


def is_equal(value1, value2) -> bool:
    return value1 == value2


def parse_french_date(date_str: str) -> datetime:
    mois_fr_en = {
        "janvier": "January",
        "février": "February",
        "mars": "March",
        "avril": "April",
        "mai": "May",
        "juin": "June",
        "juillet": "July",
        "août": "August",
        "septembre": "September",
        "octobre": "October",
        "novembre": "November",
        "décembre": "December",
    }

    date_str = date_str.lower()
    mois, annee = date_str.split()
    mois_en = mois_fr_en.get(mois)

    if not mois_en:
        raise ValueError(f"Mois inconnu: '{mois}'")

    date_en = f"{mois_en} {annee}"
    return datetime.strptime(date_en, "%B %Y")


def get_image_bytes(image_url) -> bytes | None:
    image_bytes = None
    try:
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_bytes = image_response.content
        return image_bytes
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement de l'image : {e}")


def generate_unique_filename(image_url: str) -> str:
    base = f"{image_url}_{int(time.time())}"
    hash_digest = hashlib.md5(base.encode()).hexdigest()
    return f"{hash_digest}.jpg"


def download_image(
    username: str,
    image_url: str,
    save_dir: str = "images",
    filename: str = "profile.jpg",
):
    os.makedirs(save_dir, exist_ok=True)
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        filename = generate_unique_filename(image_url)
        filepath = os.path.join(save_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"✅ Image téléchargée avec succès : {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        print(f"❌ Échec du téléchargement : {e}")
        return None


def get_user_infos(username):
    url = "https://instagram-social-api.p.rapidapi.com/v1/info"
    querystring = {
        "username_or_id_or_url": username,
        "include_about": "true",
        "url_embed_safe": "true",
    }
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": os.getenv("RAPIDAPI_HOST"),
    }
    data = check_uri(url, querystring, headers)

    if data:

        post_count = data.get("post_count", data.get("media_count"))
        if not post_count or not is_at_least(post_count, 3):
            return None
        following_count = data.get("following_count", "")
        if not is_at_least(following_count, 300):
            return None
        follower_count = data.get("follower_count", "")
        if not is_between(post_count, 50, 5000):
            return None
        date_joined = data.get("about", {}).get("date_joined")
        formatted_date_joined = datetime.strptime(date_joined, "%B %Y")
        today = datetime.today()
        months = (today.year - formatted_date_joined.year) * 12 + (
            today.month - formatted_date_joined.month
        )
        if months < 6:
            return None
        country = data.get("about", {}).get("country")
        if not is_equal(country, "United States"):
            return None

        user = {
            "user_infos": {
                "username": data.get("username", ""),
                "full_name": data.get("full_name", ""),
                "profile_link": f"https://instagram.com/{data.get('username')}",
                "bio": data.get("biography", ""),
                "image": data.get("profile_pic_url_hd", data.get("profile_pic_url")),
                "follower_count": data.get("follower_count", ""),
                "following_count": data.get("following_count", ""),
                "post_count": data.get("post_count", data.get("media_count")),
                # "account_type": data.get("about", {}).get("account_type", ""),
                # "date_joined": data.get("about", {}).get("date_joined")
            },
            "image_bytes": get_image_bytes(
                data.get("profile_pic_url_hd", data.get("profile_pic_url"))
            ),
        }
        download_image(
            username=data.get("username", ""),
            image_url=data.get("profile_pic_url_hd", data.get("profile_pic_url")),
        )
        return user
    else:
        return None


user_infos = get_user_infos("mrbeast")
print(user_infos)
