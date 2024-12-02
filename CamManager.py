"""
MIT License

Copyright (c) 2017 Eliot Kent Woodrich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

# based on https://github.com/OpenIPC/python-dvr/blob/master/DeviceManager.py
"""

from __future__ import print_function, unicode_literals, division, absolute_import

import os
import sys
import struct
import json
try: 
    import fcntl
except:
    pass
from locale import getlocale
from subprocess import check_output
import socket 
import platform
import datetime
import hashlib

#try:
#    from dvrip import DVRIPCam
#except ImportError:
#    print("Exiting: dvrip module not found. This script cannot run on Python 2.")
#    sys.exit(1)

try:
    if sys.version_info[0] == 3:
        import tkinter as Tk
    else:
        import Tkinter as Tk
    from tkinter.filedialog import asksaveasfilename, askopenfilename
    from tkinter.messagebox import showerror
    import tkinter.ttk as ttk

    GUI_TK = True
except:
    GUI_TK = False

# list of preffered interfaces - camera is supposed to be connected to a wired interface
intfs = ['eth0', 'eno1']
devices = {}
log = "search.log"
icon = "R0lGODlhIAAgAPcAAAAAAAkFAgwKBwQBABQNBRAQDQQFERAOFA4QFBcWFSAaFCYgGAoUMhwiMSUlJCsrKyooJy8wLjUxLjkzKTY1Mzw7OzY3OEpFPwsaSRsuTRUsWD4+QCo8XQAOch0nYB05biItaj9ARjdHYiRMfEREQ0hIR0xMTEdKSVNOQ0xQT0NEUVFNUkhRXlVVVFdYWFxdXFtZVV9wXGZjXUtbb19fYFRda19gYFZhbF5wfWRkZGVna2xsa2hmaHFtamV0Ynp2aHNzc3x8fHh3coF9dYJ+eH2Fe3K1YoGBfgIgigwrmypajDtXhw9FpxFFpSdVpzlqvFNzj0FvnV9zkENnpUh8sgdcxh1Q2jt3zThi0SJy0Dl81Rhu/g50/xp9/x90/zB35TJv8DJ+/EZqzj2DvlGDrlqEuHqLpHeQp26SuhqN+yiC6imH/zSM/yqa/zeV/zik/1aIwlmP0mmayWSY122h3VWb6kyL/1yP8UGU/UiW/VWd/miW+Eqp/12k/1Co/1yq/2Gs/2qr/WKh/nGv/3er9mK3/3K0/3e4+4ODg4uLi4mHiY+Qj5WTjo+PkJSUlJycnKGem6ShnY2ZrKOjo6urrKqqpLi0prS0tLu8vMO+tb+/wJrE+bzf/sTExMfIx8zMzMjIxtrWyM/Q0NXU1NfY193d3djY1uDf4Mnj+931/OTk5Ozs7O/v8PLy8gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAAALAAAAAAgACAAAAj+AAEIHEiwoMGDCBMqXMiwocOHECNKnEixosWLGDNq3Mgx4iVMnTyJInVKlclSpD550nRpUqKGmD59EjWqlMlVOFWdIgWq0iNNoBIhSujokidPn0aNKrmqVStWqjxRumTqyI5KOxI5OpiIkiakNG2yelqK5alKLSAJgbBBB6RIjArmCKLIkV1HjyZNpTTJFKgSQoI4cGBiBxBIR6QM6TGQxooWL3LwMBwkSJEcLUq8YATDAZAdMkKh+GGpAo0cL1wInJuokSNIeqdeCgLBAoVMR2CEMkHDzAcnTCzsCAKERwsXK3wYKYLIdd6pjh4guCGJw5IpT7R8CeNlCwsikx7+JTJ+PAZlRHXxOgqBAQMTLXj0AAKkJw+eJw6CXGqJyAWNyT8QgZ5rsD2igwYEOOEGH38EEoghgcQhQgJAxISJI/8ZNoQUijiX1yM7NIBAFm3wUcghh9yBhQcCFEBDJ6V8MskKhgERxBGMMILXI7AhsoAAGSgRBRlliLHHHlZgMAAJmLByCiUnfGajFEcgotVzjkhggAYjjBHFFISgkoodSDAwAyStqDIJAELs4CYQQxChVSRTQcJCFWmUyAcghmzCCRgdXCEHEU69VJiNdDmnV0s4rNHFGmzgkUcfhgiShAd0nNHDVAc9YIEFFWxAQgkVpKAGF1yw4UYdc6AhhQohJFiwQAIRPQCHFlRAccMJFCRAgAAVJXDBBAsQEEBHDwUEADs="
help = """
    Usage: %s [-q] [-n] [Command];[Command];...
    -q				No output
    -n				No gui
    -i [intf]       specify interface eg eth0, wlan0
    Command			Description

    help			This help
    echo			Just echo
    log [filename]		Set log file
    logLevel [0..100]	Set log verbosity
    search [brand]		Searching devices of [brand] or all
    table			Table of devices
    json			JSON String of devices
    device [MAC]		JSON String of [MAC]
    config [MAC] [IP] [MASK] [GATE] [Pasword]   - Configure searched divice
    """ % os.path.basename(
    sys.argv[0]
)
lang, charset = getlocale()

#locale = {'utf-8'}

#def _(msg):
#    if lang in locale.keys():
#        if msg in locale[lang].keys():
#            return locale[lang][msg]
#    return msg


CODES = {
    100: "Success",
    101: "Unknown error",
    102: "Version not supported",
    103: "Illegal request",
    104: "User has already logged in",
    105: "User is not logged in",
    106: "Username or Password is incorrect",
    107: "Insufficient permission",
    108: "Timeout",
    109: "Find failed, file not found",
    110: "Find success, returned all files",
    111: "Find success, returned part of files",
    112: "User already exists",
    113: "User does not exist",
    114: "User group already exists",
    115: "User group does not exist",
    116: "Reserved",
    117: "Message is malformed",
    118: "No PTZ protocol is set",
    119: "No query to file",
    120: "Configured to be enabled",
    121: "Digital channel is not enabled",
    150: "Success, camera restart required",
    202: "User is not logged in",
    203: "Incorrect password",
    204: "User is illegal",
    205: "User is locked",
    206: "User is in the blacklist",
    207: "User already logged in",
    208: "Invalid input",
    209: "User already exists",
    210: "Object not found",
    211: "Object does not exist",
    212: "Account in use",
    213: "Permission table error",
    214: "Illegal password",
    215: "Password does not match",
    216: "Keep account number",
    502: "Illegal command",
    503: "Talk channel has ben opened",
    504: "Talk channel is not open",
    511: "Update started",
    512: "Update did not start",
    513: "Update data error",
    514: "Update failed",
    515: "Update succeeded",
    521: "Failed to restore default config",
    522: "Camera restart required",
    523: "Default config is illegal",
    602: "Application restart required",
    603: "System restart required",
    604: "Write file error",
    605: "Features are not supported",
    606: "Verification failed",
    607: "Configuration does not exist",
    608: "Configuration parsing error",
}


def tolog(s):
    print(s)
    if logLevel >= 20:
        logfile = open(log, "wb")
        logfile.write(bytes(s, "utf-8"))
        logfile.close()


def get_nat_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


def local_ip():
    ip = get_nat_ip()
    ipn = struct.unpack(">I", socket.inet_aton(ip))
    return (
        socket.inet_ntoa(struct.pack(">I", ipn[0] + 10)),
        "255.255.255.0",
        socket.inet_ntoa(struct.pack(">I", (ipn[0] & 0xFFFFFF00) + 1)),
    )


def get_ip_address(ifname):
    if sys.platform != 'win32':
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ipadd = fcntl.ioctl(
            server.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24]
        server.close()
        return socket.inet_ntoa(ipadd)
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ipaddr = s.getsockname()[0]
        s.close()
        return ipaddr


def sofia_hash(password):
    md5 = hashlib.md5(bytes(password, "utf-8")).digest()
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return "".join([chars[sum(x) % 62] for x in zip(md5[::2], md5[1::2])])


def GetIP(s):
    return socket.inet_ntoa(struct.pack("I", int(s, 16)))


def SetIP(ip):
    return "0x%08X" % struct.unpack("I", socket.inet_aton(ip))


def GetAllAddr():
    if os.name == "nt":
        return [
            x.split(":")[1].strip()
            for x in str(check_output(["ipconfig"]), "866").split("\r\n")
            if "IPv4" in x
        ]
    else:
        iptool = ["ip", "address"]
        if platform.system() == "Darwin":
            iptool = ["ifconfig"]
        return [
            x.split("/")[0].strip().split(" ")[1]
            for x in str(check_output(iptool), "ascii").split("\n")
            if "inet " in x and "127.0." not in x
        ]


def SearchXM(devices):
    # pick the first wired interface
    det_intfs = list(zip(*socket.if_nameindex()))[1]
    print("detected network interfaces:", det_intfs)
    intfsf = list(filter(lambda i: i in intfs, det_intfs))       
    print("prefferd interfaces:", intfsf)
    intf = intfsf[0]
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    
    # hack to use eth0 interface instantly
    print("Interface:", intf)
    print("IP:", get_ip_address(intf))
    server.bind(('', 34569))
    print("binded")
    server.settimeout(3)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if sys.platform != 'win32':
        server.setsockopt(socket.SOL_SOCKET, 25, intf.encode('utf-8') + '\0'.encode('utf-8'))
    server.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    server.sendto(
        struct.pack("BBHIIHHI", 255, 0, 0, 0, 0, 0, 1530, 0), ("255.255.255.255", 34569)
    )
    print("sent")
    while True:
        data = server.recvfrom(1024)
        head, ver, typ, session, packet, info, msg, leng = struct.unpack(
            "BBHIIHHI", data[0][:20]
        )
        if (msg == 1531) and leng > 0:
            answer = json.loads(
                data[0][20:20 + leng].replace(b"\x00", b""))
            if answer["NetWork.NetCommon"]["MAC"] not in devices.keys():
                devices[answer["NetWork.NetCommon"]["MAC"]] = answer[
                    "NetWork.NetCommon"
                ]
                devices[answer["NetWork.NetCommon"]["MAC"]][u"Brand"] = u"xm"
    server.close()
    return devices


def ConfigXM(data):
    config = {}
    #TODO: may be just copy whwole devices[data[1]] to config?
    for k in [u"HostName",u"HttpPort",u"MAC",u"MaxBps",u"MonMode",u"SSLPort",u"TCPMaxConn",u"TCPPort",u"TransferPlan",u"UDPPort","UseHSDownLoad"]:
        if k in devices[data[1]]:
            config[k] = devices[data[1]][k]
    print(devices[data[1]][u"HostName"])
    config[u"DvrMac"] = devices[data[1]][u"MAC"]
    config[u"EncryptType"] = 1
    config[u"GateWay"] = SetIP(data[4])
    config[u"HostIP"] = SetIP(data[2])
    config[u"Submask"] = SetIP(data[3])
    config[u"Username"] = "admin"
    config[u"Password"] = sofia_hash(data[5])
    devices[data[1]][u"GateWay"] = config[u"GateWay"]
    devices[data[1]][u"HostIP"] = config[u"HostIP"]
    devices[data[1]][u"Submask"] = config[u"Submask"]
    config = json.dumps(
        config, ensure_ascii=False, sort_keys=True, separators=(", ", " : ")
    ).encode("utf8")
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("", 34569))
    server.settimeout(1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    clen = len(config)
    print(struct.pack(
        "BBHIIHHI%ds2s" % clen,
        255,
        0,
        254,
        0,
        0,
        0,
        1532,
        clen + 2,
        config,
        b"\x0a\x00",),)
    server.sendto(
        struct.pack(
            "BBHIIHHI%ds2s" % clen,
            255,
            0,
            254,
            0,
            0,
            0,
            1532,
            clen + 2,
            config,
            b"\x0a\x00",
        ),
        ("255.255.255.255", 34569),
    )
    answer = {"Ret": 203}
    e = 0
    while True:
        try:
            data = server.recvfrom(1024)
            head, ver, typ, session, packet, info, msg, leng = struct.unpack(
                "BBHIIHHI", data[0][:20]
            )
            if (msg == 1533) and leng > 0:
                answer = json.loads(
                    data[0][20:20 + leng].replace(b"\x00", b""))
                break
        except:
            e += 1
            if e > 3:
                break
    server.close()
    return answer


def ProcessCMD(cmd):
    global log, logLevel, devices, searchers, configure, flashers
    if logLevel == 20:
        tolog(datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S] >") + " ".join(cmd))
    if cmd[0].lower() == "q" or cmd[0].lower() == "quit":
        sys.exit(1)
    if cmd[0].lower() in ["help", "?", "/?", "-h", "--help"]:
        return help
    if cmd[0].lower() == "search":
        tolog("%s" % ("Search"))
        if len(cmd) > 1 and cmd[1].lower() in searchers.keys():
            try:
                devices = searchers[cmd[1].lower()](devices)
            except Exception as error:
                print(" ".join([str(x) for x in list(error.args)]))
            print("Searching %s, found %d devices" % (cmd[1], len(devices)))
        else:
            for s in searchers:
                tolog("Search" + " %s\r" % s)
                try:
                    devices = searchers[s](devices)
                except Exception as error:
                    print(" ".join([str(x) for x in list(error.args)]))
            tolog("Found %d devices" % len(devices))
        if len(devices) > 0:
            if logLevel > 0:
                cmd[0] = "table"
                print("")
    if cmd[0].lower() == "table":
        logs = (
            "Vendor"
            + "\t"
            + "MAC Address"
            + "\t\t"
            + "Name"
            + "\t"
            + "IP Address"
            + "\t"
            + "Port"
            + "\n"
        )
        for dev in devices:
            logs += "%s\t%s\t%s\t%s\t%s\n" % (
                devices[dev]["Brand"],
                devices[dev]["MAC"],
                devices[dev]["HostName"],
                GetIP(devices[dev]["HostIP"]),
                devices[dev]["TCPPort"],
            )
        if logLevel >= 20:
            tolog(logs)
        if logLevel >= 10:
            return logs
        if logLevel < 10:
            print(logs)
    if cmd[0].lower() == "csv":
        logs = "Vendor;MAC Address;Name;IP Address;Port;SN\n"
        for dev in devices:
            logs += "%s;%s;%s;%s;%s;%s\n" % (
                devices[dev]["Brand"],
                devices[dev]["MAC"],
                devices[dev]["HostName"],
                GetIP(devices[dev]["HostIP"]),
                devices[dev]["TCPPort"],
                devices[dev]["SN"],
            )
        if logLevel >= 20:
            tolog(logs)
        if logLevel >= 10:
            return logs
    if cmd[0].lower() == "html":
        logs = (
            "<table border=1><th>"
            + "Vendor"
            + "</th><th>"
            + "MAC Address"
            + "</th><th>"
            + "Name"
            + "</th><th>"
            + "IP Address"
            + "</th><th>"
            + "Port"
            + "</th><th>"
            + "SN"
            + "</th>\r\n"
        )
        for dev in devices:
            logs += (
                "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\r\n"
                % (
                    devices[dev]["Brand"],
                    devices[dev]["MAC"],
                    devices[dev]["HostName"],
                    GetIP(devices[dev]["HostIP"]),
                    devices[dev]["TCPPort"],
                    devices[dev]["SN"],
                )
            )
        logs += "</table>\r\n"
        if logLevel >= 20:
            tolog(logs)
        if logLevel >= 10:
            return logs
    if cmd[0].lower() == "json":
        logs = json.dumps(devices)
        if logLevel >= 20:
            tolog(logs)
        if logLevel >= 10:
            return logs
    if cmd[0].lower() == "device":
        if len(cmd) > 1 and cmd[1] in devices.keys():
            return json.dumps(devices[cmd[1]])
        else:
            return "device [MAC]"
            
    if cmd[0].lower() == "config":
        if (
            len(cmd) > 5
            and cmd[1] in devices.keys()
            and devices[cmd[1]]["Brand"] in configure.keys()
        ):
            return configure[devices[cmd[1]]["Brand"]](cmd)
        else:
            return "config [MAC] [IP] [MASK] [GATE] [Pasword]"
    
    if cmd[0].lower() == "flash":
        if (
            len(cmd) > 3
            and cmd[1] in devices.key(s)
            and devices[cmd[1]]["Brand"] in flashers.keys()
        ):
            if len(cmd) == 4:
                cmd[4] = tolog
            return flashers[devices[cmd[1]]["Brand"]](cmd)
        else:
            return "flash [MAC] [password] [file]"
    if cmd[0].lower() == "loglevel":
        if len(cmd) > 1:
            logLevel = int(cmd[1])
        else:
            return "loglevel [int]"
    if cmd[0].lower() == "log":
        if len(cmd) > 1:
            log = " ".join(cmd[1:])
        else:
            return "log [filename]"
    if cmd[0].lower() == "echo":
        if len(cmd) > 1:
            return " ".join(cmd[1:])
    return ""


class GUITk:
    def __init__(self, root):
        self.root = root
        self.root.wm_title("RMS Camera Hunter")
        self.root.tk.call("wm", "iconphoto", root._w, Tk.PhotoImage(data=icon))
        self.f = Tk.Frame(self.root)
        self.f.pack(fill=Tk.BOTH, expand=Tk.YES)

        self.f.columnconfigure(0, weight=1)
        self.f.rowconfigure(0, weight=1)

        self.fr = Tk.Frame(self.f)
        self.fr.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.fr_tools = Tk.Frame(self.f)
        self.fr_tools.grid(row=1, column=0, columnspan=6, sticky="ew")
        self.fr_config = Tk.Frame(self.f)
        self.fr_config.grid(row=0, column=5, sticky="nsew")

        self.fr.columnconfigure(0, weight=1)
        self.fr.rowconfigure(0, weight=1)

        self.table = ttk.Treeview(self.fr, show="headings", selectmode="browse", height=8)
        self.table.grid(column=0, row=0, sticky="nsew")
        self.table["columns"] = ("ID", "vendor", "addr", "port", "name", "mac", "sn")
        self.table["displaycolumns"] = ("addr", "name", "mac", "sn")

        self.table.heading("vendor", text="Vendor", anchor="w")
        self.table.heading("addr", text="IP Address", anchor="w")
        self.table.heading("port", text="Port", anchor="w")
        self.table.heading("name", text="Name", anchor="w")
        self.table.heading("mac", text="MAC Address", anchor="w")
        self.table.heading("sn", text="SN", anchor="w")

        self.table.column("vendor", stretch=0, width=50)
        self.table.column("addr", stretch=0, width=110)
        self.table.column("port", stretch=0, width=50)
        self.table.column("name", stretch=0, width=80)
        self.table.column("mac", stretch=0, width=130)
        self.table.column("sn", stretch=0, width=120)

        self.scrollY = Tk.Scrollbar(self.fr, orient=Tk.VERTICAL)
        self.scrollY.config(command=self.table.yview)
        self.scrollY.grid(row=0, column=1, sticky="ns")
        self.scrollX = Tk.Scrollbar(self.fr, orient=Tk.HORIZONTAL)
        self.scrollX.config(command=self.table.xview)
        self.scrollX.grid(row=1, column=0, sticky="ew")
        self.table.config(
            yscrollcommand=self.scrollY.set, xscrollcommand=self.scrollX.set
        )

        self.table.bind("<ButtonRelease>", self.select)
        self.popup_menu = Tk.Menu(self.table, tearoff=0)
        self.popup_menu.add_command(
            label="Copy SN",
            command=lambda: (
                self.root.clipboard_clear()
                or self.root.clipboard_append(
                    self.table.item(self.table.selection()[0], option="values")[6]
                )
            )
            if len(self.table.selection()) > 0
            else None,
        )
        self.popup_menu.add_command(
            label="Copy line",
            command=lambda: (
                self.root.clipboard_clear()
                or self.root.clipboard_append(
                    "\t".join(
                        self.table.item(self.table.selection()[0], option="values")[1:]
                    )
                )
            )
            if len(self.table.selection()) > 0
            else None,
        )
        self.table.bind("<Button-3>", self.popup)

        self.l0 = Tk.Label(self.fr_config, text="Name")
        self.l0.grid(row=0, column=0, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.name = Tk.Entry(self.fr_config, width=15, font="6")
        self.name.grid(row=0, column=1, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.l1 = Tk.Label(self.fr_config, text="IP Address")
        self.l1.grid(row=1, column=0, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.addr = Tk.Entry(self.fr_config, width=15, font="6")
        self.addr.grid(row=1, column=1, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.l2 = Tk.Label(self.fr_config, text="Mask")
        self.l2.grid(row=2, column=0, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.mask = Tk.Entry(self.fr_config, width=15, font="6")
        self.mask.grid(row=2, column=1, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.l3 = Tk.Label(self.fr_config, text="Gateway")
        self.l3.grid(row=3, column=0, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.gate = Tk.Entry(self.fr_config, width=15, font="6")
        self.gate.grid(row=3, column=1, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.aspc = Tk.Button(self.fr_config, text="As on PC", command=self.addr_pc)
        #self.aspc.grid(row=4, column=1, pady=3, padx=5, sticky="ew")
        self.l4 = Tk.Label(self.fr_config, text="HTTP Port")
        #self.l4.grid(row=5, column=0, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.http = Tk.Entry(self.fr_config, width=5, font="6")
        #self.http.grid(row=5, column=1, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.l5 = Tk.Label(self.fr_config, text="TCP Port")
        #self.l5.grid(row=6, column=0, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.tcp = Tk.Entry(self.fr_config, width=5, font="6")
        #self.tcp.grid(row=6, column=1, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.l6 = Tk.Label(self.fr_config, text="Password")
        self.l6.grid(row=7, column=0, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.passw = Tk.Entry(self.fr_config, width=15, font="6")
        self.passw.grid(row=7, column=1, pady=3, padx=5, sticky=Tk.W + Tk.N)
        self.aply = Tk.Button(self.fr_config, text="Apply", command=self.setconfig)
        self.aply.grid(row=8, column=1, pady=3, padx=5, sticky="ew")

        #self.l7 = Label(self.fr_tools, text=_("Vendor"))
        #self.l7.grid(row=0, column=0, pady=3, padx=5, sticky="wns")
        self.ven = ttk.Combobox(self.fr_tools, width=10)
        #self.ven.grid(row=0, column=1, padx=5, sticky="w")
        self.ven["values"] = ["XM",]
        self.ven.current(0)
        self.search = Tk.Button(self.fr_tools, text="Search", command=self.search)
        self.search.grid(row=0, column=2, pady=5, padx=5, sticky=Tk.W + Tk.N)
        self.reset = Tk.Button(self.fr_tools, text="Reset", command=self.clear)
        self.reset.grid(row=0, column=3, pady=5, padx=5, sticky=Tk.W + Tk.N)
        self.exp = Tk.Button(self.fr_tools, text="Export", command=self.export)
        self.exp.grid(row=0, column=4, pady=5, padx=5, sticky=Tk.W + Tk.N)
        #self.fl_state = StringVar(value=_("Flash"))
        #self.fl = Button(self.fr_tools, textvar=self.fl_state, command=self.flash)
        #self.fl.grid(row=0, column=5, pady=5, padx=5, sticky=W + N)

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def addr_pc(self):
        _addr, _mask, _gate = local_ip()
        self.addr.delete(0, Tk.END)
        self.addr.insert(Tk.END, _addr)
        self.mask.delete(0, Tk.END)
        self.mask.insert(Tk.END, _mask)
        self.gate.delete(0, Tk.END)
        self.gate.insert(Tk.END, _gate)

    def search(self):
        self.clear()
        #if self.ven["values"].index(self.ven.get()) == 0:
        ProcessCMD(["search"])
        #else:
        #    ProcessCMD(["search", self.ven.get()])
        self.pop()

    def pop(self):
        for dev in devices:
            self.table.insert(
                "",
                "end",
                values=(
                    dev,
                    devices[dev]["Brand"],
                    GetIP(devices[dev]["HostIP"]),
                    devices[dev]["TCPPort"],
                    devices[dev]["HostName"],
                    devices[dev]["MAC"],
                    devices[dev]["SN"],
                ),
            )

    def clear(self):
        global devices
        for i in self.table.get_children():
            self.table.delete(i)
        devices = {}

    def select(self, event):
        if len(self.table.selection()) == 0:
            return
        dev = self.table.item(self.table.selection()[0], option="values")[0]
        if logLevel >= 20:
            print(json.dumps(devices[dev], indent=4, sort_keys=True))
        self.name.delete(0, Tk.END)
        self.name.insert(Tk.END, devices[dev]["HostName"])
        self.addr.delete(0, Tk.END)
        self.addr.insert(Tk.END, GetIP(devices[dev]["HostIP"]))
        self.mask.delete(0, Tk.END)
        self.mask.insert(Tk.END, GetIP(devices[dev]["Submask"]))
        self.gate.delete(0, Tk.END)
        self.gate.insert(Tk.END, GetIP(devices[dev]["GateWay"]))
        self.http.delete(0, Tk.END)
        self.http.insert(Tk.END, devices[dev]["HttpPort"])
        self.tcp.delete(0, Tk.END)
        self.tcp.insert(Tk.END, devices[dev]["TCPPort"])

    def setconfig(self):
        dev = self.table.item(self.table.selection()[0], option="values")[0]
        devices[dev][u"TCPPort"] = int(self.tcp.get())
        devices[dev][u"HttpPort"] = int(self.http.get())
        devices[dev][u"HostName"] = self.name.get()
        result = ProcessCMD(
            [
                "config",
                dev,
                self.addr.get(),
                self.mask.get(),
                self.gate.get(),
                self.passw.get(),
            ]
        )
        if result["Ret"] == 100:
            self.table.item(
                self.table.selection()[0],
                values=(
                    dev,
                    devices[dev]["Brand"],
                    GetIP(devices[dev]["HostIP"]),
                    devices[dev]["TCPPort"],
                    devices[dev]["HostName"],
                    devices[dev]["MAC"],
                    devices[dev]["SN"],
                ),
            )
        else:
            showerror("Error"), CODES[result["Ret"]]

    def export(self):
        filename = asksaveasfilename(
            filetypes=(
                ("JSON files", "*.json"),
                ("HTML files", "*.html;*.htm"),
                ("Text files", "*.csv;*.txt"),
                ("All files", "*.*"),
            )
        )
        if filename == "":
            return
        ProcessCMD(["log", filename])
        ProcessCMD(["loglevel", str(100)])
        if ".json" in filename:
            ProcessCMD(["json"])
        elif ".csv" in filename:
            ProcessCMD(["csv"])
        elif ".htm" in filename:
            ProcessCMD(["html"])
        else:
            ProcessCMD(["table"])
        ProcessCMD(["loglevel", str(10)])

    def flash(self):
        self.fl_state.set("Processing...")
        filename = askopenfilename(
            filetypes=(("Flash", "*.bin"), ("All files", "*.*"))
        )
        if filename == "":
            return
        if len(self.table.selection()) == 0:
            _mac = "all"
        else:
            _mac = self.table.item(self.table.selection()[0], option="values")[4]
        result = ProcessCMD(
            ["flash", _mac, self.passw.get(), filename, self.fl_state.set]
        )
        if (
            hasattr(result, "keys")
            and "Ret" in result.keys()
            and result["Ret"] in CODES.keys()
        ):
            showerror("Error", CODES[result["Ret"]])


searchers = {
    #"wans": SearchWans,
    "xm": SearchXM,
    #"dahua": SearchDahua,
    #"fros": SearchFros,
    #"beward": SearchBeward,
}
configure = {
    #"wans": ConfigWans,
    "xm": ConfigXM,
    #"fros": ConfigFros,
}  # ,"dahua":ConfigDahua
#flashers = {"xm": FlashXM}  # ,"dahua":FlashDahua,"fros":FlashFros
logLevel = 30
if __name__ == "__main__":
    if len(sys.argv) > 1:
        argvs = (sys.argv[1:]).copy()
        if '-i' in argvs:
            ifac = argvs[argvs.index('-i')+1]
            print(f'new interface {ifac}')
            intfs.append(ifac)
            argvs.remove(ifac)
            argvs.remove('-i')
        cmds = " ".join(argvs)
        if cmds.find("-q ") != -1:
            cmds = cmds.replace("-q ", "").replace("-n ", "").strip()
            logLevel = 0
        for cmd in cmds.split(";"):
            ProcessCMD(cmd.split(" "))
    if GUI_TK and "-n" not in sys.argv:
        root = Tk.Tk()
        app = GUITk(root)
        if (
            "--theme" in sys.argv
        ):  # ('winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative')
            style = Tk.Style()
            theme = [sys.argv.index("--theme") + 1]
            if theme in style.theme_names():
                style.theme_use(theme)
        root.mainloop()
        sys.exit(1)
    print("Type help or ? to display help(q or quit to exit)")
    while True:
        data = input("> ").split(";")
        for cmd in data:
            result = ProcessCMD(cmd.split(" "))
            if hasattr(result, "keys") and "Ret" in result.keys():
                print(CODES[result["Ret"]])
            else:
                print(result)
    sys.exit(1)
    