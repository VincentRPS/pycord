from typing import List, Union

import discord
from discord import abc
from discord.commands import ApplicationContext
from discord.ext.commands import Context
from discord.utils import MISSING


class PaginateButton(discord.ui.Button):
    def __init__(self, label, emoji, style, disabled, button_type, paginator):
        super().__init__(label=label, emoji=emoji, style=style, disabled=disabled)
        self.label = label
        self.emoji = emoji
        self.style = style
        self.disabled = disabled
        self.button_type = button_type
        self.paginator = paginator

    async def callback(self, interaction: discord.Interaction):
        if self.button_type == "first":
            self.paginator.current_page = 0
        elif self.button_type == "prev":
            self.paginator.current_page -= 1
        elif self.button_type == "next":
            self.paginator.current_page += 1
        elif self.button_type == "last":
            self.paginator.current_page = self.paginator.page_count
        self.paginator.update_buttons()
        page = self.paginator.pages[self.paginator.current_page]
        await interaction.response.edit_message(
            content=page if isinstance(page, str) else None, embed=page if isinstance(page, discord.Embed) else None, view=self.paginator
        )


class Paginate(discord.ui.View):
    """Creates a paginator for a message that is navigated with buttons.
    Parameters
    ------------
    pages: Union[List[:class:`str`], List[:class:`discord.Embed`]]
        Your list of strings or embeds to paginate
    show_disabled: :class:`bool`
        Choose whether or not to show disabled buttons
    """

    def __init__(self, pages: Union[List[str], List[discord.Embed]], show_disabled=True, author_check=True):
        super().__init__()
        self.pages = pages
        self.current_page = 0
        self.page_count = len(self.pages) - 1
        self.show_disabled = show_disabled
        self.buttons = {
            "first": {
                "object": PaginateButton(label="<<", style=discord.ButtonStyle.blurple, emoji=None, disabled=True, button_type="first", paginator=self),
                "hidden": True,  # We always start by showing the first page, so there's no need to start with this button enabled
            },
            "prev": {
                "object": PaginateButton(label="<", style=discord.ButtonStyle.red, emoji=None, disabled=True, button_type="prev", paginator=self),
                "hidden": True,
            },
            "next": {
                "object": PaginateButton(label=">", style=discord.ButtonStyle.green, emoji=None, disabled=True, button_type="next", paginator=self),
                "hidden": False,
            },
            "last": {
                "object": PaginateButton(label=">>", style=discord.ButtonStyle.blurple, emoji=None, disabled=True, button_type="last", paginator=self),
                "hidden": False,
            },
        }
        self.update_buttons()

        self.usercheck = author_check
        self.user = None

    async def interaction_check(self, interaction):
        if self.usercheck:
            return self.user == interaction.user
        return True

    def update_buttons(self):
        for key, button in self.buttons.items():
            if key == "first":
                if self.current_page <= 1:
                    button["hidden"] = True
                elif self.current_page >= 1:
                    button["hidden"] = False
            elif key == "prev":
                if self.current_page <= 0:
                    button["hidden"] = True
                elif self.current_page >= 0:
                    button["hidden"] = False
            elif key == "next":
                if self.current_page == self.page_count:
                    button["hidden"] = True
                elif self.current_page < self.page_count:
                    button["hidden"] = False
            elif key == "last":
                if self.current_page >= self.page_count - 1:
                    button["hidden"] = True
                if self.current_page < self.page_count - 1:
                    button["hidden"] = False
        self.clear_items()
        for key, button in self.buttons.items():
            if button["hidden"]:
                button["object"].disabled = True
                if self.show_disabled:
                    self.add_item(button["object"])
            else:
                button["object"].disabled = False
                self.add_item(button["object"])

    async def send(self, messageable: abc.Messageable, ephemeral: bool = False):
        """Sends a message with the paginated items.
        Parameters
        ------------
        messageable: :class:`discord.abc.Messageable`
            The messageable channel to send to.
        ephemeral: :class:`bool`
            Choose whether or not the message is ephemeral. Only works with slash commands.
        Returns
        --------
        :class:`~discord.Message`
            The message that was sent.
        """

        if not isinstance(messageable, abc.Messageable):
            raise TypeError("messageable should be a subclass of abc.Messageable")

        page = self.pages[0]

        if isinstance(messageable, (ApplicationContext, Context)):
            self.user = messageable.author

        if isinstance(messageable, ApplicationContext):
            message = await messageable.respond(
                content=page if isinstance(page, str) else None, embed=page if isinstance(page, discord.Embed) else MISSING, view=self, ephemeral=ephemeral
            )
        else:
            message = await messageable.send(
                content=page if isinstance(page, str) else None, embed=page if isinstance(page, discord.Embed) else None, view=self
            )
        return message
