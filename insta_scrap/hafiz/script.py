import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd
import requests
from dotenv import load_dotenv
load_dotenv()

def analyse_usernames(usernames: list, filename):
    # Step 2 and 3 -- filter and write in file
    print(f"            - step 2 and step 3   --> Got usernames list and analysed to paste in file")
    return len(usernames)

def get_posts(username, token, min_comments=10):
    # Step 1-1
    rapidapi_key = os.getenv("rapidapi_key")
    try:
        id_list = []
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
        new_token = json_data.get("pagination_token", None)
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
    
        return id_list, new_token
    except Exception as e:
        print(f"Error while getting posts: {e}")
        return None, None

def get_com_usernames(post_id, token):
    # Step 1-2
    rapidapi_key = os.getenv("rapidapi_key")
    try:
        usernames_list = []
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
        new_token = json_data.get("pagination_token", None)
        # count = data.get("count", 0) if data else 0
        # total = data.get("total", 0) if data else 0
        comments = data.get("items", []) if data else []
        for c in comments:
            user = c.get("user", {}) if c else {}
            username = user.get("username", None) if user else None
            if username:
                usernames_list.append(username)
        return usernames_list, new_token
    except Exception as e:
        print(f"Error while getting comments: {e}")
        return None, None

def process_input_dataframe(df_source: pd.DataFrame, total_results: int):
    already_got = 0
    file_name = f"{str(int(datetime.now().timestamp()))}.csv"
    if df_source.empty:
        return None
    for index, row in df_source.iterrows():
        if already_got >= total_results:
            break
        username = row["username_or_url"]
        print(f"*** Processing Username n* {index} : {username} | total_results_to_get: {total_results} | already_got: {already_got}")
        try:
            next_for_post = True
            token_next_for_post = None
            while next_for_post:
                posts_list, token_next_for_post = get_posts(username, token_next_for_post)
                print(f"    - step 1-1   --> Total Posts: {len(posts_list) if posts_list else 0}")
                for post_id in posts_list:
                    if already_got >= total_results:
                        next_for_post = False
                        break
                    next_for_com = True
                    token_next_for_com = None
                    while next_for_com:
                        com_usernames, token_next_for_com = get_com_usernames(post_id, token_next_for_com)
                        print(f"        - step 1-2   --> Got {len(com_usernames) if com_usernames else 0} usernames")
                        added = analyse_usernames(com_usernames, file_name)
                        already_got += added
                        print(f"** Ok - Username added | Total: {already_got}/{total_results}")
                        if already_got >= total_results:
                            next_for_com = False
                            next_for_post = False
                            break
        except Exception as e:
            print(f"Error processing username {username}: {e}")

    print("DONE!")
    return file_name