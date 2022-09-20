"""
Main feature of Odd Bot, keeps track of submissions.

:copyright: (c) 2022 Isaglish
:license: MIT, see LICENSE for more details.
"""

import discord
from discord import app_commands
from discord.ext import commands
import re
from typing import List

from .utils.database import Database
from .utils.views import Confirm, EmbedPaginator
from .helper import SubmissionHelper


class Submission(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = bot.log
        self.db = Database("fanweek", "submissions")
        self.helper = SubmissionHelper()


    # groups
    submissions_group = app_commands.Group(name="submissions", description="Commands related to submissions.")


    async def handle_unsubmit_confirm_view(self, interaction: discord.Interaction, view: discord.ui.View, post: dict, query: dict):
        await view.wait()
        if view.value is None:
            embed = discord.Embed(color=discord.Color.red(), description="You took too long to respond.")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.edit_original_response(embed=embed)

        elif view.value:
            embed = discord.Embed(color=discord.Color.blue(), description=f"{self.bot.config.LOADING} Deleting submission...")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.edit_original_response(embed=embed, view=None)

            self.db.delete_one(post)

            embed.description = f"The game **{query['title']}** has been removed from the database."
            embed.color = discord.Color.green()
            await interaction.edit_original_response(embed=embed, view=None)

        else:
            embed = discord.Embed(color=discord.Color.red(), description="Command has been cancelled.")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.edit_original_response(embed=embed, view=None)


    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info(f"{self.__class__.__name__.lower()} module is ready.")


    @commands.command()
    async def sync(self, ctx: commands.Context):
        """Syncs all app commands to the server"""
        if ctx.author.id not in self.bot.config.OWNER_IDS:
            return None

        await self.bot.tree.sync(guild=self.bot.config.TEST_GUILD_ID)
        await ctx.send("All commands have been synced.")


    @submissions_group.command(name="submit", description="Submits your game to the database")
    @app_commands.describe(
        link="Your game's link, you can get this by sharing your game in Fancade.",
        member="The member you want to submit for. This requires Manage Server permission."
    )
    async def submit_command(self, interaction: discord.Interaction, link: str, member: discord.Member = None):

        if not re.match("https://play.fancade.com/[0-9A-Z]{16}", link):
            await self.helper.send_error_message(interaction, "Sorry, but I don't recognize that link.")
            return None

        can_manage_guild = interaction.user.guild_permissions.manage_guild
        query = self.db.find_one({"guild_id": interaction.guild_id, "link": link})
        game_attrs = await self.helper.get_game_attrs(link)

        if not can_manage_guild and member != interaction.user and member is not None:
            await self.helper.send_error_message(interaction, "Sorry, you can't submit for another member since you're missing `Manage Server` permission.")
            return None

        if query is not None:
            author = await interaction.guild.fetch_member(query["author_id"])
            await self.helper.send_error_message(interaction, f"Sorry, but the game **{query['title']}** has already been submitted by **{author}**.")
            return None

        if game_attrs["title"] == "Fancade":
            await self.helper.send_error_message(interaction, "Hmm, either that game hasn't been processed yet or it doesn't exist.")

        game_exists = await self.helper.check_game_exists(game_identifier)
        if game_exists:
            game_attrs["title"] = "??UNLISTED_GAME??"
        else:
            await self.helper.send_error_message(interaction, "Hmm, either that game doesn't exist or it hasn't been processed yet.")
            return None

        if member is None or member == interaction.user:
            embed = discord.Embed(color=discord.Color.blue(), description=f"{self.bot.config.LOADING} Processing submission...")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed)

            post = {
                "guild_id": interaction.guild_id,
                "author_id": interaction.user.id,
                "title": game_attrs["title"],
                "link": link
            }
            self.db.insert_one(post)

            embed.description = f"{interaction.user.mention}, your game **{game_attrs['title']}** was submitted successfully."
            embed.set_thumbnail(url=game_attrs["image_url"])
            await interaction.edit_original_response(embed=embed)

        elif member is not None or member != interaction.user:
            embed = discord.Embed(color=discord.Color.blue(), description=f"{self.bot.config.LOADING} Processing submission...")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed)

            post = {
                "guild_id": interaction.guild_id,
                "author_id": member.id,
                "title": game_attrs["title"],
                "link": link
            }
            self.db.insert_one(post)

            embed.description = f"{interaction.user.mention}, the game **{game_attrs['title']}** was submitted successfully."
            embed.set_thumbnail(url=game_attrs["image_url"])
            embed.set_footer(text=f"Submitted for {member}", icon_url=member.avatar.url)
            await interaction.edit_original_response(embed=embed)


    @submissions_group.command(name="unsubmit", description="Unsubmits your game from the database")
    @app_commands.describe(link="Your game's link, you can get this by sharing your game in Fancade.")
    async def unsubmit_command(self, interaction: discord.Interaction, link: str):

        if not re.match("https://play.fancade.com/[0-9A-Z]{16}", link):
            await self.helper.send_error_message(interaction, "Sorry, but I don't recognize that link.")
            return None

        can_manage_guild = interaction.user.guild_permissions.manage_guild
        query = self.db.find_one({"guild_id": interaction.guild_id, "link": link})

        if query is None:
            await self.helper.send_error_message(interaction, "Sorry, but I can't find that game in the database.")
            return None

        author = await interaction.guild.fetch_member(query["author_id"])
        view = Confirm(interaction.user)

        if author.id != interaction.user.id:
            if not can_manage_guild:
                await self.helper.send_error_message(interaction, "Sorry, but you can't unsubmit another member's submission since you're missing `Manage Server` permission.")
                return None

            embed = discord.Embed(
                color=discord.Color.orange(),
                description=f"This will delete the submission **{query['title']}** which was submitted by **{author}**. Are you sure you wanna proceed?"
            )
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, view=view)

            await self.handle_unsubmit_confirm_view(interaction, view, {"guild_id": interaction.guild.id, "link": link}, query)

        if author.id == interaction.user.id:
            embed = discord.Embed(
                color=discord.Color.orange(),
                description=f"This will delete your submission **{query['title']}**. Are you sure you wanna proceed?"
            )
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, view=view)

            await self.handle_unsubmit_confirm_view(interaction, view, {"guild_id": interaction.guild.id, "link": link}, query)

    @unsubmit_command.autocomplete('link')
    async def unsubmit_autocomplete(self, interaction: discord.Interaction, input: str) -> List[app_commands.Choice[str]]:
        results = self.db.find({"title": {"$regex" : input}})
        return [discord.app_commands.Choice(name=result["title"], value=result["link"]) for result in results]

    @submissions_group.command(name="show", description="Shows your (or another person's) submissions.")
    @app_commands.describe(
        member="The member you want to show the submissions of.",
        all="This will show everyone's submissions."
    )
    async def show_submissions_command(self, interaction: discord.Interaction, member: discord.Member = None, all: bool = False):
        if all:
            post = {"guild_id": interaction.guild.id}
            no_submission_text = "Hmm, it seems like nobody has submitted anything yet."
            show_all = True
            user = None

        elif member is None or member == interaction.user:
            post = {"guild_id": interaction.guild.id, "author_id": interaction.user.id}
            no_submission_text = "You haven't submitted anything yet."
            show_all = False
            user = interaction.user

        elif member is not None or member != interaction.user:
            post = {"guild_id": interaction.guild.id, "author_id": member.id}
            no_submission_text = f"**{member}** hasn't submitted anything yet."
            show_all = False
            user = member

        query = self.db.find(post)
        query = list(query)
        query.sort(key=lambda x: x["author_id"])

        if not query:
            await self.helper.send_error_message(interaction, no_submission_text)
            return None

        embed = discord.Embed(color=discord.Color.blue(), description=f"{self.bot.config.LOADING} Loading submissions...")
        embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed)

        embeds = await self.helper.create_submissions_embed(interaction, query, user, show_all)
        paginator = EmbedPaginator(interaction, embeds, query)

        if paginator.max_pages > 1:
            paginator.next.disabled = False

        embed = embeds[0]
        embed.set_footer(text=f"Page {paginator.current_page + 1}/{paginator.max_pages} • Total amount of submissions: {len(query)}")
        await interaction.edit_original_response(embed=embed, view=paginator)
            

    @submissions_group.command(name="clear", description="Clears your (or another person's) submissions.")
    @app_commands.describe(
        member="The member you want to clear the submissions of. This requires Manage Server permission.",
        all="This will clear everyone's submissions. This requires Manage Server permission."
    )
    async def clear_submissions_command(self, interaction: discord.Interaction, member: discord.Member = None, all: bool = False):
        can_manage_guild = interaction.user.guild_permissions.manage_guild

        if all:
            post = {"guild_id": interaction.guild.id}
            no_submission_text = "Hmm, it seems like nobody has submitted anything yet."
            success_text = "All submissions have been deleted."
            confirm_text = "This will delete everyone's submissions. Are you sure you wanna proceed?"

            if not can_manage_guild:
                await self.helper.send_error_message(interaction, "Sorry, but you are missing `Manage Server` permission.")
                return None

        elif member is None or member == interaction.user:
            post = {"guild_id": interaction.guild.id, "author_id": interaction.user.id}
            no_submission_text = "You haven't submitted anything yet."
            success_text = "Deleted all of your submissions."
            confirm_text = "This will delete all of your submissions. Are you sure you wanna proceed?"

        elif member is not None or member != interaction.user:
            post = {"guild_id": interaction.guild.id, "author_id": member.id}
            no_submission_text = f"**{member}** hasn't submitted anything yet."
            success_text = f"Deleted all of **{member}**'s submissions."
            confirm_text = f"This will delete all of **{member}**'s submissions. Are you sure you wanna proceed?"

            if not can_manage_guild:
                await self.helper.send_error_message(interaction, "Sorry, but you are missing `Manage Server` permission.")
                return None

        query = self.db.find(post)
        query = list(query)
        if not query:
            await self.helper.send_error_message(interaction, no_submission_text)
            return None

        view = Confirm(interaction.user)

        embed = discord.Embed(
            color=discord.Color.orange(),
            description=confirm_text
        )
        embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed, view=view)

        await view.wait()
        if view.value is None:
            embed = discord.Embed(color=discord.Color.red(), description="You took too long to respond.")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.edit_original_response(embed=embed)

        elif view.value:
            embed = discord.Embed(color=discord.Color.blue(), description=f"{self.bot.config.LOADING} Deleting submissions...")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.edit_original_response(embed=embed, view=None)

            self.db.delete_many(post)

            embed.description = success_text
            embed.color = discord.Color.green()
            embed.set_footer(text=f"Deleted {len(query)} submissions.")
            await interaction.edit_original_response(embed=embed, view=None)

        else:
            embed = discord.Embed(color=discord.Color.red(), description="Command has been cancelled.")
            embed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
            await interaction.edit_original_response(embed=embed, view=None)
        

async def setup(bot: commands.Bot):
    await bot.add_cog(Submission(bot), guilds=[bot.config.TEST_GUILD_ID])
