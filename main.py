import discord
from discord.ext import tasks
from discord import app_commands
import requests
import os
from datetime import datetime
import pytz
from flask import Flask
import threading

# Flask サーバー（Render対策）
app = Flask("")

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

# トークン
TOKEN = os.getenv("DISCORD_TOKEN")

# チャンネルID（自分のIDに置き換える）
CHANNELS = {
    "regular": 1373329458655662173,
    "bankara_challenge": 1373335594096132247,
    "bankara_open": 1373335766658449438,
    "xmatch": 1373335891040276680,
    "event": 1373335946082386052,
    "coop": 1373335963782086806,
}

# タイムゾーン設定
JST = pytz.timezone("Asia/Tokyo")

def convert_time(utc_str):
    utc_time = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    jst_time = utc_time.astimezone(JST)
    return jst_time.strftime("%m/%d %H:%M")

# Embed作成関数
def make_embed(mode_name, schedule, is_coop=False):
    start = convert_time(schedule["start_time"])
    end = convert_time(schedule["end_time"])

    if is_coop:
        stage = schedule["stage"]["name"]
        weapon_names = [w["name"] for w in schedule["weapons"]]
        embed = discord.Embed(
            title=f"{mode_name}",
            description=f"🕒 {start} ～ {end}（JST）",
            color=discord.Color.orange()
        )
        embed.add_field(name="ステージ", value=stage, inline=False)
        embed.add_field(name="支給ブキ", value="\n".join(weapon_names), inline=False)
        if schedule["stage"].get("image"):
            embed.set_image(url=schedule["stage"]["image"])
        return embed

    rule = schedule["rule"]["name"]
    stage1 = schedule["stage"]["name"]
    stage2 = schedule["stage2"]["name"]
    image_url = schedule["stage"].get("image")

    embed = discord.Embed(
        title=f"{mode_name} - {rule}",
        description=f"🕒 {start} ～ {end}（JST）",
        color=discord.Color.blue()
    )
    embed.add_field(name="ステージ①", value=stage1, inline=True)
    embed.add_field(name="ステージ②", value=stage2, inline=True)
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text="スケジュールは2時間ごとに更新されます")
    return embed

# スケジュール取得関数
def fetch_schedules():
    try:
        res = requests.get("https://splatoon3.ink/data/schedules.json")
        coop = requests.get("https://splatoon3.ink/data/coop.json")
        data = res.json()
        coop_data = coop.json()
        return data, coop_data
    except Exception as e:
        print(f"スケジュール取得エラー: {e}")
        return {}, {}

# Bot定義（スラッシュコマンド対応）
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 起動時
@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} でログインしました")
    send_schedules.start()
    await send_schedules()  # 起動時に1回送信

# 自動送信ループ
@tasks.loop(hours=2)
async def send_schedules():
    data, coop_data = fetch_schedules()

    schedules = {
        "regular": data.get("regular", [{}])[0],
        "bankara_challenge": data.get("bankara_challenge", [{}])[0],
        "bankara_open": data.get("bankara_open", [{}])[0],
        "xmatch": data.get("xmatch", [{}])[0],
        "event": data.get("event", [{}])[0],
    }

    for key, schedule in schedules.items():
        if "start_time" in schedule:
            embed = make_embed(key.replace("_", " ").title(), schedule)
            channel_id = CHANNELS.get(key)
            try:
                channel = await bot.fetch_channel(channel_id)
                await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                print(f"✅ {key} スケジュール送信成功")
            except Exception as e:
                print(f"❌ {key} スケジュール送信失敗: {e}")

    coop_schedule = coop_data.get("schedules", [{}])[0]
    if "start_time" in coop_schedule:
        coop_embed = make_embed("サーモンラン", coop_schedule, is_coop=True)
        coop_channel_id = CHANNELS.get("coop")
        try:
            coop_channel = await bot.fetch_channel(coop_channel_id)
            await coop_channel.send(embed=coop_embed, allowed_mentions=discord.AllowedMentions.none())
            print("✅ サーモンラン スケジュール送信成功")
        except Exception as e:
            print(f"❌ サーモンラン スケジュール送信失敗: {e}")

# スラッシュコマンド：手動でスケジュールを取得
@tree.command(name="schedule", description="今のスプラトゥーン3スケジュールを表示")
async def schedule_command(interaction: discord.Interaction):
    await interaction.response.defer()
    data, coop_data = fetch_schedules()

    schedules = {
        "regular": data.get("regular", [{}])[0],
        "bankara_challenge": data.get("bankara_challenge", [{}])[0],
        "bankara_open": data.get("bankara_open", [{}])[0],
        "xmatch": data.get("xmatch", [{}])[0],
        "event": data.get("event", [{}])[0],
    }

    for key, schedule in schedules.items():
        if "start_time" in schedule:
            embed = make_embed(key.replace("_", " ").title(), schedule)
            await interaction.followup.send(embed=embed)

    coop_schedule = coop_data.get("schedules", [{}])[0]
    if "start_time" in coop_schedule:
        coop_embed = make_embed("サーモンラン", coop_schedule, is_coop=True)
        await interaction.followup.send(embed=coop_embed)

# Bot起動
bot.run(TOKEN)