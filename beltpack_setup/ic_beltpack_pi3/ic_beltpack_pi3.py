# -*- coding: utf-8 -*-
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont, ImageDraw, Image
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from signal import *
import autopy3, os, socket, subprocess, sys, time

##################################################################
########## BELTPACK USER CONFIGURATION ##########
### INTERCOM CONFIGURATION
### WHO USES THIS BELTPACK ###
icUser = "UNKNOWN"
### TO WHOM IS IT BROADCASTING ###
### THIS DEVICE HAS 2 CHANNELS ["",""] 3 CHANNELS -> ["","",""]
icTalkTo = ["N/A","N/A"]
### MQTT SETTINGS
mqttServer = "192.168.10.125"
mqttPort = 8883
mqttTimeOut = 10
mqttUser = "intercom"
mqttPass = "_Interc0M_"
########## PLEASE DO NOT MAKE CHANGES BELOW THIS LINE! ##########
#################################################################

lastIcTalk = 0
lastStatusSent = 0
lastPO = int(round(time.time() * 1000))
lastBtn = 0
poOK = False
statusInterval = 5000 ### UPDATE INTERVAL FOR MQTT (IN MILLISECONDS)
lastNetErrState = 0

### WHICH DISPLAY TO CONTROL
os.environ['DISPLAY'] = ':0.0'

### Software version
icSoftVerText = "SW v1.1"

### SET DEVICE IP
deviceIP = "N/A"

### NETWORK INTERFACE USED
interface = "wlan0"

### GET DEVICE HOSTNAME
deviceHostName = socket.gethostname()

### INITIALIZE GPIO AND ACTIVATE PULL DOWN ON INPUTS
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
### OUTPUTS
v33Ports = (37,38)
GPIO.setup(v33Ports, GPIO.OUT)
### SET HIGH (3.3V)
GPIO.output(v33Ports, 1)
### POWER OFF PIN
powPort = 35
GPIO.setup(powPort, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
### PTT PINS
pttPorts = (36,40)
GPIO.setup(pttPorts, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

mqttStatus = 3
mqttStatusCodes=["SUCCESS","INCOR PROT","INVAL CLNT","SRV UNAVAIL","BAD US/OW","NOT AUTH"]

### LOAD FONTS FOR OLED DISPLAY
font1 = ImageFont.truetype('/home/pi/intercom/fonts/VeraMoBd.ttf',27)
font2 = ImageFont.truetype('/home/pi/intercom/fonts/VeraMoBd.ttf',16)
font3 = ImageFont.truetype('/home/pi/intercom/fonts/VeraMoBd.ttf',12)

### SETUP OLED I2C PORT
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, rotate=2)

### TALK STATE
talkNow = False
lastTalkNow = False

def wifiStatus():
  ### COLLECT DATA ABOUT THE WIFI
  proc = subprocess.Popen(["iwconfig", interface], stdout=subprocess.PIPE, universal_newlines=True)
  output, err = proc.communicate()
  linkQuality ="N/A"
  signalLevel = "N/A"
  activeAP = "N/A"
  if output != None:
    for line in output.split("\n"):
      cell_line = line.strip()
      if cell_line.find("Link Quality") != -1:
        output = cell_line.split('  ')
        if len(output) == 2:
          linkQuality = output[0].replace("Link Quality=","").rstrip()
          signalLevel = output[1].replace("Signal level=","").rstrip()
      if cell_line.find("Access Point:") != -1:
        output = cell_line.split('  ')
        activeAP = output[2].replace("Access Point: ","").rstrip()
  return(linkQuality, signalLevel, activeAP)

def calculateWiFiQuality():
  wifiStats = wifiStatus()
  if wifiStats[1] == "N/A":
    wifidBm = -100
  else:
    wifidBm = int((wifiStats[1].replace(" dBm", "")))
  if wifidBm <= -100:
    signalQuality = 0
  elif wifidBm >= -50:
    signalQuality = 100
  else:
    signalQuality = 2 * (wifidBm + 100)
  return signalQuality

def showWiFiQuality(draw,type):
  global lastNetErrState
  wifiQuality = calculateWiFiQuality()
  if type == "bars":
    ### DISPLAY WIFI QUALITY WITH BARS
    if wifiQuality >= 20:
      draw.rectangle((0,14,5,18), outline=1, fill=255)
    else:
      draw.rectangle((0,14,5,18), outline=1, fill=0)
    if wifiQuality >= 30:
      draw.rectangle((7,12,12,18), outline=1, fill=255)
    else:
      draw.rectangle((7,12,12,18), outline=1, fill=0)
    if wifiQuality >= 40:
      draw.rectangle((14,10,19,18), outline=1, fill=255)
    else:
      draw.rectangle((14,10,19,18), outline=1, fill=0)
    if wifiQuality >= 50:
      draw.rectangle((21,8,26,18), outline=1, fill=255)
    else:
      draw.rectangle((21,8,26,18), outline=1, fill=0)
    if wifiQuality >= 60:
      draw.rectangle((28,6,33,18), outline=1, fill=255)
    else:
      draw.rectangle((28,6,33,18), outline=1, fill=0)
    if wifiQuality >= 70:
      draw.rectangle((35,4,40,18), outline=1, fill=255)
    else:
      draw.rectangle((35,4,40,18), outline=1, fill=0)
    if wifiQuality >= 80:
      draw.rectangle((42,2,47,18), outline=1, fill=255)
    else:
      draw.rectangle((42,2,47,18), outline=1, fill=0)
    if wifiQuality >= 90:
      draw.rectangle((49,0,54,18), outline=1, fill=255)
    else:
      draw.rectangle((49,0,54,18), outline=1, fill=0)
    if not client.connected_flag or wifiQuality <= 5:
       ### NETWORK PROBLEMS
       if lastNetErrState == 0:
         if wifiQuality >= 90:
           draw.text((47, 0), "!", font=font2, fill=0)
         else:
           draw.text((47, 0), "!", font=font2, fill=255)
         lastNetErrState = 1
       else:
         if wifiQuality >= 90:
           draw.text((47, 0), " ", font=font2, fill=0)
         else:
           draw.text((47, 0), " ", font=font2, fill=255)
         lastNetErrState = 0
  elif type == "percent":
    ### DISPLAY WIFI QUALITY IN PERCENT
    tmpWifiText_size = draw.textsize(str(wifiQuality)+"%", font=font2)
    draw.text(((64-tmpWifiText_size[0])/2, 1), str(wifiQuality)+"%", font=font2, fill=255)
    if not client.connected_flag:
      ### NETWORK PROBLEMS
      if lastNetErrState == 0:
        draw.text((47, 0), "!", font=font2, fill=255)
        lastNetErrState = 1
      else:
        draw.text((47, 0), " ", font=font2, fill=255)
        lastNetErrState = 0

def startBroadcasting(btn):
  if btn == 0:
    autopy3.key.toggle(u'1', True, autopy3.key.MOD_CONTROL)
    client.publish("media/intercom/broadcast/" + icUser + "/talk", ','.join(icTalkTo[btn]), qos=1, retain=True)
  elif btn == 1:
    autopy3.key.toggle(u'2', True, autopy3.key.MOD_CONTROL)
    client.publish("media/intercom/broadcast/" + icUser + "/talk", ','.join(icTalkTo[btn]), qos=1, retain=True)
  return(True)

def stopBroadcasting(btn):
  if btn == 0:
    autopy3.key.toggle(u'1', False, autopy3.key.MOD_CONTROL)
    client.publish("media/intercom/broadcast/" + icUser + "/talk", "NOT TALKING", qos=1, retain=True)
  elif btn == 1:
    autopy3.key.toggle(u'2', False, autopy3.key.MOD_CONTROL)
    client.publish("media/intercom/broadcast/" + icUser + "/talk", "NOT TALKING", qos=1, retain=True)
  return(False)

def showIP(draw):
  ### DRAW DEVICE IP
  if not client.connected_flag:
    icIPText_size=draw.textsize(deviceIP, font=font3)
    draw.text(((128-icIPText_size[0])/2, 53), deviceIP, font=font3, fill=255)
    mqttErrText_size=draw.textsize("MQTT ERR", font=font3)
    draw.text(((64-mqttErrText_size[0])/2+60, 6), "MQTT ERR", font=font3, fill=255)
  else:
    icIPText_size=draw.textsize(deviceIP, font=font3)
    draw.text(((128-icIPText_size[0])/2, 53), deviceIP, font=font3, fill=255)

def getIPInfo():
  ### GET DEVICE IP
  deviceIP = "N/A"
  try:
    intf = interface
    deviceIP = str(subprocess.check_output(['hostname', '--all-ip-addresses']).rstrip().decode())
    if deviceIP.split(".")[0] == "169" or deviceIP == "":
      deviceIP = "N/A"
    return {'deviceIP':deviceIP}
  except:
    return {'deviceIP':deviceIP}
    pass

def multiIcTalkTo(input):
  global lastIcTalk
  multi = input.split(",")
  if lastIcTalk < len(multi):
    output = multi[lastIcTalk]
    lastIcTalk += 1
  else:
    output = multi[0]
    lastIcTalk = 1
  return output

def showICUser(draw):
  ### DISPLAY INTERCOM USER
  if talkNow == True:
    wifiStats = wifiStatus()
    if wifiStats[1] != "N/A":
      tmpicUserText_size=draw.textsize("TALK TO", font=font3)
      draw.text(((64-tmpicUserText_size[0])/2+60, 6), "TALK TO", font=font3, fill=255)
      if icTalkTo[lastBtn].find(",") != -1:
        talkTo = multiIcTalkTo(icTalkTo[lastBtn])
      else:
        talkTo = icTalkTo[lastBtn]
      tmpicUserText_size=draw.textsize(talkTo, font=font1)
      draw.text(((128-tmpicUserText_size[0])/2, 22), talkTo, font=font1, fill=255)
    else:
      tmpicUserText_size=draw.textsize("NO WIFI", font=font1)
      draw.text(((128-tmpicUserText_size[0])/2, 22), "NO WIFI", font=font1, fill=255)
  else:
    icUserText_size=draw.textsize(icUser, font=font1)
    draw.text(((128-icUserText_size[0])/2, 22), icUser, font=font1, fill=255)


def startStopOLED(type):
  ### START/STOP DISPLAY FUNCTION
  if type == "Start":
    with canvas(device) as draw:
      icStartText_size=draw.textsize("Intercom", font=font2)
      draw.text(((128-icStartText_size[0])/2, 5), "Intercom", font=font2, fill=255)
      icStartText_size=draw.textsize("beltpack", font=font2)
      draw.text(((128-icStartText_size[0])/2, 25), "beltpack", font=font2, fill=255)
      icSoftVerText_size=draw.textsize(icSoftVerText, font=font2)
      draw.text(((128-icSoftVerText_size[0])/2, 45), icSoftVerText, font=font2, fill=255)
  time.sleep(2)

  if type == "Stop":
    with canvas(device) as draw:
      draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)
      logo = Image.open('/home/pi/intercom/images/made_in_arcada_1bit_shutdown.png')
      draw.bitmap((0, 0), logo, fill=1)
    time.sleep(4)
    with canvas(device) as draw:
      draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)

  if type == "StopBlank":
    with canvas(device) as draw:
      draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)

def publishStatus():
  wifi = wifiStatus()
  client.publish("media/intercom/status/" + deviceHostName + "/battPresent", "1", qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/battOnline", "1", qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/battStatus", "N/A", qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/battCapacity", "N/A", qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/battHealth", "N/A", qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/linkQuality", wifi[0], qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/signalLevel", wifi[1], qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/activeAP", wifi[2], qos=1, retain=True)

def drawScreen():
  ### CHOOSE WHAT TO DRAW ON THE DISPLAY
  with canvas(device) as draw:
    showWiFiQuality(draw,"bars") ### "bars" or "percent"
    showICUser(draw)
    showIP(draw)

def on_connect(client, userdata, flags, rc):
    if rc==0:
      client.connected_flag=True
    else:
      client.error_code=rc
    client.publish("media/intercom/status/" + deviceHostName + "/state", "ONLINE", qos=1, retain=True)
    client.publish("media/intercom/status/" + deviceHostName + "/deviceChannels", len(icTalkTo), qos=1, retain=True)
    ### SUBSCRIBE TO ROLE (icUser)
    client.subscribe("media/intercom/setup/" + deviceHostName + "/deviceRole", qos=1)
    chCounter = 1
    for ch in icTalkTo:
      client.subscribe("media/intercom/setup/" + deviceHostName + "/channel/" + str(chCounter), qos=1)
      chCounter += 1

def on_message(client, userdata, message):
    if message.topic == "media/intercom/setup/" + deviceHostName + "/deviceRole":
       global icUser
       if str(message.payload.decode()) != "":
         icUser = str(message.payload.decode())
         client.publish("media/intercom/status/" + deviceHostName + "/deviceRole", icUser, qos=1, retain=True)

    if "media/intercom/setup/" + deviceHostName + "/channel/" in message.topic:
      chCounter = 1
      for ch in icTalkTo:
        if message.topic == "media/intercom/setup/" + deviceHostName + "/channel/" + str(chCounter):
          icTalkTo[chCounter-1] = str(message.payload.decode())
          client.publish("media/intercom/status/" + deviceHostName + "/channel/" + str(chCounter), icTalkTo[chCounter-1], qos=1, retain=True)
        chCounter += 1


def clean(*args):
    ### EXECUTE WHEN SCRIPT IS ABORTED BEFORE EXIT
    client.publish("media/intercom/status/" + deviceHostName + "/state", "OFFLINE", qos=1, retain=True)
    stopBroadcasting(lastBtn)
    client.disconnect()
    print ("\nScript aborted")
    startStopOLED("Stop")
    time.sleep(5)
    sys.exit(0)

def handler(signum, frame):
    client.publish("media/intercom/status/" + deviceHostName + "/state", "OFFLINE", qos=1, retain=True)
    stopBroadcasting(lastBtn)
    client.disconnect()
    print ("\nHandler abort")
    startStopOLED("Stop")
    sys.exit()

def connectMQTT():
  ### MQTT connection
  try:
    client.connect_async(mqttServer, mqttPort, mqttTimeOut)
    client.on_connect = on_connect
    client.on_message = on_message
  except:
    pass
  client.loop_start()

startStopOLED("Start")

mqtt.Client.connected_flag=False
mqtt.Client.error_code = 0
client = mqtt.Client(client_id=deviceHostName, clean_session=False, userdata=None)
client.tls_set("/home/pi/intercom/ca.crt")
### USE INSECURE IF YOUR CERTIFICATE IS SELF SIGNED
client.tls_insecure_set(True)
client.username_pw_set(mqttUser, password=mqttPass)
client.will_set("media/intercom/status/" + deviceHostName + "/state", "OFFLINE", qos=1, retain=True)

try:
    while True:
      ### DO WE HAVE AN IP ADDRESS?
      if deviceIP == "N/A":
        deviceInfo = getIPInfo()
        deviceIP = deviceInfo['deviceIP']
      ### IS MQTT CONNECTED?
      if not client.connected_flag:
         if deviceIP != "N/A":
           connectMQTT()
      ### IS PTT BUTTON PRESSED?
      if GPIO.input(pttPorts[0]) == 1:
        talkNow = True
        if lastTalkNow is False:
          lastTalkNow = startBroadcasting(0)
          lastBtn = 0
      elif GPIO.input(pttPorts[1]) == 1:
        talkNow = True
        if lastTalkNow is False:
          lastTalkNow = startBroadcasting(1)
          lastBtn = 1
      else:
        talkNow = False
        if lastTalkNow is True:
          lastTalkNow = stopBroadcasting(lastBtn)
      ### TURN OFF SYSTEM IF POWER OFF BUTTON IS PRESSED FOR 3 OR MORE SECONDS	
      if GPIO.input(powPort) == 1:
        if (lastPO <= int(round(time.time() * 1000)) - 3000) and poOK == False:
          stopBroadcasting(lastBtn)
          startStopOLED("Stop")
          os.system("poweroff")
          sys.exit(0)
          poOK = True
      else:
        poOK = False
        lastPO = int(round(time.time() * 1000))
      ### UPDATE DISPLAY
      drawScreen()
      ### PUBLISH DEVICE STATUS OVER MQTT
      if (lastStatusSent == 0 or int(round(time.time() * 1000))-statusInterval >= lastStatusSent):
        publishStatus()
        lastStatusSent = int(round(time.time() * 1000))

      ### CATCH INTERRUPTIONS ###
      #for sig in (SIGINT, SIGTERM, SIGABRT, SIGHUP, SIGSEGV, SIGQUIT):
      #  signal(sig, clean)
      for sig in [SIGTERM, SIGINT, SIGQUIT, SIGHUP]:
        signal(sig, handler)
      time.sleep(0.2)

finally:
    ### SHUTDOWN, CLEAN UP EVERYTHING
    stopBroadcasting(lastBtn)
    startStopOLED("StopBlank")
