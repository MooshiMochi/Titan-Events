import discord
import asyncio
import json
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


class Giveaways(commands.Cog):


    def __init__(self, client):
        self.client = client
        
        self.party = "🎁"

        with open("data/giveaways/active.json", "r") as f:
            self.giveaways = json.load(f)


        self.timeout_button = [create_button(
        style=ButtonStyle.red,
        label="Giveaway Ended!",
        emoji="🎉", 
        disabled=True)]

        self.enter_buttons = [
            create_button(
                label="Enter", 
                emoji="🎉", 
                style=ButtonStyle.green,
                custom_id="giveaway_enter")
        ]

        self.claim_buttom = [
            create_button(
                label="Claim",
                emoji="🎉",
                style=ButtonStyle.green,
                custom_id="giveaway_claim")
        ]

        self.claim_component = [create_actionrow(*self.claim_buttom)]
        self.timeout_components = [create_actionrow(*self.timeout_button)]

        self.resume_giveaways.start()

    @cog_slash(
        name="giveaway", 
        description="Create a giveaway", guild_ids=const.slash_guild_ids, 
        options=[
            create_option(name="channel", description="Please mention the name of the channel in which the giveaway should be hosted.", option_type=7, required=True),
            create_option(name="time", description="Please specify the duration of this giveaway. Eg: 1h, 1d, 12h, 1mo.", option_type=3, required=True),
            create_option(name="title", description="What should be the title of this giveaway?", option_type=3, required=True),
            create_option(name="winners", description="How many winners will this giveaway have?", option_type=4, required=False),
            create_option(name="required_role", description="What will be the role required to enter this giveaway?", option_type=8, required=False),
            create_option(name="ping_role_1", description="What role should I ping?", option_type=8, required=False),
            create_option(name="ping_role_2", description="What other role should I ping?", option_type=8, required=False),
            create_option(name="ping_role_3", description="What other role should I ping?", option_type=8, required=False)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def giveaway(self, ctx:SlashContext, channel:discord.TextChannel=None, title:str=None, time:str=None, winners:int=1, required_role:discord.Role=None, ping_role_1:discord.Role=None, ping_role_2:discord.Role=None, ping_role_3:discord.Role=None):

        pings = "|| "
        pings += ping_role_1.mention if ping_role_1 else ""
        pings += ping_role_2.mention if ping_role_2 else ""
        pings += ping_role_3.mention if ping_role_3 else ""
        if pings != "|| ":
            pings += " ||"
        else:
            pings = ""

        if not isinstance(channel, discord.TextChannel):
            return await ctx.send("I can only host giveaways in text channels.", hidden=True)

        int_duration = await self.client.format_duration(time)
        # if int_duration < 300:
        #     return await ctx.send("Giveaway duration cannot be shorter than 5 minutes.", hidden=True)
        # elif int_duration > 2419200:
        #     return await ctx.send("Giveaway duration cannot be greater than 1 month.", hidden=True)

        if winners > 10:
            return await ctx.send("There can only be a maximum of 10 winners.", hidden=True)

        if winners < 1:
            return await ctx.send("There can only be a minimum of 1 winner.", hidden=True)

        em = discord.Embed(color=self.client.success, description="")
        em.set_author(name=title, icon_url="https://media.discordapp.net/attachments/884145972995825724/935929000449167460/MainGift.png")
        em.description += f"\n\n<:lunar_dot:943374901748846602> {winners} winner(s)"
        em.description += f"\n<:lunar_dot:943374901748846602> Hosted by: {ctx.author.mention}"
        em.description += f"\n<:lunar_dot:943374901748846602> Ends: <t:{int(datetime.now().timestamp() + int_duration)}:R>"
        em.description += f"\n\n**Prize**: __Event Server Invite__"
        em.description += f"\n\nClick the button below to enter the giveaway!"
        
        action_row = create_actionrow(*self.enter_buttons)

        try:
            
            msg = await channel.send(content=f"{self.party} **GIVEAWAY** {self.party} {pings}", embed=em, components=[action_row], allowed_mentions=AllowedMentions(roles=True))
        except discord.HTTPException:
            return await ctx.send("I do not have enough permissions to create a giveaway in that channel.", hidden=True)

        self.giveaways[str(msg.id)] = {
            "message_id": msg.id,
            "required_role": {
                'id': required_role.id if required_role else None,
                'name': required_role.name if required_role else None},
            "time": int(datetime.utcnow().timestamp()) + int_duration,
            "winners": winners,
            "host": ctx.author_id,
            "members": [],
            "guild_id": msg.guild.id,
            "channel_id": msg.channel.id,
            "jump_url": msg.jump_url,
            "finished": False,
            "claimed": [],
            "giveaway_winners": []
        }

        with open("data/giveaways/active.json", "w") as f:
            json.dump(self.giveaways, f, indent=2)

        await ctx.send(f"Success!", hidden=True)

        self.client.loop.create_task(self.wait_for_giveaway(str(msg.id)))

    @tasks.loop(seconds=15.0)
    async def save_giveaways(self):
        with open("data/giveaways/active.json", "w") as f:
            json.dump(self.giveaways, f, indent=2)    

    @tasks.loop(count=1)
    async def resume_giveaways(self):
        
        self.save_giveaways.start()

        ts = datetime.utcnow().timestamp()

        tasks = []
        for key in self.giveaways.keys():
            if self.giveaways[key]["time"] < ts:
                tasks.append(self.wait_for_giveaway(key))
        if tasks:
            await asyncio.gather(*tasks)

    @tasks.loop(minutes=5)
    async def clear_giveaway_cache(self):
        ts = datetime.utcnow().timestamp()
        for key in self.giveaways.copy().keys():
            if ts - self.giveaways[key]["time"] >= 24*60*60:
                self.giveaways.pop(key, None)
        
    @resume_giveaways.before_loop
    @save_giveaways.before_loop
    @clear_giveaway_cache.before_loop
    async def before_resuming_giveaways(self):
        await self.client.wait_until_ready()


    @cog_slash(name="giveaway_reroll", description="Re-roll a giveaway", guild_ids=const.slash_guild_ids, options=[
        create_option(name="message_id", description="The ID of the giveaway message", option_type=3, required=True)
    ])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    async def giveaway_reroll(self, ctx:SlashContext, message_id:str=None):
        await ctx.defer(hidden=True)
    
        data = self.giveaways.get(message_id, None)
        if not data:
            return await ctx.send("It looks like that giveaway no longer exists. Sorry, but you cannot re-roll this giveaway", hidden=True)
        
        if not data["finished"]:
            return await ctx.send("This giveaway has not finished yet. You can only re-roll after a giveaway has ended.", hidden=True)

        guild = self.client.get_guild(data['guild_id'])
        channel = guild.get_channel(data['channel_id'])
        msg = await channel.fetch_message(data['message_id'])

        if not data["members"]:
            em = discord.Embed(color=self.client.warn, description=f"> Could not determine a new winner for this giveaway as there are no valid entrants")
            em.set_author(name="Giveaway Issue", icon_url="https://media.discordapp.net/attachments/884145972995825724/936019499742789672/MainGift.png")
            
            return await ctx.send(embed=em)

        allowed_winners = [m_id for m_id in data["members"] if m_id not in data["claimed"] and m_id != data["host"]]


        if (data["winners"] == data["claimed"]) or (not allowed_winners):
            em = discord.Embed(color=self.client.warn, description=f"> Could not determine a new winner for this giveaway as all winners have already been claimed")
            em.set_author(name="Giveaway Issue", icon_url="https://media.discordapp.net/attachments/884145972995825724/936019499742789672/MainGift.png")
            
            return await ctx.send(embed=em)
            
        try:
            winners = random.sample(allowed_winners, data['winners'])
        except ValueError:
            winners = data['members']

        data["giveaway_winners"] = winners

        public_em = discord.Embed(color=self.client.warn, description=f"You have won a [giveaway]({data['jump_url']}) for **1 Entry to Events Server**!")

        try:
            await msg.reply(content=f"""{self.party} • {', '.join([f"<@!{w_id}>" for w_id in winners])}""", embed=public_em, components=self.claim_component)
        except discord.HTTPException:
            pass
        
        em = discord.Embed(color=self.client.failure, description=f"> I have rerolled the [giveaway]({data['jump_url']}).")
        em.set_author(name="Giveaway Reroll", icon_url="https://media.discordapp.net/attachments/884145972995825724/933821589202559026/Revoked.png")
        em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)
        em.add_field(name="Giveaway", value=f"`Channel:` <#{data['channel_id']}>\n`ID:` {message_id}")
        return await ctx.send(embed=em, hidden=True)
    

    async def wait_for_giveaway(self, key:str):
        await self.client.wait_until_ready()

        data = self.giveaways[key]

        if self.giveaways[key]['finished']:
            return

        if datetime.utcnow().timestamp() < data["time"]:
            await discord.utils.sleep_until(datetime.fromtimestamp(data["time"]))
        
        guild = self.client.get_guild(data['guild_id'])
        channel = guild.get_channel(data['channel_id'])
        host = guild.get_member(data['host'])
        msg = await channel.fetch_message(str(key))

        self.giveaways[key]['finished'] = True
        #if not data["members"] or len(data["members"]) == 1 or len(data['members']) <= data["winners"]    
        if not data["members"]:
            em = discord.Embed(color=self.client.warn, description=f"[Your giveaway]({data['jump_url']}) ended without any winners.")
            try:
                
                await host.send(embed=em)
                msg = await channel.fetch_message(int(key))

                if msg:
                    edit_em = discord.Embed(color=self.client.failure, description=f"😔 No winners")
                    edit_em.set_author(name="1 Event Server Invite", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
                    edit_em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)

                    await msg.edit(content=f"{self.party}**GIVEAWAY ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
            except discord.HTTPException:
                pass
            # self.giveaways.pop(key, None)

            return
        
        try:
            winners = random.sample(data['members'], data['winners'])
        except ValueError:
            winners = data['members']
        
        data["giveaway_winners"] = winners

        public_em = discord.Embed(color=self.client.warn, description=f"You have won a [giveaway]({data['jump_url']}) for **1 Event Server Invite**!")

        try:
            await msg.reply(content=f"""{self.party} • {', '.join([f"<@!{w_id}>" for w_id in winners])}""", embed=public_em, components=self.claim_component)
        except discord.HTTPException:
            pass
        
        host_em = discord.Embed(color=self.client.success, description=f""">>> **Winner(s):** {', '.join([f"<@!{w_id}>" for w_id in winners])} `({', '.join([str(w_id) for w_id in winners])})`""")
        host_em.set_author(icon_url="https://media.discordapp.net/attachments/884145972995825724/933859630185082920/Stars.png", name="Giveaway Ended", url=data['jump_url'])
        host_em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)

        host_em.description += f"\nPrize(s):" + "\n<:lunar_dot:943374901748846602> `1 Event Server Invite`"

        try:
            await host.send(embed=host_em)
        except discord.HTTPException:
            pass

        for winner_id in winners:
            em = discord.Embed(color=self.client.warn, description=f"""You have just won a [giveaway]({data['jump_url']}) for `1 Event Server Invite` in **{guild.name}**.""")
            em.set_author(name="Giveaway Winner", url=data['jump_url'], icon_url="https://images-ext-2.discordapp.net/external/ZusSn-X4k7HaGEyw0r5Vn1AsLHIMulaePr_mBZvzK0I/%3Fsize%3D128%26quality%3Dlossless/https/cdn.discordapp.com/emojis/894171015888920576.webp")
            em.add_field(name="Information", value=f"> Hosted by: {host.mention} `({data['host']})`")
            em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)
            mem = guild.get_member(winner_id)
            try:
                await mem.send(embed=em)
            except discord.HTTPException:
                pass

        edit_em = discord.Embed(color=self.client.failure, description=f"""> **Winners:** {', '.join([f"<@!{w_id}>" for w_id in winners])}""")
        edit_em.set_author(name="1 Event Server Invite", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
        edit_em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)
        
        try:
            msg = await channel.fetch_message(key)
        except discord.NotFound:
            return

        if msg:
            try:
                await msg.edit(content=f"{self.party}**GIVEAWAY ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
            except discord.HTTPException:
                pass
        # self.giveaways.pop(key, None)
        return

    @commands.Cog.listener()
    async def on_component(self, ctx:ComponentContext):
        await self.client.wait_until_ready()

        if ctx.custom_id == "giveaway_enter":

            data = self.giveaways.get(str(ctx.origin_message_id), None)
            if not data or datetime.utcnow().timestamp() >= data['time']:
                
                edit_em = discord.Embed(color=self.client.warn, description=f"An error occured.\n\nThis giveaway is cancelled.")
                edit_em.set_author(name="1 Event Server Invite" if data else "Unknown", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
                edit_em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)

                await ctx.edit_origin(content=f"{self.party}**GIVEAWAY ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
                return

            if data["required_role"]['id']:
                if data["required_role"]['id'] in (r.id for r in ctx.author.roles):
                    if ctx.author_id in data['members']:
                        return await ctx.send("You are already in this giveaway.", hidden=True)
                    em = discord.Embed(color=self.client.success, description=f"Your entry into this [giveaway]({ctx.origin_message.jump_url}) has been approved.")
                    em.set_author(icon_url="https://images-ext-1.discordapp.net/external/ob9eIZj1RkBiQjNG-BaFVKYH4VMD0Pz0LNmUwhmeIko/%3Fsize%3D56%26quality%3Dlossless/https/cdn.discordapp.com/emojis/933776807256289380.webp", name="Entry Approved")
                    em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)
                    em.timestamp = datetime.utcnow()
                    await ctx.author.send(embed=em)
                    self.giveaways[str(ctx.origin_message_id)]['members'].append(ctx.author_id)
                    self.giveaways[str(ctx.origin_message_id)]["members"] = list(set(data['members']))
                
                else:

                    em = discord.Embed(color=self.client.failure, description=f"To enter this [giveaway]({ctx.origin_message.jump_url}) you need the following role:\n**{data['required_role']['name']}**")
                    em.set_author(icon_url="https://media.discordapp.net/attachments/884145972995825724/933799302491406377/Denied.png", name="Entry Denied")
                    em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)
                    em.timestamp = datetime.utcnow()
                    await ctx.author.send(embed=em)
                    return
            else:
                if ctx.author_id in data['members']:
                    return await ctx.send("You are already in this giveaway.", hidden=True)
                em = discord.Embed(color=self.client.success, description=f"Your entry into this [giveaway]({ctx.origin_message.jump_url}) has been approved.")
                em.set_author(icon_url="https://images-ext-1.discordapp.net/external/ob9eIZj1RkBiQjNG-BaFVKYH4VMD0Pz0LNmUwhmeIko/%3Fsize%3D56%26quality%3Dlossless/https/cdn.discordapp.com/emojis/933776807256289380.webp", name="Entry Approved")
                em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)
                em.timestamp = datetime.utcnow()
                try:
                    await ctx.author.send(embed=em)
                except discord.Forbidden:
                    pass
                
                self.giveaways[str(ctx.origin_message_id)]['members'].append(ctx.author_id)
                self.giveaways[str(ctx.origin_message_id)]["members"] = list(set(data['members']))

            participants = [create_button(
                label=f"{len(data['members'])} Participant(s)",
                style=ButtonStyle.grey,
                disabled=True
            )]

            new_ar = [create_actionrow(*self.enter_buttons, *participants)]

            await ctx.edit_origin(content=ctx.origin_message.content, embed=ctx.origin_message.embeds[0], components=new_ar)
        
        elif ctx.custom_id == "giveaway_claim":
            ## Create an invite link to the server and DM it to the user if they are a winner of the giveaway and have not claimed already
            data = self.giveaways.get(str(ctx.origin_message.reference.message_id), None)
            if not data or datetime.now().timestamp() >= data['time'] + dt.timedelta(weeks=1).total_seconds():
                edit_em = discord.Embed(color=self.client.warn, description=f"An error occured.\n\nThis giveaway is cancelled.")
                edit_em.set_author(name="1 Event Server Invite" if data else "Unknown", icon_url="https://media.discordapp.net/attachments/884145972995825724/934498580885041222/PRESENT.png")
                edit_em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)

                await ctx.edit_origin(content=f"{self.party}**GIVEAWAY ENDED**{self.party}", embed=edit_em, components=self.timeout_components)
                return

            if ctx.author_id in data['giveaway_winners']:
                if ctx.author_id in data['claimed']:
                    return await ctx.send("You have already claimed this giveaway.", hidden=True)
                else:
                    data['claimed'].append(ctx.author_id)
                    self.giveaways[str(ctx.origin_message_id)] = data
                    inv = await ctx.channel.create_invite(max_age=604800, max_uses=1, reason="Giveaway Winner")

                    em = discord.Embed(color=self.client.success, description=f"Here is your reward for the [giveaway]({ctx.origin_message.jump_url}).\n\n{inv.url}")
                    em.set_author(icon_url="https://images-ext-1.discordapp.net/external/ob9eIZj1RkBiQjNG-BaFVKYH4VMD0Pz0LNmUwhmeIko/%3Fsize%3D56%26quality%3Dlossless/https/cdn.discordapp.com/emojis/933776807256289380.webp", name="Claimed")
                    em.set_footer(text="TitanMC | Giveaways", icon_url=self.client.png)
                    em.timestamp = datetime.utcnow()
                    await ctx.author.send(embed=em)

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
                return await ctx.send("You are not in this giveaway.", hidden=True)

def setup(client):
    client.add_cog(Giveaways(client))