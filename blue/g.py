import pygatt
import logging

logging.basicConfig()
logging.getLogger('pygatt').setLevel(logging.DEBUG)

adapter = pygatt.BGAPIBackend()
adapter.start()

