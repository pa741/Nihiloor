 Nihiloor
 ---
A python discord bot with voice command support
This Bot runs a websocket server in the backhground through wich the voice client can send commands like playing or skipping a song
This bot, can run simultaneously on as many servers as your memory allows.
### Features

- Music features:
  - Shuffle `!shuffle`
  - Skip `!skip`
  - Loop `!loop`
  - Previous song, this also reverts the queue `!prev`
  - Pause / Play `!pause`
  - Interactive player that updates when the playing song changes. This player has all the above features integrated on reactions `!queue`
  - Supports [more than 1000 sites](https://github.com/ytdl-org/youtube-dl/blob/master/docs/supportedsites.md).
- Voice Features:
  - Simple CLI Voice client offering push to talk when the `insert` key is pressed. 
  - Voice commands:
    - join
    - play (song)
    - pause
    - skip
    - previous
    - shuffle
    - leave
  - Better client in progress.
- Database that logs when a user plays a song. (Usefull in case in the future I add a `!playFavourite` command
- Many more to come!

### Requirements
- Python 3.10.2 (If you get a higher version you need to replace the Pyaudio file in VoiceClient.rar for its [corresponding version](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio))
- FFMPEG is needed to play audio on discord.

### Voice QuickStart
You need to add your servers public ip to the VoiceServer.py URI (Replace localhost).
Make sure you aren't in a voice channel when the server starts because you wont be cached in memory (You can leave and rejoin and that should fix it).
The command to start voice server is `!startvc` every user that wants to use voice should type this and follow the instructions the bot sends them through DMs
If the Voice server breaks for some reason you should first tell me about it so i can fix the issue, and second run `!restartvc` to restart the voice server.
