 Nihiloor
 ---
El primer bot de discord con comandos de voz!

### Try it for yourself!
[¡Invitame a tu servidor!](https://discord.com/api/oauth2/authorize?client_id=867494633629679666&permissions=8626646080&scope=bot)

### Comandos
- Music features:
  - Shuffle `!shuffle`
  - Saltarse la cancion `!skip`
  - Modo bucle `!loop`
  - Cancion anterior `!prev`
  - Pause / Play `!pause`
  - Reproductor de canciones interactivo `!queue`
  - Puede reproducir audio de [mas de 1000 paginas distintas](https://github.com/ytdl-org/youtube-dl/blob/master/docs/supportedsites.md).
- Este comando busca en google y devuelve la primera imagen que encuentra `!img (busqueda)`
### Voz
  - Cliente de voz simple, para enviar un comando de voz pulsar `insert` y decir el comando en voz alta  
  - Comandos de voz:
    - join
    - play (cancion)
    - pause
    - skip
    - previous
    - shuffle
    - leave

### Requerimientos
- Python 3.10.2 (Si tienes una version mas alta cambiar el archivo de pyaudio en VoiceClient.rar por su [Version correspondiente](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio))
- Se necesita FFMPEG y la libreria PyNaCL para reproducir audio en discord.

### Voice QuickStart
Tienes que cambiar la url en voiceClient.py por la ip publica correspondiente al servidor donde ejecutes el bot.
El comando para iniciar el servicio de voz del bot es `!startvc`, tras escribir este comando el bot te enviara por mensajes privados 
En caso de que por cualquier motivo se estropeé el cliente de voz el comando `!restartvc` reiniciaria el servicio de bot del servidor en el que se ejecuté el comando
