import asyncio
import websockets
import speech_recognition as sr

from pynput.keyboard import Key, Listener
import sys
url = "localhost"
uri = f'ws://{url}:8800/688391132815949878_294961216634486786'
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
    pass

# Collect events until released
with Listener(
        on_press=on_press,
        on_release=on_release) as listener:
    listener.join()
