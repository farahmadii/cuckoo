from cuckoo.common.abstracts import Processing

class Aide(Processing):

    def run(self):
        self.key = "aide"

        content = ""
        with open("/var/log/aide/aide.log") as log:
            content = log.read()

        with open(self.logs_path+"/aide.log") as log:
            log.write(content)
        
        return content