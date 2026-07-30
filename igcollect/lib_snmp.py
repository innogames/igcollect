"""igcollect - SNMP common library
"""


import asyncio
import atexit

from pysnmp import proto
from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    bulk_walk_cmd,
    get_cmd,
    usmAesCfb128Protocol,
    usmDESPrivProtocol,
    usmHMACSHAAuthProtocol,
)


class IgCollectSNMPException(Exception):
    pass


def get_snmp_connection(args):
    """ Prepare SNMP transport agent.

        Connection over SNMP v2c and v3 is supported.
        The choice of authentication and privacy algorithms for v3 is
        arbitrary, matching what our switches can do.
    """

    if args.community:
        auth_data = CommunityData(args.community, mpModel=1)
    else:
        if args.priv_proto == 'des':
            priv_proto = usmDESPrivProtocol
        elif args.priv_proto == 'aes':
            priv_proto = usmAesCfb128Protocol
        else:
            raise IgCollectSNMPException(
                f'Unsupported privacy protocol {args.priv_proto}'
            )

        auth_data = UsmUserData(
            args.user, args.auth, args.priv,
            authProtocol=usmHMACSHAAuthProtocol,
            privProtocol=priv_proto,
        )

    # pysnmp 7 is asyncio-only and its SnmpEngine dispatcher binds to a single
    # event loop, so we keep one loop, engine and transport for the whole run
    # and drive every query on it via run_until_complete().  A fresh
    # asyncio.run() per query would close the loop the engine is bound to and
    # the next query would hang.
    loop = asyncio.new_event_loop()
    engine = SnmpEngine()
    transport = loop.run_until_complete(
        UdpTransportTarget.create((args.host, 161))
    )

    def close():
        # Cancel the engine's pending handle_timeout() looping-call and let the
        # loop process the cancellation, otherwise the interpreter exits with
        # "Task was destroyed but it is pending!".
        engine.close_dispatcher()
        loop.run_until_complete(asyncio.sleep(0))
        loop.close()

    atexit.register(close)

    return {
        'loop': loop,
        'engine': engine,
        'auth_data': auth_data,
        'context': ContextData(),
        'transport': transport,
    }


def get_snmp_value(snmp, OID):
    """ Get a single value from SNMP """

    async def run():
        return await get_cmd(
            snmp['engine'],
            snmp['auth_data'],
            snmp['transport'],
            snmp['context'],
            ObjectType(ObjectIdentity(OID)),
        )

    errorIndication, errorStatus, errorIndex, varBinds = \
        snmp['loop'].run_until_complete(run())
    if errorIndication:
        raise IgCollectSNMPException(f'Unable to get SNMP value: {errorIndication}')

    return convert_snmp_type(varBinds[0])


def get_snmp_table(snmp, OID):
    """ Fetch a table from SNMP.

        Returned is a dictionary mapping the last number of OID (converted to
        Python integer) to value (converted to int or str).
    """

    async def run():
        ret = {}
        # lexicographicMode=False stops the walk at the end of the requested
        # subtree, so we don't leak into another tree (which used to require a
        # manual OID-prefix check with the old oneliner bulkCmd).
        objects = bulk_walk_cmd(
            snmp['engine'],
            snmp['auth_data'],
            snmp['transport'],
            snmp['context'],
            0,  # nonRepeaters
            25,  # maxRepetitions
            ObjectType(ObjectIdentity(OID)),
            lexicographicMode=False,
        )
        async for errorIndication, errorStatus, errorIndex, varBinds in objects:
            if errorIndication:
                raise IgCollectSNMPException(
                    f'Unable to get SNMP value: {errorIndication}'
                )
            for var_bind in varBinds:
                index = int(var_bind[0][-1])
                ret[index] = convert_snmp_type(var_bind)
        return ret

    return snmp['loop'].run_until_complete(run())


def convert_snmp_type(var_bind):
    """ Convert SNMP data types to something more convenient: int or str """

    val = var_bind[1]
    if type(val) in [
        proto.rfc1902.Integer,
        proto.rfc1902.Counter32,
        proto.rfc1902.Counter64,
    ]:
        return int(val)
    return str(val)


def add_snmp_arguments(parser):
    snmp_mode = parser.add_mutually_exclusive_group(required=True)
    snmp_mode.add_argument('--community', help='SNMP community')
    snmp_mode.add_argument('--user', help='SNMPv3 user')

    parser.add_argument('--auth', help='SNMPv3 authentication key')
    parser.add_argument('--priv', help='SNMPv3 privacy key')
    parser.add_argument(
        '--priv_proto',
        help='SNMPv3 privacy protocol: aes (default) or des',
        default='aes'
    )
