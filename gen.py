#!/opt/local/bin/python2.7

import json, sys, yaml, re, copy

from host     import Host, check_hosts
from group    import Group, expand_groups
from network  import Network
import defaults

import dhcp, dns, iptables

if __name__ == '__main__':
    cfg = yaml.load(sys.stdin)
    errors = []
    errors.extend(defaults.init(cfg['defaults']))

    hosts    = map(lambda data: Host(data),    cfg['hosts'])
    networks = map(lambda data: Network(data), cfg['networks'])
    groups   = map(lambda data: Group(data),   cfg['groups'] if 'groups' in cfg else [])
    users    = cfg['users'] if 'users' in cfg else []

    errors.extend(check_hosts(hosts))
    errors.extend(expand_groups(groups, hosts))
    for host in hosts: host.clean()

    if len(errors):
        for error in errors: print >> sys.stderr, 'Error: %s' % error
        sys.exit(1)
    else:
        #with open('cfg/dhcp.template', 'r') as dhcpt:
        #    template = dhcpt.read()
        #print dhcp.gen(hosts, networks, template)
        #with open('cfg/urgu.org.template', 'r') as dnst:
        #    template = dnst.read()
        #print dns.gen_fwd(hosts, 'urgu.org', template)
        with open('cfg/adm.template', 'r') as rdnst:
            template = rdnst.read()
        print dns.gen_reverse(hosts, networks[0], template)
        #print ''.join(iptables.gen_ports(hosts, '194.226.244.126', 'server'))
        #print dns.gen_fwd(hosts, 'urgu.org')
        #for host in hosts: print host
        #for network in networks: print network; print network.get_dhcp()
