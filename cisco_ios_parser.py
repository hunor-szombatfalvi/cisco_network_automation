def port_channel(ip_address,dev=0):

    global list_of_portchannels_json
    import ssh
    if dev != 0:
        print("[[DEV:] Getting port-channel information]")
    for retries in range(0,3):
        try:
            show_port_channel_sum = ssh.connect_enable_silent('show etherchannel summary',"show port-channel summary",ip_address=ip_address,dev=dev)

            # parses the output line by line, delimits variables and collects all of them in a list
            full_list = []
            for line in show_port_channel_sum.split('\n'):
#                if "}" in line and "username" in line:
#                    pref_cred = line
                if len([character for character in line if character.isdigit()]) > 0 and "(" in line:
                    segmented_line = (' '.join(line.split(")")).split())
                    full_list += segmented_line

            # parses trough the full list of items and creates sub lists
            # the lists are delimited from the first numeral only item to the next numeral only item - 1
            delimiters = []
            for number in [item for item in full_list if item.isdigit()]:
                delimiters.append(full_list.index(number))
            delimiters.append(len(full_list))
            delimited_list = [full_list[delimiters[n]:delimiters[n + 1]] for n in range(0, len(delimiters) - 1)]

            # removes some unwanted items
            for junk in range(0, len(delimited_list)):
                del delimited_list[junk][1]
                if "show port-channel summary" in show_port_channel_sum:
                    del delimited_list[junk][1]

            # magic
            list_of_port_lists = [delimited_list[n][2:len(delimited_list[n])] for n in range(0, len(delimited_list))]
            formatted_ports = [
                [''.join([character for character in port if character.isdigit() or character == "/"]) for port in port_lists]
                for port_lists in list_of_port_lists]
            list_of_portchannels = [delimited_list[n][0:2] for n in range(0, len(delimited_list))]

            for n in range(0, len(formatted_ports)):
                list_of_portchannels[n].append(formatted_ports[n])

            #re-format to JSON
            list_of_portchannels_json = {}

            for n in range(0,len(list_of_portchannels)):
                if list_of_portchannels[n][0] not in list_of_portchannels_json:
                    list_of_portchannels_json[list_of_portchannels[n][0]] = {}
                    if list_of_portchannels[n][1] == "-":
                        list_of_portchannels_json[list_of_portchannels[n][0]]["protocol"] = "NONE"
                    else:
                        list_of_portchannels_json[list_of_portchannels[n][0]]["protocol"] = list_of_portchannels[n][1]
                    list_of_portchannels_json[list_of_portchannels[n][0]]["ports"] = list_of_portchannels[n][2]
            break

        except ssh.SSHnotEnabled:
            print ("[[DEV:] Future: Raise error for different module or pass to Telnet")
            break

        except Exception:
            print ("[[DEV:] General exception triggered in cisco.port_channel")
            continue

    if dev != 0:
        print("[[DEV:] Getting hostname]")
    for retries in range(0, 3):
        try:
            hostname = ssh.hostname_silent(ip_address=ip_address, dev=dev)
            output = {hostname: list_of_portchannels_json}
            return output

        except ssh.SSHnotEnabled:
            print ("[[DEV:] Future: Raise error for different module or pass to Telnet")
            break

        except Exception:
            print ("[[DEV:] General exception triggered in cisco.port_channel")
            continue


def cdp_neighbor(ip_address, dev=0):
    import ssh
    if dev != 0:
        print("[[DEV:] Getting CDP neighbor information]")
    for retries in range(0, 3):
        try:
            show_cdp_ne_de = ssh.connect_enable_silent('show cdp neighbors detail', ip_address=ip_address, dev=1)
            split_cdp = show_cdp_ne_de.split('\n')
            network_devices = {}

            for line in split_cdp:
                if '----------------' in line:
                    hostname = ''
                if 'Device ID:' in line:
                    (junk, hostname) = line.split('Device ID:')
                    hostname = hostname.strip()
                    if '.' in hostname:
                        hostname = hostname[0:hostname.find('.')]

                    if not hostname in network_devices:
                        network_devices[hostname] = {}

                if 'IP address:' in line:
                    (junk, ip) = line.split('IP address:')
                    ip = ip.strip()
                    network_devices[hostname]['ip'] = ip
                elif 'IPv4 Address: ' in line:
                    (junk, ip) = line.split('IPv4 Address:')
                    ip = ip.strip()
                    network_devices[hostname]['ip'] = ip

                if 'Platform:' in line:
                    (platform, capabilities) = line.split(',')
                    (junk, model) = platform.split("Platform:")
                    model = model.strip()
                    network_devices[hostname]['model'] = model

                    (junk, capabilities) = capabilities.split("Capabilities: ")
                    if 'Router' in capabilities:
                        device_type = 'router'
                    elif 'Switch' in capabilities:
                        device_type = 'switch'
                    elif 'Phone' in capabilities:
                        device_type = 'phone'
                    elif 'Trans-Bridge' in capabilities:
                        device_type = 'wireless access point'
                    else:
                        device_type = 'unknown'
                    network_devices[hostname]['model'] = model
                    network_devices[hostname]['device_type'] = device_type
            return network_devices

        except ssh.SSHnotEnabled:
            print("[[DEV:] Future: Raise error for different module or pass to Telnet")
            break

        except Exception:
            print("[[DEV:] General exception triggered in cisco.port_channel")
            continue
