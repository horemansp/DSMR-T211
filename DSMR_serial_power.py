import schedule
import time
import serial
from datetime import datetime
import requests

serial_product="FT232R"

#Read DSRM port P1
#example type: sagemcom T211 3phase P1 type 5b (should also work for S211 single phase)
def ser_port_to_use(product_name):
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    for i in ports:
        portproduct = str(i.product)
        portdevice = str(i.device)
        if product_name in portproduct: #this depends on product
            port_to_use = portdevice
    return port_to_use

savemye_url = 'http://192.168.1.230/savemye/api/store.php'

def ser_init():
    ser = serial.Serial(
        port=ser_port_to_use(serial_product),
        baudrate = 115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )
    return ser

def store_url(sensor, description, value, metric, timestamp):
    try:
        url = savemye_url
        myobj = {'sensor' : sensor,'description': description, 'value':value, 'metric': metric, 'timestamp':timestamp}
        x = requests.post(url, data = myobj)
        print(myobj,x)
    except requests.RequestException as e:
        print(e)

def DSMR_rt_consumption():
    value_consumption = 0.0
    value_injection = 0.0
    consumed = 0.0
    ser=ser_init()
    for teller in range(23):
        telegram_line=str(ser.readline())
        stop_str = telegram_line.rfind("(")
        telegram_code = telegram_line[6:stop_str]
        #print(telegram_code)
        #print(telegram_line)
        if (telegram_code == "1.7.0"):
            #vind de startpositie van de ( in de text
            start_str = telegram_line.rfind("(")+1
            stop_str = telegram_line.rfind("*")
            value_consumption = float(telegram_line[start_str:stop_str])
            print(value_consumption)
           
        if (telegram_code == "2.7.0"):
            start_str = telegram_line.rfind("(")+1
            stop_str = telegram_line.rfind("*")
            value_injection = float(telegram_line[start_str:stop_str])
            print(value_injection)
           
    consumed = value_injection - value_consumption
  
    return consumed
                    
                    


#schedule.every(15).seconds.do(telegram, telegram_codes)
#schedule.every(5).minutes.do(telegram, telegram_codes_2)
#schedule.every().day.at("01:20").do(telegram)

while True:
    consumed=(DSMR_rt_consumption())
    #store_url(sensor, description, value, metric, timestamp)
    store_url("DSMR","Real time verbruik of injectie",consumed,"kW",datetime.now())
    time.sleep(15)