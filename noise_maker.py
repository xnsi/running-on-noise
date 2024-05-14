import asyncio
import configparser
import ctypes
import numpy as np
import os
import pystray
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from scipy.io.wavfile import write
from pydub import AudioSegment
from pydub.playback import play
from PIL import Image, ImageDraw

# Parse config file
config = configparser.ConfigParser()
config.read('config.ini')
duration = float(config['DEFAULT']['duration'])
interval = int(config['DEFAULT']['interval'])

sample_rate = 44100
amplitude = 1
# Check if the white noise file exists
if not os.path.isfile("white_noise.wav"):
    # Generate white noise
    samples = (np.random.normal(0, 1, int(sample_rate * duration)) * amplitude).astype(np.int16)
    write("white_noise.wav", sample_rate, samples)
else:
    # Check the duration of the existing white noise file
    existing_noise = AudioSegment.from_wav("white_noise.wav")
    if len(existing_noise) / 1000 != duration:
        # If the duration does not match, regenerate the white noise
        samples = (np.random.normal(0, 1, int(sample_rate * duration)) * amplitude).astype(np.int16)
        write("white_noise.wav", sample_rate, samples)

# Now, you can use the "white_noise.wav" file as your white noise
noise = AudioSegment.from_wav("white_noise.wav")

# Check if the system is awake
def is_awake():
    return ctypes.windll.kernel32.GetTickCount64() != 0

# Asynchronously play white noise
async def play_noise():
    if is_awake():
        print("Playing white noise...")
        with ThreadPoolExecutor() as executor:
            executor.submit(play, noise)
        print("Finished")

# Asynchronous timer
async def timer():
    while True:
        if is_awake():
            await asyncio.sleep(interval)  # Wait for interval minutes
            await play_noise()  # Play white noise
        else:
            await asyncio.sleep(1)  # The system is asleep, wait for it to wake up

# Exit operation
def exit_action(icon):
    # TODO: not sure why this line does not work
    # loop = asyncio.get_event_loop()
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        task.cancel()
    icon.visible = False
    icon.stop()
    os._exit(0)

# Create an 64x64 pixel image for the icon
image = Image.new('RGB', (64, 64), 'white')
draw = ImageDraw.Draw(image)
draw.rectangle(
    [(5, 5), (59, 59)],
    fill='white'
)

# Create a system tray icon
icon = pystray.Icon("name", image, "White Noise Maker", menu=pystray.Menu(pystray.MenuItem("Exit", exit_action)))

def main():
    # Set loop global to avoid the get_event_loop problem
    global loop
    # icon.run will create a event loop and block the timer part. Create a new thread will solve this.
    icon_t = threading.Thread(target=icon.run)
    icon_t.start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(timer())
    pending = asyncio.all_tasks(loop)
    group = asyncio.gather(*pending, return_exceptions=True)
    loop.run_until_complete(group)

if __name__ == "__main__":
    main()
