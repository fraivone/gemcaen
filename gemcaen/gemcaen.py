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
#                 print(f"Call number {_} to {func.__name__!r}")
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
        if self.validChannel(channel_index) and self.validQuantity(channel_index,quantity):
            return get_channel_parameter(self.handle,self.board_slot,channel_index,quantity)

    def set_channel_value(self,channel_index:int,quantity:str,value):
        if self.validChannel(channel_index) and self.validQuantity(channel_index,quantity) and isinstance(value, numbers.Number):
            set_channel_parameter(self.handle,self.board_slot,channel_index,quantity, value)
        else:
            raise ValueError("Invalid value ",value," for ",quantity)


class GemBoard(BoardBase):
    __Divider_Resistors = {"G3Bot":0.625007477,"G3Top":0.525001495,"G2Bot":0.874992523,"G2Top":0.550002991,"G1Bot":0.438004665,"G1Top":0.560006579,"Drift":1.125007477}
    def __init__(self,setup_name,gem_layer=None):
        super().__init__(setup_name)
        if gem_layer not in [1,2]: raise ValueError("Invalid gem_layer parsed ",gem_layer) ## parse gem layer
        else: self.gem_layer = gem_layer
        if "A1515" not in self.board_name:raise ValueError(f"Board {self.board_name} not a GEM HV Board") ## ensure GEM HV board
        
        self.n_channels = 7  ## restrict the channel to 7
        self._channels = list(range(7)) if self.gem_layer==1 else list(range(7,14))
        self._monitorables = ["VMon","IMon","I0Set","V0Set","Pw","Status"]
        
        for k in list(self.channel_names_map): ## purge unused channels
            if k not in self._channels:
                self.channel_names_map.pop(k,None)
                self.channel_quantities_map.pop(k,None)

    def set_monitorables(self,monitorables_list:list):
        if set( monitorables_list ).issubset( set( self.channel_quantities_map[self._channels[0]] )  ): ## check if parsed monitorables are subset of possible quantities
            self.set_monitorables = monitorables_list
        else:
            raise ValueError("Parsed monitorables ",monitorables_list, " not a subset of ",self.channel_quantities_map[self._channels[0]])
    
    def get_Ieq(self):
        ieq = 0
        for ch in self._channels:
            if self.get_channel_value(ch,"Pw") == 1:
                ieq += self.get_channel_value(ch,"VMon")
            else: 
                print(f"Electrode {self.channel_names_map[ch]} is OFF. IEq can't be evaluated")
                ieq = 0
                break
        return round(float(ieq)/4.698023207	,3)

    def monitor(self):
        monitored_data = dict()
        for ch in self._channels:
            channel_data = dict()
            for mon in self.set_monitorables:
                channel_data[mon] = self.get_channel_value(ch,mon)
            monitored_data[ch] = channel_data
        return monitored_data


c =  GemBoard("IntegrationStand",1)
c.monitor()