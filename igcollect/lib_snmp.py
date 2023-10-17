"""igcollect - SNMP common library
"""


from pysnmp import proto
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.entity.rfc3413.oneliner.cmdgen import (
    CommunityData,
    UsmUserData,
    usmHMACSHAAuthProtocol,
    usmAesCfb128Protocol,
    usmDESPrivProtocol,
)


class IgCollectSNMPException(Exception):
    pass


# Predefine some variables, it makes this program run a bit faster.
cmd_gen = cmdgen.CommandGenerator()


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
        if args.priv_proto == 'aes':
            priv_proto = usmAesCfb128Protocol
        else:
            raise IgCollectSNMPException(f'Unsupported privacy protocol {args.priv_prot}')

        auth_data = UsmUserData(
            args.user, args.auth, args.priv,
            authProtocol=usmHMACSHAAuthProtocol,
            privProtocol=priv_proto,
        )

    transport_target = cmdgen.UdpTransportTarget((args.host, 161))

    return {
        'auth_data': auth_data,
        'transport_target': transport_target,
    }


def get_snmp_value(snmp, OID):
    """ Get a single value from SNMP """

    errorIndication, errorStatus, errorIndex, varBinds = cmd_gen.getCmd(
        snmp['auth_data'],
        snmp['transport_target'],
        OID,
    )
    if errorIndication:
        raise IgCollectSNMPException(f'Unable to get SNMP value: {errorIndication}')

    return convert_snmp_type(varBinds)


def get_snmp_table(snmp, OID):
    """ Fetch a table from SNMP.

        Returned is a dictionary mapping the last number of OID (converted to
        Python integer) to value (converted to int or str).
    """
    ret = {}
    errorIndication, errorStatus, errorIndex, varBindTable = cmd_gen.bulkCmd(
        snmp['auth_data'],
        snmp['transport_target'],
        0,  # nonRepeaters
        25,
        OID,
    )
    for varBind in varBindTable:
        # Oh the joy of pysnmp library!
        # When the nonrepeaters value above is 0, we might get objects from
        # another snmp tree on some hardware, for example from cisco routers.
        # we can set it to 1 but then we have high cpu usage. So keep it 0
        # and manually check if we are still in the same tree.
        # OIDs we query for must not start with a dot.
        if not str(varBind[0][0]).startswith(OID):
            break
        if errorIndication:
            raise IgCollectSNMPException(f'Unable to get SNMP value: {errorIndication}')

        index = int(str(varBind[0][0][-1:]))
        ret[index] = convert_snmp_type(varBind)

    return ret


def convert_snmp_type(varBinds):
    """ Convert SNMP data types to something more convenient: int or str """

    val = varBinds[0][1]
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