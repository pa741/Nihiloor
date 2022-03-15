import asyncio
import websockets
import speech_recognition as sr
from pynput import keyboard
from pynput.keyboard import Key, Listener
import sys

#Tiene que ser ejecutado desde la cmd tal y como el bot indica
#Deberiais tener el servidor en un host remoto o al menos con los puertos abiertos poner aqui la IP del servidor
#En lugar de localhost
uri = f'ws://localhost:8800/{sys.argv[1]}_{sys.argv[2]}'
print(uri)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


async def send_message(message):
    async with websockets.connect(uri) as websocket:
        await websocket.send(message)
        print(f"[ws client] message  > {message}")


def speechtotext():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Speak:")
        try:
            audio = r.listen(source, timeout=3)
            try:
                text = r.recognize_google(audio)
                text = text.lower()
                print(text)
                loop.run_until_complete(send_message(text))
            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError as e:
                print("Could not request results; {0}".format(e))
        except sr.WaitTimeoutError as e:
            print("Timeout; {0}".format(e))


def on_press(key):
    if key == Key.insert:
        speechtotext()


def on_release(key):
    print()


# Collect events until released
with Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()
