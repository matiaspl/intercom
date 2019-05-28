import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont, ImageDraw, Image
from signal import *
from threading import Thread
import paho.mqtt.client as mqtt
import autopy3, os, socket, subprocess, sys, time, datetime, smbus2

#################################################################
################# BASESTATION USER CONFIGURATION ################
### INTERCOM CONFIGURATION
### WHO USES THIS BASESTATION ###
icUser = ""
### THIS DEVICE HAS 8 CHANNELS ["","","","","","","",""] (3 CHANNELS -> ["","",""])
icTalkTo = [" "," "," "," "," "," "," "," "]
oledIcTalkTo = ["","","","","","","",""]
### MQTT SETTINGS
mqttServer = "192.168.10.125"
mqttPort = 8883
mqttTimeOut = 10
mqttUser = "intercom"
mqttPass = "_Interc0M_"
########## PLEASE DO NOT MAKE CHANGES BELOW THIS LINE! ##########
#################################################################

### NETWORK INTERFACE USED
interface = "eth0"
### URL CONFIGURATION
statusInterval = 5000 ### UPDATE INTERVAL FOR MQTT (IN MILLISECONDS)
### Software version
icSoftVerText = "SW v1.1"

os.environ['DISPLAY'] = ':0.0'

font1 = ImageFont.truetype('/home/pi/intercom/fonts/VeraMoBd.ttf',27)
font2 = ImageFont.truetype('/home/pi/intercom/fonts/VeraMoBd.ttf',16)
font3 = ImageFont.truetype('/home/pi/intercom/fonts/VeraMoBd.ttf',12)

### GET DEVICE HOSTNAME
deviceHostName = socket.gethostname()
### SET DEVICE IP
deviceIP = "N/A"

### INITIALIZE GPIO AND ACTIVATE PULL DOWN ON INPUTS
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
### Power Off buttons
powPort = 19
GPIO.setup(powPort, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
### PTT buttons
pttPorts = (31,32,33,35,36,37,38,40)
GPIO.setup(pttPorts, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
### OLED MUX
muxPorts = (23,24,26)
GPIO.setup(muxPorts, GPIO.OUT)
### SET MUX TO ADDRESS 0x70
GPIO.output(23, 0)
GPIO.output(24, 0)
GPIO.output(26, 0)

### INITIALIZE SCRIPT SETTINGS
mqttStatus = 3
mqttStatusCodes=["SUCCESS","INCOR PROT","INVAL CLNT","SRV UNAVAIL","BAD US/OW","NOT AUTH"]
lastPTT = ["low","low","low","low","low","low","low","low"]
oledLastPTT = ["","","","","","","",""]
lastPTTLow = [0,0,0,0,0,0,0,0]
lastPTTHigh = [0,0,0,0,0,0,0,0]
talkList = []
talksToMe = []
talksToMeState = [0,0,0,0,0,0,0,0]
lastTalkList = "0"
lastIcTalk = [0,0,0,0,0,0,0,0]
pttLocked = ["","","","","","","",""]
lastPO = int(round(time.time() * 1000))
poOK = False
updateOLED = True
lastStatusSent = 0

def multiIcTalkTo(input,ch):
  global lastIcTalk
  multi = input.split(",")
  if lastIcTalk[ch] < len(multi):
    output = multi[lastIcTalk[ch]]
    lastIcTalk[ch] += 1
  else:
    output = multi[0]
    lastIcTalk[ch] = 1
  return output

def oledUpdate():
  global icTalkTo
  global lastPTT
  global updateOLED
  global talksToMe
  while updateOLED == True:
    oledPort = [0x01,0x02,0x04,0x08]
    channelOrder = [0,4,1,5,2,6,3,7]
    channelPointer = 0
    ### LOOP THRU ALL 4 DISPLAYS
    for x in range(0, 4):
      bus.write_byte(0x70, oledPort[x])
      with canvas(device) as draw:
        ### OLED UPPER PART
        if lastPTT[channelOrder[channelPointer]] == "low":
          ### MULTIPLE TALK TO ADDRESSES?
          tmpTalk = []
          if icTalkTo[channelOrder[channelPointer]].find(",") != -1:
            talkTo = multiIcTalkTo(icTalkTo[channelOrder[channelPointer]],channelOrder[channelPointer])
            tmpTalk = icTalkTo[channelOrder[channelPointer]].split(',')
          else:
            talkTo = icTalkTo[channelOrder[channelPointer]]
            tmpTalk.append(icTalkTo[channelOrder[channelPointer]])
          ### TALKING TO ME?
          isTalking = False
          for s in talksToMe:
            for talk in tmpTalk:
              if talk == "CAMS":
                if talk[:3] in s:
                  isTalking = True
              elif talk == s:
                isTalking = True
          if isTalking == True and talksToMeState[channelOrder[channelPointer]] == 0:
            #oledDraw(display,ud,talkTo,talkedTo,isTalking)
            draw.rectangle((0,0,127,32), outline=0, fill=255)
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 8), talkTo, font=font2, fill=0)
            talksToMeState[channelOrder[channelPointer]] = 1
          else:
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 8), talkTo, font=font2, fill=255)
            talksToMeState[channelOrder[channelPointer]] = 0
        else:
          tmpTalk = []
          if icTalkTo[channelOrder[channelPointer]].find(",") != -1:
            talkTo = multiIcTalkTo(icTalkTo[channelOrder[channelPointer]],0)
            tmpTalk = icTalkTo[channelOrder[channelPointer]].split(',')
          else:
            talkTo = icTalkTo[channelOrder[channelPointer]]
            tmpTalk.append(icTalkTo[channelOrder[channelPointer]])
          ### TALKING TO ME?
          isTalking = False
          for s in talksToMe:
            for talk in tmpTalk:
              if talk == "CAMS":
                if talk[:3] in s:
                  isTalking = True
              elif talk == s:
                isTalking = True
          if isTalking == True and talksToMeState[channelOrder[channelPointer]] == 0:
            draw.rectangle((0,0,127,32), outline=0, fill=255)
            logo = Image.open('/home/pi/intercom/images/send_left.png')
            draw.bitmap((2, 8), logo, fill=0)
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 8), talkTo, font=font2, fill=0)
            logo = Image.open('/home/pi/intercom/images/send_right.png')
            draw.bitmap((106, 8), logo, fill=0)
            talksToMeState[channelOrder[channelPointer]] = 1
          else:
            logo = Image.open('/home/pi/intercom/images/send_left.png')
            draw.bitmap((2, 8), logo, fill=255)
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 8), talkTo, font=font2, fill=1)
            logo = Image.open('/home/pi/intercom/images/send_right.png')
            draw.bitmap((106, 8), logo, fill=255)
            talksToMeState[channelOrder[channelPointer]] = 0
        channelPointer+=1

        ### OLED LOWER PART
        if lastPTT[channelOrder[channelPointer]] == "low":
          tmpTalk = []
          if icTalkTo[channelOrder[channelPointer]].find(",") != -1:
            talkTo = multiIcTalkTo(icTalkTo[channelOrder[channelPointer]],channelOrder[channelPointer])
            tmpTalk = icTalkTo[channelOrder[channelPointer]].split(',')
          else:
            talkTo = icTalkTo[channelOrder[channelPointer]]
            tmpTalk.append(icTalkTo[channelOrder[channelPointer]])
          ### TALKING TO ME?
          isTalking = False
          for s in talksToMe:
            for talk in tmpTalk:
              if talk == "CAMS":
                if talk[:3] in s:
                  isTalking = True
              elif talk == s:
                isTalking = True
          if isTalking == True and talksToMeState[channelOrder[channelPointer]] == 0:
            draw.rectangle((0,33,127,64), outline=0, fill=255)
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 40), talkTo, font=font2, fill=0)
            talksToMeState[channelOrder[channelPointer]] = 1
          else:
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 40), talkTo, font=font2, fill=255)
            talksToMeState[channelOrder[channelPointer]] = 0
        else:
          tmpTalk= []
          if icTalkTo[channelOrder[channelPointer]].find(",") != -1:
            talkTo = multiIcTalkTo(icTalkTo[channelOrder[channelPointer]],channelOrder[channelPointer])
            tmpTalk = icTalkTo[channelOrder[channelPointer]].split(',')
          else:
            talkTo = icTalkTo[channelOrder[channelPointer]]
            tmpTalk.append(icTalkTo[channelOrder[channelPointer]])
          ### TALKING TO ME?
          isTalking = False
          for s in talksToMe:
            for talk in tmpTalk:
              if talk == "CAMS":
                if talk[:3] in s:
                  isTalking = True
              elif talk == s:
                isTalking = True
          if isTalking == True and talksToMeState[channelOrder[channelPointer]] == 0:
            draw.rectangle((0,33,127,64), outline=0, fill=255)
            logo = Image.open('/home/pi/intercom/images/send_left.png')
            draw.bitmap((2, 40), logo, fill=0)
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 40), talkTo, font=font2, fill=0)
            logo = Image.open('/home/pi/intercom/images/send_right.png')
            draw.bitmap((106, 50), logo, fill=0)
            talksToMeState[channelOrder[channelPointer]] = 1
          else:
            logo = Image.open('/home/pi/intercom/images/send_left.png')
            draw.bitmap((2, 40), logo, fill=255)
            textSize=draw.textsize(talkTo, font=font2)
            draw.text(((128-textSize[0])/2, 40), talkTo, font=font2, fill=1)
            logo = Image.open('/home/pi/intercom/images/send_right.png')
            draw.bitmap((106, 40), logo, fill=255)
            talksToMeState[channelOrder[channelPointer]] = 0
        channelPointer+=1
    time.sleep(0.1)

def clearBG(type):
  global updateOLED
  ### START/STOP DISPLAY FUNCTION
  if type == "Start":
    with canvas(device) as draw:
      icStartText_size=draw.textsize("Intercom", font=font2)
      draw.text(((128-icStartText_size[0])/2, 5), "Intercom", font=font2, fill=255)
      icStartText_size=draw.textsize("starting", font=font2)
      draw.text(((128-icStartText_size[0])/2, 25), "starting", font=font2, fill=255)
      icSoftVerText_size=draw.textsize(icSoftVerText, font=font2)
      draw.text(((128-icSoftVerText_size[0])/2, 45), icSoftVerText, font=font2, fill=255)
    time.sleep(4)

  if type == "Stop":
    updateOLED = False
    time.sleep(1)
    bus.write_byte(0x70, 0xFF)
    with canvas(device) as draw:
      draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)
    bus.write_byte(0x70, 0xFF)
    with canvas(device) as draw:
      draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)
      logo = Image.open('/home/pi/intercom/images/made_in_arcada_1bit_shutdown.png')
      draw.bitmap((0, 0), logo, fill=1)
    time.sleep(2)
    with canvas(device) as draw:
      draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)
    GPIO.cleanup()

def getIPInfo():
  ### GET DEVICE IP
  deviceIP = "N/A"
  try:
    intf = interface
    deviceIP = str(subprocess.check_output(['hostname', '--all-ip-addresses']).rstrip().decode())
    if deviceIP == "" or deviceIP.split(".")[0] == "169":
      deviceIP = "N/A"
    return {'deviceIP':deviceIP}
  except:
    return {'deviceIP':deviceIP}
    pass

def clean(*args):
  ### EXECUTE WHEN SCRIPT IS ABORTED
  print ("\nScript aborted")
  ### STOP BROADCASTING ON ALL ACTIVE CHANNELS
  for index in range(len(lastPTT)):
    if lastPTT[index] == "high":
      autopy3.key.toggle(str(index+1), False, autopy3.key.MOD_CONTROL)
      lastPTT[index] = "low"
  client.publish("media/intercom/status/" + deviceHostName + "/state", "OFFLINE", qos=1, retain=True)
  client.disconnect()
  clearBG("Stop")
  sys.exit(0)

def on_connect(client, userdata, flags, rc):
  print("MQTT connected...")
  global mqttStatus
  mqttStatus = rc
  client.publish("media/intercom/status/" + deviceHostName + "/state", "ONLINE", qos=1, retain=True)
  client.publish("media/intercom/status/" + deviceHostName + "/deviceChannels", len(icTalkTo), qos=1, retain=True)
  ### SUBSCRIBE TO ROLE (icUser)
  client.subscribe("media/intercom/setup/" + deviceHostName + "/deviceRole", qos=1)
  client.subscribe("media/intercom/broadcast/+/talk", qos=1)
  chCounter = 1
  for ch in icTalkTo:
    client.subscribe("media/intercom/setup/" + deviceHostName + "/channel/" + str(chCounter), qos=1)
    chCounter += 1

def on_disconnect(client, userdata, rc):
  print("MQTT disconnected!!")
  global mqttStatus
  mqttStatus = rc

def on_message(client, userdata, message):
  if message.topic == "media/intercom/setup/" + deviceHostName + "/deviceRole":
    global icUser
    icUser = str(message.payload.decode())
    client.publish("media/intercom/status/" + deviceHostName + "/deviceRole", icUser, qos=1, retain=True)

  if "media/intercom/setup/" + deviceHostName + "/channel/" in message.topic:
    chCounter = 1
    global icTalkTo
    for ch in icTalkTo:
      if message.topic == "media/intercom/setup/" + deviceHostName + "/channel/" + str(chCounter):
        icTalkTo[chCounter-1] = str(message.payload.decode())
        client.publish("media/intercom/status/" + deviceHostName + "/channel/" + str(chCounter), icTalkTo[chCounter-1], qos=1, retain=True)
      chCounter += 1

  if "media/intercom/broadcast/" and "/talk" in message.topic:
    global talksToMe
    print(message.topic)
    print(message.payload.decode())

    talks = False
    talkFrom = message.topic.replace("media/intercom/broadcast/","")
    talkFrom = talkFrom.replace("/talk","")

    if b"," not in message.payload:
      otherToMe = [""]
      otherToMe[0] = str(message.payload.decode())
    else:
      otherToMe = [""]
      otherToMe = str(message.payload.decode().split(','))

    if icUser in otherToMe:
      talks = True

    if talks == True:
      talksToMe.append(talkFrom)
    else:
      if talkFrom in talksToMe:
        talksToMe.remove(talkFrom)

bus = smbus2.SMBus(1)
bus.write_byte(0x70, 0xFF)
device = ssd1306(port=0, address=0x3c, rotate=0)

clearBG("Start")

### OWN THREAD FOR OLED UPDATE
try:
   t = Thread(target=oledUpdate, args=())
   t.start()
except:
   print("Error: unable to start thread")

def connectMQTT():
  ### MQTT connection
  try:
    client.connect_async(mqttServer, mqttPort, mqttTimeOut)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.loop_start()
  except:
    pass

client = mqtt.Client(client_id=deviceHostName, clean_session=False, userdata=None)
client.tls_set("/home/pi/intercom/ca.crt")
### USE INSECURE IF YOUR CERTIFICATE IS SELF SIGNED
client.tls_insecure_set(True)
client.username_pw_set(mqttUser, password=mqttPass)
client.will_set("media/intercom/status/" + deviceHostName + "/state", "OFFLINE", qos=1, retain=True)

while True:
  ### DO WE HAVE AN IP ADDRESS?
  if deviceIP == "N/A":
    icTalkTo[0] = "NO IP"
    deviceInfo = getIPInfo()
    deviceIP = deviceInfo['deviceIP']
  ### IS MQTT CONNECTED?
  if mqttStatus > 0:
    if deviceIP == "N/A":
      icTalkTo[0]="NO IP"
    else:
      icTalkTo[0]=deviceIP
    icTalkTo[4]=mqttStatusCodes[mqttStatus]
    if deviceIP != "N/A":
      icTalkTo[0]=deviceIP
      connectMQTT()
  for keyCounter, portNum in enumerate(pttPorts):
    if GPIO.input(portNum) == 1:
      if lastPTTHigh[keyCounter] == 0:
        lastPTTHigh[keyCounter] = int((time.time() + 0.5) * 1000)
      if lastPTT[keyCounter] == "low" or lastPTT[keyCounter] == "":
        ### PUSH AND HOLD "CTRL + 1" ###
        autopy3.key.toggle(str(keyCounter+1), True, autopy3.key.MOD_CONTROL)
        lastPTT[keyCounter] = "high"
      lastPTTLow[keyCounter] = 0
    else:
      if lastPTTLow[keyCounter] == 0:
        lastPTTLow[keyCounter] = int((time.time() + 0.5) * 1000)
        ### CHECK IF PTT PRESS WAS SHORT
        if lastPTTHigh[keyCounter] + 600 >= lastPTTLow[keyCounter]:
          if pttLocked[keyCounter] == True:
            pttLocked[keyCounter] = False
          else:
            pttLocked[keyCounter] = True
        else:
          pttLocked[keyCounter] = False
      ### IF lastPTT[x] LAST STATE WAS HIGH AND lastPTT[x] PTT STATE IS NOT LOCKED -> SET lastPTT[x] LOW ###
      if (lastPTT[keyCounter] == "high" or lastPTT[keyCounter] == "") and pttLocked[keyCounter] == False:
        ### RELEASE "CTRl + 1" ###
        autopy3.key.toggle(str(keyCounter+1), False, autopy3.key.MOD_CONTROL)
        lastPTT[keyCounter] = "low"
        ### Loop to ensure that all active channels are broadcasting
        for index in range(len(lastPTT)):
          if lastPTT[index] == "high":
            autopy3.key.toggle(str(index+1), True, autopy3.key.MOD_CONTROL)
      lastPTTHigh[keyCounter] = 0
  talkList = []
  for idx, val in enumerate(lastPTT):
    if val == "high":
      talkList.append(icTalkTo[idx])

  ### TURN OFF SYSTEM IF POWER OFF BUTTON IS PRESSED FOR 3 OR MORE SECONDS
  if GPIO.input(powPort) == 1:
    if (lastPO <= int(round(time.time() * 1000)) - 3000) and poOK == False:
      poOK = True
      ### STOP BROADCASTING ON ALL ACTIVE CHANNELS
      for index in range(len(lastPTT)):
        if lastPTT[index] == "high":
          autopy3.key.toggle(str(index+1), False, autopy3.key.MOD_CONTROL)
          lastPTT[index] = "low"
      client.publish("media/intercom/status/" + deviceHostName + "/state", "OFFLINE", qos=1, retain=True)
      client.disconnect()
      clearBG("Stop")
      os.system('poweroff')
      sys.exit(0)
  else:
    poOK = False
    lastPO = int(round(time.time() * 1000))

  ### PUBLISH TALK STATUS TO MQTT SERVER
  if (icUser != ""):
    if (','.join(talkList) != lastTalkList):
      if len(talkList) == 0:
        result = client.publish("media/intercom/broadcast/" + icUser + "/talk", "NOT TALKING", qos=1, retain=True)
      else:
        result = client.publish("media/intercom/broadcast/" + icUser + "/talk", ','.join(talkList), qos=1, retain=True)
      # TODO CHECK IF MESSAGE WAS RECEIVED
      lastTalkList = ','.join(talkList)


  if (lastStatusSent == 0 or int(round(time.time() * 1000))-statusInterval >= lastStatusSent):
      ### Publish device status
      lastStatusSent = int(round(time.time() * 1000))
      client.publish("media/intercom/status/" + deviceHostName + "/deviceRole", icUser, qos=1, retain=True)
      client.publish("media/intercom/status/" + deviceHostName + "/deviceChannels", len(icTalkTo), qos=1, retain=True)
      chCount = 1
      for chData in icTalkTo:
        client.publish("media/intercom/status/" + deviceHostName + "/channel/" + str(chCount), chData, qos=1, retain=True)
        chCount += 1

  ### WAIT FOR 100 MS BEFORE START THE LOOP AGAIN ###
  time.sleep(0.1)

  ### CATCH INTERRUPTIONS ###
  for sig in (SIGINT, SIGTERM, SIGABRT, SIGILL, SIGHUP, SIGSEGV):
    signal(sig, clean)
