import bluetooth
# simple inquiry example

nearby_devices = bluetooth.discover_devices(lookup_names=True)
print("found %d devices" % len(nearby_devices))

for addr, name in nearby_devices:
    print("  %s - %s" % (addr, name))


from bluetooth.ble import DiscoveryService

service = DiscoveryService()
devices = service.discover(4)

for address, name in devices.items():
    print("name: {}, address: {}".format(name, address))
