from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import MyClient

import discord
import asyncio
import random

from discord import AllowedMentions
from discord.ext import commands, tasks

from discord_slash import SlashContext, ComponentContext
from discord_slash.cog_ext import cog_slash
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_actionrow, create_button

import datetime as dt
from datetime import datetime

from constants import const


class EventRaffle(commands.Cog):


    def __init__(self, client):
        self.client: MyClient = client
        
        self.party = "🎁"
        self.last_claim = 0
        self.claim_queue = []

        self.raffles = self.client.db.raffles
        # with open("data/raffles/active.json", "r") as f:
        #     self.raffles = json.load(f)

        self.timeout_button = [create_button(
        style=ButtonStyle.red,
        label="Raffle Ended!",
        emoji="🎉", 
        disabled=True)]

        self.enter_buttons = [
            create_button(
                label="Enter", 
                emoji="🎉", 
                style=ButtonStyle.green,
                custom_id="raffle_enter")
        ]

        self.claim_buttom = [
            create_button(
                label="Claim",
                emoji="🎉",
                style=ButtonStyle.green,
                custom_id="raffle_claim")
        ]

        self.claim_component = [create_actionrow(*self.claim_buttom)]
        self.timeout_components = [create_actionrow(*self.timeout_button)]

        self.resume_raffles.start()

    @cog_slash(
        name="raffle", 
        description="Create a raffle", guild_ids=const.slash_guild_ids, 
        options=[
            create_option(name="channel", description="Please mention the name of the channel in which the raffle should be hosted.", option_type=7, required=True),
            create_option(name="time", description="Please specify the duration of this raffle. Eg: 1h, 1d, 12h, 1mo.", option_type=3, required=True),
            create_option(name="title", description="What should be the title of this raffle?", option_type=3, required=True),
            create_option(name="winners", description="How many winners will this raffle have?", option_type=4, required=False),
            create_option(name="required_role", description="What will be the role required to enter this raffle?", option_type=8, required=False),
            create_option(name="ping_role_1", description="What role should I ping?", option_type=8, required=False),
            create_option(name="ping_role_2", description="What other role should I ping?", option_type=8, required=False),
            create_option(name="ping_role_3", description="What other role should I ping?", option_type=8, required=False)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def raffle(self, ctx:SlashContext, channel:discord.TextChannel=None, title:str=None, time:str=None, winners:int=1, required_role:discord.Role=None, ping_role_1:discord.Role=None, ping_role_2:discord.Role=None, ping_role_3:discord.Role=None):
        
        await ctx.defer(hidden=True)

        guild = self.client.get_guild(self.client.db.settings["raffle_server"])
        if guild:
            role = guild.get_role(self.client.db.settings["raffle_role"])
            if role:
                if len(role.members) > 0:
                    await ctx.send("An event is already ongoing. Please use `/end_event` to end the event.", hidden=True)
                    return

        pings = "|| "
        pings += ping_role_1.mention if ping_role_1 else ""
        pings += ping_role_2.mention if ping_role_2 else ""
        pings += ping_role_3.mention if ping_role_3 else ""
        if pings != "|| ":
            pings += " ||"
        else:
            pings = ""

        if not isinstance(channel, discord.TextChannel):
            return await ctx.send("I can only host raffles in text channels.", hidden=True)

        int_duration = await self.client.format_duration(time)
        if int_duration < 300:
            return await ctx.send("Raffle duration cannot be shorter than 5 minutes.", hidden=True)
        elif int_duration > 2419200:
            return await ctx.send("Raffle duration cannot be greater than 1 month.", hidden=True)

        if winners > 100:
            return await ctx.send("There can only be a maximum of 100 winners.", hidden=True)

        if winners < 1:
            return await ctx.send("There can only be a minimum of 1 winner.", hidden=True)

        em = discord.Embed(color=self.client.success, description="")
        em.set_author(name=title, icon_url="https://media.discordapp.net/attachments/884145972995825724/935929000449167460/MainGift.png")
        em.description += f"\n\n<:lunar_dot:943374901748846602> {winners} winner(s)"
        em.description += f"\n<:lunar_dot:943374901748846602> Hosted by: {ctx.author.mention}"
        em.description += f"\n<:lunar_dot:943374901748846602> Ends: <t:{int(datetime.now().timestamp() + int_duration)}:R>"
        em.description += f"\n\n**Prize**: __Event Server Invite__"
        em.description += f"\n\nClick the button below to enter the raffle!"
        em.description += f"\n\nIf you're in the TitanMC server, you get 2x entries!\nhttps://discord.gg/titanmc"
        
        action_row = create_actionrow(*self.enter_buttons)

        try:
            msg = await channel.send(content=f"{self.party} **RAFFLE** {self.party} {pings}", embed=em, components=[action_row], allowed_mentions=AllowedMentions(roles=True))
        except discord.HTTPException:
            return await ctx.send("I do not have enough permissions to create a raffle in that channel.", hidden=True)
        
        for msg_id in self.raffles:
            self.raffles[msg_id]["latest"] = False

        self.raffles[str(msg.id)] = {
            "message_id": msg.id,
            "required_role": {
                'id': required_role.id if required_role else None,
                'name': required_role.name if required_role else None},
            "time": int(datetime.now().timestamp()) + int_duration,
            "winners": winners,
            "host": ctx.author_id,
            "members": [],
            "guild_id": msg.guild.id,
            "channel_id": msg.channel.id,
            "jump_url": msg.jump_url,
            "finished": False,
            "claimed": [],
            "raffle_winners": [],
            "latest": True,
        }

        await ctx.send(f"Success!", hidden=True)

        self.client.loop.create_task(self.wait_for_raffle(str(msg.id)))

    @cog_slash(name="end_event", description="End the event and remove server access from regular members.", guild_ids=const.slash_guild_ids)
    async def end_event(self, ctx: SlashContext):
        if not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions("administrator")

        await ctx.defer(hidden=True)
        
        guild = self.client.db.settings["raffle_server"]
        guild: discord.Guild = self.client.get_guild(guild)
        if not guild:
            return await ctx.send("I can't find the raffle server.", hidden=True)
        role: discord.Role = guild.get_role(self.client.db.settings["raffle_role"])
        if not role:
            return await ctx.send("I can't find the raffle role.", hidden=True)
        
        if len(role.members) == 0:
            return await ctx.send("No regular members have access to the server channels.", hidden=True)

        em = discord.Embed(color=self.client.failure, description="Started remove server access from regular members.", title="🎉 Event Ended 🎉")
        await ctx.send(embed=em, hidden=True)

        for member in role.members:
            await member.remove_roles(role)


    async def gradual_invites(self, member: discord.Member, jump_url: str, delay: int = 0, ts: int = None):
        await asyncio.sleep(delay)
        try:
            em = discord.Embed(color=self.client.success, description=f"Here is your reward for the [raffle]({jump_url}).\n\n{self.client.db.settings['invite_link']}")
            em.set_author(icon_url="https://images-ext-1.discordapp.net/external/ob9eIZj1RkBiQjNG-BaFVKYH4VMD0Pz0LNmUwhmeIko/%3Fsize%3D56%26quality%3Dlossless/https/cdn.discordapp.com/emojis/933776807256289380.webp", name="Claimed")
            em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
            em.timestamp = datetime.now()
            await member.send(embed=em, delete_after=6*60*60)
            return
        except Exception:
            pass

        try:
            self.claim_queue.remove((member.id, ts))
        except ValueError:
            return

    @tasks.loop(count=1)
    async def resume_raffles(self):        
        ts = datetime.now().timestamp()

        tasks = []
        for key in self.raffles.keys():
            if self.raffles[key]["time"] < ts:
                tasks.append(self.wait_for_raffle(key))
        if tasks:
            await asyncio.gather(*tasks)

    @tasks.loop(minutes=5)
    async def clear_raffle_cache(self):
        ts = datetime.now().timestamp()
        for key in self.raffles.copy().keys():
            if ts - self.raffles[key]["time"] >= 24*60*60:
                self.raffles.pop(key, None)

    @resume_raffles.before_loop
    @clear_raffle_cache.before_loop
    async def before_resuming_raffles(self):
        await self.client.wait_until_ready()


    @cog_slash(name="raffle_reroll", description="Re-roll a raffle", guild_ids=const.slash_guild_ids, options=[
        create_option(name="message_id", description="The ID of the raffle message", option_type=3, required=True)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def raffle_reroll(self, ctx:SlashContext, message_id:str=None):
        await ctx.defer(hidden=True)
    
        data = self.raffles.get(message_id, None)
        if not data:
            return await ctx.send("It looks like that raffle no longer exists. Sorry, but you cannot re-roll this raffle", hidden=True)
        
        if not data["finished"]:
            return await ctx.send("This raffle has not finished yet. You can only re-roll after a raffle has ended.", hidden=True)

        guild = self.client.get_guild(data['guild_id'])
        channel = guild.get_channel(data['channel_id'])

        try:
            msg = await channel.fetch_message(data['message_id'])
        except (discord.HTTPException, discord.NotFound, discord.Forbidden):
            await ctx.send(f"Could not fetch message {data['message_id']} in {channel.name}", hidden=True)
            return

        if not data["members"]:
            em = discord.Embed(color=self.client.warn, description=f"> Could not determine a new winner for this raffle as there are no valid entrants")
            em.set_author(name="Raffle Issue", icon_url="https://media.discordapp.net/attachments/884145972995825724/936019499742789672/MainGift.png")
            
            return await ctx.send(embed=em)

        allowed_winners = [m_id for m_id in data["members"] if m_id not in data["claimed"] and m_id != data["host"]]


        if (data["winners"] == data["claimed"]) or (not allowed_winners):
            em = discord.Embed(color=self.client.warn, description=f"> Could not determine a new winner for this raffle as all winners have already been claimed")
            em.set_author(name="Raffle Issue", icon_url="https://media.discordapp.net/attachments/884145972995825724/936019499742789672/MainGift.png")
            
            return await ctx.send(embed=em)
            
        try:
            winners = random.sample(allowed_winners, data['winners'])
        except ValueError:
            winners = data['members']

        data["raffle_winners"] = winners

        public_em = discord.Embed(color=self.client.warn, description=f"You have won a [raffle]({data['jump_url']}) for **1 Entry to Events Server**!")

        try:
            await msg.reply(content=f"""{self.party} • {', '.join([f"<@!{w_id}>" for w_id in winners])}""", embed=public_em, components=self.claim_component)
        except discord.HTTPException:
            pass
        
        em = discord.Embed(color=self.client.failure, description=f"> I have rerolled the [raffle]({data['jump_url']}).")
        em.set_author(name="Raffle Reroll", icon_url="https://media.discordapp.net/attachments/884145972995825724/933821589202559026/Revoked.png")
        em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
        em.add_field(name="Raffle", value=f"`Channel:` <#{data['channel_id']}>\n`ID:` {message_id}")
        return await ctx.send(embed=em, hidden=True)
    

    async def wait_for_raffle(self, key:str):
        await self.client.wait_until_ready()

        data = self.raffles[key]

        if self.raffles[key]['finished']:
            return

        if datetime.now().timestamp() < data["time"]:
            print(datetime.fromtimestamp(data['time']))
            await asyncio.sleep(data["time"] - datetime.now().timestamp())
            # await discord.utils.sleep_until(datetime.fromtimestamp(data["time"]))
        
        guild = self.client.get_guild(data['guild_id'])
        channel = guild.get_channel(data['channel_id'])
        host = guild.get_member(data['host'])
        
        try:
            msg = await channel.fetch_message(int(key))
        except (discord.HTTPException, discord.NotFound, discord.Forbidden):
            print(f"Could not fetch message {key} in {channel.name}".encode("utf-8"))
            return

        self.raffles[key]['finished'] = True
        #if not data["members"] or len(data["members"]) == 1 or len(data['members']) <= data["winners"]    
        if not data["members"]:
            em = discord.Embed(color=self.client.warn, description=f"[Your raffle]({data['jump_url']}) ended without any winners.")
            try:
                
                await host.send(embed=em)

                try:
                    msg = await channel.fetch_message(int(key))
                except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                    print(f"Could not fetch message {key} in {channel.name}".encode("utf-8"))
                    return

                if msg:
                    edit_em = discord.Embed(color=self.client.failure, description=f"😔 No winners")
                    edit_em.set_author(name="1 Event Server Invite", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
                    edit_em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
                    try:
                        await msg.edit(content=f"{self.party}**RAFFLE ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
                    except (discord.NotFound, AttributeError, TypeError):
                        pass

            except discord.HTTPException:
                pass
            # self.raffles.pop(key, None)
            return
        
        try:
            titan_mc_guild = self.client.get_guild(932413718397083678)
            if titan_mc_guild is not None:
                titan_mc_members = [m.id for m in titan_mc_guild.members]
                for m_id in data['members'].copy():
                    if m_id in titan_mc_members:
                        data['members'].append(m_id)

            winners = random.sample(data['members'], data['winners'])
        except ValueError:
            winners = data['members']
        
        data["raffle_winners"] = winners

        self.client.loop.create_task(self.add_participant_role_to_winners_if_in_server_already(winners))

        public_em = discord.Embed(color=self.client.warn, description=f"You have won a [raffle]({data['jump_url']}) for **1 Event Server Invite**!")

        try:
            await msg.reply(content=f"""{self.party} • {', '.join([f"<@!{w_id}>" for w_id in winners])}""", embed=public_em, components=self.claim_component)
        except discord.HTTPException:
            pass
        
        host_em = discord.Embed(color=self.client.success, description=f""">>> **Winner(s):** {', '.join([f"<@!{w_id}>" for w_id in winners])} `({', '.join([str(w_id) for w_id in winners])})`""")
        host_em.set_author(icon_url="https://media.discordapp.net/attachments/884145972995825724/933859630185082920/Stars.png", name="Raffle Ended", url=data['jump_url'])
        host_em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)

        host_em.description += f"\nPrize(s):" + "\n<:lunar_dot:943374901748846602> `1 Event Server Invite`"

        try:
            await host.send(embed=host_em)
        except discord.HTTPException:
            pass

        for winner_id in winners:
            em = discord.Embed(color=self.client.warn, description=f"""You have just won a [raffle]({data['jump_url']}) for `1 Event Server Invite` in **{guild.name}**.""")
            em.set_author(name="Raffle Winner", url=data['jump_url'], icon_url="https://images-ext-2.discordapp.net/external/ZusSn-X4k7HaGEyw0r5Vn1AsLHIMulaePr_mBZvzK0I/%3Fsize%3D128%26quality%3Dlossless/https/cdn.discordapp.com/emojis/894171015888920576.webp")
            em.add_field(name="Information", value=f"> Hosted by: {host.mention} `({data['host']})`")
            em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
            mem = guild.get_member(winner_id)
            try:
                await mem.send(embed=em)
            except discord.HTTPException:
                pass

        edit_em = discord.Embed(color=self.client.failure, description=f"""> **Winners:** {', '.join([f"<@!{w_id}>" for w_id in winners])}""")
        edit_em.set_author(name="1 Event Server Invite", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
        edit_em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
        
        try:
            msg = await channel.fetch_message(key)
        except discord.NotFound:
            return

        if msg:
            try:
                await msg.edit(content=f"{self.party}**RAFFLE ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
            except discord.HTTPException:
                pass
        # self.raffles.pop(key, None)
        return

    async def add_participant_role_to_winners_if_in_server_already(self, winners: list):
        guild = self.client.get_guild(self.client.db.settings["raffle_server"])
        if guild:
            role = guild.get_role(self.client.db.settings["raffle_role"])
            if role:
                for winner_id in winners:
                    mem = guild.get_member(winner_id)
                    if mem:
                        await mem.add_roles(role)

    @commands.Cog.listener()
    async def on_component(self, ctx:ComponentContext):
        await self.client.wait_until_ready()

        if ctx.custom_id == "raffle_enter":

            data = self.raffles.get(str(ctx.origin_message_id), None)
            if not data or datetime.now().timestamp() >= data['time']:
                
                edit_em = discord.Embed(color=self.client.warn, description=f"An error occured.\n\nThis raffle is cancelled.")
                edit_em.set_author(name="1 Event Server Invite" if data else "Unknown", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
                edit_em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)

                try:
                    await ctx.send(content=f"{self.party}**RAFFLE ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
                except:
                    pass
                return

            if data["required_role"]['id']:
                if data["required_role"]['id'] in (r.id for r in ctx.author.roles):
                    if ctx.author_id in data['members']:
                        return await ctx.send("You are already in this raffle.", hidden=True)
                    em = discord.Embed(color=self.client.success, description=f"Your entry into this [raffle]({ctx.origin_message.jump_url}) has been approved.")
                    em.set_author(icon_url="https://images-ext-1.discordapp.net/external/ob9eIZj1RkBiQjNG-BaFVKYH4VMD0Pz0LNmUwhmeIko/%3Fsize%3D56%26quality%3Dlossless/https/cdn.discordapp.com/emojis/933776807256289380.webp", name="Entry Approved")
                    em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
                    em.timestamp = datetime.now()
                    await ctx.author.send(embed=em)
                    self.raffles[str(ctx.origin_message_id)]['members'].append(ctx.author_id)
                    self.raffles[str(ctx.origin_message_id)]["members"] = list(set(data['members']))
                
                else:
                    em = discord.Embed(color=self.client.failure, description=f"To enter this [raffle]({ctx.origin_message.jump_url}) you need the following role:\n**{data['required_role']['name']}**")
                    em.set_author(icon_url="https://media.discordapp.net/attachments/884145972995825724/933799302491406377/Denied.png", name="Entry Denied")
                    em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
                    em.timestamp = datetime.now()
                    await ctx.author.send(embed=em)
                    return
            else:
                if ctx.author_id in data['members']:
                    return await ctx.send("You are already in this raffle.", hidden=True)
                em = discord.Embed(color=self.client.success, description=f"Your entry into this [raffle]({ctx.origin_message.jump_url}) has been approved.\n\n**Note:** If you are in the TitanMC server, you get 2x chance of winning.\nhttps://discord.gg/titanmc")
                em.set_author(icon_url="https://images-ext-1.discordapp.net/external/ob9eIZj1RkBiQjNG-BaFVKYH4VMD0Pz0LNmUwhmeIko/%3Fsize%3D56%26quality%3Dlossless/https/cdn.discordapp.com/emojis/933776807256289380.webp", name="Entry Approved")
                em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)
                em.timestamp = datetime.now()
                try:
                    await ctx.author.send(embed=em)
                except discord.Forbidden as e:
                    if const.DEBUG:
                        print(e)
                
                self.raffles[str(ctx.origin_message_id)]['members'].append(ctx.author_id)
                self.raffles[str(ctx.origin_message_id)]["members"] = list(set(data['members']))

            participants = [create_button(
                label=f"{len(data['members'])} Participant(s)",
                style=ButtonStyle.grey,
                disabled=True
            )]

            new_ar = [create_actionrow(*self.enter_buttons, *participants)]

            try:
                await ctx.edit_origin(content=ctx.origin_message.content, embed=ctx.origin_message.embeds[0], components=new_ar)
            except:
                pass
        
        elif ctx.custom_id == "raffle_claim":
            ## Create an invite link to the server and DM it to the user if they are a winner of the raffle and have not claimed already

            data = self.raffles.get(str(ctx.origin_message.reference.message_id), None)
            if not data or datetime.now().timestamp() >= data['time'] + dt.timedelta(weeks=1).total_seconds():
                edit_em = discord.Embed(color=self.client.warn, description=f"An error occured.\n\nThis raffle is cancelled.")
                edit_em.set_author(name="1 Event Server Invite" if data else "Unknown", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
                edit_em.set_footer(text="TitanMC | Raffles", icon_url=self.client.png)

                try:
                    await ctx.edit_origin(content=f"{self.party}**RAFFLE ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
                except Exception as e:
                    if const.DEBUG:
                        print("Failed to edit message\n", e)
                return

            if ctx.author_id in data['raffle_winners']:
                if ctx.author_id in data['claimed']:
                    return await ctx.send("You have already claimed this raffle.", hidden=True)
                else:
                    data['claimed'].append(ctx.author_id)
                    self.raffles[str(ctx.origin_message_id)] = data

                    curr_ts = datetime.now().timestamp()

                    if not self.claim_queue:
                        self.claim_queue.append((ctx.author_id, curr_ts))
                        self.client.loop.create_task(self.gradual_invites(ctx.author, ctx.origin_message.jump_url, 0, curr_ts))
                    else:
                        self.claim_queue.append((ctx.author_id, curr_ts))
                        self.client.loop.create_task(self.gradual_invites(ctx.author, ctx.origin_message.jump_url, len(self.claim_queue) * 2, curr_ts))

                    ___em = discord.Embed(description=f"You have been added to the invite queue.\n\nYou will be notified when your invite is ready.\n`ETA: {len(self.claim_queue) * 2} seconds`")
                    await ctx.send(embed=___em, hidden=True)

                    if len(data["claimed"]) == data["winners"]:
                        disabled_button = [create_button(
                            label="Claim.",
                            style=ButtonStyle.grey,
                            disabled=True,
                            emoji="🎉"
                        )]
                        new_ar = [create_actionrow(*disabled_button)]
                        try:
                            await ctx.edit_origin(content=ctx.origin_message.content, embed=ctx.origin_message.embeds[0], components=new_ar)
                        except:
                            pass
                    return
            else:
                return await ctx.send("You are not in this raffle.", hidden=True)

def setup(client):
    client.add_cog(EventRaffle(client))