import os
import json
import time
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# ---------- Setup ----------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "."
PAGE_SIZE = 10
BRAND = "by AFG"

if not TOKEN:
    raise SystemExit("ERROR: DISCORD_TOKEN missing in .env")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
START_TIME = time.time()

# ---------- Load index ----------
try:
    with open("files.json", "r", encoding="utf-8") as f:
        FILES = json.load(f)
except FileNotFoundError:
    raise SystemExit("ERROR: files.json not found.")

print(f"[+] Loaded {len(FILES)} files into index.")


# ---------- Search ----------
def search_files(query: str):
    q = query.lower().strip()
    if not q:
        return []
    return [f for f in FILES if q in f.get("name", "").lower()]


def chunk_pages(items, size=PAGE_SIZE):
    for i in range(0, len(items), size):
        yield items[i:i + size]


# ---------- Formatting ----------
def build_embed(query, results, page=0):
    pages = list(chunk_pages(results))
    total_pages = max(1, len(pages))
    page = max(0, min(page, total_pages - 1))
    slice_ = pages[page] if pages else []

    embed = discord.Embed(title=f"🔎 Results for: {query}", color=0x5865F2)
    embed.set_author(name=BRAND)

    if not slice_:
        embed.description = "❌ nothing found, L"
        embed.set_footer(text=f"{BRAND} • Page 0/0")
        return embed, page, total_pages

    lines = []
    for i, item in enumerate(slice_, start=page * PAGE_SIZE + 1):
        name = item.get("name", "unknown")
        url = item.get("url", "")
        size = item.get("size", "?")
        display = name if len(name) <= 60 else name[:57] + "..."
        lines.append(f"`{i:>2}.` [{display}]({url}) — `{size}`")

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"{BRAND} • Page {page + 1}/{total_pages} • {len(results)} total")
    return embed, page, total_pages


def format_uptime(seconds):
    seconds = int(seconds)
    d, seconds = divmod(seconds, 86400)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def build_status_embed():
    total_members = sum(g.member_count or 0 for g in bot.guilds)

    embed = discord.Embed(title="📊 Bot Status", color=0x57F287)
    embed.set_author(name=BRAND)
    embed.add_field(name="🏓 Latency", value=f"`{round(bot.latency * 1000)} ms`", inline=True)
    embed.add_field(name="🌐 Servers", value=f"`{len(bot.guilds)}`", inline=True)
    embed.add_field(name="👥 Members", value=f"`{total_members:,}`", inline=True)
    embed.add_field(name="📁 Files", value=f"`{len(FILES):,}`", inline=True)
    embed.add_field(name="⏱️ Uptime", value=f"`{format_uptime(time.time() - START_TIME)}`", inline=True)
    embed.add_field(name="🤖 User", value=f"`{bot.user}`", inline=True)
    embed.set_footer(text=f"{BRAND} • online")
    return embed


def build_files_embed():
    embed = discord.Embed(
        title="📁 File Index",
        description=f"This bot currently has **`{len(FILES):,}`** files indexed.",
        color=0xFEE75C,
    )
    embed.set_author(name=BRAND)
    embed.add_field(name="🔎 Search", value="`/find <query>` or `.find <query>`", inline=False)
    embed.set_footer(text=f"{BRAND} • {len(bot.guilds)} servers")
    return embed


# ---------- Pagination View ----------
class PagerView(discord.ui.View):
    def __init__(self, query, results, author_id):
        super().__init__(timeout=120)
        self.query = query
        self.results = results
        self.page = 0
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        _, _, total_pages = build_embed(self.query, self.results, self.page)
        self.prev_btn.disabled = self.page <= 0
        self.next_btn.disabled = self.page >= total_pages - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Not your search, run your own `/find`.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.update_buttons()
        embed, _, _ = build_embed(self.query, self.results, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.update_buttons()
        embed, _, _ = build_embed(self.query, self.results, self.page)
        await interaction.response.edit_message(embed=embed, view=self)


# ---------- Events ----------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"[+] Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"[!] Slash sync failed: {e}")

    await update_presence()
    print(f"[+] Logged in as {bot.user} (ID: {bot.user.id}) — {BRAND}")
    print(f"[+] Serving {len(bot.guilds)} servers.")


async def update_presence():
    """Watching: number of servers the bot is in."""
    server_count = len(bot.guilds)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{server_count} server{'s' if server_count != 1 else ''}"
        )
    )


@bot.event
async def on_guild_join(guild):
    await update_presence()


@bot.event
async def on_guild_remove(guild):
    await update_presence()


# ---------- Prefix command: .find ----------
@bot.command(name="find")
async def find_prefix(ctx: commands.Context, *, query: str = None):
    if not query:
        await ctx.reply(f"Usage: `.find <query>`  {BRAND}")
        return
    results = search_files(query)
    embed, _, total = build_embed(query, results, 0)
    if total <= 1:
        await ctx.reply(embed=embed)
    else:
        view = PagerView(query, results, ctx.author.id)
        await ctx.reply(embed=embed, view=view)


# ---------- Prefix command: .status ----------
@bot.command(name="status")
async def status_prefix(ctx: commands.Context):
    await ctx.reply(embed=build_status_embed())


# ---------- Prefix command: .files (aliases: .howmanyfiles, .allfiles) ----------
@bot.command(name="files", aliases=["howmanyfiles", "allfiles", "total"])
async def files_prefix(ctx: commands.Context):
    await ctx.reply(embed=build_files_embed())


# ---------- Slash command: /find ----------
@bot.tree.command(name="find", description="Find files by name — by AFG")
@app_commands.describe(query="Search term, e.g. lagger")
async def find_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = search_files(query)
    embed, _, total = build_embed(query, results, 0)
    if total <= 1:
        await interaction.followup.send(embed=embed)
    else:
        view = PagerView(query, results, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)


# ---------- Slash command: /status ----------
@bot.tree.command(name="status", description="Show bot status — by AFG")
async def status_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    await interaction.followup.send(embed=build_status_embed())


# ---------- Slash command: /files ----------
@bot.tree.command(name="files", description="Show how many files are indexed — by AFG")
async def files_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    await interaction.followup.send(embed=build_files_embed())


# ---------- Run ----------
if __name__ == "__main__":
    bot.run(TOKEN)
