import asyncio
import json
import warnings

import discord
import websockets

from Bots import Bot
from VoiceServer import VServer
from VoiceServer import Voice

client = discord.Client()
# Juntar todos los diccionarios en uno creando un clase que contenga las otras como atributos
voiceDict = {}
botDict = {}

print(voiceDict)


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
            bot = Bot(voiceDict, message.guild)
            botDict[serverid] = bot
        await bot.runcommand(message)
    # BORRAR
    if message.content == "vtest":
        print(voiceDict)

@client.event
async def on_voice_state_update(member,before,after):
    if member == client.user:
        if after.channel is None:
            bot = botDict[member.guild.id]
            await bot.cleanup()

    print(member)
        #Si el canal esta vacio

#Considerar un on client leave, destroy player aqui
server = websockets.serve(VServer(voiceDict).response, "", '8800', ping_interval=None)

asyncio.get_event_loop().run_until_complete(server)

with open("keys.json") as jsonFile:
    jsonObject = json.load(jsonFile)
    jsonFile.close()
client.run(jsonObject["devKey"])
