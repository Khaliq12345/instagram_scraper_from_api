import config
from google.genai import types
from google import genai
from pydantic import BaseModel
from config.config import GEMINI_API_KEY, RAPID_API_KEY, RAPID_API_HOST
import requests
from dateparser import parse
import pandas as pd
import os
from the_retry import retry
from insta_scrap.exceptions_client import exceptions
from insta_scrap.log_client import logger
from supabase import create_client

client = genai.Client(api_key=GEMINI_API_KEY)


# model
class IsMale(BaseModel):
    is_male: bool


# Define system prompt
system_prompt = """
You are an analytical assistant tasked with determining if an image depicts a male person based on visual cues and provided textual information (name, bio).
Use the bio to identify explicit gender indicators (e.g., pronouns like 'he/him', 'she/her', or direct statements like 'I am a man').
If the bio is ambiguous, make a best-effort judgment based on the image, but prioritize textual evidence.
If the bio contains 'promo,' 'crypto,' 'bot,' 'giveaway,' 'follow for,' or any spam account words, return False.
Exclude usernames with lots of numbers, spam phrases, or foreign text; return False if something like that shows up.
Return only 'True' if the person is male, or 'False' if not, with no additional text.
"""


def send_data_to_csv(file_name: str, df: pd.DataFrame, user_info: dict):
    if os.path.exists(file_name):
        df.to_csv(file_name, mode="a", header=False, index=False)
    else:
        df.to_csv(file_name, index=False)

    # Send to supabase
    # supabase = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
    # supabase.table("scraped_users").upsert(user_info).execute()


# Define user prompt
def user_prompt(full_name: str, bio: str, country: str):
    return f"""
        Analyze the provided image to determine if it depicts a male person. 
        Use the following name, and bio to inform your decision, prioritizing explicit gender indicators in the bio:
        Name: {full_name}
        Bio: {bio}
        Return 'True' if the person is male and country is valid, 'False' if not.
    """


@retry(attempts=2, backoff=5)
def generate_gender(img_bytes: bytes, full_name: str, bio: str, country: str):
    logger.info("Using LLM to generate gender")
    # Prepare content
    content = [
        types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/jpeg",
        ),
        user_prompt(full_name, bio, country),
    ]

    # generate the gender
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=content,
        config={
            "response_mime_type": "application/json",
            "response_schema": IsMale,
            "system_instruction": system_prompt,
        },
    )
    if response.parsed:
        return response.parsed.is_male


@retry(attempts=5, backoff=5, expected_exception=exceptions)
def get_username_last_post_date(username: str):
    logger.info("Getting the date of user last post date")
    # initialise the parameter and variables needed for the requests
    url = f"https://{RAPID_API_HOST}/v1/posts"

    querystring = {"username_or_id_or_url": username}

    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": f"{RAPID_API_HOST}",
    }

    # send the requests and parse the response
    response = requests.get(url, headers=headers, params=querystring)
    response.raise_for_status()
    json_data = response.json()
    post_data = json_data.get("data", {})
    if post_data:
        posts = post_data.get("items") if post_data else []
        if posts:
            try:
                last_post_date = (
                    posts[0]["caption"]["created_at_utc"] if posts else None
                )
            except Exception:
                last_post_date = None
            last_post_date = (
                parse(str(last_post_date)).isoformat()
                if last_post_date
                else None
            )
            return last_post_date


def start_gender_service(
    user_info: dict, img_bytes: bytes, file_name: str, token: str
) -> int:
    logger.info("Starting Gender service")
    # get the gender
    gender = generate_gender(
        img_bytes,
        user_info["full_name"],
        user_info["bio"],
        user_info["country"],
    )

    # validate gender and get last post date
    logger.info(f"Gender - {gender}")
    if gender:
        last_post_date = get_username_last_post_date(user_info["username"])

        logger.info(f"Last post date: {last_post_date}")

        # send data to file
        logger.info("Finally saving data")
        df = pd.DataFrame(user_info, index=[0])
        df["token"] = token
        send_data_to_csv(file_name, df, user_info)
        return 1
    return 0
