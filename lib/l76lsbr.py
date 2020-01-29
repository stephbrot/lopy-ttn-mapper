"""
Quectel GNSS L76-L (GPS) I2C driver
"""

import utime
from machine import I2C

class L76LSBR:

    GPS_I2CADDR = const(0x10)

    def __init__(self, pytrack=None, sda='P22', scl='P21'):
        if pytrack is not None:
            self.i2c = pytrack.i2c
        else:
            from machine import I2C
            self.i2c = I2C(0, mode=I2C.MASTER, pins=(sda, scl))

        self.reg = bytearray(1)
        self.i2c.writeto(GPS_I2CADDR, self.reg)

    def get_gga(self, chunksize=255):
        while True:
            data = self.i2c.readfrom(GPS_I2CADDR, chunksize)
            while data[-2:] !=b'\x0a\x0a':
                utime.sleep_ms(2)
                data = data + self.i2c.readfrom(GPS_I2CADDR, chunksize)
            data = data.replace(b'\x0a', b'').replace(b'\x0d', b'\x0d\x0a')
            for sentence in data.split():
                if sentence[3:6] == b'GGA':
                    # Sometimes, for unknown reason, get incomplete GGA
                    # sentence. Check at least that we return a sentence with
                    # the right number of fields
                    if len(sentence.decode().split(',')) == 15:
                        return sentence
            utime.sleep_ms(500)
