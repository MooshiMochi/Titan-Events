from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MyClient

import json
import asyncio
import aiofiles

class DB:
    def __init__(self, client: MyClient):
        self.client: MyClient = client
        self.settings = {}
        self.raffles = {}

    async def __autosave_task(self):
        try:
            while True:
                try:
                    async with aiofiles.open("data/raffles/settings.json", mode="w") as f:
                        await f.write(json.dumps(self.settings, indent=2))
                    async with aiofiles.open("data/raffles/active.json", mode="w") as f:
                        await f.write(json.dumps(self.raffles, indent=2))
                    print("[Database]> Saved all data to database.")
                except FileNotFoundError:
                    print("[Database]> File not found. Skipping.")

                await asyncio.sleep(60)
        except asyncio.CancelledError:
            print("[Database]> Autosave task cancelled.")
            raise
        
        except Exception as exc:
            print(f"[Database]> Autosave task failed.")
            raise exc

    def __load_data(self):
        try:
            with open("data/raffles/settings.json", mode="r") as f:
                self.settings = json.loads(f.read())
            with open("data/raffles/active.json", mode="r") as f:
                self.raffles = json.loads(f.read())

            print(f"[Database]> Loaded data from files into database.")
        except FileNotFoundError:
            print(f"[Database]> File not found. Skipping.")
        
        self.__prepare_settings()

    def __prepare_settings(self):
        if "invite_link" not in self.settings:
            self.settings["invite_link"] = ""
        if "raffle_role" not in self.settings:
            self.settings["raffle_role"] = 0
        if "raffle_server" not in self.settings:
            self.settings["raffle_server"] = ""

    async def save(self):
        try:            
            async with aiofiles.open("data/raffles/settings.json", mode="w") as f:
                await f.write(json.dumps(self.settings, indent=2))
            async with aiofiles.open("data/raffles/active.json", mode="w") as f:
                await f.write(json.dumps(self.raffles, indent=2))
            print("[Database]> Saved all data to database.")
        except FileNotFoundError:
            print("[Database]> File not found. Skipping.")

    def __autosave(self):
        self.client.loop.create_task(self.__autosave_task())
        print("[Database]> Autosave task created.")

    def initialise(self):
        task = self.client.loop.run_in_executor(None, self.__load_data)
        print("[Database]> Loading data from database.")
        task.add_done_callback(lambda _: self.__autosave())