import schedule
import time
import serial
from datetime import datetime
import requests
import struct
from pyModbusTCP.client import ModbusClient


serial_product="FT232R"
SMA_modbus_to_collect = [[30775,2,"W","Real time power (W) production"]]
SMA_modbus_to_collect_daily_energy = [[30535,2,"Wh","Total energy (Wh) produced today"]]
savemye_url = 'http://192.168.1.230/savemye/api/store.php'
Modbus_Device_IP="192.168.0.237"
Modbus_Device_ID="3"
Modbus_Device_Port = 502
debug = False

#telegram_codes_volt  =[["32.7.0","spanning f1"],["52.7.0","spanning f2"],["72.7.0","spanning f3"]]


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
        if debug: print(myobj,x)
    except requests.RequestException as e:
        print(e)
        
def telegram(telegram_codes_record):
     try:
         ser=ser_init()
         for codes_teller in range(len(telegram_codes_record)):
            for teller in range(23):
                telegram_line=str(ser.readline())
                stop_str = telegram_line.rfind("(")
                telegram_code = telegram_line[6:stop_str]
                if (telegram_code == telegram_codes_record[codes_teller][0]):
                    start_str = telegram_line.rfind("(")+1
                    if ("*" in telegram_line):
                        stop_str = telegram_line.rfind("*")
                        telegram_value = telegram_line[start_str:stop_str]
                        start_str = telegram_line.rfind("*")+1
                        stop_str = telegram_line.rfind(")")
                        telegram_metric = telegram_line[start_str:stop_str]
                    else:
                        stop_str = telegram_line.rfind(")")
                        telegram_value = telegram_line[start_str:stop_str]
                        telegram_metric = "none"
                    if debug: print("DSMR"+telegram_codes_record[codes_teller][0],telegram_codes_record[codes_teller][1]," Value=" + telegram_value,"timestamp=" + str(datetime.now()))
                    store_url(("DSMR"+telegram_codes_record[codes_teller][0]), telegram_codes_record[codes_teller][1],telegram_value, telegram_metric, datetime.now())
     except:
        print("Could not read from serial port",datetime.now())

def DSMR_rt_consumption():
    value_consumption = 0.0
    value_injection = 0.0
    consumed = 0.0
    ser=ser_init()
    try:
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
                try: #adding to avoid error when string has something like 00.\\x in it
                    value_consumption = float(telegram_line[start_str:stop_str])
                except:
                    value_consumptoin = 0.0
                if debug: print(value_consumption)
               
            if (telegram_code == "2.7.0"):
                start_str = telegram_line.rfind("(")+1
                stop_str = telegram_line.rfind("*")
                try:
                    value_injection = float(telegram_line[start_str:stop_str])
                except:
                    value_injection = 0.0
                if debug: print(value_injection)
               
        consumed = value_injection - value_consumption
      
        return consumed
    except:
        print('Could not complete some taks... could not convert telegram to string',datetime.now())

def Collect_Modbus(Collect_Array):
    #define variables
    generated = 0.0
    try:
        c= ModbusClient(host=Modbus_Device_IP,unit_id=Modbus_Device_ID,port=Modbus_Device_Port,debug=False)
        c.open()
        
        for x in range(len(Collect_Array)):
            collected_array = [0]
            collected_array.pop()
            collected = c.read_input_registers(Collect_Array[x][0],Collect_Array[x][1])
            collected_merged = struct.pack('>HH',collected[0],collected[1])
            collected_array.append(struct.unpack('>i', collected_merged)[0])
            #store_url format : (sensor, description, value, metric, timestamp)
            if collected_array[0] < 100000 and collected_array[0] > -100000:
                #store_url("SMA",Collect_Array[x][3],collected_array,Collect_Array[x][2],datetime.now())
                if debug: print("SMA",Collect_Array[x][3],collected_array[0],Collect_Array[x][2],datetime.now())
                generated = collected_array[0]
                
            else:
                #store_url("SMA",Collect_Array[x][3],0,Collect_Array[x][2],datetime.now())
                generated = 0.0
                if debug: print("unrealistic value detected set value to 0")
                
        c.close()
        
    except:
        print("Could not read from modbus",datetime.now())
        
    return generated

def Collect_Modbus_daily(Collect_Array):
    #define variables
    generated = 0.0
    try:
        c= ModbusClient(host=Modbus_Device_IP,unit_id=Modbus_Device_ID,port=Modbus_Device_Port,debug=False)
        c.open()
        
        for x in range(len(Collect_Array)):
            collected_array = [0]
            collected_array.pop()
            collected = c.read_input_registers(Collect_Array[x][0],Collect_Array[x][1])
            collected_merged = struct.pack('>HH',collected[0],collected[1])
            collected_array.append(struct.unpack('>i', collected_merged)[0])
            #store_url format : (sensor, description, value, metric, timestamp)
            if collected_array[0] < 100000 and collected_array[0] > -100000:
                #store_url("SMA",Collect_Array[x][3],collected_array,Collect_Array[x][2],datetime.now())
                if debug: print("SMA",Collect_Array[x][3],collected_array[0],Collect_Array[x][2],datetime.now())
                generated = collected_array[0]
                
            else:
                #store_url("SMA",Collect_Array[x][3],0,Collect_Array[x][2],datetime.now())
                generated = 0.0
                if debug: print("unrealistic value detected set value to 0")
                
        c.close()
        
    except:
        print("Could not read from modbus",datetime.now())
        


''' schedule examples
schedule.every(10).seconds.do(job)
schedule.every(10).minutes.do(job)
schedule.every().hour.do(job)
schedule.every().day.at("10:30").do(job)
schedule.every(5).to(10).minutes.do(job)
schedule.every().monday.do(job)
schedule.every().wednesday.at("13:15").do(job)
schedule.every().minute.at(":17").do(job)
'''
schedule.every().day.at("23:30").do(Collect_Modbus, SMA_modbus_to_collect_daily_energy)


while True:
    consumed = 0.0
    generated = 0.0
    home_consumed = 0.0
    home_consumed_to_store = 0.0
    energy_consumed_day = 0.0
    energy_generated_day = 0.0
    energy_consumed_home_day = 0.0
    schedule.run_pending()

    consumed=(DSMR_rt_consumption())
    #store_url(sensor, description, value, metric, timestamp)
    
    store_url("DSMR","Real time verbruik of injectie",consumed,"kW",datetime.now())
    
    #SMA_modbus_to_collect = [[30775,2,"W","Real time power (W) production"]]
    generated = Collect_Modbus(SMA_modbus_to_collect)
    store_url("SMA",SMA_modbus_to_collect[0][3],generated,SMA_modbus_to_collect[0][2],datetime.now())
    home_consumed = generated - consumed*1000
    if home_consumed > 0.0:
        store_url("HOME","Real time verbruik van het huis",home_consumed,"W",datetime.now())
    
    #collect voltage
    telegram_codes_volt  =[["32.7.0","spanning f1"]]
    telegram(telegram_codes_volt)
    telegram_codes_volt  =[["52.7.0","spanning f2"]]
    telegram(telegram_codes_volt)
    telegram_codes_volt  =[["72.7.0","spanning f3"]]
    telegram(telegram_codes_volt)
            
    time.sleep(15)
    
    
    