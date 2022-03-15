# clase con constructor que necesita el contexto
# se crea con un comando /startvoice
# devuelve con link al path al que se tendra que enviar la voz
# si no se crea un server por que ya hay uno creado devuelve su link

# el path es el id del server (ya que solo abra un canal de voz para cada server)
import Bots


class VServer:
    __slots__ = ('serverDict', 'x')

    def __init__(self, serverDict):
        print("test")
        self.serverDict = serverDict

    async def response(self, websocket, path):
        # El path se corresponde a /serverid_userid
        print("server started")
        message = await websocket.recv()
        print(message)
        serverid = int(path.split("_")[0][1:])
        userid = int(path.split("_")[1])
        if serverid in self.serverDict:
            voice = self.serverDict[serverid].voice
            await voice.command(message, userid)

        else:
            await websocket.send("Voice was not started on this server")


class Voice:
    __slots__ = ("ctx", "bot")

    def __init__(self, ctx=None, bot=None):
        self.ctx = ctx #el contexto de la voz (Es el mensaje !startVC)
        self.bot = bot #el bot que ejecutara los comandos de voz

    async def command(self, message, userid):
        command = message.split()[0]
        params = message[message.find(" ")+1:]
        print(command)
        print(params)
        match command.lower():
            case "join":
                await self.bot.joinVC(userid)
            case "play":
                await self.bot.play(params, userid)
            case "skip":
                await self.bot.skip()
            case "shuffle":
                await self.bot.shuffle()
            case "previous":
                await self.bot.previous()
            case "pause":
                await self.bot.playPause()
            case "leave":
                await self.bot.leaveVC()



