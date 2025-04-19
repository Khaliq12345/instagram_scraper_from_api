import sys

sys.path.append(".")

import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from insta_scrap.get_gender import start_gender_service
from config import config
import requests
from insta_scrap.user_info import get_user_infos
from the_retry import retry
from insta_scrap.exceptions_client import exceptions


@retry(attempts=5, expected_exception=exceptions)
def get_com_usernames(post_id, token):
    # Get the usernames of the comments, use token in available
    try:
        usernames_list = []
        url = "https://instagram-social-api.p.rapidapi.com/v1/comments"
        querystring = {"code_or_id_or_url": post_id}
        if token:
            querystring["pagination_token"] = token
        headers = {
            "x-rapidapi-key": config.RAPID_API_KEY,
            "x-rapidapi-host": "instagram-social-api.p.rapidapi.com",
        }

        # Analyse and parse the comments to get the usernames
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


@retry(attempts=5, expected_exception=exceptions)
def get_posts(username, token, min_comments=10):
    # get the post ids and use token in available
    try:
        # Initialise the parameters needed to send the requests
        id_list = []
        url = "https://instagram-social-api.p.rapidapi.com/v1/posts"
        querystring = {"username_or_id_or_url": username}
        if token:
            querystring["pagination_token"] = token
        headers = {
            "x-rapidapi-key": config.RAPID_API_KEY,
            "x-rapidapi-host": "instagram-social-api.p.rapidapi.com",
        }

        # Analyse and parse the response
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


def analyse_username(username: str, file_name: str) -> int:
    # start the user analysis (step 2)
    print("Starting ------------------------------------ Analysis")
    user_info = get_user_infos(username)
    gender_output = 0
    if user_info:
        gender_output = start_gender_service(
            user_info["user_infos"], user_info["image_bytes"], file_name=file_name
        )
    print(f"Gender - {gender_output}")
    print("Ending ------------------------------------ Analysis")
    return gender_output


def anaylse_usernames(usernames: list[str], file_name: str):
    results = []
    with ThreadPoolExecutor(max_workers=1) as worker:
        futures = [
            worker.submit(analyse_username, username, file_name)
            for username in usernames
        ]

        # Collect results from each Future
        for future in futures:
            print(future.result())
            results.append(future.result() if future.result() else 0)

    return sum(results)


def process_input_dataframe(
    df_source: pd.DataFrame, file_name: str, total_results: int
):
    # Initialise the variable to use
    already_got = 0
    # file_name = f"{str(int(datetime.now().timestamp()))}.csv"
    if df_source.empty:
        return None

    # starting the iteration of the input usernames
    for index, row in df_source.iterrows():
        if already_got >= total_results:
            break
        username = row["username_or_url"]
        print(
            f"*** Processing Username n* {index} : {username} | total_results_to_get: {total_results} | already_got: {already_got}"
        )
        try:
            # going through all the posts to extract the ids
            next_for_post = True
            token_next_for_post = None
            while next_for_post:
                posts_list, token_next_for_post = get_posts(
                    username, token_next_for_post
                )
                print(
                    f"    - step 1-1   --> Total Posts: {len(posts_list) if posts_list else 0}"
                )
                for post_id in posts_list:
                    if already_got >= total_results:
                        next_for_post = False
                        break

                    #  going through all the comments to extract the username of the commentor
                    next_for_com = True
                    token_next_for_com = None
                    while next_for_com:
                        com_usernames, token_next_for_com = get_com_usernames(
                            post_id, token_next_for_com
                        )
                        print(
                            f"- step 1-2   --> Got {len(com_usernames) if com_usernames else 0} usernames"
                        )

                        # analyse and filter the username to get the gender, metric, e.t.c And save it if valid
                        added = anaylse_usernames(com_usernames, file_name)
                        already_got += added
                        print(
                            f"** Ok - Username added | Total: {already_got}/{total_results}"
                        )
                        if already_got >= total_results:
                            next_for_com = False
                            next_for_post = False
                            break
        except Exception as e:
            print(f"Error processing username {username}: {e}")

    print("DONE!")
    return file_name


if __name__ == "__main__":
    # analyse_username("weetravelmonkeys", "weetravelmonkeys.csv")
    df = pd.read_csv("./insta_scrap/output.csv")
    process_input_dataframe(df_source=df, total_results=10)
