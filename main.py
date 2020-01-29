#!/usr/bin/env python
import time
import utime
import binascii
import math
import socket
import pycom
import config
from machine import Pin
from network import LoRa
from pytrack import Pytrack
from l76lsbr import L76LSBR

# Colors
off = 0x000000
red = 0xFF0000
green = 0x00FF00
blue = 0x0000FF
orange = 0xFFA500

last_lat_tx = 0.0
last_lon_tx = 0.0

def nmea_to_decimal(latlon, latlon_nsew):
    """
        Convert latitude or longitude from NMEA GGA format to decimal
    """

    latlond = (float(latlon) // 100) + ((float(latlon) % 100) / 60)
    if latlon_nsew == 'S' or latlon_nsew == 'W':
        latlond *= -1

    return latlond


def decimal_to_payload(latd, lond, alt, hdop):
    """
        Convert to binary LoRaWAN payload
    """
    payload = []

    latb = int(((latd + 90) / 180) * 0xFFFFFF)
    payload.append((latb >> 16) & 0xFF)
    payload.append((latb >> 8) & 0xFF)
    payload.append(latb & 0xFF)

    lonb = int(((lond + 180) / 360) * 0xFFFFFF)
    payload.append((lonb >> 16) & 0xFF)
    payload.append((lonb >> 8) & 0xFF)
    payload.append(lonb & 0xFF)

    altb = int(round(float(alt), 0))
    payload.append((altb >> 8) & 0xFF)
    payload.append(altb & 0xFF)

    hdopb = int(float(hdop) * 100)
    payload.append(hdopb & 0xFF)

    return payload

# Turn off hearbeat LED
pycom.heartbeat(False)
pycom.rgbled(off)

force_join_input = Pin('P11', mode=Pin.IN, pull=Pin.PULL_UP)
force_join = not force_join_input.value()
print('Force join : {}'.format(force_join))

py = Pytrack()
receiver = L76LSBR(py)

# Initialize LoRaWAN radio
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

if not force_join:
    print('Restoring LoraWAN parameters from NVRAM')
    lora.nvram_restore()
    time.sleep(0.5)
    print ('Checking joined status')
    if lora.has_joined():
        print('OK')
        pycom.rgbled(blue)
        time.sleep(0.2)
        pycom.rgbled(off)
        lora.nvram_save()
    else:
        print('NAK')
        force_join = True

if force_join:

    print('Performing LoraWAN OTAA join')
    app_eui = binascii.unhexlify(config.app_eui_str)
    app_key = binascii.unhexlify(config.app_key_str)
    lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)
    pycom.rgbled(blue)

    # Loop until joined
    while not lora.has_joined():
        print('Not joined yet...')
        pycom.rgbled(off)
        time.sleep(0.2)
        pycom.rgbled(blue)
        time.sleep(2)

    print('Joined !')
    pycom.rgbled(off)
    lora.nvram_save()

s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)
s.setblocking(True)

while True:
    blink_color = red

    gga = receiver.get_gga()
    fields = gga.decode().split(',')
    print(fields)
    #fix_time = fields[1]
    lat = fields[2]
    lat_ns = fields[3]
    lon = fields[4]
    lon_ew = fields[5]
    fix_status = int(fields[6])
    #nb_sv = int(fields[7])
    hdop = fields[8]
    alt = fields[9]

    if (fix_status > 0) and (float(hdop) < 1.5):
        blink_color = orange
        latd = nmea_to_decimal(lat, lat_ns)
        lond = nmea_to_decimal(lon, lon_ew)

        delta = math.sqrt((latd-last_lat_tx)**2 + (lond-last_lon_tx)**2)
        print(delta)

        if delta > 0.0002:
            blink_color = green
            payload = decimal_to_payload(latd, lond, alt, hdop)
            print(payload)

            count = s.send(bytes(payload))
            print('Sent %s bytes' % count)

            last_lat_tx = latd
            last_lon_tx = lond

            time.sleep(0.5)
            lora.nvram_save()

    pycom.rgbled(blink_color)
    time.sleep(0.2)
    pycom.rgbled(off)
    time.sleep(4)
