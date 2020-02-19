import collections
import logging
from sets import Set

from cuckoo.common.abstracts import BehaviorHandler

log = logging.getLogger(__name__)

class LinuxApiStats(BehaviorHandler):
    """Counts API calls."""
    key = "apistats"
    event_types = ["process"]

    def __init__(self, *args, **kwargs):
        super(LinuxApiStats, self).__init__(*args, **kwargs)
        self.processes = {}

    def handle_event(self, event):
        log.info("Generating linux api stats report p:%s...." % event["pid"])
        pid = str(event["pid"])
        self.processes[pid] = {}

        for call in event["calls"]:
            if call["api"] in self.processes[pid]: 
                self.processes[pid][call["api"]] += 1
            else:
                self.processes[pid][call["api"]] = 1

    def run(self):
        return self.processes

# Sample openat system call:
#-----------------------------------------------------------------------------------------
# {
#     "status": "",
#     "raw": "Sun Feb 16 12:09:05 2020.771877 uname@7efd41e2adb1[3175] openat(AT_FDCWD, \"/usr/lib/locale/locale-archive\", O_RDONLY|O_CLOEXEC) = 9\n",
#     "api": "openat",
#     "return_value": "9", ---> file descriptor
#     "instruction_pointer": "7efd41e2adb1",
#     "time": 1581854945.771877,
#     "process_name": "uname",
#     "pid": 3175,
#     "arguments": {
#         "p2": "O_RDONLY|O_CLOEXEC",
#         "p0": "AT_FDCWD",
#         "p1": "/usr/lib/locale/locale-archive"
#     }
# }
#-----------------------------------------------------------------------------------------
# Sample read system call:
#-----------------------------------------------------------------------------------------
# {
#     "status": "",
#     "raw": "Sun Feb 16 12:09:05 2020.770649 sh@7fce6ea68da4[3174] read(9, 0x7fffc6cc78a8, 832) = 832\n",
#     "api": "read",
#     "return_value": "832",
#     "instruction_pointer": "7fce6ea68da4",
#     "time": 1581854945.770649,
#     "process_name": "sh",
#     "pid": 3174,
#     "arguments": {
#         "p2": "832",
#         "p0": "9", ---> file descriptor
#         "p1": "0x7fffc6cc78a8"
#     }
# }
#-----------------------------------------------------------------------------------------

# Sample write system call:
#-----------------------------------------------------------------------------------------
# {
#     "status": "",
#     "raw": "Sun Feb 16 12:09:05 2020.978106 python@7f7e5d743154[3173] write(6, \"CHANGES.rst\\nCOPYRIGHT.txt\\nLICENSE.txt\\nMANI\"..., 1055) = 1055\n",
#     "api": "write",
#     "return_value": "1055",
#     "instruction_pointer": "7f7e5d743154",
#     "time": 1581854945.978106,
#     "process_name": "python",
#     "pid": 3173,
#     "arguments": {
#         "p2": "1055",
#         "p0": "6", ---> file descriptor 
#         "p1": "\"CHANGES.rst\\nCOPYRIGHT.txt\\nLICENSE.txt\\nMANI\"..."
#     }
# }
#-----------------------------------------------------------------------------------------
class LinuxFiles(BehaviorHandler):
    """File related system call."""
    key = "files"
    event_types = ["process"]

    def __init__(self, *args, **kwargs):
        super(LinuxFiles, self).__init__(*args, **kwargs)
        self.opened_files_map = {}
        self.opened_files_readonly = Set()
        self.opened_files_towrite = Set()
        self.opened_files_created = Set()
        self.opened_files_toappend = Set()
        self.open_files = Set()
        self.read_files = Set()
        self.written_files = Set()
        self.opened_directories = Set()
        self.failed_to_open = Set()
        self.pwd = ''

    def handle_event(self, event):
        log.info("Generating linux files report p:%s...." % event["pid"])

        if event["process_name"] == '.buildwatch.sh':
            # e.g "command_line": "/tmpnmxNz9/.buildwatch.sh"
            self.pwd = event['command_line'].replace('/.buildwatch.sh', '')

        for call in event["calls"]:
            api = call["api"]
            
            # creat() A  call  to  creat()  is equivalent to calling openat() with flags
            # equal to O_CREAT|O_WRONLY|O_TRUNC.
            if api == "creat":
                fd = int(call["return_value"])
                path = call["arguments"]["p0"]
                if fd >= 0:
                    self.opened_files_map[fd] = {
                        "return_value": fd, # file descriptor of the opened file or error code
                        "path": path, # filename
                        "flags": "O_CREAT|O_WRONLY|O_TRUNC",
                    }

                    self.open_files.add(path)
                else: # an error occurred so it's a failed try
                    self.failed_to_open.add(path)
                
            elif api == "openat":
                fd = int(call["return_value"])
                flags = call["arguments"]["p2"]
                path = call["arguments"]["p1"]
                if fd >= 0:
                    self.opened_files_map[fd] = {
                        "return_value": fd, # file descriptor of the opened file or error code
                        "path": path, # filename
                        "flags": flags, # Flags like O_RDONLY, O_CREAT, O_APPEND, ...
                    }
                    self.open_files.add(path)

                    if 'O_DIRECTORY' in flags:
                        self.opened_directories.add(path)
                    
                    if 'O_APPEND' in flags:
                        self.opened_files_toappend.add(path)
                        
                    if 'O_CREAT' in flags:
                        self.opened_files_created.add(path)
                    elif 'O_RDONLY' in flags:
                        self.opened_files_readonly.add(path)
                    elif 'O_WRONLY' in flags:
                        self.opened_files_towrite.add(path)
                    
                    

                else: # an error occurred so it's a failed try
                    self.failed_to_open.add(path)
                    
            elif api == "read":
                # file descriptor of the file. Later must be mapped to return_value 
                # of an openat system call to find the corresponding filename
                fd = int(call["arguments"]["p0"])
                ret = int(call["return_value"])
                if ret >= 0:
                    if fd in self.opened_files_map:
                        self.read_files.add(self.opened_files_map[fd]["path"])
                    elif fd not in [0, 1, 2]: #stdin/out/err
                        log.warning("Try to read file with unknown file descriptor")

            elif api == "write":
                fd = int(call["arguments"]["p0"])
                ret = int(call["return_value"])
                if ret >= 0:
                    if fd in self.opened_files_map:
                        self.written_files.add(self.opened_files_map[fd]["path"])
                    elif fd not in [0, 1, 2]: #stdin/out/err
                        log.warning("Try to write file with unknown file descriptor")

    def run(self):
        return {
            "pwd": self.pwd,
            "read_filenames": list(self.read_files),
            "written_filenames": list(self.written_files),
            "opened": {
                "all": list(self.open_files),
                "to_append": list(self.opened_files_toappend), 
                "to_write": list(self.opened_files_towrite),
                "readonly": list(self.opened_files_readonly),
                "created": list(self.opened_files_created),
                "failed": list(self.failed_to_open),
            },
            "directories": list(self.opened_directories),
        }

#-----------------------------------------------------------------------------------------
# Network connect system call:
#-----------------------------------------------------------------------------------------
# {
#   "status": "EINPROGRESS",
#   "raw": "Thu Jan  9 22:54:55 2020.015918 python@7fbc4b88d8b4[1556] connect(6, {AF_INET, 121.42.217.44, 8080}, 16) = -115 (EINPROGRESS)\n",
#   "api": "connect",
#   "return_value": "-115",
#   "instruction_pointer": "7fbc4b88d8b4",
#   "time": 1578610495.015918,
#   "process_name": "python",
#   "pid": 1556,
#   "arguments": {
#     "p2": "16",
#     "p0": "6",
#     "p1": [
#       "AF_INET",
#       "121.42.217.44",
#       "8080"
#     ]
#   }
# }
#-----------------------------------------------------------------------------------------

class LinuxNetwork(BehaviorHandler):
    """Network related system call."""
    key = "network"
    event_types = ["process"]

    def __init__(self, *args, **kwargs):
        super(LinuxNetwork, self).__init__(*args, **kwargs)
        self.connected_ips = Set()
        self.connected_sockets = Set()
    
    def handle_event(self, event):
        log.info("Generating linux network report p:%s...." % event["pid"])
        for call in event["calls"]:
            api = call["api"]
            
            if api == "connect":
                addr = call["arguments"]["p1"]
                if len(addr) == 3 and type(addr) == list: # e.g addr: ["AF_INET", "121.42.217.44", "8080"]
                    self.connected_ips.add(addr[1] + ":" + addr[2]) # "121.42.217.44:8080"
                elif len(addr) == 2 and type(addr) == list: # e.g addr: ["AF_UNIX", "/var/run/nscd/socket"]
                    self.connected_sockets.add(addr[1])
    
    def run(self):
        return {
            "connected_ips": list(self.connected_ips),
            "connected_sockets": list(self.connected_sockets),
        }
