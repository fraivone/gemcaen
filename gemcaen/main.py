from prompt_logger import logger as logging
from argparse import RawTextHelpFormatter
from logger_classes import MainframeLogger,DeviceLogger
from config_parser import load_config
import argparse
import threading
import signal
import functools


terminateEvent = threading.Event() ## when set, kills all the threads

## catch keyboard interrupt and issue terminateEvent
@functools.lru_cache
def sigint_handler(signal, frame):
    terminateEvent.set()
    print()
    logging.warning(f"Received interrupt signal")
    logging.warning("Execution will terminate upon mainframes connections closure... ")

#### PARSER
parser = argparse.ArgumentParser(
    description='''Scripts that: \n\t-Takes as input a list of keys that match those in the config.yml file\n\t-Checks if the parsed keys have a legit configuration\n\t-Starts the monitoring of the specified HW quantities''',
    epilog="""Typical exectuion\n\t python main.py ME0_0001_CERN ME0_0001_CERN_LV""",
    formatter_class=RawTextHelpFormatter
)
parser.add_argument("setupNames", type=str, help="Setup names you want to monitor as they appear in the config file. Space separated.", nargs="*")
args = parser.parse_args()

def run():
    loggers = {}
    cfg = load_config(args.setupNames)
    [logging.debug(f"Mainframe {ip}, devices {list(cfg[ip]['configs'].keys())}") for ip in cfg.keys()]
    

    for ip in cfg:
        mainframe_cfg = cfg[ip]["MAINFRAME"]
        device_configs = cfg[ip]["configs"]
        loggers[ip] = MainframeLogger(mainframe_cfg,device_configs,terminateEvent)
        loggers[ip].start()
        
    signal.signal(signal.SIGINT, sigint_handler)
if __name__ == "__main__":
    run()

