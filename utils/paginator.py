from typing import Iterable, Union
from asyncio import TimeoutError
from datetime import datetime

from discord.embeds import Embed
from discord.errors import NotFound
from discord.ext.commands import Context, Paginator as CommandPaginator

from discord_slash import ComponentContext, SlashContext
from discord_slash.model import ButtonStyle
from discord_slash.utils import manage_components


class Paginator:
    def __init__(self, _iterable:list=None, ctx:Union[SlashContext, Context]=None) -> None:
        self._iterable = _iterable
        self.ctx = ctx

        self.button_left_id = f'paginator__{datetime.utcnow().timestamp()}_l'
        self.button_right_id = f'paginator__{datetime.utcnow().timestamp()}_r'

        if not self._iterable and not self.ctx:
            raise AttributeError("A list of items of type 'Union[str, int, discord.Embed]' was not provided to iterate through as well as the invocation context.")

        elif not _iterable:
            raise AttributeError("A list of items of type 'Union[str, int, discord.Embed]' was not provided to iterate through.")

        elif not ctx:
            raise AttributeError("The ctx of the invocation command was not provided.")

        if not isinstance(_iterable, Iterable):
            raise AttributeError("An iterable containing items of type 'Union[str, int, discord.Embed]' classes is required.")
        
        elif False in [isinstance(item, (str, int, Embed)) for item in _iterable]:
            raise AttributeError("All items within the iterable must be of type 'str', 'int' or 'discord.Embed'.")

        self._iterable = list(self._iterable)

    async def create_buttons(self):
        btnLeftID = f"paginator__{datetime.utcnow().timestamp()}_l"
        btnRightID = f"paginator__{datetime.utcnow().timestamp()}_r"
        command_buttons = [
            manage_components.create_button(
                style=ButtonStyle.blue,
                label="Previous Page",
                custom_id=btnLeftID),
            manage_components.create_button(
                style=ButtonStyle.blue,
                label="Next Page",
                custom_id=btnRightID)]

        my_action_row = manage_components.create_actionrow(*command_buttons)
        self.button_left_id = btnLeftID; self.button_right_id = btnRightID
        return my_action_row

    async def run(self):
        timeout_buttons = [manage_components.create_button(
            style=ButtonStyle.danger,
            label="Menu timed out.",
            custom_id="paginator_button_timeout",
            disabled=True
        )]

        timeout_action_row = manage_components.create_actionrow(*timeout_buttons)

        my_action_row = await self.create_buttons()

        if isinstance(self._iterable[0], Embed):
            if isinstance(self.ctx, Context):
                msg = await self.ctx.send(embed=self._iterable[0], components=[my_action_row])
            else:
                msg = await self.ctx.send(embed=self._iterable[0], components=[my_action_row], hidden=self.ctx._deferred_hidden)
        else:
            if isinstance(self.ctx, Context):
                msg = await self.ctx.send(content=self._iterable[0], components=[my_action_row])
            else:
                msg = await self.ctx.send(content=self._iterable[0], components=[my_action_row], hidden=self.ctx._deferred_hidden)
        
        page = 0

        while 1:

            try:
                button_ctx: ComponentContext = await manage_components.wait_for_component(
                    self.ctx.bot, components=[my_action_row], timeout=30
                    )

                if button_ctx.author_id != self.ctx.author.id:
                    await button_ctx.reply("You were not the author of this command therefore cannot use these components.", hidden=True)
                    continue
                
                if button_ctx.custom_id == self.button_left_id:
                    page -= 1
                    if page == -1:
                        page = len(self._iterable)-1


                elif button_ctx.custom_id == self.button_right_id:
                    page += 1
                    if page > len(self._iterable)-1:
                        page = 0

                try:
                    my_action_row = await self.create_buttons()
                    if isinstance(self._iterable[page], Embed):
                        await button_ctx.edit_origin(embed=self._iterable[page], components=[my_action_row])
                    else:
                        await button_ctx.edit_origin(content=self._iterable[page], components=[my_action_row])
                except NotFound:
                    # message was probably deleted so we will return without raising TimeoutError
                    return

            except TimeoutError:
                
                if isinstance(self.ctx, Context):
                    if isinstance(self._iterable[page], Embed):
                        await msg.edit(embed=self._iterable[page], components=[timeout_action_row])
                    else:
                        await msg.edit(content=self._iterable[page], components=[timeout_action_row])
                break


class TextPageSource:
    """ Get pages for text paginator """
    def __init__(self, text, *, prefix='```', suffix='```', max_size=2000, code_block=False):
        if code_block:
            prefix += "py\n"
        pages = CommandPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split('\n'):
            pages.add_line(line)
        self.pages = pages

    def getPages(self, *, page_number=True):
        """ Gets the pages. """
        pages = []
        pagenum = 1
        for page in self.pages.pages:
            if page_number:
                page += f'\nPage {pagenum}/{len(self.pages.pages)}'
                pagenum += 1
            pages.append(page)
        return pages