import logging
import os
import subprocess

from cuckoo.common.abstracts import Auxiliary

log = logging.getLogger(__name__)

class Aide(Auxiliary):
    def __init__(self):
        Auxiliary.__init__(self)
        self.aide = self.options.get("aide", "/usr/bin/aide")
        self.config = self.options.get("config", "/etc/aide/aide.conf")
        self.db_dir = self.options.get("db_dir", "/var/lib/aide")
        self.log = self.options.get("log", "/var/log/aide/aide.log")
       
    def start(self):
        if not os.path.exists(self.aide):
            log.error("aide does not exist at path \"%s\", aide "
                      "check aborted", self.aide)
            return False
        
        if not os.path.exists(self.config):
            log.error("aide config does not exist at path \"%s\", aide "
                      "check aborted", self.config)
            return False

        aide_init = [
            self.aide, "--config", self.config, "--init",
        ]

        delete_cmd = [
            "rm", "-rf", self.db_dir + "/*", 
        ]
        
        try:
            # deleting current AIDE database
            subprocess.check_output(delete_cmd, universal_newlines=True)

            # initing AIDE database
            subprocess.check_output(aide_init, universal_newlines=True)
                        
        except (OSError, ValueError, subprocess.CalledProcessError) as e:
            log.exception(
                "Failed to start init aide: %s",
                e
            )
            return False
        
        return True
    
    def stop(self):
        aide_check = [
            self.aide, "--config", self.config, "--check",
        ]

        try:
            log_file = open(self.log, "w")

            # checking AIDE database
            p = subprocess.Popen(aide_check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, output_err = p.communicate()
        except (OSError, ValueError) as e:
            log.exception(
                "Failed to start check aide: %s",
                e
            )
        except Exception as e:
            log.exception(
                "AIDE exited with none-zero code. Files integrity has "
                "been changed. %s",
                e
            )
        finally:
            if output:
                log_file.write(output)
            if output_err:
                log_file.write(output_err)
            log_file.close()