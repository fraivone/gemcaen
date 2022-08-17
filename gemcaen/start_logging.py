from argparse import RawTextHelpFormatter
import argparse
from logger import *
import yaml

CONFIG_PATH = pathlib.Path(__file__).parent / "config/config.yml"


def load_config(setup_name):
    with CONFIG_PATH.open() as ymlfile:
        cfg = yaml.full_load(ymlfile)
    cfg = cfg[setup_name]
    check_config(setup_name,cfg)
    return cfg

def check_config(setup_name,cfg):
    ## Required keys
    CFG_REQ_KEYS = ["HW","influxDB","Monitorables","isGEMDetector"] 
    HW_REQ_KEYS = ["CAENHV_BOARD_TYPE","CAENHV_LINK_TYPE","CAENHV_BOARD_ADDRESS","CAENHV_USER","CAENHV_PASSWORD","SLOT"] 
    DB_REQ_KEYS = ["DB_BUCKET","ORG","URL","TOKEN"]
    
    ## Check cfg req keys
    for key in CFG_REQ_KEYS:
        try:
            cfg[key]
        except:
            raise ValueError("Expected key "+key+" not found in configuration file for the setup "+str(setup_name))
    cfg_temp = cfg["HW"]
    
    ## Check HW req keys

    # Handle case of GEM Detector 
    if cfg["isGEMDetector"]: HW_REQ_KEYS.append("LAYER")
    else: HW_REQ_KEYS.append("CHANNELS")

    for key in HW_REQ_KEYS:
        try:
            cfg_temp[key]
        except:
            raise ValueError("Expected key \'",key," not found in ",cfg_temp.keys())
    
    cfg_temp = cfg["influxDB"]    
    ## Check DB req keys
    for key in DB_REQ_KEYS:
        try:
            cfg_temp[key]
        except:
            raise ValueError("Expected key \'",key," not found in ",cfg_temp.keys())


#### PARSER
parser = argparse.ArgumentParser(
    description='''Scripts that: \n\t-Takes a list of key in the config.yml file\n\t-Check if the parsed config is legit\n\t-Starts the monitoring of the specified HW quantities''',
    epilog="""Typical exectuion\n\t python start_logging.py ME0CosmicStand IntegrationStand""",
    formatter_class=RawTextHelpFormatter
)
parser.add_argument("setupNames", type=str, help="Key in the config file", nargs="*")
args = parser.parse_args()


loggers = {}
parsed_setupnames = args.setupNames

for setup_name in parsed_setupnames:
    ## Load config
    cfg = load_config(setup_name)

    isGEMDetector = cfg["isGEMDetector"]
    HW_Config = cfg["HW"]
    DB_Config = cfg["influxDB"]
    Monitorables = cfg["Monitorables"]

    ## logger class now inherits from Thread
    logger = BaseLogger(setup_name,HW_Config,DB_Config,isGEMDetector,rate=2)
    logger.set_monitored_quantities(Monitorables)
    loggers[setup_name] = logger

for name,loggr in loggers.items():
    loggr.start()



