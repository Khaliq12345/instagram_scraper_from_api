import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd
import requests
from dotenv import load_dotenv
from retry import retry
load_dotenv()

# 
RETRY_CONFIG = {
    'tries': 3,
    'delay': 2,
    'backoff': 2,
    'max_delay': 10
}

def ecrire_ligne_resultat(file_name: str, df: pd.DataFrame):
    if os.path.exists(file_name):
        df.to_csv(file_name, mode="a", header=False, index=False)
    else:
        df.to_csv(file_name, index=False)

def get_user_data(username):
    # Step 2
    result = {
        "username": username,
        "full_name": "Full Name",
        "profil_url": "https://profil.png",
        "last_post_date": "1673578844444",
    }
    return result

def special_function(user_data):
    # Step 3
    return True

@retry(exceptions=Exception, **RETRY_CONFIG)
def get_posts(username, result_count=10, min_comments=10):
    # Step 1-1
    rapidapi_key = os.getenv("rapidapi_key")
    token = None
    try:
        id_list = []
        while result_count > len(id_list):
            url = "https://instagram-social-api.p.rapidapi.com/v1/posts"
            querystring = {"username_or_id_or_url": username}
            if token:
                querystring["pagination_token"] = token
            headers = {
                "x-rapidapi-key": rapidapi_key,
                "x-rapidapi-host": "instagram-social-api.p.rapidapi.com",
            }
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            json_data = response.json()
            data = json_data.get("data", {})
            token = json_data.get("pagination_token", None)
            user = data.get("user", {}) if data else {}
            is_private = user.get("is_private", False) if user else False
            if is_private:
                return None
            posts = data.get("items", []) if data else []
            for p in posts:
                comment_count = p.get("comment_count", 0) if p else 0
                post_id = p.get("id", None) if p else None
                if comment_count > min_comments and post_id:
                    id_list.append(post_id)
            if not token:
                break
        return id_list
    except Exception as e:
        print(f"Error while getting posts: {e}")
        raise

@retry(exceptions=Exception, **RETRY_CONFIG)
def get_com_usernames(post_id):
    # Step 1-2
    rapidapi_key = os.getenv("rapidapi_key")
    token = None
    comments_got = 0
    try:
        usernames_list = []
        while True:
            url = "https://instagram-social-api.p.rapidapi.com/v1/comments"
            querystring = {"code_or_id_or_url": post_id}
            if token:
                querystring["pagination_token"] = token
            headers = {
                "x-rapidapi-key": rapidapi_key,
                "x-rapidapi-host": "instagram-social-api.p.rapidapi.com",
            }
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            json_data = response.json()
            data = json_data.get("data", {})
            token = json_data.get("pagination_token", None)
            count = data.get("count", 0) if data else 0
            total = data.get("total", 0) if data else 0
            comments = data.get("items", []) if data else []
            for c in comments:
                user = c.get("user", {}) if c else {}
                username = user.get("username", None) if user else None
                if username:
                    usernames_list.append(username)
            comments_got = comments_got + count
            if total == comments_got or not token:
                break
        return usernames_list
    except Exception as e:
        print(f"Error while getting comments: {e}")
        raise

def process_input_dataframe(df_source: pd.DataFrame, total_results: int):
    already_got = 0
    file_name = f"{str(int(datetime.now().timestamp()))}.csv"
    if df_source.empty:
        return None
    with ThreadPoolExecutor(max_workers=10) as executor:
        for index, row in df_source.iterrows():
            if already_got >= total_results:
                break
            username = row["username_or_url"]
            print(f"*** Processing Username n* {index} : {username} | total_results_to_get: {total_results} | already_got: {already_got}")
            try:
                posts_list = get_posts(username)
                print(f"    - step 1-1   --> Total Posts: {len(posts_list) if posts_list else 0}")
                if not posts_list:
                    continue
                futures = []
                for post_id in posts_list:
                    if already_got >= total_results:
                        break
                    futures.append(executor.submit(get_com_usernames, post_id))
                for future in as_completed(futures):
                    if already_got >= total_results:
                        break
                    try:
                        com_usernames = future.result()
                        print(f"        - step 1-2   --> Got {len(com_usernames) if com_usernames else 0} usernames")
                        if com_usernames:
                            for sub_i, sub_username in enumerate(com_usernames):
                                sub_user_data = get_user_data(sub_username)
                                print(f"            - step 2   --> Got UserData n* {sub_i} ? {'Yes' if sub_user_data else 'No'}")
                                if not sub_user_data:
                                    continue
                                verified = special_function(sub_user_data)
                                print(f"                - step 3   --> Verified UserData n* {sub_i} ? {'Yes' if verified else 'No'}")
                                if verified:
                                    df = pd.DataFrame(sub_user_data, index=[0])
                                    ecrire_ligne_resultat(file_name, df)
                                    already_got += 1
                                    print(f"** Ok - Username added | Total: {already_got}/{total_results}")
                           
                    except Exception as e:
                        print(f"Error processing post: {e}")
            except Exception as e:
                print(f"Error processing username {username}: {e}")
    
    print("DONE!")
    return file_name