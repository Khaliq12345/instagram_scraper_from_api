from datetime import datetime
import dateparser
import requests
from the_retry import retry
from config import config
from insta_scrap.exceptions_client import exceptions


# Décorateur pour gérer les tentatives multiples avec un délai croissant en cas d'échec
# Fonction pour effectuer une requête HTTP GET avec gestion des erreurs.
def check_uri(url, querystring, headers, timeout=30):
    response = requests.get(
        url=url, headers=headers, params=querystring, timeout=timeout
    )
    response.raise_for_status()
    return response.json().get("data", None)


# Vérifie si la valeur est supérieure ou égale à la valeur minimale.
def is_at_least(value, minimum) -> bool:
    return value >= minimum


# Vérifie si la valeur est inférieure ou égale à la valeur maximale.
def is_at_most(value, maximum) -> bool:
    return value <= maximum


# Vérifie si la valeur est comprise entre les bornes inférieure et supérieure.
def is_between(value, lower, upper) -> bool:
    return lower <= value <= upper


# Vérifie si les deux valeurs sont égales.
def is_equal(value1, value2) -> bool:
    return value1 == value2


# Récupère l'image à partir de son URL et renvoie son contenu sous forme de bytes.
def get_image_bytes(image_url) -> bytes | None:
    print("Getting Image bytes")
    image_bytes = None
    try:
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_bytes = image_response.content
        return image_bytes
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement de l'image : {e}")


"""
    Récupère les informations publiques d'un utilisateur Instagram via une API externe.

    Arguments:
    - username: nom d'utilisateur Instagram

    Retour:
    - Un dictionnaire contenant les informations de l'utilisateur et les bytes de l'image de profil si les critères sont remplis,
      sinon None si l'utilisateur ne correspond pas aux critères
"""


@retry(attempts=2, expected_exception=exceptions)
def get_user_infos(username):
    print(f"Getting user - {username} info")
    url = "https://instagram-social-api.p.rapidapi.com/v1/info"
    querystring = {
        "username_or_id_or_url": username,
        "include_about": "true",
        "url_embed_safe": "true",
    }
    headers = {
        "X-RapidAPI-Key": config.RAPID_API_KEY,
        "X-RapidAPI-Host": "instagram-social-api.p.rapidapi.com",
    }
    data = check_uri(url, querystring, headers)

    if data:
        print(f"Validating user - {username} info")
        # Validation des critères de l'utilisateur
        post_count = data.get("post_count", data.get("media_count"))
        if not post_count or not is_at_least(post_count, 3):
            return None
        following_count = data.get("following_count", 0)
        if not is_at_least(following_count, 300):
            return None
        follower_count = data.get("follower_count", 0)
        if not is_between(follower_count, 50, 5000):
            return None
        date_joined = data.get("about", {}).get("date_joined")
        formatted_date_joined = dateparser.parse(date_joined)
        today = datetime.today()
        months = (today.year - formatted_date_joined.year) * 12 + (
            today.month - formatted_date_joined.month
        )
        if months < 6:
            return None
        # country = data.get("about", {}).get("country")
        # if not is_equal(country, "United States"):
        #     return None

        user = {
            "user_infos": {
                "username": data.get("username", ""),
                "full_name": data.get("full_name", ""),
                "profile_link": f"https://instagram.com/{data.get('username')}",
                "bio": data.get("biography", ""),
                "image": data.get("profile_pic_url_hd", data.get("profile_pic_url")),
                "follower_count": data.get("follower_count", ""),
                "following_count": data.get("following_count", ""),
                "post_count": data.get("media_count"),
            },
            "image_bytes": get_image_bytes(
                data.get("profile_pic_url_hd", data.get("profile_pic_url"))
            ),
        }
        print(f"User is valid - {username}")
        return user
    else:
        return None


# # Appel de la fonction avec un exemple d'utilisateur
# user_infos = get_user_infos("mrbeast")
# print(user_infos)
