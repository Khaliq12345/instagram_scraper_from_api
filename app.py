import os
from io import BytesIO

import pandas as pd
from nicegui import events, ui, run, app

from insta_scrap.app import process_input_dataframe
from dotenv import load_dotenv
from dateparser import parse
from config import config
from datetime import datetime

load_dotenv()


class InstaApp:
    def __init__(self):
        self.input_df = None
        self.password = None
        self.total_results = 10
        self.file_name = f"{str(int(datetime.now().timestamp()))}.csv"

    async def start_bot(self):
        self.spinner.visible = True
        file_name = await run.cpu_bound(
            process_input_dataframe, self.input_df, self.file_name, self.total_results
        )
        self.spinner.visible = False

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
        if self.password == config.APP_KEY:
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

    @ui.refreshable
    def reload_output(self):
        total_users = 0
        try:
            users_df = pd.read_csv(self.file_name)
            total_users = len(users_df)
        except Exception:
            total_users = 0
        ui.label(f"Total users extracted - {total_users}").classes(
            "text-h5 text-blue text-center"
        )

    def main(self):
        with ui.header().classes("flex justify-center"):
            ui.label("Instagram Follower scraper").classes("md:text-h4 text-h6")

        with ui.element("div").classes("w-full"):
            ui.upload(on_upload=self.handle_upload, auto_upload=True).props(
                "accept=.csv flat"
            ).classes("w-full")
            ui.number(label="Total to scrape").bind_value(self, "total_results")
            ui.button("Start Extracting").classes("full-width m-5").on_click(
                self.start_bot
            )
            self.spinner = ui.spinner(size="lg", type="box").classes("w-full")
            self.spinner.visible = False
            self.reload_output()
            ui.timer(2, callback=lambda: self.reload_output.refresh())


@ui.page("/")
def start_app():
    ui.colors(primary="black")
    insta_app = InstaApp()
    api_key = app.storage.user.get("api_key")
    if api_key:
        diff = abs(parse(api_key["exp"]) - parse("now"))
        if (api_key["value"] != config.APP_KEY) or (diff.days > 0):
            insta_app.login()
        else:
            insta_app.main()
    else:
        insta_app.login()


ui.run(host="0.0.0.0", storage_secret=config.SECRET_KEY)
