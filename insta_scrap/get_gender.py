import sys

sys.path.append(".")

from google.genai import types
from google import genai
from pydantic import BaseModel
from config.config import GEMINI_API_KEY, RAPID_API_KEY
import requests
from dateparser import parse
import pandas as pd
import os

client = genai.Client(api_key=GEMINI_API_KEY)


# model
class IsMale(BaseModel):
    is_male: bool


# Define system prompt
system_prompt = """
You are an analytical assistant tasked with determining, 
if an image depicts a male person based on visual cues and provided textual information (name and bio). 
Use the bio to identify explicit gender indicators (e.g., pronouns like 'he/him', 'she/her', or direct statements like 'I am a man'). 
If the bio is ambiguous, make a best-effort judgment based on the image, but prioritize textual evidence. 
Return only 'True' if the person is male, or 'False' if not, with no additional text.
"""


def send_data_to_csv(file_name: str, df: pd.DataFrame):
    if os.path.exists(file_name):
        df.to_csv(file_name, mode="a", header=False, index=False)
    else:
        df.to_csv(file_name, index=False)


# Define user prompt
def user_prompt(full_name: str, bio: str):
    f"""
    Analyze the provided image to determine if it depicts a male person. Use the following name and bio to inform your decision, 
    prioritizing explicit gender indicators in the bio:

    Name: {full_name}
    Bio: {bio}

    Return 'True' if the person is male, 'False' if not.
    """


def generate_gender(img_bytes: bytes, full_name: str, bio: str):
    # Prepare content
    content = [
        types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/jpeg",
        ),
        user_prompt(full_name, bio),
    ]

    # generate the gender
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents=content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_schema=IsMale,
            response_mime_type="application/json",
        ),
    )
    if response.parsed:
        return response.parsed.is_male


def get_username_last_post_date(username: str):
    # initialise the parameter and variables needed for the requests
    url = "https://instagram-social-api.p.rapidapi.com/v1/posts"

    querystring = {"username_or_id_or_url": username}

    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "instagram-social-api.p.rapidapi.com",
    }

    # send the requests and parse the response
    response = requests.get(url, headers=headers, params=querystring)
    response.raise_for_status()
    json_data = response.json()
    post_data = json_data.get("data", {})
    posts = post_data.get("items") if post_data else []
    last_post_date = posts[0]["caption"]["created_at_utc"] if posts else None
    last_post_date = parse(str(last_post_date)).isoformat() if last_post_date else None
    return last_post_date


def start_gender_service(user_info: dict, img_bytes: bytes, file_name: str):
    # get the gender
    gender = generate_gender(img_bytes, user_info["full_name"], user_info["bio"])

    # validate gender and get last post date
    if gender:
        last_post_date = get_username_last_post_date(user_info["username"])
        user_info["last_post_date"] = last_post_date

        # send data to file
        df = pd.DataFrame(user_info, index=[0])
        send_data_to_csv(file_name, df)
