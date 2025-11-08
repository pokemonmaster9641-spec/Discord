start
import discord
from discord import app_commands
from discord.ui import Button, View
import json
import asyncio
from datetime import datetime, time, timedelta
from keep_alive import keep_alive

BOT_TOKEN = "MTQzNjc1OTEzNDE2NTc5NDgzNg.GHQIjz.HgCc4C_1xF5KkCZfoF5s7GZ_H4ZKLo2qtbeaJU"
BANK_CHANNEL_ID = 1436752464677175489
OWNER_ID = 1427580708830052412
DATA_FILE = "data.json"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": {}, "panel_message_id": None}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_user_balance(user_id):
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {"skellys": 0, "money": 0}
        save_data(data)
    return data["users"][user_id_str]

def set_user_balance(user_id, skellys, money):
    data = load_data()
    user_id_str = str(user_id)
    data["users"][user_id_str] = {"skellys": skellys, "money": money}
    save_data(data)

async def get_or_create_category(guild, category_name):
    category = discord.utils.get(guild.categories, name=category_name)
    if category is None:
        category = await guild.create_category(category_name)
    return category

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Only the owner can close tickets!", ephemeral=True)
            return
        
        await interaction.response.send_message("🔒 Closing ticket...", ephemeral=True)
        await interaction.channel.delete()

class BankPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Bank", emoji="🏦", style=discord.ButtonStyle.primary, custom_id="bank_button")
    async def bank_button(self, interaction: discord.Interaction, button: Button):
        balance = get_user_balance(interaction.user.id)
        embed = discord.Embed(
            title=f"🏦 {interaction.user.name}'s Bank Balance",
            description=f"**Skellys:** {balance['skellys']:,}\n**Money:** ${balance['money']:,}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Deposit", emoji="➕", style=discord.ButtonStyle.success, custom_id="deposit_button")
    async def deposit_button(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        owner = guild.get_member(OWNER_ID)
        
        category = await get_or_create_category(guild, "Deposits")
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        ticket_channel = await guild.create_text_channel(
            name=f"deposit-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title="💰 Deposit Ticket",
            description=f"{interaction.user.mention} has requested a deposit.\n\n<@{OWNER_ID}> can credit Skellys using `/setbalance`.",
            color=discord.Color.gold()
        )
        close_view = CloseTicketView()
        await ticket_channel.send(embed=embed, view=close_view)
        await interaction.response.send_message(f"✅ Deposit ticket created: {ticket_channel.mention}", ephemeral=True)
    
    @discord.ui.button(label="Withdraw", emoji="➖", style=discord.ButtonStyle.danger, custom_id="withdraw_button")
    async def withdraw_button(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        owner = guild.get_member(OWNER_ID)
        balance = get_user_balance(interaction.user.id)
        
        category = await get_or_create_category(guild, "Withdrawals")
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        ticket_channel = await guild.create_text_channel(
            name=f"withdraw-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title="💸 Withdrawal Request",
            description=f"{interaction.user.mention} has requested a withdrawal.\n\n**Current Balance:**\nSkellys: {balance['skellys']:,}\nMoney: ${balance['money']:,}\n\n<@{OWNER_ID}> will process your withdrawal.",
            color=discord.Color.orange()
        )
        close_view = CloseTicketView()
        await ticket_channel.send(embed=embed, view=close_view)
        await interaction.response.send_message(f"✅ Withdrawal ticket created: {ticket_channel.mention}", ephemeral=True)

async def post_bank_panel(channel):
    data = load_data()
    
    try:
        await channel.purge(limit=100)
    except:
        pass
    
    embed = discord.Embed(
        title="🏦 DonutSMP Bank",
        description="Welcome to the DonutSMP Bank!\n\n**Features:**\n🏦 **Bank** - Check your balance\n➕ **Deposit** - Request to deposit Skellys\n➖ **Withdraw** - Withdraw your money\n\n**Daily Payout:** 1 Skelly = $100,000/day",
        color=discord.Color.blue()
    )
    embed.set_footer(text="DonutSMP Banking System | v1.0")
    
    view = BankPanel()
    message = await channel.send(embed=embed, view=view)
    
    data["panel_message_id"] = message.id
    save_data(data)

@tree.command(name="setbalance", description="Set a user's balance (Owner only)")
@app_commands.describe(
    user="The user to set balance for",
    skellys="Amount of Skellys",
    money="Amount of money"
)
async def setbalance(interaction: discord.Interaction, user: discord.Member, skellys: int, money: int):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Only the owner can use this command!", ephemeral=True)
        return
    
    set_user_balance(user.id, skellys, money)
    embed = discord.Embed(
        title="✅ Balance Updated",
        description=f"**User:** {user.mention}\n**Skellys:** {skellys:,}\n**Money:** ${money:,}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="resetbank", description="Reset all bank data (Owner only)")
async def resetbank(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Only the owner can use this command!", ephemeral=True)
        return
    
    data = {"users": {}, "panel_message_id": None}
    save_data(data)
    
    embed = discord.Embed(
        title="🔄 Bank Reset",
        description="All bank data has been reset!",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

async def daily_payout():
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            now = datetime.now()
            target_time = datetime.combine(now.date(), time(0, 0))
            
            if now >= target_time:
                target_time = datetime.combine(now.date(), time(0, 0))
                target_time = target_time + timedelta(days=1)
            
            seconds_until_midnight = (target_time - now).total_seconds()
            print(f"Next payout scheduled for {target_time} (in {seconds_until_midnight/3600:.2f} hours)")
            await asyncio.sleep(seconds_until_midnight)
            
            data = load_data()
            payout_count = 0
            for user_id, balance in data["users"].items():
                skellys = balance["skellys"]
                payout = skellys * 100000
                balance["money"] += payout
                payout_count += 1
            
            save_data(data)
            print(f"Daily payout completed at {datetime.now()} - {payout_count} users paid")
        except Exception as e:
            print(f"Error in daily payout: {e}")
            await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    client.add_view(BankPanel())
    client.add_view(CloseTicketView())
    
    await tree.sync()
    print("Commands synced!")
    
    bank_channel = client.get_channel(BANK_CHANNEL_ID)
    if bank_channel:
        await post_bank_panel(bank_channel)
        print(f"Bank panel posted in channel {BANK_CHANNEL_ID}")
    else:
        print(f"Warning: Could not find channel {BANK_CHANNEL_ID}")
    
    client.loop.create_task(daily_payout())
    print("Daily payout task started!")

keep_alive()
client.run(BOT_TOKEN)

from keep_alive import keep_alive
keep_alive()

client.run(BOT_TOKEN)


