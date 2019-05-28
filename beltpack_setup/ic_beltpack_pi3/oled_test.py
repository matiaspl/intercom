import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont, ImageDraw, Image

import time, smbus2

#bus = smbus2.SMBus(1)
#bus.write_byte(0x70, 0xFF)
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, rotate=0)

### INITIALIZE GPIO AND ACTIVATE PULL DOWN ON INPUTS
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
### Power Off buttons
powPort = 37
GPIO.setup(powPort, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
### PTT buttons
pttPorts = (38,40)
GPIO.setup(pttPorts, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

lastPTT = [0,0]

def updateOLED():
  with canvas(device) as draw:
    if "high" in lastPTT:
      text = "Button " + str(lastPTT.index("high")+1) + " pressed"
    else:
      text = "Button not pressed"
    draw.rectangle(device.bounding_box, outline="white", fill="black")
    draw.text((10, 20), text, fill="white")

while True:
  for keyCounter, portNum in enumerate(pttPorts):
    if GPIO.input(portNum) == 1:
      if lastPTT[keyCounter] == "low" or lastPTT[keyCounter] == "":
        lastPTT[keyCounter] = "high"
    else:
      lastPTT[keyCounter] = "low"
  updateOLED()
  time.sleep(0.1)
