#!/usr/bin/env python
from __future__ import print_function

import binascii
import pygatt

# 34:81:F4:47:31:DE Millennium
#

# YOUR_DEVICE_ADDRESS = "44:85:00:2C:E5:D8"
YOUR_DEVICE_ADDRESS = "34:81:F4:47:31:DE"

# Many devices, e.g. Fitbit, use random addressing - this is required to
# connect.
ADDRESS_TYPE = pygatt.BLEAddressType.random

adapter = pygatt.GATTToolBackend()
# adapter = pygatt.BGAPIBackend()
adapter.start()
print("Started adapter")
device = adapter.connect(
    YOUR_DEVICE_ADDRESS, timeout=10)

for uuid in device.discover_characteristics().keys():
    # print("Read UUID %s: %s" % (uuid, binascii.hexlify(device.char_read(uuid))))
    print("UUID {}".format(uuid))
