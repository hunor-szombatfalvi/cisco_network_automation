import netaddr
import apic
import iptools
import csv
import re
import tqdm


def solarwinds_file(file):                                                                                              #creates a per router list of the output of commands ran from solarwinds
    return re.split(r'\w{10}\d{2}(?:\.\w*\.\w* )\(\d+\.\d+\.\d+\.\d+\):', open(file).read())


def parsed_apic_show_run():                                                                                             # creates a list of all running configurations with apic_id:id at end
    input = apic.run_api('show_run')
    all_config = ''
    for i in input['response']:
        all_config += i['runningConfig'] + 'apic_id:' + i['id']
    return re.split(r'\nBuilding configuration...', all_config)


def strip_ipset(ipset):
    return re.sub(r'IPSet\(\[|\]\)|\'', '', str(ipset))


def net2cidr(net):                                                                                                      # takes lists of subnets in format [subnet netmask, subnet netmask...]
    net = [n.split(" ", 1) for n in net]
    net = ['{}/{}'.format(n[0], iptools.ipv4.netmask2prefix(n[1])) for n in net]
    return net                                                                                                          # returns list of subnets in format [subnet/cidr, subnet/cidr...]


def subtract_subnet(aggregate, network):
    for a_cidr in aggregate:
        a_cidr = netaddr.IPSet([a_cidr])
        for n_cidr in network:
            n_cidr = netaddr.IPSet([n_cidr])
            if n_cidr.issubset(a_cidr):
                a_cidr.remove(n_cidr.iprange())
        if a_cidr:
            return strip_ipset(a_cidr).split(',')


def scrap_bgp(input):                                                                                                   # parses either a running configuration or solarwinds output for BGP
    h = ''.join(re.findall(r'^(?: *)hostname (.*)', input, re.M))                                                       # (\w{10}\d{2}) for productions instead of (.*)

    if re.findall(r'(?:router bgp \d+)', input):                                                                        # if router bgp \d+ exists in the configuration
        junk, input = re.split(r'(?:router bgp \d+)', input)                                                            # discard everything before router bgp \d+
        if re.findall(r'!\n(?!( *address-family| *bgp router))', input, re.M):                                          # if the configuration contains a ! not followed by address-family or bgp router
            input, junk = re.split(r'!\n(?!( *address-family| *bgp router))', input)                                    # discard everything after this !

    n = [re.sub(r'network | mask', '', i) for i in
         re.findall(r'network \d+\.\d+\.\d+\.\d+ mask \d+\.\d+\.\d+\.\d+', input)]                                      # within this section find all network commands
    n_cidr = net2cidr(n)                                                                                                # save a cidr version of all network commands
    a = [re.sub(r'aggregate-address ', '', i) for i in
         re.findall(r'aggregate-address \d+\.\d+\.\d+\.\d+ \d+\.\d+\.\d+\.\d+', input)]                                 # within this section find all aggregate-address commands
    a_cidr = net2cidr(a)                                                                                                # save a cidr version of all aggregate-address commands
    u = subtract_subnet(a_cidr, n_cidr)                                                                                 # subtract all network commands from aggregate-address, save remaining
    if not u:                                                                                                           # would sometimes return None
        u = []

    return {'hostname':h, 'networks':n, 'networks_cidr':n_cidr, 'a_addresses':a, 'a_addresses_cidr':a_cidr,
            'unallocated':u}


def bgp_net_agg_unaloc(input, output='bgp_net_agg_unaloc.csv'):                                                         # creates a CSV file from BGP data found on routers
    with open(output, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['hostname', 'network', 'aggregate-address', 'undeclared subnets']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in tqdm.tqdm(input[1:], desc='Extracting BGP information and creating {}'.format(output)):
            r = scrap_bgp(i)

            if r['networks']:
                for network in r['networks']:
                    writer.writerow({'hostname':r['hostname'], 'network':network})
            else:
                writer.writerow({'hostname':r['hostname'], 'network':'none'})
            for address in r['a_addresses']:
                writer.writerow({'hostname':r['hostname'], 'aggregate-address':address})
            if r['unallocated']:
                for unalloc in r['unallocated']:
                    writer.writerow({'hostname':r['hostname'], 'undeclared subnets':
                        '{} {}'.format(netaddr.IPNetwork(unalloc).ip, netaddr.IPNetwork(unalloc).netmask)})


def bgp_duplicate_networks(input, output='overlap.csv'):                                                                # finds overlaping network commands in BGP on different routers
    all_networks = []                                                                                                   # and exports output to CSV
    with open(output, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['Router', 'Subnet', 'Overlap Router', 'Overlap Subnet', 'Overlap Unallocated']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in tqdm.tqdm(input[1:], desc='Creating list of all declared networks'):
            all_networks += [[scrap_bgp(i)['hostname'], [netaddr.IPSet([n]) for n in scrap_bgp(i)['networks_cidr']],
                              [netaddr.IPSet([n]) for n in scrap_bgp(i)['unallocated']]]]
        for n_1_pr in tqdm.tqdm(all_networks, desc='Comparing all networks and looking for duplicates and inclusions'):
            for n_1 in n_1_pr[1]:
                for n_2_pr in all_networks:
                    for n_2 in n_2_pr[1]:
                        if n_1.issubset(n_2):
                            if re.search(r'\w{10}', str(n_1_pr[0]), re.IGNORECASE).group(0) != re.search(r'\w{10}', str(n_2_pr[0]), re.IGNORECASE).group(0):
                                writer.writerow({'Router': n_1_pr[0], 'Subnet': strip_ipset(n_1), 'Overlap Router': n_2_pr[0], 'Overlap Subnet': strip_ipset(n_2)})
                    for unallocated in n_2_pr[2]:
                        if unallocated.issubset(n_1):
                            if re.search(r'\w{10}', str(n_1_pr[0]), re.IGNORECASE).group(0) != re.search(r'\w{10}', str(n_2_pr[0]), re.IGNORECASE).group(0):
                                writer.writerow({'Router': n_1_pr[0], 'Subnet': strip_ipset(n_1), 'Overlap Router': n_2_pr[0], 'Overlap Unallocated': strip_ipset(unallocated)})


input = solarwinds_file('solarwinds_output')
#input = parsed_apic_show_run()
bgp_net_agg_unaloc(input)
bgp_duplicate_networks(input)
