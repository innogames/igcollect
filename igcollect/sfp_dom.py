#!/usr/bin/env python3
"""igcollect - SFP Digital Optical Monitoring metric collector

Copyright (c) 2022 InnoGames GmbH

This script reads SFP EEPROM and parses it in order to collect optical
diagnostics data.

To properly understand what happens on this script, a read of the SFF-8472
standard is highly recommended.
"""
import ctypes
import fcntl
import socket
import struct
import sys

from argparse import ArgumentParser
from os import listdir
from os.path import isdir, islink, join
from time import time

# From include/uapi/linux/if.h
IFNAMSIZ = 16

# From include/uapi/linux/sockios.h
SIOCETHTOOL = 0x8946

# From include/uapi/linux/ethtool.h
ETHTOOL_GMODULEINFO = 0x00000042  # Get plug-in module information
ETHTOOL_GMODULEEEPROM = 0x00000043  # Get plug-in module EEPROM

# From include/uapi/linux/ethtool.h
ETH_MODULE_SFF_8079 = 0x1
ETH_MODULE_SFF_8079_LEN = 256
ETH_MODULE_SFF_8472 = 0x2
ETH_MODULE_SFF_8472_LEN = 512
ETH_MODULE_SFF_8636 = 0x3
ETH_MODULE_SFF_8636_LEN = 256
ETH_MODULE_SFF_8436 = 0x4
ETH_MODULE_SFF_8436_LEN = 256

# From ethtool/sfpdiag.c
SFF_A0_DOM = 92
SFF_A0_DOM_PWRT = (1 << 3)
SFF_A0_DOM_EXTCAL = (1 << 4)

# From ethtool/sfpdiag.c
SFF_A2_BASE = 0x100
SFF_A2_TEMP = 96
SFF_A2_TEMP_HALRM = 0
SFF_A2_TEMP_LALRM = 2
SFF_A2_TEMP_HWARN = 4
SFF_A2_TEMP_LWARN = 6
SFF_A2_VCC = 98
SFF_A2_VCC_HALRM = 8
SFF_A2_VCC_LALRM = 10
SFF_A2_VCC_HWARN = 12
SFF_A2_VCC_LWARN = 14
SFF_A2_BIAS = 100
SFF_A2_BIAS_HALRM = 16
SFF_A2_BIAS_LALRM = 18
SFF_A2_BIAS_HWARN = 20
SFF_A2_BIAS_LWARN = 22
SFF_A2_TX_PWR = 102
SFF_A2_TX_PWR_HALRM = 24
SFF_A2_TX_PWR_LALRM = 26
SFF_A2_TX_PWR_HWARN = 28
SFF_A2_TX_PWR_LWARN = 30
SFF_A2_RX_PWR = 104
SFF_A2_RX_PWR_HALRM = 32
SFF_A2_RX_PWR_LALRM = 34
SFF_A2_RX_PWR_HWARN = 36
SFF_A2_RX_PWR_LWARN = 38


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='sfp_dom')
    return parser.parse_args()


def main():
    args = parse_args()
    physical_interfaces = get_physical_interfaces()

    for iface in physical_interfaces:
        try:
            data = ethtool_get_module_data(iface)
            print_metrics(args.prefix, iface, data.metrics)
        except (NoSFPException, UnsupportedSFPException) as exc:
            print(exc, file=sys.stderr)
            continue


def get_physical_interfaces():
    scn = '/sys/class/net'
    physical_interfaces = []
    for dev in listdir(scn):
        # Physical interfaces have device as a symlink to /sys/class/device_id
        if islink(join(scn, dev, 'device')):
            physical_interfaces.append(dev)

    return physical_interfaces


def a2_offset_to_celsius(data, offset):
    """
    Returns a signed float built from a 16-bit signed int.
    Each LSB is equivalent to an increment of 1/256 degrees Celsius.
    """
    signed = struct.unpack_from('>h', data, SFF_A2_BASE + offset)[0]
    return signed / 256


def a2_offset_to_volts(data, offset):
    """
    Voltage is 16-bit unsigned integer with LSB equal to 100µV.
    The divison by 10000 yields a value in Volts.
    """
    return a2_offset_to_int(data, offset) / 10000


def a2_offset_to_milliwatts(data, offset):
    """
    Power is a 16-bit unsigned integer with LSB equal to 0.1µW.
    The division by 10000 yields a value in mW.
    """
    return a2_offset_to_int(data, offset) / 10000


def a2_offset_to_milliamps(data, offset):
    """
    Bias current is 16-bit unsigned integer with LSB equal to 2µA.
    The division by 500 yields a value in mA.
    """
    return a2_offset_to_int(data, offset) / 500


def a2_offset_to_int(data, offset):
    """
    Returns an integer built from a 16-bit unsigned integer obtained from
    data, at the specified offset
    """
    return struct.unpack_from('>H', data, SFF_A2_BASE + offset)[0]


def print_metrics(prefix, interface, metrics):
    timestamp = int(time())
    for metric, child in metrics.items():
        for value_key, value in child.items():
            print(
                f'{prefix}.{interface}.{metric}.{value_key}'
                f' {value} {timestamp}'
            )


def ethtool_get_module_data(interface):
    """
    Using the received interface name, we perform an ioctl call to read the
    length and type of the SFP module plugged.
    With this information, we make a second ioctl call that reads the
    contents of the whole EEPROM.
    Last, we create and return an SFPData object that contains the EEPROM
    data parsed and already converted into proper metrics.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # This is a ctypes byte array of size IFNAMSIZ built from the
    # interface name.
    name = (ctypes.c_ubyte * IFNAMSIZ)(*bytearray(str(interface).encode()))
    ifr = IFReq(ifr_name=name)

    # Build the struct with the ETHTOOL_GMODULEINFO command and request.
    # Objects below are ctypes structs that will be later used with the
    # ioctl calls.
    em = EthtoolModinfo(cmd=ETHTOOL_GMODULEINFO)
    ifr.ifr_data.ethtool_modinfo_ptr = ctypes.pointer(em)

    # If the queried interface doesn't have an SFP module (a copper interface
    # for example), the ioctl returns OSError 95. We change the exception,
    # so we can deal with it properly.
    try:
        fcntl.ioctl(sock, SIOCETHTOOL, ifr)
    except OSError as exc:
        if exc.errno == 95:
            raise NoSFPException(f'Interface {interface} has no SFP module') \
                from exc
        else:
            raise

    # Build the struct with the ETHTOOL_GMODULEEEPROM command and request.
    # Objects below are ctypes structs that will be later used with the
    # ioctl calls.
    ee = EthtoolEEPROM(cmd=ETHTOOL_GMODULEEEPROM, len=em.eeprom_len, offset=0)
    ifr.ifr_data.ethtool_eeprom_ptr = ctypes.pointer(ee)

    fcntl.ioctl(sock, SIOCETHTOOL, ifr)

    if em.type == ETH_MODULE_SFF_8472:
        return SFPData(ee.data, interface)

    raise UnsupportedSFPException(f'SFP type {em.type} is not supported')


class EthtoolModinfo(ctypes.Structure):
    _fields_ = [
        ('cmd', ctypes.c_uint32),
        ('type', ctypes.c_uint32),
        ('eeprom_len', ctypes.c_uint32),
        ('reserved', ctypes.c_uint32 * 8)
    ]


class EthtoolEEPROM(ctypes.Structure):
    _fields_ = [
        ('cmd', ctypes.c_uint32),
        ('magic', ctypes.c_uint32),
        ('offset', ctypes.c_uint32),
        ('len', ctypes.c_uint32),
        ('data', ctypes.c_byte * 512)
    ]


class IFRData(ctypes.Union):
    _fields_ = [
        ('ethtool_modinfo_ptr', ctypes.POINTER(EthtoolModinfo)),
        ('ethtool_eeprom_ptr', ctypes.POINTER(EthtoolEEPROM)),
    ]


class IFReq(ctypes.Structure):
    _fields_ = [
        ('ifr_name', (ctypes.c_ubyte * IFNAMSIZ)),
        ('ifr_data', IFRData)
    ]


class SFPData:
    FN_MAP = {
        'temperature': a2_offset_to_celsius,
        'bias_current_lane1': a2_offset_to_milliamps,
        'sfp_voltage': a2_offset_to_volts,
        'tx_power_lane1': a2_offset_to_milliwatts,
        'rx_power_lane1': a2_offset_to_milliwatts,
    }

    OFFSET_MAP = {
        'temperature': {
            'current': SFF_A2_TEMP,
            'low_warning': SFF_A2_TEMP_LWARN,
            'high_warning': SFF_A2_TEMP_HWARN,
            'low_critical': SFF_A2_TEMP_LALRM,
            'high_critical': SFF_A2_TEMP_HALRM,
        },
        'bias_current_lane1': {
            'current': SFF_A2_BIAS,
            'low_warning': SFF_A2_BIAS_LWARN,
            'high_warning': SFF_A2_BIAS_HWARN,
            'low_critical': SFF_A2_BIAS_LALRM,
            'high_critical': SFF_A2_BIAS_HALRM,
        },
        'sfp_voltage': {
            'current': SFF_A2_VCC,
            'low_warning': SFF_A2_VCC_LWARN,
            'high_warning': SFF_A2_VCC_HWARN,
            'low_critical': SFF_A2_VCC_LALRM,
            'high_critical': SFF_A2_VCC_HALRM,
        },
        'tx_power_lane1': {
            'current': SFF_A2_TX_PWR,
            'low_warning': SFF_A2_TX_PWR_LWARN,
            'high_warning': SFF_A2_TX_PWR_HWARN,
            'low_critical': SFF_A2_TX_PWR_LALRM,
            'high_critical': SFF_A2_TX_PWR_HALRM,
        },
        'rx_power_lane1': {
            'current': SFF_A2_RX_PWR,
            'low_warning': SFF_A2_RX_PWR_LWARN,
            'high_warning': SFF_A2_RX_PWR_HWARN,
            'low_critical': SFF_A2_RX_PWR_LALRM,
            'high_critical': SFF_A2_RX_PWR_HALRM,
        },
    }

    def __init__(self, data, interface):
        # Check if SFP data is externally calibrated. We don't support it.
        external_calibration = data[SFF_A0_DOM] & SFF_A0_DOM_EXTCAL
        if external_calibration:
            raise UnsupportedSFPException(
                'SFPs calibrated externally are not supported'
            )

        # We finish the object creation only if the SFP is internally
        # calibrated.
        self._data = data
        self.interface = interface
        self.metrics = {
            'temperature': {
                'current': None,
                'low_warning': None,
                'high_warning': None,
                'low_critical': None,
                'high_critical': None,
            },
            'bias_current_lane1': {
                'current': None,
                'low_warning': None,
                'high_warning': None,
                'low_critical': None,
                'high_critical': None,
            },
            'sfp_voltage': {
                'current': None,
                'low_warning': None,
                'high_warning': None,
                'low_critical': None,
                'high_critical': None,
            },
            'tx_power_lane1': {
                'current': None,
                'low_warning': None,
                'high_warning': None,
                'low_critical': None,
                'high_critical': None,
            },
            'rx_power_lane1': {
                'current': None,
                'low_warning': None,
                'high_warning': None,
                'low_critical': None,
                'high_critical': None,
            },
        }
        self._parse_eeprom_data()

    def _parse_eeprom_data(self):
        for metric in self.metrics:
            for value in self.metrics[metric]:
                self.metrics[metric][value] = self.FN_MAP[metric](
                    self._data, self.OFFSET_MAP[metric][value]
                )


class NoSFPException(Exception):
    pass


class UnsupportedSFPException(Exception):
    pass


if __name__ == '__main__':
    main()
