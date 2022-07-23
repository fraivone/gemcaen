import yaml
from gemcaen.gemcaen import *

def test_loadconfig():
    cfg = load_config()
    print(cfg)
    assert "IntegrationStand" in cfg.keys() 
    assert "904QC" in cfg.keys() 

def test_class():
    c = CAEN_Control("IntegrationStand")
    assert c.valid_name()  == True

def test_class2():
    c = CAEN_Control("904QC")
    assert c.valid_name()  == True

    


