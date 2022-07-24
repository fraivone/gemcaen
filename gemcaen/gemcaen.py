import pathlib
import yaml
import functools
import tableformatter as tf
import numbers

from pycaenhv.wrappers import init_system, deinit_system, get_board_parameters, get_crate_map, get_channel_parameters,get_channel_parameter, list_commands,get_channel_parameter_property,get_channel_name,set_channel_parameter
from pycaenhv.enums import CAENHV_SYSTEM_TYPE, LinkType
from pycaenhv.errors import CAENHVError


CONFIG_PATH = pathlib.Path(__file__).parent / "config/config.yml"

def load_config():
    with CONFIG_PATH.open() as ymlfile:
        cfg = yaml.full_load(ymlfile)
    return cfg

# def repeat_until(_func=None,*,max_rep=5,success_value=0,sleep_time= 1):
#     """ Repeat the execution of a function max_rep of times. If success, break """
#     def decorator_repeat_until(func):
#         @functools.wraps(func)
#         def wrapper(*args,**kwargs):
#             for _ in range(max_rep): 
#                 print(f"Call {_} to {func.__name__!r}")
#                 value = func(*args,**kwargs)
#                 if value == success_value: break
#                 time.sleep(sleep_time)
#             return value
#         return wrapper
#     if _func is None:
#         return decorator_repeat_until
#     else:
#         return decorator_repeat_until(_func)
    
#     return decorator_repeat_until

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

    def validChannel(self,channel_index:int):
        if channel_index not in range(self.n_channels):
            raise ValueError("Invalid channel index ",channel_index)
            return False
        return True
    def validQuantity(self,channel_index:int,quantity:str):
        if quantity not in self.channel_quantities_map[channel_index]:
            raise ValueError("Invalid quantity ",quantity,". Valid quantities are ",self.channel_quantities_map[channel_index])
            return False
        return True

    def map_channels(self):
        channel_names_map = dict()
        channel_quantities_map = dict()
        for ch in range(self.n_channels):
            channel_names_map[ch] = get_channel_name(self.handle,self.board_slot,ch)
            channel_quantities_map[ch] = get_channel_parameters(self.handle,self.board_slot,ch)
        return  channel_names_map,channel_quantities_map

    def print_board_status(self):
        print(f"Board {self.board_name} status --> {self.board_description}")
        cols, rows = ["Ch_Number","Ch_Name"], []
        
        for ch,channel_name in self.channel_names_map.items():
            row = [ch,channel_name]
            for quantity in self.channel_quantities_map[ch]:
                channel_value = get_channel_parameter(self.handle,self.board_slot,ch,quantity)
                row.append(round(channel_value,3))    
            rows.append(row)
        
        cols = cols + self.channel_quantities_map[ch] ## assume all board's channels have same quantities
        print(tf.generate_table(rows, cols, grid_style=tf.AlternatingRowGrid()))

    def get_channel_value(self,channel_index:int,quantity:str):
        if validChannel(channel_index) and validChannel(channel_index,quantity):
            return get_channel_parameter(self.handle,self.board_slot,channel_index,quantity)

    def set_channel_value(self,channel_index:int,quantity:str,value):
        if validChannel(channel_index) and validChannel(channel_index,quantity) and isinstance(value, numbers.Number):
            set_channel_parameter(self.handle,self.slot,channel_index,quantity, value)

c = BoardBase("IntegrationStand_Scintillator")
c.print_board_status()
print(c.get_channel_value(2,"VMon"))
print(c.set_channel_value(2,"VMon","ciao"))




