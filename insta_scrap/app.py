import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from get_gender import start_gender_service


def analyse_username(username: str, file_name: str):
    # start the user analysis (step 2)
    # user_info = from_step_two()
    # start_gender_service(
    #     user_info["user_info"], user_info["img_bytes"], file_name=file_name
    # )
    pass


def anaylse_usernames(usernames: list[str], file_name: str):
    with ThreadPoolExecutor(max_workers=5) as worker:
        for username in usernames:
            worker.submit(analyse_username, username, file_name)


def process_input_dataframe(df_source: pd.DataFrame, total_results: int = 10):
    # initialise the variable needed for the workflow
    already_got = 0
    file_name = f"{str(int(datetime.now().timestamp()))}.csv"
    if df_source.empty:
        return None

    # loop through the provided usernames
    for index, row in df_source.iterrows():
        username = row["username_or_url"]

        is_next_for_post = True
        while is_next_for_post:
            valid_posts = []
            for valid_post in valid_posts:
                is_next_comments = True
                while is_next_comments:
                    comment_usernames = []
                    if already_got == total_results:
                        is_next_for_post = False
                        is_next_comments = False
                    else:
                        anaylse_usernames(comment_usernames, file_name)

        # todo: loop through the posts, get the comment usernames and keep paginating, but for each batch of the comment pagination we send the username to the analyser and verify the we have the total number needed. If not we continue paginating or go to the next post or paginate if we still have more or go to the next username given
