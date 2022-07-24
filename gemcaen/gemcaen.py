import pathlib
import yaml
import functools
import tableformatter as tf

from pycaenhv.wrappers import init_system, deinit_system, get_board_parameters, get_crate_map, get_channel_parameters,get_channel_parameter, list_commands,get_channel_parameter_property,get_channel_name,set_channel_parameter
from pycaenhv.enums import CAENHV_SYSTEM_TYPE, LinkType
from pycaenhv.errors import CAENHVError


CONFIG_PATH = pathlib.Path(__file__).parent / "config/config.yml"

def load_config():
    with CONFIG_PATH.open() as ymlfile:
        cfg = yaml.full_load(ymlfile)
    return cfg

def singleton(cls):
    """ allow only one istance of a class """
    @functools.wraps(cls)
    def wrapper_singleton(*args, **kwargs):
        if not wrapper_singleton.istance:
            wrapper_singleton.istance = cls(*args, **kwargs)
        return wrapper_singleton.istance

    wrapper_singleton.istance = None
    return wrapper_singleton

@singleton
class BoardBase:
    def __init__(self,setup_name):
        self.setup_name = setup_name
        self.cfg_keys = ["CAENHV_BOARD_TYPE","CAENHV_LINK_TYPE","CAENHV_BOARD_ADDRESS","CAENHV_USER","CAENHV_PASSWORD","SLOT"] 
        self.check_good_config()
        self.cfg = load_config()[self.setup_name]
        self.board_slot = self.cfg["SLOT"]
        self.handle = self.get_cratehandle()
        
        self.crate_map = get_crate_map(self.handle)

        self.board_name = self.crate_map["models"][self.board_slot]
        self.board_description = self.crate_map["descriptions"][self.board_slot]
        
        self.n_channels = self.crate_map["channels"][self.board_slot]
        self.channel_names_map, self.channel_quantities_map = self.map_channels()  ## channel_<name/quant>_map[ch_index] = ch_<name/quant>
        
    def check_good_config(self):
        if self.setup_name in load_config().keys():
            if all(key in load_config()[self.setup_name].keys()  for key in self.cfg_keys):
                return True
        raise ValueError(self.setup_name, " has an invalid/incomplete configuration in ",CONFIG_PATH)


    def get_cratehandle(self):
        system_type = CAENHV_SYSTEM_TYPE[self.cfg['CAENHV_BOARD_TYPE']]
        link_type = LinkType[self.cfg['CAENHV_LINK_TYPE']]
        handle = init_system(system_type, link_type,
                         self.cfg['CAENHV_BOARD_ADDRESS'],
                         self.cfg['CAENHV_USER'],
                         self.cfg['CAENHV_PASSWORD'])
        try:
            crate_map = get_crate_map(handle)
            return handle
        except CAENHVError as err:
            print(f"Got error: {err}\nExiting ...")


    def print_board_status(self):
        print(f"Board {self.board_name} status --> {self.board_description}")
        cols, rows = ["Ch_Number","Ch_Name"], []
        
        for ch,channel_name in self.channel_map.items():
            row = [channel_name]
            for quantity in self.channel_quantities_map[ch]:
                channel_value = get_channel_parameter(self.handle,self.board_slot,ch,quantity)
                row.append(round(channel_value,3))    
            rows.append(row)
        
        cols = cols + self.channel_quantities_map[ch] ## assume all board's channels have same quantities
        print(tf.generate_table(rows, cols, grid_style=tf.AlternatingRowGrid()))
    
    def map_channels(self):
        channel_names_map = dict()
        channel_quantities_map = dict()
        for ch in range(self.n_channels):
            channel_names_map[ch] = get_channel_name(self.handle,self.board_slot,ch)
            channel_quantities_map[ch] = get_channel_parameters(self.handle,self.slot,ch)
        return  channel_names_map,channel_quantities_map


    def get_channel_value(self,channel_index:int,quantity:str):
        if channel_index not in range(self.n_channels):
            raise ValueError("Invalid channel index ",channel_index)
        if quantity not in self.channel_quantities_map[channel_index]:
            raise ValueError("Invalid quantity ",quantity,". Valid quantities are ",self.channel_quantities_map)
        return get_channel_parameter(self.handle,self.slot,channel_index,quantity)

c = BoardBase("IntegrationStand_Scintillator")
c.print_board_status()
print(c.get_channel_value(2,"VMon"))







