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


def subtract_subnet(aggregate, network):                                                                                # takes lists of subnets in format [subnet/cidr, subnet/cidr...]
    for a_cidr in aggregate:                                                                                            # subtracts the networks from the aggregate
        a_cidr = netaddr.IPSet([a_cidr])                                                                                # if networks outside of aggregate, these are ignored
        for n_cidr in network:
            n_cidr = netaddr.IPSet([n_cidr])
            if n_cidr.issubset(a_cidr):
                a_cidr.remove(n_cidr.iprange())
        if a_cidr:
            return strip_ipset(a_cidr).split(',')                                                                       # returns list of (aggregate - subnets) in format [subnet/cidr, subnet/cidr...]


def scrap_bgp(input):                                                                                                   # parses either a running configuration or solarwinds output for BGP
    h = ''.join(re.findall(r'^(?: *)hostname (.*)', input, re.M))                                                       # (\w{10}\d{2}) for productions instead of (.*)
    r = re.findall(r'(?:router bgp \d+)', input)

    if re.findall(r'(?:router bgp \d+)', input):                                                                        # if router bgp \d+ exists in the configuration
        junk, input = re.split(r'(?:router bgp \d+)', input)                                                            # discard everything before router bgp \d+
        if re.findall(r'!\n(?!( *address-family| *bgp router))', input, re.M):                                          # if the configuration contains a ! not followed by address-family or bgp router
            input = re.split(r'!\n(?!( *address-family| *bgp router))', input)[0]                                       # discard everything after this !

    n = [re.sub(r'network | mask', '', i) for i in
         re.findall(r'network \d+\.\d+\.\d+\.\d+ mask \d+\.\d+\.\d+\.\d+', input)]                                      # within this section find all network commands
    n_cidr = net2cidr(n)                                                                                                # save a cidr version of all network commands
    a = [re.sub(r'aggregate-address ', '', i) for i in
         re.findall(r'aggregate-address \d+\.\d+\.\d+\.\d+ \d+\.\d+\.\d+\.\d+', input)]                                 # within this section find all aggregate-address commands
    a_cidr = net2cidr(a)                                                                                                # save a cidr version of all aggregate-address commands
    u = subtract_subnet(a_cidr, n_cidr)                                                                                 # subtract all network commands from aggregate-address, save remaining
    if not u:                                                                                                           # would sometimes return None
        u = []
    if not h:
        h = 'none'
    return {'hostname':h, 'AS':r, 'networks':n, 'networks_cidr':n_cidr, 'a_addresses':a, 'a_addresses_cidr':a_cidr,
            'unallocated':u}

def scrap_RVO(input):
    h = ''.join(re.findall(r'^(?: *)hostname (.*)', input, re.M))                                                       # (\w{10}\d{2}) for productions instead of (.*)

    if re.findall(r'(?:object-group network RVO_LOCAL_SUBNET)', input, re.IGNORECASE):
        junk, local_sub = re.split(r'object-group network RVO_LOCAL_SUBNET', input)
        local_sub = re.split(r'!\n', local_sub)[0]
        local_sub = re.findall(r'\d+\.\d+\.\d+\.\d+ \d+\.\d+\.\d+\.\d+', local_sub)
        local_sub = net2cidr(local_sub)
    else:
        local_sub = []

    if re.findall(r'(?:object-group network RVO_GLOBAL_SUBNETS)', input, re.IGNORECASE):
        junk, global_sub = re.split(r'object-group network RVO_GLOBAL_SUBNETS', input)
        global_sub = re.split(r'!\n', global_sub)[0]
        global_sub = re.findall(r'\d+\.\d+\.\d+\.\d+ \d+\.\d+\.\d+\.\d+', global_sub)
        global_sub = net2cidr(global_sub)
    else:
        global_sub = []

    return {'hostname': h, 'RVO local': local_sub, 'RVO global':global_sub}

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


def findRVO(input, output='RVO.csv'):                                                                                   # finds RVO related data and exports output to CSV
    all_local = []                                                                                                      # because it attempts to re-create a global RVO list collecting all local subnets
    with open(output, 'a', newline='', encoding='utf-8') as f:                                                          # and then compare if to the global RVO access list on each router
        fieldnames = ['Router', 'RVO Subnet', 'Missing from RVO_GLOBAL_SUBNETS', 'Extra in RVO_GLOBAL_SUBNETS']         # if input does not contain all routers, script will claim that a lot of subnets
        writer = csv.DictWriter(f, fieldnames=fieldnames)                                                               # in global RVO access lists are there as extra
        writer.writeheader()

        for i in tqdm.tqdm(input[1:], desc='Calculating RVO subnets'):
            if scrap_RVO(i)['RVO local']:
                all_local += scrap_RVO(i)['RVO local']
                for n in scrap_RVO(i)['RVO local']:
                    writer.writerow({'Router': scrap_RVO(i)['hostname'], 'RVO Subnet': n})

                not_in_global = set(all_local) - set(scrap_RVO(i)['RVO global'])
                for n in not_in_global:
                     writer.writerow({'Router': scrap_RVO(i)['hostname'], 'Missing from RVO_GLOBAL_SUBNETS': n})

                extra_in_global = set(scrap_RVO(i)['RVO global']) - set(all_local)
                for n in extra_in_global:
                     writer.writerow({'Router': scrap_RVO(i)['hostname'], 'Extra in RVO_GLOBAL_SUBNETS': n})

input = solarwinds_file('solarwinds_sh_run_nala.txt')

#input = parsed_apic_show_run()
#bgp_net_agg_unaloc(input)
#bgp_duplicate_networks(input)
findRVO(input)
