import collections

class LinuxApiStats(BehaviorHandler):
    """Counts API calls."""
    key = "apistats"
    event_types = ["process"]

    def __init__(self, *args, **kwargs):
        super(ApiStats, self).__init__(*args, **kwargs)
        self.processes = []

    def handle_event(self, event):
        pid = str(event["pid"])
        self.processes[pid] = []

        for call in event["calls"]:
            if call["api"] in self.processes[pid]: 
                self.processes[pid][call["api"]] += 1
            else 
                self.processes[pid][call["api"]] = 1

    def run(self):
        return self.processes