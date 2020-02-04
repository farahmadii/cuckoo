import logging
import os
import subprocess

from lib.common.results import NetlogFile
from lib.common.abstracts import Auxiliary

log = logging.getLogger(__name__)

class Aide(Auxiliary):
    priority = -20

    @staticmethod
    def _upload_file(local, remote):
        if os.path.exists(local):
            nf = NetlogFile(remote)
            with open(local, "rb") as f:
                for chunk in f:
                    nf.sock.sendall(chunk)  # dirty direct send, no reconnecting
            nf.close()

    def __init__(self):
        self.aide = "/usr/bin/aide"
        self.config = "/etc/aide/aide.conf"
        self.db_dir = "/var/lib/aide"
        self.log_file = "/var/log/aide/aide.log"

    def start(self):
        if not os.path.exists(self.aide):
            log.error("Aide does not exist at path \"%s\", aide "
                      "check aborted", self.aide)
            return False

        if not os.path.exists(self.config):
            log.error("Aide config does not exist at path \"%s\", aide "
                      "check aborted", self.config)
            return False

        aide_init = [
            self.aide, "--config", self.config, "--init",
        ]

        delete_cmd = [
            "rm", "-rf", self.db_dir + "/*", 
        ]

        try:
            log.debug("Aide: deleting old database.")
            # deleting current AIDE database
            subprocess.check_output(delete_cmd, universal_newlines=True)
            
            log.debug("Aide: initiliazing new database.")
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
            log.info("Aide: writing log to %s", self.log_file)
            log_file = open(self.log_file, "w")

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

            self._upload_file(self.log_file, "logs/aide.log")