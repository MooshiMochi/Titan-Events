from __future__ import annotations
from typing import TYPE_CHECKING, Literal
if TYPE_CHECKING:
    from main import MyClient

import discord
import asyncio
import re

from discord.ext import commands

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_actionrow, create_button, wait_for_component

from constants import const


class Settings(commands.Cog):
    def __init__(self, client):
        self.client: MyClient = client

    async def __view_settings(self):
        link = self.client.db.settings["invite_link"]
        role = self.client.db.settings["raffle_role"]
        server = self.client.db.settings["raffle_server"]
        guild_obj = self.client.get_guild(int(server)) if server else None
        
        if not link:
            link = "Not Set"

        if not server:
            server = "Not Set"
        else:
            server = guild_obj.name if guild_obj else "Not Found: {}".format(server)

        if not role:
            role = "Not Set"
        else:
            role = "@" + str(guild_obj.get_role(int(role))) if guild_obj is not None else "Not Found: {}".format(role)

        em = discord.Embed(title="Bot Settings", color=self.client.failure, description="")
        em.set_author(name=self.client.user.name, icon_url=self.client.png)
        em.set_thumbnail(url=self.client.png)
        em.add_field(name="Invite Link", value=f"**`{link}`**" if link else "Not Set", inline=False)
        em.add_field(name="Raffle Winner Role", value=f"**`{role}`**" if role else "Not Set", inline=False)
        em.add_field(name="Raffle winner Server", value=f"**`{server}`**" if server else "Not Set", inline=False)
        return em

    @cog_slash(name="settings", description="Settings for the raffle bot.", guild_ids=const.slash_guild_ids, options=[
        create_option(name="action", description="View the settings for the raffle bot.", option_type=3, required=True, choices=[
            create_choice(value="view", name="View the settings for the raffle bot."),
            create_choice(value="edit", name="Edit the settings for the raffle bot.")
        ])
    ])
    @commands.guild_only()
    async def settings(self, ctx: SlashContext, action: str):
        """
        Show the current settings for the bot.
        """
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send(f"{ctx.author.mention}, you do not have permission to use this command.", hidden=True)
        
        # if the action is edit:
        edit_buttons = [
            create_button(
                label="Invite Link",
                style=ButtonStyle.green,
                custom_id="invite_link"
            ),
            create_button(
                label="Winner Role",
                style=ButtonStyle.green,
                custom_id="raffle_role"
            ),
            create_button(
                label="Winner Server",
                style=ButtonStyle.green,
                custom_id="raffle_server"
            ),
            create_button(
                label="Update",
                style=ButtonStyle.blue,
                custom_id="update"
            ),
            create_button(
                label="Save",
                style=ButtonStyle.blue,
                custom_id="save"
            )
        ]
        edit_actionrow = create_actionrow(*edit_buttons)

        if action == "view":
            return await ctx.send(embed=await self.__view_settings(), hidden=True)

        await ctx.send(embed=await self.__view_settings(), components=[edit_actionrow], hidden=True)

        start_questions = {
            "invite_link": "Please enter the new invite link for the server.", 
            "raffle_role": "Please enter the ID of the role the winners will receive in the winners' server.", 
            "raffle_server": "Please enter the ID of the server where the winners will be invited to."}

        while True:
            try:
                button_ctx: ComponentContext = await wait_for_component(self.client, components=edit_actionrow)
                if button_ctx.author_id != ctx.author_id:
                    await ctx.send("You are not the author of this command.", hidden=True)
                    continue
                
                if button_ctx.custom_id == "update":
                    await button_ctx.edit_origin(embed=await self.__view_settings())
                    continue
                elif button_ctx.custom_id == "save":
                    await button_ctx.edit_origin(embed=await self.__view_settings(), components=[], hidden=True)
                    break
                elif button_ctx.custom_id == "raffle_role":
                    if not self.client.db.settings["raffle_server"]:
                        await button_ctx.send("Please configure a server first.", hidden=True)
                        continue
                    elif not self.client.get_guild(self.client.db.settings["raffle_server"]):
                        await button_ctx.send("I could not find the server you configured.\nMake sure I am in that server.", hidden=True)
                        continue

                await button_ctx.send(f"{start_questions[button_ctx.custom_id]}\nType 'cancel' to stop.", hidden=True)
                response = await self.get_text_response(ctx, button_ctx.custom_id)
                if response is None:
                    continue
                elif response == "timeout":
                    raise asyncio.TimeoutError
                    
                self.client.db.settings[button_ctx.custom_id] = response

            except asyncio.TimeoutError:
                return await ctx.send(f"{ctx.author.mention}, you took too long to respond.", hidden=True)

    async def get_text_response(self, 
        ctx: ComponentContext, 
        response_type: Literal["invite_link", "raffle_role", "raffle_server"]
        ):

        error_questions = {
            "invite_link": {
                "invalid_input": "Please enter a valid invite link.",
                "not_found": "Please enter a valid invite link."}, 
            "raffle_role": {
                "invalid_input": "Please enter a valid role ID.", 
                "not_found": "The role you entered could not be found."}, 
            "raffle_server": {
                "not_found": "I could not find a server with that ID.",
                "invalid_input": "Please enter a valid server ID."}}

        regex_patterns = {
            "invite_link": r"^((:?https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]{0,})$",
            "raffle_role": r"^((<@&)?[0-9]{18,}>?)$",
            "raffle_server": r"^([0-9]{18,})$"
        }

        messages_to_delete = []
        while True:
            try:
                msg = await self.client.wait_for('message', check=lambda m: m.author.id == ctx.author_id, timeout=30)
                messages_to_delete.append(msg)

                if msg.content.lower() == "cancel":
                    await ctx.send("Cancelled.", hidden=True)
                    await ctx.channel.delete_messages(messages_to_delete) if messages_to_delete else None
                    return None
                pattern = re.search(regex_patterns[response_type], msg.content)
                if pattern is None:
                    await ctx.send(f"{error_questions[response_type]}", hidden=True)
                    continue
                
                if response_type == "raffle_server":
                    if not self.client.get_guild(int(pattern.group(0))):
                        await ctx.send(f"{error_questions[response_type]['not_found']}", hidden=True)
                        continue

                await ctx.channel.delete_messages(messages_to_delete) if messages_to_delete else None
                return msg.content if response_type == "invite_link" else int(msg.content)

            except asyncio.TimeoutError:
                await ctx.channel.delete_messages(messages_to_delete) if messages_to_delete else None
                return "timeout"

def setup(client):
    client.add_cog(Settings(client))
