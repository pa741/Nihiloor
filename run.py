import asyncio
import json
import warnings

import discord
import websockets

from Bots import Bot
from VoiceServer import VServer
from Music import MusicPlayer

from dbConection import MySQL

client = discord.Client()
con = MySQL()
botDict = {}


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!"):
        serverid = message.guild.id
        if serverid in botDict:
            bot = botDict[serverid]
        else:
            bot = Bot(message.guild, con)
            botDict[serverid] = bot
        await bot.runcommand(message)


@client.event
# Crea y destruye el reproductor de musica segun entra o sale el bot
async def on_voice_state_update(member, before, after):
    if member == client.user and after is not None:
        bot = botDict[member.guild.id]
        if after.channel is None:
            await bot.cleanup()
        if before.channel is None and after.channel is not None:
            if bot.music is None:
                bot.music = MusicPlayer(bot)


@client.event
async def on_reaction_add(reaction, user):
    # Reproductor de emojis
    message = reaction.message
    print(str(reaction.emoji))
    bot = botDict[message.guild.id]
    # comprobar que los emojis se añaden al mensaje reproductor
    if not client.user == user and bot.playerMessage == message:
        match str(reaction.emoji):
            case "❌":
                await bot.cleanup()
                await message.delete()
            case "⏮":
                await bot.previous()
            case "⏭":
                bot.skip(user.id)
            # En caso del loop, si esta descativado el icono sera 🔁 sino sera el recuadro verde
            case ("🔁" | "🟩"):
                bot.loop()
                if bot.music.looping:
                    await message.add_reaction("🟩")
                    await reaction.clear()
            case "🟩":
                bot.loop()
                if not bot.music.looping:
                    await message.add_reaction("🔁")
                    await reaction.clear()
            case "⏯":
                bot.playPause()
            case "🔀":
                await bot.shuffle()

        await reaction.remove(user)


#Servidor de websockets
#Es a donde el cliente de voz envia los comandos.
server = websockets.serve(VServer(botDict).response, "", '8800', ping_interval=None)
asyncio.get_event_loop().run_until_complete(server)

#Aqui es donde guardo mis llaves de la API de discord
#Si estais usando el codigo podeis quitar esto y poner la vuestra
with open("keys.json") as jsonFile:
    jsonObject = json.load(jsonFile)
    jsonFile.close()

#Ejecucion del bot
client.run(jsonObject["devKey"])
