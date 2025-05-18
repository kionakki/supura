import discord
from discord.ext import commands
import os
import random
from flask import Flask
import threading

# Flaskサーバーの準備（Renderで起動を維持する用）
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run).start()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

used_words = []
current_word = ""

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')

@bot.command()
async def start(ctx):
    global used_words, current_word
    used_words = []
    current_word = ""
    await ctx.send("しりとりを始めます！最初の言葉をどうぞ！")

@bot.event
async def on_message(message):
    global current_word, used_words

    if message.author.bot:
        return

    await bot.process_commands(message)

    if not current_word:
        word = message.content.strip()
        if word in used_words:
            await message.channel.send("その言葉はすでに使われました！")
            return
        if word[-1] == "ん":
            await message.channel.send("「ん」で終わったのであなたの負けです！")
            return
        current_word = word
        used_words.append(word)
        await message.channel.send(f"了解！じゃあ「{word[-1]}」で始まる言葉は…")
        await send_bot_word(message)
    else:
        word = message.content.strip()
        if word in used_words:
            await message.channel.send("その言葉はすでに使われました！")
            return
        if word[0] != current_word[-1]:
            await message.channel.send(f"「{current_word[-1]}」で始まる言葉を入力してください！")
            return
        if word[-1] == "ん":
            await message.channel.send("「ん」で終わったのであなたの負けです！")
            return
        current_word = word
        used_words.append(word)
        await message.channel.send(f"なるほど！じゃあ「{word[-1]}」で始まる言葉は…")
        await send_bot_word(message)

async def send_bot_word(message):
    global current_word, used_words
    # 仮の単語リスト（辞書としては小さいです）
    word_list = ["りんご", "ごりら", "らっぱ", "ぱんだ", "だるま", "まくら", "らいおん", "んま", "まんが"]
    
    candidates = [w for w in word_list if w[0] == current_word[-1] and w not in used_words]

    if not candidates:
        await message.channel.send("うーん…思いつきません！あなたの勝ちです！")
        current_word = ""
        used_words = []
        return

    bot_word = random.choice(candidates)
    used_words.append(bot_word)
    current_word = bot_word
    await message.channel.send(f"「{bot_word}」！次は「{bot_word[-1]}」です！")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)