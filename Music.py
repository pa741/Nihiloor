import asyncio

import discord
import youtube_dl
from async_timeout import timeout

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'yesplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YoutubeSource(discord.PCMVolumeTransformer):
    # Clase que almacena el audio y informacion sobre el mismo, como titulo y requester
    # __slots__ = ("requester, title, duration, webpageurl")

    def __init__(self, source):
        super().__init__(source)  # Envia el AudioSource al constructor de la superclase

    @classmethod
    def get_data(cls, search: str):
        # Tarda mucho en sacar la informacion, usar lo minimo posible y cuando se lanze el comando,
        # volver a lanzar si la reproduccion del video da error
        data = ytdl.extract_info(search, download=False)

        return data

    @classmethod
    def create_source(cls, data):
        # Devuelve YoutubeSource desde la url pasada por data, esto lo convierte en audio.
        return cls(discord.FFmpegPCMAudio(data['url']))


class MusicPlayer:
    # clase que reproduce las canciones y tiene la queue de canciones.

    # Se destruye cuando no hay canciones que poner.
    # Se crea con un get_player que duelve el player si esxiste y si no lo crea
    #
    __slots__ = ("loop", "queue", "playing", "looping", "current", "bot")

    def __init__(self, bot):

        self.loop = asyncio.get_running_loop()  # Es posible que necesite el de disc.
        self.queue = asyncio.Queue()
        self.playing = asyncio.Event()
        self.looping = False
        self.bot = bot
        self.current = None

        self.loop.create_task(self.player_loop())

    async def player_loop(self):

        while True:
            self.playing.clear()  # Establece el evento como empezado.
            # Espera 10 segundos hasta que la fila tenga otra cancion, si no tiene nada salta la excepcion y termina el while
            try:
                async with timeout(10):
                    data = await self.queue.get()
            except asyncio.TimeoutError:  # !!!!!!No me pilla la excepcion ???
                await self.destroy()  # Cuando no obtenga mas canciones de la fila se destruye el reproductor.
                return

            source = YoutubeSource.create_source(data)

            # Reproduce la cancion, y cambia el evento cuando a terminado
            self.bot.guild.voice_client.play(source, after=lambda e: self.playing.set())
            print("Teest")
            if self.looping:  # Si esta en modo bucle
                await self.queue.put(data)  # Vuelve a poner la cancion en la cola

            self.current = data
            await self.playing.wait()  # Espera a que termine la cancion

    # hace que se salga del canal lo cual llama a on_voice_state_change, que destruye el reproductor.
    async def destroy(self):
        # TODO
        # ver si seria rentable que no se rompiera
        await self.bot.guild.voice_client.disconnect()
