import discord
from discord.ext import commands
import traceback
from datetime import datetime
from discord_slash import SlashContext
from discord_slash import error as Error
from discord_slash.model import BucketType


class ErrorHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: SlashContext, error):
    
        if not ctx.deferred:
            try:
                await ctx.defer(hidden=True)
            except Error.AlreadyResponded:
                pass

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        error = getattr(error, "original", error)


        if isinstance(error, discord.NotFound) or isinstance(error, discord.Forbidden):
            # probably because a message got deleted, so we'll ignore it.

            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass

        elif isinstance(error, Error.RequestFailure):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="Oops, something went wrong.",
                                  description=f"Something's gone terribly wrong. " +
                                              f"Please forward the following output to a server administrator." +
                                              f"\n```\n{f'Request failed with resp: {error.status} | {error.msg}'}\n```",
                                  color=self.client.failure)
            try:
                await ctx.embed(embed, footer="Error Handler")
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.MaxConcurrencyReached):
            d = {commands.BucketType.default: "globally",
                 commands.BucketType.user: "per user",
                 commands.BucketType.guild: "per guild",
                 commands.BucketType.channel: "per channel",
                 commands.BucketType.member: "per member",
                 commands.BucketType.category: "per category",
                 commands.BucketType.role: "per role",
                 BucketType.default: "globally",
                 BucketType.user: "per user",
                 BucketType.guild: "per guild",
                 BucketType.channel: "per channel",
                 BucketType.member: "per member",
                 BucketType.category: "per category",
                 BucketType.role: "per role"
                 }
            if error.number > 1:
                e = f"{error.number} times"
            else:
                e = f"{error.number} time"
            embed = discord.Embed(title="Woah, calm down.",
                                  description=f"This command can only be used {e} {d[error.per]}.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.MissingRole):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="Hey, you can't do that!",
                                  description=f"Sorry, you need to have the role <@&{error.missing_role}> " +
                                               "to execute that command.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.MissingAnyRole):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="Hey, you can't do that!",
                                  description="Sorry, you need to have one of the following roles: " +
                                             f"<@&{'>, <@&'.join(error.missing_roles)}> to execute that command.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the bot doesn't have enough permissions
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ', '.join(error.missing_perms)
            if 'send_messages' in perms:
                return
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="I can't do that.",
                                  description=f"Sorry, I require the permission(s) `{perms}` to " +
                                               "execute that command. Please contact a server " +
                                               "administrator to fix this issue.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.TooManyArguments):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="That's not right.",
                                  description="That's a lot of arguments. Too many in fact.", color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.BadUnionArgument):
            param = str(error.param.name).replace("_", " ")
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="That's not right.",
                                  description=f"Invalid `{param}` argument. Please try again.", color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If a user tries to run a restricted command
        elif isinstance(error, commands.NotOwner):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="Hey, you can't do that!", description="This command is restricted.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.MemberNotFound):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="That's not right.", description="Invalid member. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.UserNotFound):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="That's not right.", description="Invalid user. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.RoleNotFound):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="That's not right.", description="Invalid role. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.ChannelNotFound):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="That's not right.", description="Invalid channel. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the command is disabled
        elif isinstance(error, commands.DisabledCommand):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="Hey, you can't do that!", description="This command is disabled.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the command is on a cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            timeout = str(error.retry_after)
            timeout = timeout.replace('s', '')
            seconds = int(float(timeout))
            m, sec = divmod(seconds, 60)
            hour, m = divmod(m, 60)
            if hour == 0:
                if m == 0:
                    if sec == 1:
                        message = f"That command is on cooldown. You may try again in {sec} second."
                    else:
                        message = f"That command is on cooldown. You may try again in {sec} seconds."
                elif m == 1:
                    message = f"That command is on cooldown. You may try again in {m} minute."
                else:
                    message = f"That command is on cooldown. You may try again in {m} minutes."
            elif hour == 1:
                message = f"That command is on cooldown. You may try again in {hour} hour."
            else:
                message = f"That command is on cooldown. You may try again in {hour} hours."
            embed = discord.Embed(title="Woah, calm down.", description=message, color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the user provides an argument that has quotes and the bot gets pissed off
        elif isinstance(error, commands.InvalidEndOfQuotedStringError) or isinstance(error,
                                                                                     commands.ExpectedClosingQuoteError
                                                                                     ) or isinstance(
                error, commands.UnexpectedQuoteError):
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            embed = discord.Embed(title="That's not right.",
                                  description="I don't like quotes, please omit any quotes in the command.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the user doesnt have enough permissions to run a command
        elif isinstance(error, commands.MissingPermissions):
            if isinstance(error.missing_perms, str):
                perms = error.missing_perms.replace("_", " ").title()
            else:
                perms = ', '.join([str(x).replace("_", " ").title() for x in error.missing_perms])
            
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass
            if len(error.missing_perms) == 1:
                embed = discord.Embed(title="Hey, you can't do that!",
                                      description=f"Sorry, you need the permission `{perms}` to execute this command.",
                                      color=self.client.failure)
                embed.set_thumbnail(url=self.client.png)
                try:
                    return await ctx.embed(embed)
                except discord.HTTPException:
                    return
            else:
                embed = discord.Embed(title="Hey, you can't do that!",
                                      description=f"Sorry, you need the permissions `{perms}` to execute this command.",
                                      color=self.client.failure)
                embed.set_thumbnail(url=self.client.png)
                try:
                    return await ctx.embed(embed)
                except discord.HTTPException:
                    return
        
        # If the error is not recognized
        else:
            try:
                self.client.slash.commands[ctx.command].reset_cooldown(ctx)
            except AttributeError:
                pass

            embed = discord.Embed(title="Oops, something went wrong.",
                                  description=f"Something's gone terribly wrong. " +
                                              f"Please forward the following output to a server administrator." +
                                              f"\n```\n{str(error)}\n```",
                                  color=self.client.failure)
            try:
                await ctx.embed(embed, footer="Error Handler")
            except discord.HTTPException:
                pass

            try:
                raise error
            except Exception:
                tb = traceback.format_exc()
            self.client.logger.error(f"An unhandled error has occurred: {str(error)} - More details can be found in logs/error.log")
            with open('logs/error.log', 'a', encoding="utf8") as logfile:
                logfile.write("NEW ERROR\n\n")
                logfile.write(str(tb))

            if self.client.config.log_channel is not None:
                channel = self.client.get_channel(self.client.config.log_channel)
                if channel is not None:

                    _arguments = ' '.join([f"{x[0]}: '{x[1]}'" for x in ctx.kwargs.items()])
                    
                    embed = discord.Embed(title=f"Exception in '{ctx.command}'",
                                              description=f"Command Invoker: {ctx.author.mention}\n" +
                                                          f"Command: `/{ctx.name} {_arguments}`\n",
                                              color=self.client.failure)
                    embed.set_footer(text="Error Handler", icon_url=self.client.png)
                    embed.timestamp = datetime.utcnow()
                    
                    if len(tb) < 2000:
                        file = None
                        embed.description += f"\n```\n{str(tb)}\n```"
                        
                    else:
                        embed.description += f"\nTraceback is too long to be displayed.```"
                        
                        with open('logs/last_command_error.log', 'a') as latest_logfile:
                            latest_logfile.write(str(tb))
                        
                        file = discord.File(fp="logs/last_command_error.log", filename="last_command_error.log")
                    await channel.send(embed=embed, file=file) if file else await channel.send(embed=embed)

                else:
                    raise ValueError("Log channel does not exist.")

    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # This prevents any commands with local handlers being handled here in on_command_error.
        # if hasattr(ctx.command, 'on_error'):
        #     return

        # This prevents any cogs with an overwritten cog_command_error being handled here.

        if isinstance(ctx, SlashContext):
            return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        error = getattr(error, "original", error)

        # If a user tries to run a nonexistant command
        if isinstance(error, commands.CommandNotFound):
            return  # we dont need to reset the cooldown, it doesnt exist

        elif isinstance(error, (discord.NotFound, discord.errors.NotFound)) or isinstance(error, (discord.Forbidden, discord.errors.Forbidden)):
            # probably because a message got deleted, so we'll ignore it.
            return ctx.command.reset_cooldown(ctx)

        elif isinstance(error, commands.MaxConcurrencyReached):
            d = {commands.BucketType.default: "globally",
                 commands.BucketType.user: "per user",
                 commands.BucketType.guild: "per guild",
                 commands.BucketType.channel: "per channel",
                 commands.BucketType.member: "per member",
                 commands.BucketType.category: "per category",
                 commands.BucketType.role: "per role"
                 }
            if error.number > 1:
                e = f"{error.number} times"
            else:
                e = f"{error.number} time"
            embed = discord.Embed(title="Woah, calm down.",
                                  description=f"This command can only be used {e} {d[error.per]}.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.MissingRole):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="Hey, you can't do that!",
                                  description=f"Sorry, you need to have the role <@&{error.missing_role}> " +
                                               "to execute that command.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.MissingAnyRole):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="Hey, you can't do that!",
                                  description="Sorry, you need to have one of the following roles: " +
                                             f"<@&{'>, <@&'.join(error.missing_roles)}> to execute that command.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the bot doesn't have enough permissions
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ', '.join(error.missing_perms)
            if 'send_messages' in perms:
                return
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="I can't do that.",
                                  description=f"Sorry, I require the permission(s) `{perms}` to " +
                                               "execute that command. Please contact a server " +
                                               "administrator to fix this issue.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.TooManyArguments):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.",
                                  description="That's a lot of arguments. Too many in fact.", color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If a user doesn't provide a required argument
        elif isinstance(error, commands.MissingRequiredArgument):
            param = str(error.param.name).replace("_", " ")
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.", description=f"Please provide the `{param}` argument.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.BadUnionArgument):
            param = str(error.param.name).replace("_", " ")
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.",
                                  description=f"Invalid `{param}` argument. Please try again.", color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If a user tries to run a restricted command
        elif isinstance(error, commands.NotOwner):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="Hey, you can't do that!", description="This command is restricted.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.MemberNotFound):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.", description="Invalid member. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.UserNotFound):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.", description="Invalid user. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.RoleNotFound):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.", description="Invalid role. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        elif isinstance(error, commands.ChannelNotFound):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.", description="Invalid channel. Please try again.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the command is disabled
        elif isinstance(error, commands.DisabledCommand):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="Hey, you can't do that!", description="This command is disabled.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the command is on a cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            timeout = str(error.retry_after)
            timeout = timeout.replace('s', '')
            seconds = int(float(timeout))
            m, sec = divmod(seconds, 60)
            hour, m = divmod(m, 60)
            if hour == 0:
                if m == 0:
                    if sec == 1:
                        message = f"That command is on cooldown. You may try again in {sec} second."
                    else:
                        message = f"That command is on cooldown. You may try again in {sec} seconds."
                elif m == 1:
                    message = f"That command is on cooldown. You may try again in {m} minute."
                else:
                    message = f"That command is on cooldown. You may try again in {m} minutes."
            elif hour == 1:
                message = f"That command is on cooldown. You may try again in {hour} hour."
            else:
                message = f"That command is on cooldown. You may try again in {hour} hours."
            embed = discord.Embed(title="Woah, calm down.", description=message, color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the user provides an argument that has quotes and the bot gets pissed off
        elif isinstance(error, commands.InvalidEndOfQuotedStringError) or isinstance(error,
                                                                                     commands.ExpectedClosingQuoteError
                                                                                     ) or isinstance(
                error, commands.UnexpectedQuoteError):
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="That's not right.",
                                  description="I don't like quotes, please omit any quotes in the command.",
                                  color=self.client.failure)
            try:
                return await ctx.embed(embed)
            except discord.HTTPException:
                return

        # If the user doesnt have enough permissions to run a command
        elif isinstance(error, commands.MissingPermissions):
            if isinstance(error.missing_perms, str):
                perms = error.missing_perms.replace("_", " ").title()
            else:
                perms = ', '.join([str(x).replace("_", " ").title() for x in error.missing_perms])
            ctx.command.reset_cooldown(ctx)
            if len(error.missing_perms) == 1:
                embed = discord.Embed(title="Hey, you can't do that!",
                                      description=f"Sorry, you need the permission `{perms}` to execute this command.",
                                      color=self.client.failure)
                embed.set_thumbnail(url=self.client.png)
                try:
                    return await ctx.embed(embed)
                except discord.HTTPException:
                    return
            else:
                embed = discord.Embed(title="Hey, you can't do that!",
                                      description=f"Sorry, you need the permissions `{perms}` to execute this command.",
                                      color=self.client.failure)
                embed.set_thumbnail(url=self.client.png)
                try:
                    return await ctx.embed(embed)
                except discord.HTTPException:
                    return

        # If the error is not recognized
        else:
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed(title="Oops, something went wrong.",
                                  description=f"Something's gone terribly wrong. " +
                                              f"Please forward the following output to a server administrator." +
                                              f"\n```\n{str(error)}\n```",
                                  color=self.client.failure)
            try:
                await ctx.embed(embed)
            except discord.HTTPException:
                pass

            try:
                raise error
            except Exception:
                tb = traceback.format_exc()
            self.client.logger.error(f"An unhandled error has occurred: {str(error)} - More details can be found in logs/error.log")
            with open('logs/error.log', 'a', encoding="utf8") as logfile:
                logfile.write("NEW ERROR\n\n")
                logfile.write(str(tb))
            if self.client.config.log_channel is not None:
                channel = self.client.get_channel(self.client.config.log_channel)
                if channel is not None:
                    if len(tb) < 2000:
                        file = None
                        embed = discord.Embed(title=f"Exception in '{ctx.command}'",
                                              description=f"Command Invoker: {ctx.author.mention}\n" +
                                                          f"Command: `{ctx.message.content}`\n\n```\n{str(tb)}\n```",
                                              color=self.client.failure)
                        embed.set_footer(text="Error Handler", icon_url=self.client.png)
                        embed.timestamp = datetime.utcnow()
                    else:
                        embed = discord.Embed(title=f"Exception in '{ctx.command}'",
                                              description=f"Command Invoker: {ctx.author.mention}\n" +
                                                          f"Command: `{ctx.message.content}`\n\n" +
                                                          f"```\n" +
                                                          f"Traceback is too long to be displayed.```",
                                              color=self.client.failure)
                        embed.set_footer(text="Error Handler", icon_url=self.client.png)
                        embed.timestamp = datetime.utcnow()
                        
                        with open('logs/last_command_error.log', 'a') as latest_logfile:
                            latest_logfile.write(str(tb))
                        
                        file = discord.File(fp="logs/last_command_error.log", filename="last_command_error.log")
                    await channel.send(embed=embed, file=file) if file else await channel.send(embed=embed)

                else:
                    raise ValueError("Log channel does not exist.")


def setup(client):
    client.add_cog(ErrorHandler(client))