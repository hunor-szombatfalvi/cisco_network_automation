def port_channel(ip_address,dev=0):
    import ssh
    for retries in range(0,3):
        try:
            show_port_channel_sum = ssh.connect_enable_silent('show etherchannel summary',"show port-channel summary",ip_address=ip_address,dev=1)

            # parses the output line by line, delimits variables and collects all of them in a list
            full_list = []
            for line in show_port_channel_sum.split('\n'):
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

            for n in range(0,len(list_of_portchannels)-1):
                if list_of_portchannels[n][0] not in list_of_portchannels_json:
                    list_of_portchannels_json[list_of_portchannels[n][0]] = {}
                    if list_of_portchannels[n][1] == "-":
                        list_of_portchannels_json[list_of_portchannels[n][0]]["protocol"] = "NONE"
                    else:
                        list_of_portchannels_json[list_of_portchannels[n][0]]["protocol"] = list_of_portchannels[n][1]
                    list_of_portchannels_json[list_of_portchannels[n][0]]["ports"] = list_of_portchannels[n][2]
            return list_of_portchannels_json

        except ssh.SSHnotEnabled:
            print ("[[DEV:] Future: Raise error for different module or pass to Telnet")
            break

        except Exception:
            print ("[[DEV:] General exception triggered in cisco.port_channel")
            continue
