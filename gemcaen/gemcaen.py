import pathlib
import functools
import tableformatter as tf
import numbers
import socket
import time
from datetime import datetime
import sys
from pycaenhv.wrappers import init_system, deinit_system, get_board_parameters, get_crate_map, get_channel_parameters,get_channel_parameter, list_commands,get_channel_parameter_property,get_channel_name,set_channel_parameter
from pycaenhv.enums import CAENHV_SYSTEM_TYPE, LinkType
from pycaenhv.errors import CAENHVError
import pycaenhv
import logging 


def logconfig():
    logging.basicConfig(format='[{asctime}] {threadName} {levelname} - {message}', datefmt='%B %d - %H:%M:%S',level=logging.DEBUG,style="{",handlers=[logging.FileHandler("debug.log"),logging.StreamHandler()])

    logging.addLevelName( logging.DEBUG, "\033[1;90m%s\033[1;0m" % logging.getLevelName(logging.DEBUG))
    logging.addLevelName( logging.INFO, "\033[1;92m%s\033[1;0m" % logging.getLevelName(logging.INFO))
    logging.addLevelName( logging.WARNING, "\033[1;93m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
    logging.addLevelName( logging.ERROR, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))

def throwVomit(value=16):
    global timestamp
    date = datetime.now().timestamp()
    if int(date) - timestamp > value:
        timestamp = int(date)
        raise pycaenhv.errors.CAENHVError("Login failed ")

## TODO 
# Possible to simplify channel managing? The variables _channels,n_channels,channel_names_map,channel_quantities_map may be merged into 2
# Catch communication errors coming from pycaen

timestamp = int(datetime.now().timestamp())


class BaseMainframe:
    def __init__(self,cfg_Mainframe):
        self.cfg = cfg_Mainframe
        self.handle = None

    def __enter__(self):
        try:
            logging.debug(f"Init mainframe ({self.cfg['CAENHV_BOARD_ADDRESS']})")
            self.handle = self.get_cratehandle()
        except pycaenhv.errors.CAENHVError as a:
            logging.error(f"... failed")
            if self.__exit__(*sys.exc_info()):
                pass
            else:
                raise a
        return self
    
    def close(self):
        if self.handle != None:
            logging.debug(f"Deinit mainframe ({self.cfg['CAENHV_BOARD_ADDRESS']})")
            deinit_system(self.handle)
            self.handle = None
        
    def __exit__(self,type,value,traceback):
        self.close()
        ## if the exit method gets called upon an execption, handle it by printing out the exception only if it's a pycaenhv, otherwise raise
        if type == pycaenhv.errors.CAENHVError:
            logging.error(f"Handling exception of type {type}. Exception value: {value}")
            return True


    def get_cratehandle(self):
        system_type = CAENHV_SYSTEM_TYPE[self.cfg['CAENHV_BOARD_TYPE']]
        link_type = LinkType[self.cfg['CAENHV_LINK_TYPE']]
        logging.debug(f"Getting crate handle and logging in...")
        handle = init_system(system_type, link_type,
                             self.cfg['CAENHV_BOARD_ADDRESS'],
                             self.cfg['CAENHV_USER'],
                             self.cfg['CAENHV_PASSWORD'])
        logging.debug(f"... success")
        return handle

class BaseBoard:
    """ Base class to handle a CAEN board """
    def __init__(self,cfg_Board,handle):
        self.handle = handle
        if self.handle == None:
            raise ValueError("Invalid Mainframe handle ",self.handle)
        else:
            self.cfg = cfg_Board
            self.board_slot = self.cfg["SLOT"]
            self._monitorables = ["VMon","IMon","I0Set","V0Set","Pw","Status"]
            self.crate_map = get_crate_map(self.handle)
            self.board_name = self.crate_map["models"][self.board_slot]
            self.board_description = self.crate_map["descriptions"][self.board_slot]
            self.n_channels = self.crate_map["channels"][self.board_slot]
            self._channels = list(range(self.n_channels)) ## take all possible channels
            self.channel_names_map, self.channel_quantities_map = self.map_channels()  ## channel_<name/quant>_map[ch_index] = ch_<name/quant>
            if "CHANNELS" in self.cfg.keys(): self.set_channels(self.cfg["CHANNELS"])  ## use only those specified in the config file, if any

    def validChannel(self,channel_index:int):
        if channel_index not in self._channels:
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
        for ch in self._channels:
            channel_names_map[ch] = get_channel_name(self.handle,self.board_slot,ch)
            channel_quantities_map[ch] = get_channel_parameters(self.handle,self.board_slot,ch)
        return  channel_names_map,channel_quantities_map

    def set_channels(self,channels_list:list):
        if all( channel in self._channels for channel in channels_list): ## parsed channel list is contained in the available channels (self._channels)
            self.n_channels = len(channels_list)
            self._channels = channels_list

            for k in list(self.channel_names_map): ## purge unused channels
                if k not in self._channels:
                    self.channel_names_map.pop(k,None)
                    self.channel_quantities_map.pop(k,None)
        else:
            raise ValueError("Invalid parsed channel list ",channels_list)
    
    def set_monitorables(self,monitorables_list:list):
        self._monitorables = monitorables_list

    def table_printer(self,cols,rows):
        print(tf.generate_table(rows, cols, grid_style=tf.AlternatingRowGrid()))
        
    def print_board_status(self):
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
        if self.validChannel(channel_index) and self.validQuantity(channel_index,quantity):
            try:
                return get_channel_parameter(self.handle,self.board_slot,channel_index,quantity)
            except Exception as e:
                logging.error(e)
                logging.warning(f"Found a problem in retrieving the channel. Retying in 5 secs")
                time.sleep(5)
                self.get_channel_value(channel_index,quantity)
                
    def set_channel_value(self,channel_index:int,quantity:str,value):
        if self.validChannel(channel_index) and self.validQuantity(channel_index,quantity) and isinstance(value, numbers.Number):
            set_channel_parameter(self.handle,self.board_slot,channel_index,quantity, value)
        else:
            raise ValueError("Invalid value ",value," for ",quantity)

    def monitor(self):
        monitored_data = dict()
        for ch in self._channels:
            channel_data = dict()
            for mon in self._monitorables:
                channel_data[mon] = self.get_channel_value(ch,mon)
            monitored_data[ch] = channel_data
        return monitored_data

    def log(self):
        monitored_data = self.monitor()

        monitored_data["ip"] = self.cfg['CAENHV_BOARD_ADDRESS']
        monitored_data["slot"] = self.board_slot
        monitored_data["time"] = time.time()

        return monitored_data


class GemBoard(BaseBoard):
    __Divider_Resistors = {"G3BOT":0.625007477,"G3TOP":0.525001495,"G2BOT":0.874992523,"G2TOP":0.550002991,"G1BOT":0.438004665,"G1TOP":0.560006579,"G0BOT":1.125007477}
    def __init__(self,cfg_Board,handle):
        super().__init__(cfg_Board,handle) ## init parent class
        self.gem_layer = self.cfg["LAYER"]
       self._monitorables = ["VMon","IMon","I0Set","V0Set","Pw","Status","Ieq"]

        if self.gem_layer not in [1,2]: ## badly parsed layer --> deinit mainframe and raise error
            raise ValueError("Invalid gem_layer parsed ",gem_layer) ## parse gem layer
        if "A1515" not in self.board_name: ## not a gem board --> deinit mainframe and raise error
            raise ValueError(f"Board {self.board_name!r} on slot {self.board_slot} not a GEM HV Board.") ## ensure GEM HV board
        if self.gem_layer == 1: self.set_channels(list(range(7)))
        else: self.set_channels(list(range(7,14)))

        return self

    def channel_IEq(self,ch,VMon):
        ch_name = self.channel_names_map[ch]
        resistor = self.__Divider_Resistors[ ch_name.split("_")[-1] ]
        return int( VMon / resistor)
    def channel_VMon(self,ch,ieq):
        ch_name = self.channel_names_map[ch]
        resistor = self.__Divider_Resistors[ ch_name.split("_")[-1] ]
        return round( ieq * resistor, 0)

    def print_Ieq(self):
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
        logging.info("{:>40}{:>30}".format("Current (VMon,Pw,Ieq)","Next (VMon,Pw,Ieq)"))
        for ch,value in monitored.items():
            vmon = round(value['VMon'],1)
            pw = value['Pw']
            logging.info("{:<10}{:<10}{:<5}{:<10}{:>5}{:>5}{:>5}".format(ch, 
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
            logging.info(f"Ieq {ieq}uA not applied")
