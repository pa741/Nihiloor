import asyncio

import discord
import youtube_dl
from async_timeout import timeout

# '%(extractor)s-%(id)s-%(title)s.%(ext)s',
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(id)s-%(title)s.%(ext)s',
    'noplaylist': True, # si un video contiene tambien info de playlist añade solo el video.
    'ignoreerrors': False,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    'cachedir': False  # En teoria deveria evitar errores 403 Forbidden
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YoutubeSource(discord.PCMVolumeTransformer):
    # Clase que almacena el audio y informacion sobre el mismo, como titulo y requester

    # __slots__ = ("requester, title, duration, webpageurl")
    # Por si acabo haciendo que la fila sea de YTSource en lugar de data extraida de YTDL

    def __init__(self, source):
        super().__init__(source)  # Envia el AudioSource al constructor de la superclase

    @classmethod
    def get_data(cls, search: str):
        print("get data")
        # Tarda mucho en sacar la informacion, usar lo minimo posible y cuando se lanze el comando,
        data = ytdl.extract_info(url=search, download=False)

        return data

    @classmethod
    def create_source(cls, data):
        # Devuelve YoutubeSource desde la url pasada por data, esto lo convierte en audio.
        print(f"create source for {data['title']}")
        return cls(discord.FFmpegPCMAudio(data['url']))


class MusicPlayer:
    # clase que reproduce las canciones y tiene la queue de canciones.

    # Se destruye cuando no hay canciones que poner.
    # Se crea con un get_player que duelve el player si esxiste y si no lo crea
    #
    __slots__ = ("loop", "queue", "playing", "looping", "current", "bot")

    def __init__(self, bot):

        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue()
        self.playing = asyncio.Event()
        self.looping = False
        self.bot = bot
        self.current = None

        self.loop.create_task(self.player_loop())

    async def player_loop(self):
        # MESSAGE ERROR 404 en playerMessage no enonctrado

        while True:
            self.playing.clear()  # Establece el evento como empezado.
            # Espera 60 segundos hasta que la fila tenga otra cancion, si no tiene nada salta la excepcion y termina el while
            try:
                async with timeout(60):
                    data = await self.queue.get()
            except asyncio.TimeoutError:
                await self.destroy()  # Cuando no obtenga mas canciones de la fila se destruye el reproductor.
                return

            # Igual es mejor que la fila se de esto para no tener que cargarlo en medio del loop
            source = YoutubeSource.create_source(data)
            self.current = data


            # Reproduce la cancion, y cambia el evento cuando a terminado
            self.bot.guild.voice_client.play(source, after=lambda e: self.playing.set())

            try : #Posiblemente inecesario falta testear en condiciones
                await self.bot.updatePlayer(current=self.current)
            except Exception:
                print("Algo salio mal actualizando el reproductor")

            await self.playing.wait()  # Espera a que termine la cancion

            if self.looping:  # Si esta en modo bucle
                if self.current is not None: # Reproducir la cancion anterior hace esto para que no se dupliquen canciones
                    await self.queue.put(self.current)  # Vuelve a poner la cancion en la cola

    # hace que se salga del canal lo cual llama a on_voice_state_change, que destruye el reproductor.
    async def destroy(self):
        await self.bot.guild.voice_client.disconnect()
