import asyncio
import itertools
import json
import queue
from functools import partial

import discord
import youtube_dl

import websockets
from discord.ext import commands
from random import shuffle
from async_timeout import timeout
from datetime import date

import mysql.connector

# Suppress noise about console usage from errors

youtube_dl.utils.bug_reports_message = lambda: ''

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

ffmpeg_options = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.data = data

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        self.duration = data.get('duration')

    def __getitem__(self, item):
        return self.__getattribute__(item)

    @classmethod
    async def get_data(cls, search: str, loop, download=False):
        print("get data")
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        return data

    @classmethod
    async def create_source(cls, ctx, data, *, download=False):
        print("-create source")

        # loop = loop or asyncio.get_event_loop()

        # OBTIENE LOS DATOS DE FORMA NO INTRUSIVA
        # to_run = partial(ytdl.extract_info, url=search, download=download)
        # data = await loop.run_in_executor(None, to_run)

        if download:
            source = ytdl.prepare_filename(data)
        else:

            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        print("-regather")
        """Used for preparing a stream, instead of downloading.
               Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']
        ytdl.cache.remove()
        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)
        # print(data)
        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


class MusicPlayer:
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume', 'looping', 'dbcon')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        self.looping = False
        self.dbcon = MySQL()

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(5):
                    source = await self.queue.get()
                    if self.looping:
                        await self.queue.put(source)
            except asyncio.TimeoutError:
                return self.destroy(self._guild)
            except Exception as e:
                print(f"Eerror de timeout:"
                      f'```css\n[{e}]\n```''')
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source
            print(self._guild)
            print(self._guild.voice_client)
            # print(source)

            try:
                self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
                embed = discord.Embed(title="Now playing", description=f"[{source.title}]({source.web_url})",
                                      colour=discord.Color.green())
                self.np = await self._channel.send(embed=embed)
                dbcon = self.dbcon
                print(f"{self._guild.id} {self._guild.name}")
                dbcon.playSong(source.data['id'], source.title, source.web_url, source.data['duration'], self._guild.id,
                               self._guild.name, source.requester.id, source.requester.name)

                await self.next.wait()
            except discord.errors.ClientException as e:
                print(f'There was an error processing your song.\n'
                      f'```css\n[{e}]\n```')

            source.cleanup()
            self.current = None

    def destroy(self, guild):

        return self.bot.loop.create_task(self._cog.cleanup(guild))


playerw = None
loopw = None
ctxw = None
vcw = None


async def response(websocket, path):
    # AVERIGUAR SI EL CLIENTE PUEDE ENVIAR LA ID DEL USUARIO PARA MULTIUSUARIO
    message = await websocket.recv()
    print(f"[ws server] message  < {message}")
    answer = f"[{message}]"
    command = message.split()[0]
    if (command == "play"):
        await playw(message.split(' ', 1)[1])
    if (command == "pause"):
        await pausew()
    if (command == "skip"):
        await skipw()
    if (command == "silence"):
        await callate(message.split(' ', 1)[1])
    if (command == "unsilence"):
        await descallate(message.split(' ', 1)[1])
    if (command == "stop"):
        await stop()
    if (command == "kick"):
        await kickw(message.split(' ', 1)[1])
    if (command == "clear"):
        await clear()
    if (command == "liked"):
        await playFavW()
    if (command == "best"):
        await playBestW()
    if (command == "join"):
        await join()


async def playw(message):
    player = playerw
    print(f"player: {player}")
    ctx = ctxw

    await join()
    if player is not None:
        data = await YTDLSource.get_data(message, loop=loopw, download=False)
        if 'entries' in data:
            for entry in data['entries']:
                source = await YTDLSource.create_source(ctx, entry, download=False)
                await player.queue.put(source)
                embed = discord.Embed(title="El cielo nos ofrenda una cancion", description=f"{message}")
                await ctx.send(embed=embed)


async def playBestW():
    player = playerw
    ctx = ctxw
    con = MySQL()
    songs = con.bestSongs(ctx.guild.id, 20)
    if vcw is None:
        await join()
    if player:
        for song in songs:
            data = await  YTDLSource.get_data(song, loop=loopw, download=False)
            if 'entries' in data:
                for entry in data['entries']:
                    source = await YTDLSource.create_source(ctx, entry, download=False)
                    print(entry['duration'])
                    await player.queue.put(source)
                    embed = discord.Embed(title="El cielo nos ofrenda las mejores canciones",
                                          description="Las 20 mejores canciones han sido añadidas")
                    await ctx.send(embed=embed)


async def playFavW():
    player = playerw
    ctx = ctxw
    con = MySQL()
    if vcw is None:
        await join()
    songs = con.favSongs(ctx.author.id, 20)
    if player is not None:
        for song in songs:
            data = await YTDLSource.get_data(song, loop=loopw, download=False)
            if 'entries' in data:
                for entry in data['entries']:
                    source = await YTDLSource.create_source(ctx, entry, download=False)
                    print(entry['duration'])
                    await player.queue.put(source)
                    embed = discord.Embed(title="El cielo nos ofrenda las mejores canciones",
                                          description=f"Las 20 canciones favoritas de {ctx.author.name} han sido añadidas")
                    await ctx.send(embed=embed)


async def join():
    try:
        user = ctxw.author.name
        print(user)
        voice_channels = ctxw.guild.voice_channels
        print(voice_channels)
        for voice in voice_channels:
            print(voice)
            members = voice.members
            print(members)
            for member in members:
                print(member)
                if member.name == user:
                    globals()['vcw'] = voice
                    print("test")
                    await voice.connect()
                    return
    except discord.errors.ClientException as e:
        print(e)


async def stop():
    player = playerw
    player.destroy(ctxw.guild)
    vc = ctxw.voice_client
    await vc.disconnect()


async def pausew():
    vc = ctxw.voice_client
    if vc.is_paused():
        vc.resume()
    else:
        ctxw.voice_client.pause()


async def skipw():
    vc = ctxw.voice_client
    con = MySQL()
    con.skipSong(vc.source.data['id'], ctxw.guild.id, ctxw.author.id)
    vc.stop()


async def callate(user):
    canal = ctxw.author.voice.channel
    members = canal.members
    print(members)
    for member in members:
        if member.name == user:
            print(member.name)
            await member.edit(mute=True)


async def descallate(user):
    canal = ctxw.author.voice.channel
    members = canal.members
    for member in members:
        if member.name == user:
            await member.edit(mute=False)


async def kickw(user):
    canal = ctxw.author.voice.channel
    members = canal.members
    for member in members:
        if member.name == user:
            await member.edit(voice_channel=None)


async def clear():
    playerw.queue.empty()  # ??


# MYSQL

class MySQL():
    __slots__ = ('dbcon')

    def __init__(self):
        self.dbcon = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="bot"
        )

    def setuser(self, id, username):
        cursor = self.dbcon.cursor()
        cursor.execute(
            f"SELECT ID ,COUNT(*) FROM users WHERE ID={id} GROUP BY ID"
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (%s, %s)", (id, username)
            )
            self.dbcon.commit()
            print("añadido " + username + " a la tabla usuarios")

    def setguild(self, id, guildName):
        cursor = self.dbcon.cursor()
        cursor.execute(
            f"SELECT ID , COUNT(*) FROM servers WHERE ID={id} GROUP BY ID"
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO servers (id,servername) VALUES (%s,%s)", (id, guildName)
            )
            self.dbcon.commit()
            print("añadido " + guildName + " a la tabla servidores")

    # ID	NAME	URL	ARTIST	GENRE	DURATION
    def setsong(self, id, name, url, duration):
        cursor = self.dbcon.cursor()

        cursor.execute(
            "SELECT id, COUNT(*) FROM songs WHERE id=%s GROUP BY id",
            (id,)
        )

        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO songs (id,name,url,duration) VALUES (%s,%s,%s,%s)", (id, name, url, duration)
            )
            self.dbcon.commit()
            print("añadido " + name + " a la tabla songs")

    def skipSong(self, songid, serverid, userid):
        cursor = self.dbcon.cursor()
        cursor.execute(
            "SELECT songid, serverid, userid, COUNT(*) FROM songstats WHERE songid = %s AND serverid=%s AND userid=%s "
            "GROUP BY songid, serverid, userid",
            (songid, serverid, userid)
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO songstats (songid, serverid, userid, timesplayed, timesskipped, firsttime) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (songid, serverid, userid, 0, 1, date.today())
            )
            self.dbcon.commit()
        else:
            cursor.execute(
                "UPDATE songstats SET timesskipped = timesskipped + 1 "
                f"WHERE userid = %s "
                f"AND serverid= %s "
                f"AND songid = %s ",
                (userid, serverid, songid)
            )
            self.dbcon.commit()

    def playSong(self, songid, songName, songURL, duration, serverid, guildname, userid, username):
        cursor = self.dbcon.cursor()
        self.setuser(userid, username)
        self.setguild(serverid, guildname)
        self.setsong(songid, songName, songURL, duration)
        # Ver si la fila ya existe
        # Por clarificar las columnas son estas:
        # userid songid serverid timesplayed timesskipped firsttimeplayed
        # Las 3 primeros son la PK
        print(userid)
        cursor.execute(
            "SELECT songid, serverid, userid, COUNT(*) FROM songstats WHERE songid= %s and serverid= %s and userid=%s "
            "GROUP BY songid, serverid, userid"
            , (songid, serverid, userid)
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        print(results)
        if row_count == 0:
            cursor.execute(
                "INSERT INTO songstats (songid,serverid,userid,timesplayed,timesskipped,firsttime)"
                f"VALUES (%s, %s ,%s ,%s ,%s ,%s )",
                (songid, serverid, userid, 1, 0, date.today())

            )
            self.dbcon.commit()
            print(f"Insertado en songstats cancion {songName} para {username} en {serverid}")
        else:
            cursor.execute(
                "UPDATE songstats SET timesplayed = timesplayed + 1 "
                f"WHERE userid = %s "
                f"AND serverid= %s "
                f"AND songid = %s ",
                (userid, serverid, songid)
            )
            self.dbcon.commit()

    def bestSongs(self, serverid, size):
        cursor = self.dbcon.cursor()
        cursor.execute(
            "SELECT songs.url FROM songs "
            "INNER JOIN songstats ON songs.id = songstats.songid "
            "WHERE songstats.serverid = %s "
            "ORDER BY songstats.timesplayed DESC, songstats.timesskipped ASC "
            f"LIMIT {size}",
            (serverid,)
        )
        results = cursor.fetchall()
        return results

    def favSongs(self, userid, size):
        cursor = self.dbcon.cursor()
        cursor.execute(
            "SELECT songs.url FROM songs "
            "INNER JOIN songstats ON songs.id = songstats.songid "
            "WHERE songstats.userid = %s "
            "ORDER BY songstats.timesplayed DESC, songstats.timesskipped ASC "
            f"LIMIT {size}",
            (userid,)
        )
        results = cursor.fetchall()
        return results

    def request(self, params):
        cursor = self.dbcon.cursor()
        try:
            cursor.execute(params)
            return cursor.fetchall()
        except Exception:
            print("La consulta salio mal")
            return "Error"


class Music(commands.Cog):
    __slots__ = ('bot', 'players', 'webserver', 'dbcons')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.dbcons = {}
        self.webserver = None

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass
        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    def get_db(self, ctx):
        return MySQL()

    @commands.command(name="play", aliases=["p"], description="El comando base para añadir canciones a la cola")
    async def play(self, ctx, *, search):
        """Comando tipico para reproducir canciones de casi cualquier pagina"""
        print(f"[{ctx.author}]: ({search})")
        if globals()['playerw'] is None:
            await self.startvoice(ctx)
        await ctx.trigger_typing()
        vc = ctx.voice_client
        if not vc:
            await ctx.invoke(self.join)

        data = await YTDLSource.get_data(search, loop=self.bot.loop, download=False)

        player = self.get_player(ctx)
        if 'entries' in data:
            if len(data['entries']) >= 10:
                embed = discord.Embed(title="A la cola+",
                                      description=f"se ha añadido una playlist de {len(data['entries'])} canciones")
                await ctx.send(embed=embed)
            for entry in data['entries']:

                source = await YTDLSource.create_source(ctx, entry, download=False)
                if len(data['entries']) < 10:
                    embed = discord.Embed(title="A la cola", description=f"{source['title']}",
                                          colour=discord.Color.green())
                    await ctx.send(embed=embed)
                await player.queue.put(source)
        else:
            # Si se reproduce una cancion por url no tiene entries:
            source = await YTDLSource.create_source(ctx, data, download=False)
            embed = discord.Embed(title="A la cola", description=f"{source['title']}",
                                  colour=discord.Color.green())
            await ctx.send(embed=embed)
            await player.queue.put(source)

    @commands.command(name="best", description="Reproduce X de las canciones mas escuchadas en el servidor")
    async def playBestSongs(self, ctx, size):
        """Reproduce las mejores canciones del servidor """
        con = self.get_db(ctx)
        player = self.get_player(ctx)
        await ctx.trigger_typing()
        vc = ctx.voice_client
        if not vc:
            await ctx.invoke(self.join)
        songsURLS = con.bestSongs(ctx.guild.id, size)
        embed = discord.Embed(title="Lo mejor del server",
                              description=f"{len(songsURLS)} canciones fueron añadidas a la cola")
        await ctx.send(embed=embed)
        shuffle(songsURLS)
        for song in songsURLS:
            data = await YTDLSource.get_data(song[0], loop=self.bot.loop, download=False)
            source = await YTDLSource.create_source(ctx, data, download=False)
            await player.queue.put(source)

    @commands.command(name="fav", description="Reproduce las X canciones favoritas del usuario")
    async def playFavSongs(self, ctx, size):
        """Reproduce las X canciones favoritas del usuario"""
        con = self.get_db(ctx)
        player = self.get_player(ctx)
        songURLS = con.favSongs(ctx.author.id, size)
        await ctx.trigger_typing()
        vc = ctx.voice_client
        if not vc:
            await ctx.invoke(self.join)
        embed = discord.Embed(title=f"Las canciones favoritas de {ctx.author.name}",
                              description=f"{len(songURLS)} canciones añadidas a la cola")
        await ctx.send(embed=embed)
        shuffle(songURLS)
        for song in songURLS:
            data = await YTDLSource.get_data(song[0], loop=self.bot.loop, download=False)
            source = await YTDLSource.create_source(ctx, data, download=False)
            await player.queue.put(source)

    @commands.command(name="startv", description="Comando de ayuda para el cliente de voz")
    async def startvoice(self, ctx):
        """Commando ayuda para el cliente de voz espero poder quitarlo en un futuro"""
        listofglob = globals()
        playerg = self.get_player(ctx)
        loopg = self.bot.loop
        print("voz empezado")
        if playerg is not None:
            listofglob['playerw'] = playerg
            listofglob['loopw'] = loopg
            listofglob['ctxw'] = ctx

    @commands.command(name='queue', aliases=['q', 'playlist', 'que'])
    async def queue_info(self, ctx):

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="Ando perdido invocame si eso",
                                  color=discord.Color.green())
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        print(f"-- player: {player}")
        if player.queue.empty():
            embed = discord.Embed(title="", description="Mi cola esta vacia :c", color=discord.Color.green())
            return await ctx.send(embed=embed)
        if vc.source is None:
            return

        seconds = vc.source.duration % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if hour > 0:
            duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
        else:
            duration = "%02dm %02ds" % (minutes, seconds)

        # Grabs the songs in the queue...
        queuelength = int(len(player.queue._queue))
        if (queuelength > 10):
            queuelength = 10
        upcoming = list(itertools.islice(player.queue._queue, 0, queuelength))
        fmt = '\n'.join(
            f"{(upcoming.index(_)) + 1}.` [{_['title']}]({_['webpage_url']}) | ` {duration} cortesia de: {_['requester']}`\n"
            for _ in upcoming)
        fmt = f"\n__La que esta sonando__:\n[{vc.source.title}]({vc.source.web_url}) | ` {duration} cortesia de: {vc.source.requester}`\n\n__La que vendra despues:__\n" + fmt + f"\n**{int(len(player.queue._queue))} canciones en la cola**"
        embed = discord.Embed(title=f'La cola de {ctx.guild.name}', description=fmt, color=discord.Color.green())
        embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(name='remove', aliases=['rm', 'quitar', 'fuera'], description="Quita la cancion de la lista)")
    async def rm(self, ctx, *, search):

        player = self.get_player(ctx)
        data = await YTDLSource.get_data(search, loop=self.bot.loop, download=False)

        if 'entries' in data:
            data = data['entries'][0]

        upcoming = list(itertools.islice(player.queue._queue, 0, int(len(player.queue._queue))))

        for _ in upcoming:

            if _['title'] != data['title']:
                await player.queue.put(_)
            await player.queue.get()

    @commands.command(name="skipTo",
                      description="Se salta la cola hasta la cancion elejida, en plan que adelanta una cancion a la primera")
    async def skipto(self, ctx, search):
        """Adelanta la cancion elejida a la primera (Realiza busqueda)"""
        player = self.get_player(ctx)
        data = await YTDLSource.get_data(search, loop=self.bot.loop, download=False)
        vc = ctx.voice_client
        if 'entries' in data:
            data = data['entries'][0]

        upcoming = list(itertools.islice(player.queue._queue, 0, int(len(player.queue._queue))))

        for _ in upcoming:

            if _['title'] != data['title']:
                await player.queue.put(_)
            else:
                break
            await player.queue.get()
        vc.stop()

    @commands.command(name='loop', aliases=['infinito', 'lp'],
                      description="Las canciones volveran a ser añadidas a la cola cuando terminen de sonar")
    async def loop(self, ctx):

        player = self.get_player(ctx)
        looping = player.looping
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="Ando perdido, invocame si eso",
                                  color=discord.Color.green())
            return await ctx.send(embed=embed)

        data = await YTDLSource.get_data(vc.source.title, self.bot.loop, download=False)
        if 'entries' in data:
            data = data['entries'][0]
        source = await YTDLSource.create_source(ctx, data)
        await player.queue.put(source)
        player.looping = not looping
        print(f"loop: {player.looping}")
        msg = "loop"
        if not looping:
            msg = msg + " activado!"
        else:
            msg = msg + " desactivado"
        await ctx.send(msg)

    @commands.command(name='shuffle', aliases=['barajar', 'random', 'sf'],
                      description="Hace que la fila sea random, nunca sabras cuando puede sonar balada triste de trompeta")
    async def shuffle(self, ctx):

        player = self.get_player(ctx)
        if player.queue._queue:
            shuffle(player.queue._queue)

    @commands.command(name="join")
    async def join(self, ctx):

        if ctx.message.author.voice:
            user = ctx.message.author
            channel = user.voice.channel
            await channel.connect()

        else:
            await ctx.send("metete a un canal genio")

    @commands.command(name="skip")
    async def skip(self, ctx):

        con = self.get_db(ctx)
        vc = ctx.voice_client
        source = vc.source
        con.skipSong(source.data['id'], ctx.guild.id, ctx.author.id)
        if not vc or not vc.is_connected():
            return await ctx.send("NO estoy en ningun canal")
        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return
        vc.stop()

    @commands.command(name="clear")
    async def clear(self, ctx):

        player = self.get_player(ctx)
        if player.queue._queue:
            player.queue._queue.clear()

    @commands.command(name="pause")
    async def pause(self, ctx):

        vc = ctx.voice_client
        if vc.is_paused():
            vc.resume()
        else:
            ctx.voice_client.pause()

    @commands.command(name="volume")
    async def volume(self, ctx, volume: int):

        if ctx.voice_client is None:
            return await ctx.send("No estoy en un canal genio.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"El volumen ahora es {volume}%")

    @commands.command(name="stop")
    async def stop(self, ctx):

        player = self.get_player(ctx)
        self.players[ctx.guild.id] = None
        player.destroy(ctx.guild)
        await self.leave(ctx)

    @commands.command()
    async def getchannel(self, ctx):

        channel = discord.utils.get(ctx.guild.channels, name="general")
        channel_id = channel.id
        print(channel_id)

    @commands.command()
    async def leave(self, ctx):
        """Despidete """
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        else:
            await ctx.send("no estoy en ningun canal")

    @commands.command(name="SQL",
                      description="NO TOQUEIS SI NO SABIES LO QUE HACEIS, Realiza la consulta que le pongas")
    async def sql(self, ctx, *, params):
        """NO TOQUEIS SI NO SABIES LO QUE HACEIS, Realiza la consulta que le pongas"""
        con = MySQL()
        requests = con.request(params)
        for request in requests:
            await ctx.send(request)

    @play.before_invoke
    @playBestSongs.before_invoke
    @playFavSongs.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()


bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"),
                   description='Nihiloot bot intentando no morise :D')


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


print('running websockets ws://127.0.0.1:8000')

bot.add_cog(Music(bot))
server = websockets.serve(response, "", '8000', ping_interval=None)
asyncio.get_event_loop().run_until_complete(server)
with open("keys.json") as jsonFile:
    jsonObject = json.load(jsonFile)
    jsonFile.close()

bot.run(jsonObject["devKey"])
