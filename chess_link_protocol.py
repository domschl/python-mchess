
import logging

millennium_protocol_replies = {'v': 7, 's': 67, 'l': 3, 'x': 3, 'w': 7, 'r': 7}


def add_odd_par(b):
    byte = ord(b) & 127
    par = 1
    for _ in range(7):
        bit = byte & 1
        byte = byte >> 1
        par = par ^ bit
    if par == 1:
        # byte = ord(b) & 127
        byte = ord(b) | 128
    else:
        byte = ord(b) & 127
    return byte


def hexd(digit):
    if digit < 10:
        return chr(ord('0')+digit)
    else:
        return chr(ord('A')-10+digit)


def hex2(num):
    d1 = num//16
    d2 = num % 16
    s = hexd(d1)+hexd(d2)
    return s


def check_block_crc(msg):
    if len(msg) > 2:
        gpar = 0
        for b in msg[:-2]:
            gpar = gpar ^ ord(b)
        if msg[-2]+msg[-1] != hex2(gpar):
            logging.warning("CRC error rep={} CRCs: {}!={}".format(msg,
                                                                   ord(msg[-2]), hex2(gpar)))
            return False
        else:
            return True
    else:
        logging.warning("Message {} too short for CRC check".format(msg))
        return False


def add_block_crc(msg):
    gpar = 0
    for b in msg:
        gpar = gpar ^ ord(b)
    msg = msg+hex2(gpar)
    return msg
