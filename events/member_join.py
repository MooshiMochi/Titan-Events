from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import MyClient

import discord
from discord.ext import commands


class JoinGuildCog(commands.Cog):
    def __init__(self, client):
        self.client: MyClient = client
        self.role: discord.Role = None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != self.client.db.settings["raffle_server"]:
            return

        if not self.client.db.settings["raffle_role"]:
            return

        if self.role is None:
            self.role = member.guild.get_role(self.client.db.settings["raffle_role"])
            if not self.role:
                return

        latest = {}

        for msg_id in self.client.db.raffles:
            if self.client.db.raffles[msg_id]["latest"]:
                latest = self.client.db.raffles[msg_id]
                break
        
        if member.id in latest["raffle_winners"]:
            await member.add_roles(self.role)
        

def setup(client):
    client.add_cog(JoinGuildCog(client))