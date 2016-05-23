# cisco_network_automation

ssh.py:

# ssh.py is based on netmiko (so this will be necessary to be installed for it to work) which is wrapper around paramiko
# for some reason in python 3 running on windows, I could not get paramiko itself to run more then one command before closing the SSH channel, this works from netmiko though.

# the aim of ssh.py is to provide a platform to run cisco ios commands on for usage in projects such as network discovery, where failiure and re-trying is expected.
# due to this, it is able to take more then one credential sets, which are defined in credentials.txt (will possibly try to encrypt it at some point) and also more then one command at the same time.
# the feature to take more than one command is geared towards syntax differences in IOS, IOS-XE and IOS-NX and is not meant to pass multiple different commands, but different versions of the same one.

#the functions in ssh.py also raise their own errors to be further used in any project where ssh.py is incorporated
