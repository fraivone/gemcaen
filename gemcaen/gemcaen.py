import pathlib
import yaml
import functools
import tableformatter as tf
import numbers
import socket
import time

from pycaenhv.wrappers import init_system, deinit_system, get_board_parameters, get_crate_map, get_channel_parameters,get_channel_parameter, list_commands,get_channel_parameter_property,get_channel_name,set_channel_parameter
from pycaenhv.enums import CAENHV_SYSTEM_TYPE, LinkType
from pycaenhv.errors import CAENHVError


CONFIG_PATH = pathlib.Path(__file__).parent / "config/config.yml"

def load_config():
    with CONFIG_PATH.open() as ymlfile:
        cfg = yaml.full_load(ymlfile)
    return cfg

class BaseBoard:
    """ Base class to handle a CAEN board """

    _cfg_keys = ["CAENHV_BOARD_TYPE","CAENHV_LINK_TYPE","CAENHV_BOARD_ADDRESS","CAENHV_USER","CAENHV_PASSWORD","SLOT"] 

    def __init__(self,setup_name):
        self._inside_context = False

        self.setup_name = setup_name
        self.check_good_config()
        self.cfg = load_config()[self.setup_name]
        self.board_slot = self.cfg["SLOT"]
        self.hostname = socket.gethostbyaddr(str(self.cfg["CAENHV_BOARD_ADDRESS"]))[0]
        
        self._monitorables = ["VMon","IMon","I0Set","V0Set","Pw","Status"]
       
    ## Always makes sure to close the connection to the mainframe
    def __enter__(self):
        self._inside_context = True

        print(f"Init mainframe {self.hostname} ({self.cfg['CAENHV_BOARD_ADDRESS']})")
        self.handle = self.get_cratehandle()
        self.crate_map = get_crate_map(self.handle)

        self.board_name = self.crate_map["models"][self.board_slot]
        self.board_description = self.crate_map["descriptions"][self.board_slot]

        self.n_channels = self.crate_map["channels"][self.board_slot]
        self._channels = list(range(self.n_channels))
        self.channel_names_map, self.channel_quantities_map = self.map_channels()  ## channel_<name/quant>_map[ch_index] = ch_<name/quant>
        
        return self
    
    def close(self):
        print(f"Deinit mainframe {self.hostname} ({self.cfg['CAENHV_BOARD_ADDRESS']})")
        deinit_system(self.handle)

    def __exit__(self,type,value,traceback):
        self._inside_context = False
        self.close()
        if type==KeyboardInterrupt:
            print("Terminating due to keyboard interrupt")
            return True
    def _ContextManager_ensure(self):
        if not self._inside_context:
            raise ValueError(f"Method has to be executed in a context manager, i.e \nwith {self.__class__.__name__}() as b:\n\t....")

    def check_good_config(self):
        if self.setup_name in load_config().keys():
            if all(key in load_config()[self.setup_name].keys()  for key in self._cfg_keys):
                return True
        raise ValueError(self.setup_name, " has an invalid/incomplete configuration in ",CONFIG_PATH)

    def get_cratehandle(self):
        self._ContextManager_ensure()
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
        self._ContextManager_ensure()
        if channel_index not in self._channels:
            raise ValueError("Invalid channel index ",channel_index)
            return False
        return True
    def validQuantity(self,channel_index:int,quantity:str):
        self._ContextManager_ensure()
        if quantity not in self.channel_quantities_map[channel_index]:
            raise ValueError("Invalid quantity ",quantity,". Valid quantities are ",self.channel_quantities_map[channel_index])
            return False
        return True

    def map_channels(self):
        self._ContextManager_ensure()
        channel_names_map = dict()
        channel_quantities_map = dict()
        for ch in self._channels:
            channel_names_map[ch] = get_channel_name(self.handle,self.board_slot,ch)
            channel_quantities_map[ch] = get_channel_parameters(self.handle,self.board_slot,ch)
        return  channel_names_map,channel_quantities_map

    def set_monitorables(self,monitorables_list:list):
        self._ContextManager_ensure()
        self._monitorables = monitorables_list

    def table_printer(self,cols,rows):
        print(tf.generate_table(rows, cols, grid_style=tf.AlternatingRowGrid()))
        
    def print_board_status(self):
        self._ContextManager_ensure()
        cols, rows = ["Ch_Number","Ch_Name"], []
        
        for ch,channel_name in self.channel_names_map.items():
            row = [ch,channel_name]
            for quantity in self._monitorables:
                channel_value = self.get_channel_value(ch,quantity)
                row.append(round(channel_value,3))    
            rows.append(row)
        
        cols = cols + self._monitorables ## assume all board's channels have same quantities
        self.table_printer(cols,rows)
        

    def get_channel_value(self,channel_index:int,quantity:str):
        self._ContextManager_ensure()
        if self.validChannel(channel_index) and self.validQuantity(channel_index,quantity):
            return get_channel_parameter(self.handle,self.board_slot,channel_index,quantity)
                
    def set_channel_value(self,channel_index:int,quantity:str,value):
        self._ContextManager_ensure()
        if self.validChannel(channel_index) and self.validQuantity(channel_index,quantity) and isinstance(value, numbers.Number):
            set_channel_parameter(self.handle,self.board_slot,channel_index,quantity, value)
        else:
            raise ValueError("Invalid value ",value," for ",quantity)

    def monitor(self):
        self._ContextManager_ensure()
        monitored_data = dict()
        for ch in self._channels:
            channel_data = dict()
            for mon in self._monitorables:
                channel_data[mon] = self.get_channel_value(ch,mon)
            monitored_data[ch] = channel_data
        return monitored_data

    def log(self):
        self._ContextManager_ensure()
        monitored_data = self.monitor()

        monitored_data["setup"] = self.setup_name
        monitored_data["ip"] = self.cfg['CAENHV_BOARD_ADDRESS']
        monitored_data["slot"] = self.board_slot
        monitored_data["time"] = time.time()

        return monitored_data


class GemBoard(BaseBoard):
    __Divider_Resistors = {"G3BOT":0.625007477,"G3TOP":0.525001495,"G2BOT":0.874992523,"G2TOP":0.550002991,"G1BOT":0.438004665,"G1TOP":0.560006579,"G0BOT":1.125007477}
    def __init__(self,setup_name):
        super().__init__(setup_name) ## init parent class
        self._cfg_keys.append("LAYER") #GEM board must be specified with layer
        self.check_good_config()
        self.gem_layer = self.cfg["LAYER"]
        self._monitorables = ["VMon","IMon","I0Set","V0Set","Pw","Status","Ieq"]
        
    def __enter__(self):
        super().__enter__()
        if self.gem_layer not in [1,2]: ## badly parsed layer --> deinit mainframe and raise error
            self.close()
            raise ValueError("Invalid gem_layer parsed ",gem_layer) ## parse gem layer
        if "A1515" not in self.board_name: ## not a gem board --> deinit mainframe and raise error
            self.close()
            raise ValueError(f"Board {self.board_name!r} on slot {self.board_slot} not a GEM HV Board.") ## ensure GEM HV board
        
        self.n_channels = 7  ## restrict the channel to 7
        self._channels = list(range(7)) if self.gem_layer==1 else list(range(7,14))
        
        for k in list(self.channel_names_map): ## purge unused channels
            if k not in self._channels:
                self.channel_names_map.pop(k,None)
                self.channel_quantities_map.pop(k,None)
        return self
    
    def __exit__(self,type,value,traceback):
        super().__exit__(type,value,traceback)

    def channel_IEq(self,ch,VMon):
        ch_name = self.channel_names_map[ch]
        resistor = self.__Divider_Resistors[ ch_name.split("_")[-1] ]
        return int( VMon / resistor)
    def channel_VMon(self,ch,ieq):
        ch_name = self.channel_names_map[ch]
        resistor = self.__Divider_Resistors[ ch_name.split("_")[-1] ]
        return round( ieq * resistor, 0)

    def print_Ieq(self):
        self._ContextManager_ensure()
        monitored = self.monitor()
        cols = ["chName","VMon","ch_IEq","PW"]
        rows = []
        for ch,value in monitored.items():
            ch_name = self.channel_names_map[ch]
            VMon = round(value["VMon"],2)
            PW = value["Pw"]
            channel_IEq = self.channel_IEq(ch,VMon)
            rows.append([ch_name,VMon,channel_IEq,PW])
        self.table_printer(cols,rows)

    def monitor(self):
        self._ContextManager_ensure()
        monitored_data = dict()
        for ch in self._channels:
            channel_data = dict()
            for mon in self._monitorables:
                if mon == "Ieq":
                    channel_data[mon] = self.channel_IEq( ch , self.get_channel_value(ch,"VMon") )
                else:
                    channel_data[mon] = self.get_channel_value(ch,mon)
            monitored_data[ch] = channel_data
        return monitored_data

    
    def set_Ieq(self,ieq): ## under development
        self.set_monitorables(["VMon","Pw"])
        monitored = self.monitor()
        print("{:>40}{:>30}".format("Current (VMon,Pw,Ieq)","Next (VMon,Pw,Ieq)"))
        for ch,value in monitored.items():
            vmon = round(value['VMon'],1)
            pw = value['Pw']
            print("{:<10}{:<10}{:<5}{:<10}{:>5}{:>5}{:>5}".format(ch, 
                                                                vmon,
                                                                pw,
                                                                self.channel_IEq(ch,vmon),   
                                                                self.channel_VMon(ch,ieq),
                                                                pw,
                                                                ieq)
                                                                )
        if(input("Confirm(Y/N)?") =="Y"):
            for ch in self._channels:
                self.set_channel_value(ch,"V0Set",self.channel_VMon(ch,ieq))
        else    :
            print(f"Ieq {ieq}uA not applied")
