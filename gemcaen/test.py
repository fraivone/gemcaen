import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

influx_config = dict(
    bucket = "GEM 904 integration stand",
    org = "CMS GEM project",
    token = "mDg5QyXVh3DxQcxdFtEqnPDwaiq4N_Vt5TLqJCx2c2nsl1Kuyhj8wiF0agLWgvkLsDevjBXpuDKUR1Zyms5DsA==",
    url = "http://gem904bigscreens:8086"
)

def main():

    # Instantiate InfluxDB client and connect:
    client = influxdb_client.InfluxDBClient(
            url=influx_config["url"],
            token=influx_config["token"],
            org=influx_config["org"]
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    
    print("Writing fake data to influxDB")
    point = influxdb_client.Point("bananas").field("color", 330)
    write_api.write(bucket=influx_config["bucket"], org=influx_config["org"], record=point)

if __name__=="__main__": main()
