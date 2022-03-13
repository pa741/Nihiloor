import discord
import youtube_dl

from Music import YoutubeSource, MusicPlayer
from VoiceServer import Voice


class Bot:
    __slots__ = ("voices", "music", "guild", "mysql")

    def __init__(self, voices, guild):
        self.music = None
        # todo
        # sustituirlo con un unico objeto de voz.
        self.voices = voices
        self.guild = guild

    async def runcommand(self, message):
        print(message.content)
        command = message.content.split(" ")[0][1:]
        params = message.content[message.content.find(" "):]
        # comandos:
        match command.lower():

            case "join":
                await self.joinVC(message.author.id, message)

            case ("leave", "stop"):
                await self.leaveVC(message)

            case "startvc":  # Comando que comienza el servicio de voz en el server.
                serverid = self.guild.id
                if serverid not in self.voices:
                    self.voices[serverid] = Voice(message, self)
                await message.reply(f"{serverid}_{message.author.id}")

            case "restartvc":
                # Comando para crear otro objecto de voz
                self.voices[message.guild.id] = Voice(message)

            case "echo":
                await message.reply(params)

            case "sound":
                if self.music is None:
                    await message.channel.send("Playing" + params)
                    self.playSound(params.strip())

            case "play":  # No playlist support yet
                await self.play(params, message.author.id, message)
            case "skip":
                await self.skip()

            case "loop":
                if self.music:
                    self.music.looping = True

            case "queue":
                print(self.music.queue._queue)

    async def leaveVC(self, message=None):
        voice = self.guild.voice_client
        if voice is not None:
            await voice.disconnect()
        elif message is not None:
            await message.reply("No estoy connectado a ningun canal")

    async def joinVC(self, userid, message=None):
        print(userid)
        voice = self.guild.voice_client
        if voice is None:
            if message is not None:
                voice = message.author.voice
                if voice is not None:
                    await voice.channel.connect()
                await message.reply("No estas conectado ningun canal")
            else:
                for v in self.guild.voice_channels:
                    # El bot no detecta los miembros que lleban en un canal desde que el bot se inicio
                    # si se sale y se vuelve a entrar al canal se soluciona.
                    # todo
                    # buscar solucion a esto por que veo que causara problemas con startvoice
                    for m in v.members:
                        print(m.id)
                        print(userid)
                        if m.id == userid:
                            await v.connect()
                            return

        elif message is not None:
            await message.reply("Ya estoy en un canal")

    def playSound(self, sound):
        vc = self.guild.voice_client
        vc.play(discord.FFmpegPCMAudio("sounds/" + sound + ".mp3"), after=lambda e: print('done', e))

    async def play(self, search, userid, message=None):
        await self.joinVC(userid)
        # todo
        # meter este if en los eventos del cliente.
        if self.music is None:
            self.music = MusicPlayer(
                self)  # Solo hacerlo si sale bien! No puede estar este objeto creado si el bot no esta en un canal

        try:
            if message is not None:
                async with message.channel.typing():
                    data = YoutubeSource.get_data(search)
            else:
                data = YoutubeSource.get_data(search)
        except youtube_dl.DownloadError:
            print("Error de descarga")

        print(f"{data['title']} ha sido añadido a la cola")

        if "entries" in data:
            for entry in data['entries']:  # Por cada cancion encontrada (en caso de playlist abra mas de 1)
                await self.music.queue.put(entry)  # se añaden a la cola
            if message is not None:  # Como siempre el mensaje es opcional, (para añadir canciones por comados)
                entry = data['entries'][0]  # Cojemos la primera cancion

                embed = discord.Embed(title=entry['title'], url=entry['webpage_url'],
                                      colour=discord.Color.green())
                embed.set_thumbnail(url=entry['thumbnail'])
                embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                if len(data['entries']) > 1:
                    embed.set_footer(text=f"y {len(data['entries']) - 1} cancion(es) mas han sido añadidas")
                await message.channel.send(embed=embed)
                # TODO
                # Añadir contoles como reaccion del mensaje.

        else:  # Si se introduce una cancion directa desde una url data no tiene entries.
            await self.music.queue.put(data)

    async def skip(self):
        if self.music is not None:
            voice = self.guild.voice_client
            if voice:
                voice.stop()

    async def cleanup(self):
        # Metodo necesario para el funcionamiento de el reproductor. Ya que el loop comienza en el constructor.
        print("cleanup started")
        self.music = None
        await self.leaveVC()


def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    return start
