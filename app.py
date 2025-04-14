import os
from io import BytesIO

import pandas as pd
from nicegui import events, ui, run

from insta_scrap.script import process_input_dataframe

class InstaApp:
    def __init__(self):
        self.input_df = None

    async def start_bot(self):
        ui.notify("Starting the bot")
        with ui.element('div').classes('w-full'):
            spinner = ui.spinner(size="lg").classes('w-full')
        file_name = await run.cpu_bound(process_input_dataframe, self.input_df)
        spinner.visible = False

        output_df = pd.read_csv(file_name)
        buffer = BytesIO()
        output_df.to_csv(buffer, index=False)
        os.remove(file_name)
        ui.button(
            "Download output",
            on_click=lambda: ui.download.content(buffer.getvalue(), filename="output.csv"),
        ).classes("full-width m-5")

    def handle_upload(self, e: events.UploadEventArguments):
        byte_content = e.content.read()
        self.input_df = pd.read_csv(BytesIO(byte_content))
        ui.notify(f"We have {len(self.input_df)} Instagram profiles in the csv file")

    def main(self):
        with ui.header().classes("flex justify-center"):
            ui.label("Instagram Follower scraper").classes("md:text-h4 text-h6")

        with ui.element("div").classes("w-full"):
            ui.upload(on_upload=self.handle_upload, auto_upload=True).props(
                "accept=.csv flat"
            ).classes("w-full")
            ui.button("Start Extracting").classes("full-width m-5").on_click(self.start_bot)


@ui.page("/")
def start_app():
    ui.colors(primary="black")
    insta_app = InstaApp()
    insta_app.main()


ui.run(host="0.0.0.0")