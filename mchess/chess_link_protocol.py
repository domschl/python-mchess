
"""
Helper functions for the Chess Link protocol for character-based odd-parity and 
message-block-parity.

The chess link protocol sends ASCII messages. Each ASCII character gets an additional
odd-parity-bit. Each block of ASCII+odd-parity bytes gets an additional block parity.
"""

import logging

protocol_replies = {'v': 7, 's': 67, 'l': 3, 'x': 3, 'w': 7, 'r': 7}


def add_odd_par(b):
    """
    The chess link protocol is 7-Bit ASCII. This adds an odd-parity-bit to an ASCII char

    :param b: an ASCII character (0..127)
    :returns: a byte (0..255) with odd parity in most significant bit.
    """
    byte = ord(b) & 127
    par = 1
    for _ in range(7):
        bit = byte & 1
        byte = byte >> 1
        par = par ^ bit
    if par == 1:
        byte = ord(b) | 128
    else:
        byte = ord(b) & 127
    return byte


def hexd(digit):
    """
    Returns a hex digit '0'..'F' for an integer 0..15

    :param digit: integer 0..15
    :return: an ASCII hex character '0'..'F'
    """
    if digit < 10:
        return chr(ord('0')+digit)
    else:
        return chr(ord('A')-10+digit)


def hex2(num):
    """
    Returns a 2-digit hex code '00'..FF for an uint_8 integer 0..255
    """
    d1 = num//16
    d2 = num % 16
    s = hexd(d1)+hexd(d2)
    return s


def check_block_crc(msg):
    """
    Chess link messages consist of 7-bit-ASCII characters with odd parity. At the end of each
    message, an additional block-parity is added. Valid chess link messages must have correct odd
    parity for each character and a valid block parity at the end.
    """
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
    """Add block parity at the end of the message"""
    gpar = 0
    for b in msg:
        gpar = gpar ^ ord(b)
    msg = msg+hex2(gpar)
    return msg
