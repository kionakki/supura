import discord
from discord.ext import tasks, commands
import requests
import os
from datetime import datetime
import pytz
from flask import Flask
import threading

app = Flask("")


@app.route("/")
def home():
    return "Bot is alive!"


def run():
    app.run(host="0.0.0.0", port=8080)


# Flaskサーバーを別スレッドで起動
threading.Thread(target=run).start()


TOKEN = os.getenv("DISCODE_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ▼ あなたのサーバーのチャンネルIDに書き換えてください
CHANNELS = {
    "regular": 1373329458655662173,  # ナワバリバトル
    "bankara_challenge": 1373335594096132247,  # バンカラ チャレンジ
    "bankara_open": 1373335766658449438,  # バンカラ オープン
    "xmatch": 1373335891040276680,  # Xマッチ
    "event": 1373335946082386052,  # イベントマッチ
    "coop": 1373335963782086806,  # サーモンラン
}

JST = pytz.timezone("Asia/Tokyo")


def convert_time(utc_str):
    utc_time = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    jst_time = utc_time.astimezone(JST)
    return jst_time.strftime("%m/%d %H:%M")


def make_embed(mode_name, schedule, is_coop=False):
    start = convert_time(schedule["start_time"])
    end = convert_time(schedule["end_time"])

    if is_coop:
        stage = schedule["stage"]["name"]
        weapon_names = [w["name"] for w in schedule["weapons"]]
        embed = discord.Embed(
            title=f"{mode_name}", description=f"🕒 {start} ～ {end}（JST）", color=discord.Color.orange()
        )
        embed.add_field(name="ステージ", value=stage, inline=False)
        embed.add_field(name="支給ブキ", value="\n".join(weapon_names), inline=False)
        if schedule["stage"]["image"]:
            embed.set_image(url=schedule["stage"]["image"])
        return embed

    rule = schedule["rule"]["name"]
    stage1 = schedule["stage"]["name"]
    stage2 = schedule["stage2"]["name"]
    image_url = schedule["stage"]["image"]

    embed = discord.Embed(
        title=f"{mode_name} - {rule}", description=f"🕒 {start} ～ {end}（JST）", color=discord.Color.blue()
    )
    embed.add_field(name="ステージ①", value=stage1, inline=True)
    embed.add_field(name="ステージ②", value=stage2, inline=True)
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text="スケジュールは2時間ごとに更新されます")
    return embed


def fetch_schedules():
    res = requests.get("https://spla3.yuu26.com/api/schedules")
    coop = requests.get("https://spla3.yuu26.com/api/coop/schedules")

    return res.json(), coop.json()


@tasks.loop(hours=2)
async def send_schedules():
    data, coop_data = fetch_schedules()

    schedules = {
        "regular": data["regular"][0],
        "bankara_challenge": data["bankara_challenge"][0],
        "bankara_open": data["bankara_open"][0],
        "xmatch": data["xmatch"][0],
        "event": data["event"][0],
    }

    for key, schedule in schedules.items():
        embed = make_embed(key.replace("_", " ").title(), schedule)
        channel_id = CHANNELS.get(key)
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    # サーモンランも送信
    coop_schedule = coop_data["schedules"][0]
    coop_embed = make_embed("サーモンラン", coop_schedule, is_coop=True)
    coop_channel = bot.get_channel(CHANNELS["coop"])
    if coop_channel:
        await coop_channel.send(embed=coop_embed, allowed_mentions=discord.AllowedMentions.none())


@bot.event
async def on_ready():
    print(f"{bot.user} でログインしました")
    send_schedules.start()


bot.run(TOKEN)
