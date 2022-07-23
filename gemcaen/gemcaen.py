import pathlib
import yaml
import pkg_resources
import functools

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
        self.cfg_keys = ["CAENHV_BOARD_TYPE","CAENHV_LINK_TYPE","CAENHV_BOARD_ADDRESS","CAENHV_USER","CAENHV_PASSWORD","SLOT","LAYER"] 
        self.good_config()
        self.cfg = load_config()[self.setup_name]
        self.board_slot = self.cfg["SLOT"]
        self.handle = self.get_cratehandle()

    def good_config(self):
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


    def get_board_status(self):
        crate_map = get_crate_map(self.handle)
        board_name = crate_map["models"][self.board_slot]
        description = crate_map["descriptions"][self.board_slot]
        number_of_channels = crate_map["channels"][self.board_slot]
        print(board_name,"\n",description,"\n",number_of_channels)

        for ch in range(number_of_channels):
            quantities = get_channel_parameters(self.handle,self.board_slot,ch)
            channel_name = get_channel_name(self.handle,self.board_slot,ch)
            for quantity in quantities:
                print(f"Board{board_name} {channel_name}\t{quantity} = {get_channel_parameter(self.handle,self.board_slot,ch,quantity)}")
            print()

c = BoardBase("IntegrationStand")



