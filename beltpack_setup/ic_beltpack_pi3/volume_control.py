import smbus2, subprocess, time

lastVolume = 0
bus=smbus2.SMBus(1)

def translate(sensor_val, in_from, in_to, out_from, out_to):
    out_range = out_to - out_from
    in_range = in_to - in_from
    in_val = sensor_val - in_from
    val=(float(in_val)/in_range)*out_range
    out_val = out_from+val
    return out_val

while True:
  data = [0x84,0x83]
  bus.write_i2c_block_data(0x4a, 0x01, data)
  data = bus.read_i2c_block_data(0x4a,0x00, 2)
  raw_adc = data[0] * 256 + data[1]
  if raw_adc > 32767:
    raw_adc -= 65535
  # UNCOMMENT NEXT LINE FOR FINE-TUNING OF POTENTIOMETER
  #print(raw_adc)
  # Translate analog input from 0 to 100
  volume = int(translate(raw_adc,20680,-4600,0,100))
  if lastVolume <= volume -2 or lastVolume >= volume + 2:
    # UNCOMMENT NEXT LINE TO CHECK DATA FED INTO SOUNDCARD
    #print("Digital Value of Analog Input : %d" %volume)
    subprocess.Popen('amixer -q -c1 set Speaker ' + str(volume) + '%', shell=True)
    lastVolume = volume
  time.sleep(0.25)
