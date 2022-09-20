"""
Classes for discord views.

:copyright: (c) 2022 Isaglish
:license: MIT, see LICENSE for more details.
"""

import discord


class Confirm(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__()
        self.value = None
        self.author = author
        

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()


    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()


    async def interaction_check(self, interaction: discord.Interaction):
        if self.author == interaction.user:
            return True
        else:
            await interaction.response.send_message("You don't have the permission to do that.", ephemeral=True)
            return False


class EmbedPaginator(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, embeds: list, query: list):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.author = interaction.user
        self.embeds = embeds
        self.query = query

        self.current_page = 0
        self.max_pages = len(embeds)


    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.blurple, custom_id="prev_page:button", disabled=True)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = self.current_page - 1 == 0
        self.next.disabled = False
        self.current_page -= 1
        
        embed = self.embeds[self.current_page]
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} • Total amount of submissions: {len(self.query)}")
        await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.blurple, custom_id="next_page:button", disabled=True)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = self.current_page + 1 == self.max_pages - 1
        self.prev.disabled = False
        self.current_page += 1

        embed = self.embeds[self.current_page]
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} • Total amount of submissions: {len(self.query)}")
        await interaction.response.edit_message(embed=embed, view=self)


    async def interaction_check(self, interaction: discord.Interaction):
        if self.author == interaction.user:
            return True
        else:
            await interaction.response.send_message("You don't have the permission to do that.", ephemeral=True)
            return False
