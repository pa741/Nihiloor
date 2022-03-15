import asyncio
import random

import discord
import youtube_dl
from discord import File

from Music import YoutubeSource
from VoiceServer import Voice


class Bot:
    __slots__ = ("voice", "music", "playerMessage", "guild", "mysql")

    def __init__(self, guild, con):
        self.guild = guild
        self.mysql = con

        self.playerMessage = None
        self.music = None
        self.voice = None

    async def runcommand(self, message):
        print(message.content)
        command = message.content.split(" ")[0][1:]
        params = message.content[message.content.find(" "):].strip()
        # comandos:
        match command.lower():

            case "join":
                await self.joinVC(message.author.id, message)

            case "stop":
                await self.leaveVC(message)
            case "leave":
                await self.leaveVC(message)
            case "startvc":  # Comando que comienza el servicio de voz en el server.
                if self.voice is None:
                    self.voice = Voice(message, self)
                    self.mysql.setuser(message.author.id, message.author.name)
                await message.author.send(content="Descarga este archivo si no lo tienes")
                await message.author.send(file=File(fp=open("VoiceClient.py", "rb"), filename="VoiceClient.py"))
                await message.author.send(
                    content="Ahora ejecuta este comando en la cmd (asegurate estar en la ruta del archivo)")
                await message.author.send(content=f"```python VoiceClient.py {self.guild.id} {message.author.id}```")

            case "restartvc":
                # Comando para crear otro objecto de voz
                self.voice = Voice(message, self)

            case "echo":
                await message.reply(params)

            case "sound":
                if self.music is None:
                    await message.channel.send("Playing" + params)
                    self.playSound(params.strip())

            case "play":  # No playlist support yet
                await self.play(params, message.author.id, message)
            case "skip":
                self.skip(message.author.id)
            case "prev":
                await self.previous()
            case "loop":
                self.loop()
            case "shuffle":
                await self.shuffle()
            case "pause":
                self.playPause()
            case "clear":
                self.clear()
            case "queue":
                await self.queue(message)

    async def leaveVC(self, message=None):
        voice = self.guild.voice_client
        if voice is not None:
            await voice.disconnect()
        elif message is not None:
            await message.reply("No estoy connectado a ningun canal")

    async def joinVC(self, userid, message=None):

        voice = self.guild.voice_client
        if voice is None:
            if message is not None:
                voice = message.author.voice
                if voice is not None:
                    await voice.channel.connect()
            else:
                for v in self.guild.voice_channels:
                    for m in v.members:
                        print(m.id)
                        print(userid)
                        if m.id == userid:
                            await v.connect()
                            return

    def playSound(self, sound):
        vc = self.guild.voice_client
        vc.play(discord.FFmpegPCMAudio("sounds/" + sound + ".mp3"), after=lambda e: print('done', e))

    async def play(self, search, userid, message=None):
        username = None
        await self.joinVC(userid, message=message)
        if not search:  # Si el mensaje no tiene contenido, se despausa el reproductor
            self.playPause(playOnly=True)

        try:
            if message is not None:
                async with message.channel.typing():
                    data = YoutubeSource.get_data(search)
                username = message.author.name
            else:
                data = YoutubeSource.get_data(search)
        except youtube_dl.DownloadError:
            print("Error de descarga")
        length = 0
        if "entries" in data:
            for entry in data['entries']:  # Por cada cancion encontrada (en caso de playlist abra mas de 1)
                await self.music.queue.put(entry)  # se añaden a la cola
                print(f"{entry['title']} ha sido añadido a la cola")
                self.mysql.playSong(entry['id'], entry['title'], entry['webpage_url'], entry['duration'], self.guild.id,
                                    self.guild.name, userid, username)
            # Informacion para mostrar por el canal de texto

            length = len(data['entries'])
            data = data['entries'][0]


        else:  # Si se introduce una cancion directa desde una url data no tiene entries.
            await self.music.queue.put(data)
            self.mysql.playSong(data['id'], data['title'], data['webpage_url'], data['duration'], self.guild.id,
                                self.guild.name, userid, username)
        # Mostrar la cancion añadida por el canal de texto:
        if message is not None:
            embed = await embedSong(data, message)
            if length > 1:
                embed.set_footer(text=f"y {length - 1} cancion(es) mas han sido añadidas")
            await message.channel.send(embed=embed)

    async def queue(self, message):
        if not self.music.queue.empty():
            embed = discord.Embed(title="Cargando...")
            msg = await message.channel.send(embed=embed)
            await self.addPlayer(msg)
            await self.updatePlayer(self.music.current)
        else:
            message.channel.send("No hay canciones en la fila")

    async def shuffle(self):
        if self.music.queue.qsize() > 1:
            random.shuffle(self.music.queue._queue)
            await self.updatePlayer(self.music.current)

    def skip(self, userid):
        if self.music is not None:
            voice = self.guild.voice_client
            if voice is not None:
                current = self.music.current
                if current is not None:
                    self.mysql.skipSong(current['id'], self.guild.id, userid)
                voice.stop()

    async def previous(self):
        if self.music is not None:
            self.music.queue._queue.appendleft(self.music.current)
            lastsong = self.music.queue._queue.pop()
            self.music.queue._queue.appendleft(lastsong)
            voice = self.guild.voice_client
            if voice is not None:
                voice.stop()
            if self.music.looping:
                self.music.current = None

    def clear(self):
        if self.music is not None:
            self.music.queue = asyncio.Queue()

    def playPause(self, playOnly=False):
        if self.music is not None:
            voice = self.guild.voice_client

            if voice is not None:
                if voice.is_paused():
                    voice.resume()
                elif playOnly is False:
                    voice.pause()

    def loop(self):
        if self.music is not None:
            if self.music.looping:
                self.music.looping = False
            else:
                self.music.looping = True

    async def addPlayer(self, message):
        if self.playerMessage is not None:
            await self.playerMessage.delete()
        await message.add_reaction("❌")
        await message.add_reaction("⏮")
        await message.add_reaction("⏯")
        await message.add_reaction("⏭")
        await message.add_reaction("🔀")
        await message.add_reaction("🔁")
        self.playerMessage = message

    async def updatePlayer(self, current):
        if self.playerMessage is not None:
            songs = 0
            description = ""
            for song in self.music.queue._queue:
                description = f"{description}\n{song['title'][:50]}"
                songs = songs + 1
                if songs > 10:
                    break

            embed = discord.Embed(title=current['title'], description=description, url=current['webpage_url'],
                                  colour=discord.Color.green())
            embed.set_thumbnail(url=current['thumbnail'])
            restantes = len(self.music.queue._queue) - songs

            if restantes > 0:
                embed.set_footer(text=f"Y {restantes} canciones mas")
            await self.playerMessage.edit(embed=embed)

    async def cleanup(self):
        # Metodo necesario para el funcionamiento de el reproductor. Ya que el loop comienza en el constructor.
        print("cleanup started")
        self.music = None
        await self.leaveVC()


async def embedSong(entry, message):
    embed = discord.Embed(title=entry['title'], url=entry['webpage_url'],
                          colour=discord.Color.green())
    embed.set_thumbnail(url=entry['thumbnail'])
    embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
    return embed
