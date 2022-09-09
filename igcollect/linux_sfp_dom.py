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
from os.path import islink, join
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
SFF_A0_ID_OFFSET = 0x00
SFF_A0_DOM = 92
SFF_A0_DOM_PWRT = (1 << 3)
SFF_A0_DOM_EXTCAL = (1 << 4)
SFF_A0_DOM_IMPL = (1 << 6)

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

# From ethtool/sff-common.h
SFF8024_ID_UNKNOWN = 0x00
SFF8024_ID_QSFP = 0x0C
SFF8024_ID_QSFP_PLUS = 0x0D
SFF8024_ID_QSFP28 = 0x11

# From ethtool/qsfp.h
SFF8636_ID_OFFSET = 0x00
SFF8636_TEMP_CURR = 0x16
SFF8636_VCC_CURR = 0x1A
SFF8636_RX_PWR_1_OFFSET = 0x22
SFF8636_RX_PWR_2_OFFSET = 0x24
SFF8636_RX_PWR_3_OFFSET = 0x26
SFF8636_RX_PWR_4_OFFSET = 0x28
SFF8636_TX_BIAS_1_OFFSET = 0x2A
SFF8636_TX_BIAS_2_OFFSET = 0x2C
SFF8636_TX_BIAS_3_OFFSET = 0x2E
SFF8636_TX_BIAS_4_OFFSET = 0x30
SFF8636_TX_PWR_1_OFFSET = 0x32
SFF8636_TX_PWR_2_OFFSET = 0x34
SFF8636_TX_PWR_3_OFFSET = 0x36
SFF8636_TX_PWR_4_OFFSET = 0x38

SFF8636_TEMP_HALRM = 0x80
SFF8636_TEMP_LALRM = 0x82
SFF8636_TEMP_HWARN = 0x84
SFF8636_TEMP_LWARN = 0x86
SFF8636_VCC_HALRM = 0x90
SFF8636_VCC_LALRM = 0x92
SFF8636_VCC_HWARN = 0x94
SFF8636_VCC_LWARN = 0x96
SFF8636_RX_PWR_HALRM = 0xB0
SFF8636_RX_PWR_LALRM = 0xB2
SFF8636_RX_PWR_HWARN = 0xB4
SFF8636_RX_PWR_LWARN = 0xB6
SFF8636_TX_BIAS_HALRM = 0xB8
SFF8636_TX_BIAS_LALRM = 0xBA
SFF8636_TX_BIAS_HWARN = 0xBC
SFF8636_TX_BIAS_LWARN = 0xBE
SFF8636_TX_PWR_HALRM = 0xC0
SFF8636_TX_PWR_LALRM = 0xC2
SFF8636_TX_PWR_HWARN = 0xC4
SFF8636_TX_PWR_LWARN = 0xC6

SFF8636_PAGE3_OFFSET = 0x180
ETH_MODULE_SFF_8636_MAX_LEN = 640


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
            timestamp = int(time())
            data.print_metrics(args.prefix, timestamp)
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
        # On Cumulus switches, it's impossible to differentiate the switchport
        # interfaces by just looking at /sys/class/net.
        if 'swp' in dev and len(dev.replace('swp', '')) > 0:
            physical_interfaces.append(dev)

    return physical_interfaces


def a2_offset_to_celsius(data, offset):
    return offset_to_celsius(data, SFF_A2_BASE + offset)


def a2_offset_to_volts(data, offset):
    return offset_to_volts(data, SFF_A2_BASE + offset)


def a2_offset_to_milliwatts(data, offset):
    return offset_to_milliwatts(data, SFF_A2_BASE + offset)


def a2_offset_to_milliamps(data, offset):
    return offset_to_milliamps(data, SFF_A2_BASE + offset)


def sff8636_offset_to_celsius(data, offset):
    return offset_to_celsius(data, SFF8636_PAGE3_OFFSET + offset)


def sff8636_offset_to_milliamps(data, offset):
    return offset_to_milliamps(data, SFF8636_PAGE3_OFFSET + offset)


def sff8636_offset_to_milliwatts(data, offset):
    return offset_to_milliwatts(data, SFF8636_PAGE3_OFFSET + offset)


def sff8636_offset_to_volts(data, offset):
    return offset_to_volts(data, SFF8636_PAGE3_OFFSET + offset)


def offset_to_milliamps(data, offset):
    """
    Bias current is 16-bit unsigned integer with LSB equal to 2µA.
    The division by 500 yields a value in mA.
    """
    return offset_to_int(data, offset) / 500


def offset_to_volts(data, offset):
    """
    Voltage is 16-bit unsigned integer with LSB equal to 100µV.
    The divison by 10000 yields a value in Volts.
    """
    return offset_to_int(data, offset) / 10000


def offset_to_milliwatts(data, offset):
    """
    Power is a 16-bit unsigned integer with LSB equal to 0.1µW.
    The division by 10000 yields a value in mW.
    """
    return offset_to_int(data, offset) / 10000


def offset_to_int(data, offset):
    """
    Returns an integer built from a 16-bit unsigned integer obtained from
    data, at the specified offset.
    """
    return struct.unpack_from('>H', data, offset)[0]


def offset_to_celsius(data, offset):
    """
    Returns a signed float built from a 16-bit signed int at the given offset.
    Each LSB is equivalent to an increment of 1/256 degrees Celsius.
    """
    signed = struct.unpack_from('>h', data, offset)[0]
    return signed / 256


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
        # Cumulus will return OSError 5 when you query for eth0, eth1
        # Debian will return OSError 95 for interfaces without SFP
        if exc.errno == 5 or exc.errno == 95:
            raise NoSFPException(f'{interface}: SFP not present') \
                from exc
        else:
            raise

    # Build the struct with the ETHTOOL_GMODULEEEPROM command and request.
    # Objects below are ctypes structs that will be later used with the
    # ioctl calls.
    # We limit the length to ETH_MODULE_SFF_8636_MAX_LEN, as that is the
    # biggest size of an EEPROM according to the standard and we don't want
    # buffer overruns.
    length = min(ETH_MODULE_SFF_8636_MAX_LEN, em.eeprom_len)
    ee = EthtoolEEPROM(cmd=ETHTOOL_GMODULEEEPROM, len=length, offset=0)
    ifr = IFReq(ifr_name=name)
    ifr.ifr_data.ethtool_eeprom_ptr = ctypes.pointer(ee)

    fcntl.ioctl(sock, SIOCETHTOOL, ifr)

    if em.type == ETH_MODULE_SFF_8472:
        return SFF8472Data(ee.data, interface)
    # SFF8436 and SFF8636 share the same data format
    elif em.type == ETH_MODULE_SFF_8436 or em.type == ETH_MODULE_SFF_8636:
        return SFF8636Data(ee.data, interface)

    raise UnsupportedSFPException(
        f'{interface}: SFP type {em.type} is not supported'
    )


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
        ('data', ctypes.c_byte * ETH_MODULE_SFF_8636_MAX_LEN)
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


class SFFChannelData:
    bias_current = None
    rx_power = None
    tx_power = None

    def set_values(self, bias_current=None, rx_power=None, tx_power=None):
        self.bias_current = bias_current
        self.rx_power = rx_power
        self.tx_power = tx_power

    def get_values(self):
        return {
            'bias_current': self.bias_current,
            'rx_power': self.rx_power,
            'tx_power': self.tx_power,
        }


class SFFData:
    OFFSET_MAP = None

    interface = None

    supports_dom = None
    supports_alarms = None
    rx_power_type = None
    tx_power_type = None

    _data = None

    sfp_voltage = {
        'current': None,
        'low_warning': None,
        'high_warning': None,
        'low_critical': None,
        'high_critical': None,
    }
    temperature = {
        'current': None,
        'low_warning': None,
        'high_warning': None,
        'low_critical': None,
        'high_critical': None,
    }
    bias_current = {
        'low_warning': None,
        'high_warning': None,
        'low_critical': None,
        'high_critical': None,
    }
    tx_power = {
        'low_warning': None,
        'high_warning': None,
        'low_critical': None,
        'high_critical': None,
    }
    rx_power = {
        'low_warning': None,
        'high_warning': None,
        'low_critical': None,
        'high_critical': None,
    }
    channel_data = None

    def __init__(self, num_channels):
        self.channel_data = {
            i: SFFChannelData() for i in range(num_channels)
        }

        self._parse_eeprom_data()

    def _parse_eeprom_data(self):
        for metric in self.OFFSET_MAP:
            if metric == 'channel_diags':
                self._parse_channel_values(self.OFFSET_MAP['channel_diags'])
            else:
                self._parse_generic_value(metric)

    def _parse_generic_value(self, metric):
        values = {}
        for value, params in self.OFFSET_MAP[metric].items():
            values[value] = params[1](self._data, params[0])

        setattr(self, metric, values)

    def _parse_channel_values(self, channels):
        for channel in channels:
            values = {}
            for value, params in channels[channel].items():
                values[value] = params[1](self._data, params[0])
            self.channel_data[channel].set_values(**values)

    def print_metrics(self, prefix, timestamp):
        for metric in [
            'sfp_voltage', 'temperature', 'bias_current', 'tx_power',
            'rx_power'
        ]:
            for k, v in getattr(self, metric).items():
                print(
                    f'{prefix}.{self.interface}.{metric}.{k} {v} {timestamp}'
                )

        for channel, diag in self.channel_data.items():
            for metric, value in diag.get_values().items():
                print(
                    f'{prefix}.{self.interface}.{metric}.current.{channel} '
                    f'{value} {timestamp}'
                )


class SFF8472Data(SFFData):
    OFFSET_MAP = {
        'temperature': {
            'current': (SFF_A2_TEMP, a2_offset_to_celsius),
            'low_warning': (SFF_A2_TEMP_LWARN, a2_offset_to_celsius),
            'high_warning': (SFF_A2_TEMP_HWARN, a2_offset_to_celsius),
            'low_critical': (SFF_A2_TEMP_LALRM, a2_offset_to_celsius),
            'high_critical': (SFF_A2_TEMP_HALRM, a2_offset_to_celsius),
        },
        'bias_current': {
            'low_warning': (SFF_A2_BIAS_LWARN, a2_offset_to_milliamps),
            'high_warning': (SFF_A2_BIAS_HWARN, a2_offset_to_milliamps),
            'low_critical': (SFF_A2_BIAS_LALRM, a2_offset_to_milliamps),
            'high_critical': (SFF_A2_BIAS_HALRM, a2_offset_to_milliamps),
        },
        'sfp_voltage': {
            'current': (SFF_A2_VCC, a2_offset_to_volts),
            'low_warning': (SFF_A2_VCC_LWARN, a2_offset_to_volts),
            'high_warning': (SFF_A2_VCC_HWARN, a2_offset_to_volts),
            'low_critical': (SFF_A2_VCC_LALRM, a2_offset_to_volts),
            'high_critical': (SFF_A2_VCC_HALRM, a2_offset_to_volts),
        },
        'tx_power': {
            'low_warning': (SFF_A2_TX_PWR_LWARN, a2_offset_to_milliwatts),
            'high_warning': (SFF_A2_TX_PWR_HWARN, a2_offset_to_milliwatts),
            'low_critical': (SFF_A2_TX_PWR_LALRM, a2_offset_to_milliwatts),
            'high_critical': (SFF_A2_TX_PWR_HALRM, a2_offset_to_milliwatts),
        },
        'rx_power': {
            'low_warning': (SFF_A2_RX_PWR_LWARN, a2_offset_to_milliwatts),
            'high_warning': (SFF_A2_RX_PWR_HWARN, a2_offset_to_milliwatts),
            'low_critical': (SFF_A2_RX_PWR_LALRM, a2_offset_to_milliwatts),
            'high_critical': (SFF_A2_RX_PWR_HALRM, a2_offset_to_milliwatts),
        },
        'channel_diags': {
            0: {
                'bias_current': (SFF_A2_BIAS, a2_offset_to_milliamps),
                'rx_power': (SFF_A2_RX_PWR, a2_offset_to_milliwatts),
                'tx_power': (SFF_A2_TX_PWR, a2_offset_to_milliwatts),
            }
        }
    }

    def __init__(self, data, interface):
        # Interfaces without SFP sometimes will return data, but the type
        # will be null.
        unknown_id = data[SFF_A0_ID_OFFSET] == SFF8024_ID_UNKNOWN

        if unknown_id:
            raise UnsupportedSFPException(
                f'{interface}: SFP type {data[SFF8636_ID_OFFSET]} is not '
                'supported'
            )

        # Check if SFP supports DOM
        supports_dom = data[SFF_A0_DOM] & SFF_A0_DOM_IMPL
        if not supports_dom:
            raise UnsupportedSFPException(
                f'{interface}: SFP does not support DOM'
            )

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

        super().__init__(num_channels=1)


class SFF8636Data(SFFData):
    OFFSET_MAP = {
        'temperature': {
            'current': (SFF8636_TEMP_CURR, offset_to_celsius),
            'low_warning': (SFF8636_TEMP_LWARN, sff8636_offset_to_celsius),
            'high_warning': (SFF8636_TEMP_HWARN, sff8636_offset_to_celsius),
            'low_critical': (SFF8636_TEMP_LALRM, sff8636_offset_to_celsius),
            'high_critical': (SFF8636_TEMP_HALRM, sff8636_offset_to_celsius),
        },
        'sfp_voltage': {
            'current': (SFF8636_VCC_CURR, offset_to_volts),
            'low_warning': (SFF8636_VCC_LWARN, sff8636_offset_to_volts),
            'high_warning': (SFF8636_VCC_HWARN, sff8636_offset_to_volts),
            'low_critical': (SFF8636_VCC_LALRM, sff8636_offset_to_volts),
            'high_critical': (SFF8636_VCC_HALRM, sff8636_offset_to_volts),
        },
        'bias_current': {
            'low_warning': (
                SFF8636_TX_BIAS_LWARN, sff8636_offset_to_milliamps
            ),
            'high_warning': (
                SFF8636_TX_BIAS_HWARN, sff8636_offset_to_milliamps
            ),
            'low_critical': (
                SFF8636_TX_BIAS_LALRM, sff8636_offset_to_milliamps
            ),
            'high_critical': (
                SFF8636_TX_BIAS_HALRM, sff8636_offset_to_milliamps
            ),
        },
        'tx_power': {
            'low_warning': (
                SFF8636_TX_PWR_LWARN, sff8636_offset_to_milliwatts
            ),
            'high_warning': (
                SFF8636_TX_PWR_HWARN, sff8636_offset_to_milliwatts
            ),
            'low_critical': (
                SFF8636_TX_PWR_LALRM, sff8636_offset_to_milliwatts
            ),
            'high_critical': (
                SFF8636_TX_PWR_HALRM, sff8636_offset_to_milliwatts
            ),
        },
        'rx_power': {
            'low_warning': (
                SFF8636_RX_PWR_LWARN, sff8636_offset_to_milliwatts
            ),
            'high_warning': (
                SFF8636_RX_PWR_HWARN, sff8636_offset_to_milliwatts
            ),
            'low_critical': (
                SFF8636_RX_PWR_LALRM, sff8636_offset_to_milliwatts
            ),
            'high_critical': (
                SFF8636_RX_PWR_HALRM, sff8636_offset_to_milliwatts
            ),
        },
        'channel_diags': {
            0: {
                'bias_current': (
                    SFF8636_TX_BIAS_1_OFFSET, offset_to_milliamps
                ),
                'rx_power': (SFF8636_RX_PWR_1_OFFSET, offset_to_milliwatts),
                'tx_power': (SFF8636_TX_PWR_1_OFFSET, offset_to_milliwatts),
            },
            1: {
                'bias_current': (
                    SFF8636_TX_BIAS_2_OFFSET, offset_to_milliamps
                ),
                'rx_power': (SFF8636_RX_PWR_2_OFFSET, offset_to_milliwatts),
                'tx_power': (SFF8636_TX_PWR_2_OFFSET, offset_to_milliwatts),
            },
            2: {
                'bias_current': (
                    SFF8636_TX_BIAS_3_OFFSET, offset_to_milliamps
                ),
                'rx_power': (SFF8636_RX_PWR_3_OFFSET, offset_to_milliwatts),
                'tx_power': (SFF8636_TX_PWR_3_OFFSET, offset_to_milliwatts),
            },
            3: {
                'bias_current': (
                    SFF8636_TX_BIAS_4_OFFSET, offset_to_milliamps
                ),
                'rx_power': (SFF8636_RX_PWR_4_OFFSET, offset_to_milliwatts),
                'tx_power': (SFF8636_TX_PWR_4_OFFSET, offset_to_milliwatts),
            },
        }
    }

    def __init__(self, data, interface):
        # Check SFP type. There is only support for QSFP, QSFP+ and QSFP28
        unsupported = data[SFF8636_ID_OFFSET] not in [SFF8024_ID_QSFP,
                                                      SFF8024_ID_QSFP_PLUS,
                                                      SFF8024_ID_QSFP28]

        if unsupported:
            raise UnsupportedSFPException(
                f'{interface}: QSFP type {data[SFF8636_ID_OFFSET]} is not '
                'supported'
            )

        self._data = data
        self.interface = interface

        super().__init__(num_channels=4)


class NoSFPException(Exception):
    pass


class UnsupportedSFPException(Exception):
    pass


if __name__ == '__main__':
    main()
