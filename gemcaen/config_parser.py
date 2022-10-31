import yaml
from deepdiff import DeepDiff
import pathlib
from prompt_logger import logger as logging

CONFIG_PATH = pathlib.Path(__file__).parent / "config/config.yml"

def load_config(setup_names):
    loaded_cfg = {}
    for setup_name in setup_names:
        with CONFIG_PATH.open() as ymlfile:
            cfg = yaml.full_load(ymlfile)
        check_config(setup_name,cfg[setup_name])
        loaded_cfg[setup_name] = cfg[setup_name]
    cfg = MergeMainframes_config(loaded_cfg)
    return cfg


## Group setups by mainframes IP
## output cfg:  {<IP> : dict( 
##                           configs: dict( <setup_name>: <config>), 
##                           mainframe:<cfg_mainframe>
##                           )
##              }
def MergeMainframes_config(cfg):
    mainframe2setupnames,mainframe_configs = {},{}
    output_dict = {}
    for setup_name in cfg: 
        ip_mainframe = cfg[setup_name]["MAINFRAME"]["CAENHV_BOARD_ADDRESS"]
        mainframe2setupnames.setdefault(ip_mainframe,[])
        mainframe2setupnames[ip_mainframe].append(setup_name)

    for ip in mainframe2setupnames.keys():
        ## Ensure all MAINFRAME config realted to the same ip are identical
        s = [ DeepDiff(cfg[current_setup]["MAINFRAME"], cfg[x]["MAINFRAME"], verbose_level=2) == {} for current_setup in mainframe2setupnames[ip] for x in mainframe2setupnames[ip] ]
        if not all(s):
            logging.error(f"Setups related to ip {ip} do not share the same config for the key MAINFRAME. Check the config file.")
            raise ValueError(f"Config file error")

        output_dict.setdefault(ip,{"MAINFRAME":None,"configs":{}})
        output_dict[ip]["MAINFRAME"] = cfg[mainframe2setupnames[ip][0]]["MAINFRAME"]
        for setup_name in mainframe2setupnames[ip]: 
            del cfg[setup_name]["MAINFRAME"]
            output_dict[ip]["configs"][setup_name] = cfg[setup_name]
          
    logging.info(f"Merged configuration based on mainframes IPs")
    return output_dict

def check_config(setup_name,cfg):
    ## Required keys  
    CFG_REQ_KEYS = ["MAINFRAME","BOARD","influxDB","Monitorables","isGEMDetector","HoldOffTime"] 
    MAINFRAME_REQ_KEYS = ["CAENHV_BOARD_TYPE","CAENHV_LINK_TYPE","CAENHV_BOARD_ADDRESS","CAENHV_USER","CAENHV_PASSWORD"]
    BOARD_REQ_KEYS = ["SLOT"]
    DB_REQ_KEYS = ["DB_BUCKET","ORG","URL","TOKEN"]
    
    # Handle case of GEM Detector 
    if cfg["isGEMDetector"]: BOARD_REQ_KEYS.append("LAYER")
    else: BOARD_REQ_KEYS.append("CHANNELS")

    ## Check cfg_file,MAINFRAME,BOARD and influxDB req keys
    logging.debug(f"Checking config file for {setup_name}")
    for config_key,item in {"":(cfg,CFG_REQ_KEYS),"BOARD":(cfg["BOARD"],BOARD_REQ_KEYS),"MAINFRAME":(cfg["MAINFRAME"],MAINFRAME_REQ_KEYS),"influxDB":(cfg["influxDB"],DB_REQ_KEYS)}.items():
        cfg_found,required = item
        for key in required:
            try:
                cfg_found[key]
            except:
                raise ValueError("Expected key \'",key," not found in ",cfg_found.keys())

        if config_key != "": logging.debug(f"\tconfig[{setup_name}][{config_key}] has all the keys")
    logging.debug(f"Config file for {setup_name} is ok")

if __name__ == '__main__':
    pass
