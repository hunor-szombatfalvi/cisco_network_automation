import netmiko
from netmiko import ConnectHandler
import globals
import json


class SSHnotEnabled(ConnectionError):
    pass
class JsonIncorrectFormat(SyntaxWarning):
    pass
class IosSyntaxError(SyntaxWarning):
    pass
class UnknownError(Warning):
    pass


def connect_enable_silent(*ios_commands,ip_address,dev=0):
    global output
    try:
        with open ("credentials.txt") as line:
            line = json.load(line)
            try_credentials = 0
            for k,v in line.items():
                router=(k,v)
                try_credentials += 1
                try:
                    if globals.pref_cred != {} and try_credentials == 1:
                        if dev != 0:
                            print("[[DEV:] Trying Prefered credentials]")
                        ssh = ConnectHandler(**globals.pref_cred, device_type="cisco_ios", ip=ip_address)
                        ssh.enable()
                    else:
                        if dev != 0:
                            print("[[DEV:] Trying Privileged EXEC credentials '", k, "']", sep="")
                        ssh = ConnectHandler(**router[1], device_type="cisco_ios", ip=ip_address)
                        ssh.enable()
                except netmiko.ssh_exception.NetMikoAuthenticationException:
                    if dev != 0:
                        print ("[[DEV:] Incorrect credentials]")
                    continue
                except netmiko.ssh_exception.NetMikoTimeoutException:
                    # oddly enough if it can log in but not able to authenticate to enable mode,
                    # the ssh.enable() command does not give an authentication error but a time-out error instead
                    try:
                        if globals.pref_cred != {} and try_credentials == 1:
                            if dev != 0:
                                print("[[DEV:] Trying User EXEC Prefered credentials (Privileged EXEC timed out)]")
                            ssh = ConnectHandler(**globals.pref_cred, device_type="cisco_ios", ip=ip_address)
                        else:
                            if dev != 0:
                                print("[[DEV:] Trying User EXEC credentials (Privileged EXEC timed out)]")
                            ssh = ConnectHandler(username=router[1]['username'], password=router[1]['password'],
                                             device_type="cisco_ios", ip=ip_address)
                    except netmiko.ssh_exception.NetMikoTimeoutException:
                        if dev != 0:
                            print("[[DEV:] SSH not enabled (User EXEC timed out)]")
                        raise SSHnotEnabled("SSH not enabled on target device (" + ip_address + ")") from None
                    except Exception:
                        if dev != 0:
                            print("[[DEV:] Unknown error in ssh.connect_enable_silent)]")
                        raise UnknownError ("Unknown error in ssh.connect_enable_silent")
                    else:
                        for ios_command in ios_commands:
                            if dev != 0:
                                print("[[DEV:] Running command '", ios_command, "']", sep="")
                            output = ios_command + "\n" + ssh.send_command(ios_command)
                            if dev != 0 and "at '^' marker" in output:
                                print("[[DEV:] '", ios_command, "' incorrect syntax or requires enable mode]", sep="")
                            if "at '^' marker" not in output:
                                ssh.disconnect()
                                if dev != 0 and globals.pref_cred == {} or dev != 0 and globals.pref_cred != {} and try_credentials > 1:
                                    print("[[DEV:] Saving '", k, "' as prefered credentials]", sep="")
                                    globals.pref_cred = v
                                break
                        if "at '^' marker" not in output:
                            return output
                        else:
                            continue
                except Exception:
                    if dev != 0:
                        print("[[DEV:] Unknown error in ssh.connect_enable_silent]")
                    raise UnknownError ("Unknown error in ssh.connect_enable_silent")
                else:
                    for ios_command in ios_commands:
                        if dev != 0:
                            print("[[DEV:] Running command '", ios_command, "']", sep="")
                        output = ios_command + "\n" + ssh.send_command(ios_command)
                        if dev != 0 and "at '^' marker" in output:
                            print("[[DEV:] '", ios_command, "' incorrect syntax]", sep="")
                        if "at '^' marker" not in output:
                            ssh.disconnect()
                            break
                    if "at '^' marker" in output:
                        raise IosSyntaxError
                    if dev != 0 and globals.pref_cred == {} or dev != 0 and globals.pref_cred != {} and try_credentials > 1:
                        print("[[DEV:] Saving '", k, "' as prefered credentials]", sep="")
                        globals.pref_cred = v
                    return output
    except json.decoder.JSONDecodeError:
        if dev != 0:
            print("[[DEV:] credentials file not in JSON format]")
    raise JsonIncorrectFormat ("Credentials file not in JSON format")


def hostname_silent(ip_address,dev=0):
    try:
        with open ("credentials.txt") as line:
            line_1 = json.load(line)
            try_credentials = 0
            for k,v in line_1.items():
                router=(k,v)
                try_credentials += 1
                try:
                    if globals.pref_cred != {} and try_credentials == 1:
                        if dev != 0:
                            print("[[DEV:] Trying Prefered credentials]")
                        ssh = ConnectHandler(**globals.pref_cred, device_type="cisco_ios", ip=ip_address)
                    else:
                        if dev != 0:
                            print("[[DEV:] Trying Privileged EXEC credentials '", k, "']", sep="")
                        ssh = ConnectHandler(**router[1],device_type="cisco_ios",ip=ip_address)
                except netmiko.ssh_exception.NetMikoAuthenticationException:
                    if dev != 0:
                        print("[[DEV:] Incorrect credentials]")
                    continue
                except netmiko.ssh_exception.NetMikoTimeoutException:
                    if dev != 0:
                        print("[[DEV:] SSH not enabled (User EXEC timed out)]")
                    raise SSHnotEnabled("SSH not enabled on target device (" + ip_address + ")") from None
                except Exception:
                    if dev != 0:
                        print("[[DEV:] Unknown error in ssh.hostname_silent]")
                    raise UnknownError("Unknown error in ssh.hostname_silent")
                else:
                    output = ssh.find_prompt()
                    if ('#') in output:
                        (output_split,junk) = output.split('#')
                    else:
                        (output_split, junk) = output.split('>')
                    ssh.disconnect()
                    if dev != 0 and globals.pref_cred == {} or dev != 0 and globals.pref_cred != {} and try_credentials > 1:
                        print("[[DEV:] Saving '", k, "' as prefered credentials]", sep="")
                        globals.pref_cred = v
                    return output_split
    except json.decoder.JSONDecodeError:
        if dev != 0:
            print("[[DEV:] credentials file not in JSON format]")
    raise JsonIncorrectFormat("Credentials file not in JSON format")
