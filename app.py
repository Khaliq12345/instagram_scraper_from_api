import os
from io import BytesIO

import pandas as pd
from nicegui import events, ui, run, app

from insta_scrap.script import process_input_dataframe
from dotenv import load_dotenv
from dateparser import parse

load_dotenv()


class InstaApp:
    def __init__(self):
        self.input_df = None
        self.password = None

    async def start_bot(self):
        with ui.element("div").classes("w-full"):
            spinner = ui.spinner(size="lg").classes("w-full")
        file_name = await run.cpu_bound(process_input_dataframe, self.input_df)
        spinner.visible = False

        output_df = pd.read_csv(file_name)
        buffer = BytesIO()
        output_df.to_csv(buffer, index=False)
        os.remove(file_name)
        ui.button(
            "Download output",
            on_click=lambda: ui.download.content(
                buffer.getvalue(), filename="output.csv"
            ),
        ).classes("full-width m-5")

    def handle_upload(self, e: events.UploadEventArguments):
        byte_content = e.content.read()
        self.input_df = pd.read_csv(BytesIO(byte_content))

    def handle_login(self):
        if self.password == os.getenv("api_key"):
            ui.notify("Logged IN", position="top", type="positive")
            app.storage.user["api_key"] = {
                "value": self.password,
                "exp": parse("now").isoformat(),
            }
            ui.navigate.reload()
        else:
            ui.notify("Wrong Credentials", position="top", type="negative")

    def login(self):
        with ui.element("div").classes("w-full justify-items-center flex-col"):
            ui.input(
                label="API KEY", password=True, password_toggle_button=True
            ).classes("w-1/2 text-center m-5 flat").bind_value(self, "password")
            ui.button("Login").classes("flat").on_click(lambda: self.handle_login())

    def main(self):
        with ui.header().classes("flex justify-center"):
            ui.label("Instagram Follower scraper").classes("md:text-h4 text-h6")

        with ui.element("div").classes("w-full"):
            ui.upload(on_upload=self.handle_upload, auto_upload=True).props(
                "accept=.csv flat"
            ).classes("w-full")
            ui.button("Start Extracting").classes("full-width m-5").on_click(
                self.start_bot
            )


@ui.page("/")
def start_app():
    ui.colors(primary="black")
    insta_app = InstaApp()
    api_key = app.storage.user.get("api_key")
    if api_key:
        diff = abs(parse(api_key["exp"]) - parse("now"))
        if (api_key["value"] != os.getenv("api_key")) or (diff.days > 0):
            insta_app.login()
        else:
            insta_app.main()
    else:
        insta_app.login()


ui.run(host="0.0.0.0", storage_secret=os.getenv("secret_key"))
