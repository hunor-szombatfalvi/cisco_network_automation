# cisco_network_automation

these are my attempts at automating some of the task at my job (https://imgs.xkcd.com/comics/automation.png).
my first project is to write an exhaustive network mapping tool which when ready should use all the tricks i personally use to discover a network. For further management APIs are the way to go but for initial discovery and capabilities assesment the plan is to use as much backwards compatibility as possible, which means CLI scraping using Telnet and SSH and SNMP.
it's still work in progress and up untill now i have written the following modules:

#ssh.py:

ssh.py is based on netmiko (so this will be necessary to be installed for it to work) which is wrapper around paramiko.
for some reason in python 3 running on windows, I could not get paramiko itself to run more than one command before closing the SSH channel, this works from netmiko though.

the aim of ssh.py is to provide a platform to run cisco ios commands on SSH, for usage in projects where failure and re-trying is expected.
due to this, it is able to take more than one credential set, which are defined in credentials.txt (will possibly try to encrypt it at some point) and also more then one command at the same time.
the feature to take more than more one command is geared towards syntax differences in IOS, IOS-XE and IOS-NX and is not meant to pass multiple different commands, but different versions of the same one.

the functions in ssh.py also raise their own errors to be further used in any project where ssh.py is incorporated.

passing any function in ssh.py an optional parameter of "dev=1" will enabled status messages to be displayed as the functions are running, this is meant for debugging.


#cisco_ios_parser.py

CLI parsing is bad, mmk? but sometimes you need to do it. cisco_ios_parser.py contains a collection of parsers for differed cisco ios commands.

The parsers also support the optional parameter of "dev=1" to enable status messages.


#roadmap

encrypted credentials file and saved jobs
having the option to run commands to neighboring routers from different source ips (ip where script is running, ip of devices in the netwokr for non-routeble ranges)
