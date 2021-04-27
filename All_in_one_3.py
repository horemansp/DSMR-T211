import schedule
import time
import serial
from datetime import datetime
import requests
import struct
from pyModbusTCP.client import ModbusClient
from pyModbusTCP import utils
voltage = True
debug=True
debugDSMR=False
debugSMA=False
debugVICTRON=False
debugSERIAL=False
debugURL=False
url_store_values = True #call URL


serial_product="FT232R"
SMA_modbus_to_collect = [[30775,2,"W","Real time power (W) production"]]
SMA_modbus_to_collect_daily_energy = [[30535,2,"Wh","Total energy (Wh) produced today"]]
#savemye_url = 'http://www.phconsul.com/savemye/api/store.php'
savemye_url = 'http://192.168.1.230/savemye/api/store.php'
#Read DSRM port P1
#example type: sagemcom T211 3phase P1 type 5b (should also work for S211 single phase)
def ser_port_to_use(product_name):
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    if debugSERIAL:print("Serial ports found:",ports)
    for i in ports:
        portproduct = str(i.product)
        portdevice = str(i.device)
        if product_name in portproduct: #this depends on product
            port_to_use = portdevice
    return port_to_use



def ser_init():
    debug=debugSERIAL
    ser = serial.Serial(
        port=ser_port_to_use(serial_product),
        baudrate = 115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )
    if debug: print("serial init=",ser)
    return ser

def store_url(sensor, description, value, metric, timestamp):
    debug=debugURL
    try:
        url = savemye_url
        myobj = {'sensor' : sensor,'description': description, 'value':value, 'metric': metric, 'timestamp':timestamp}
        if url_store_values: x = requests.post(url, data = myobj)
        if debug:
            print("Serial debug info",myobj)
            print(x.content)
            print(x.headers)
            print(x.history)
            print(x.text)
    except requests.RequestException as e:
        print(e)
        
def telegram(telegram_codes_record):
     debug=debugDSMR
     try:
         ser=ser_init()
         for teller in range(29):
                telegram_line=str(ser.readline())
                stop_str = telegram_line.rfind("(")
                telegram_code = telegram_line[6:stop_str]
                for codes_teller in range(len(telegram_codes_record)):
                    #print(telegram_codes_record[codes_teller][0])
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
     return telegram_value

def DSMR_rt_consumption():
    debug=debugDSMR
    value_consumption = 0.0
    value_injection = 0.0
    consumed = 0.0
    ser=ser_init()
    try:
        for teller in range(29):
            telegram_line=str(ser.readline())
            
            stop_str = telegram_line.rfind("(")
            telegram_code = telegram_line[6:stop_str]
            if debug: print(telegram_line,"telegram code filter=",telegram_code)
            #print(telegram_code)
            #print(telegram_line)
            if (telegram_code == "1.7.0"):
                #vind de startpositie van de ( in de text
                start_str = telegram_line.rfind("(")+1
                stop_str = telegram_line.rfind("*")
                if debug: print(telegram_line,"telegram code filter=",telegram_code,"Extracted value=",telegram_line[start_str:stop_str])
                try: #adding to avoid error when string has something like 00.\\x in it
                    value_consumption = float(telegram_line[start_str:stop_str])
                except:
                    value_consumption = 0.0
                if debug: print("value_consumption=",value_consumption)             
            if (telegram_code == "2.7.0"):
                start_str = telegram_line.rfind("(")+1
                stop_str = telegram_line.rfind("*")
                if debug: print(telegram_line,"telegram code filter=",telegram_code,"Extracted value=",telegram_line[start_str:stop_str])
                value_injection = float(telegram_line[start_str:stop_str])
                if debug: print("value_injection=",value_injection)
               
        consumed = (value_injection - value_consumption)*1000        
    except:
        print('Could not complete some tasks... could not convert telegram to string',datetime.now())
    return consumed

def SMA_modbus(Collect_Array):
    debug=debugSMA
    #define variables
    #Modbus_Device_IP = "192.168.1.170"
    Modbus_Device_IP = "192.168.0.237"
    Modbus_Device_ID = "3"
    Modbus_Device_Port = 502
    generated = 0.0
    collected= [0]
    collected_array= [0]
    collected_array.pop()
    if debug: print("SMA collecting from ID",Modbus_Device_ID,"register",Collect_Array[1])
    try:
        c= ModbusClient(host=Modbus_Device_IP,unit_id=Modbus_Device_ID,port=Modbus_Device_Port,debug=debug)
        c.open()
        collected = c.read_input_registers(Collect_Array[0],Collect_Array[1])
        c.close()
        if debug: print("SMA collected from modbus=",collected)
        collected_merged = struct.pack('>HH',collected[0],collected[1])
        collected_array.append(struct.unpack('>i', collected_merged)[0])
        if collected_array[0] < 100000 and collected_array[0] > -100000:
            if debug: print("SMA debug",collected, collected_array)
            generated = collected_array[0]
        else:
            generated = 0.0
            if debug: print("unrealistic value detected set value to 0")
    except:
        print("Could not read from SMA Modus IP=",Modbus_Device_IP,"DeviceID=",Modbus_Device_ID,"Port=",Modbus_Device_Port,"Register=",Collect_Array)
    return generated


#255,266 = bat status & 100,842 = RT power
def VICTRON_modbus(Modbus_Device_ID, Modbus_read_address,factor):
    debug=debugVICTRON
    Modbus_Device_IP="192.168.1.190"
    Modbus_Device_Port = 502
    value=0.0
    collected = [0]
    collected_array = [0]
    collected_array.pop()
    if debug: print("Victron Modbus collecting from ID",Modbus_Device_ID,"register",Modbus_read_address)
    try:
        c= ModbusClient(host=Modbus_Device_IP,unit_id=Modbus_Device_ID,port=Modbus_Device_Port,debug=debug)
        c.open()
        collected = c.read_input_registers(Modbus_read_address,1)
        if debug: print("VICTRON collected from modbus=",collected)
        value = collected[0]
        value = value/factor
        if debug: print("Modbus IP=",Modbus_Device_IP,"Modbus ID=",Modbus_Device_ID,"Modbus address=",Modbus_read_address,"Value=",value)
        c.close()
    except:
        print("could not read from SMA Modbus IP=",Modbus_Device_IP,"Modbus ID=",Modbus_Device_ID,"Modbus address=",Modbus_read_address)
    return value

def VICTRON_modbus_power():
    debug=debugVICTRON
    Modbus_Device_IP="192.168.1.190"
    Modbus_Device_ID="100"
    Modbus_Device_Port = 502
    modbus_read_address = 842
    debug=False
    value = 0.0
    try:
        c= ModbusClient(host=Modbus_Device_IP,unit_id=Modbus_Device_ID,port=Modbus_Device_Port,debug=debug)
        c.open()
        collected = c.read_input_registers(modbus_read_address,1)
        value = utils.get_2comp(collected[0],16) #utils.get_list_2comp to convert a list
        c.close()
        if debug: print("Modbus IP=",Modbus_Device_IP,"Modbus ID=",Modbus_Device_ID,"Modbus address=",modbus_read_address,"Value=",value,"Collected=",collected)       
    except:
        print("Could not read power from Victron modbus")
    return value
        
def SMA_daily():
    daily_pv_generated = 0.0
    daily_pv_generated =  SMA_modbus([30535,2,"Wh","Total energy (Wh) produced today"])
''' schedule examples

'''
schedule.every().day.at("23:30").do(SMA_modbus, SMA_daily)
telegram_daily_consumption =[["1.8.1","Total consumption from grid tarif 1"],["1.8.2","Total consumption from grid tarif 1"],["2.8.1","Total injection to grid tarif 1"],["2.8.2","Total injection to grid tarif 2"]]
schedule.every().day.at("23:59:00").do(telegram, telegram_daily_consumption)

#Initialize variables
consumed = 0.0
generated = 0.0
home_consumed = 0.0
bat_power = 0.0
bat_status = 0.0

#Start main loop
while True:
    schedule.run_pending()
    current_time = datetime.now()
    
    #DSRM power consumption or injection
    consumed=DSMR_rt_consumption()
    store_url("DSMR","Real time verbruik of injectie",consumed,"W",current_time)
    #PV power generation
    generated = SMA_modbus([30775,2,"W","Real time power (W) production"])
    store_url("SMA","Real time power (W) production",generated,"W",current_time)
    
    #BAT power generation
    bat_power= VICTRON_modbus_power()
    store_url("BAT","power",bat_power,"W",current_time)
    #calculated consumption excluding battery    
    home_consumed = generated - consumed - bat_power
    home_consumed = round(home_consumed,0)
    if home_consumed > 0.0:
        store_url("HOME","Real time home consumption (ex battery)",home_consumed,"W",current_time)
    #Calculated consumption from all home devices, including battery  
    all_consumed = generated - consumed
    all_consumed = round(all_consumed,0)
    store_url("HOME","Real time home consumption (incl battery)",all_consumed,"W",current_time) 
    #255,266 = bat status
    bat_status= int(VICTRON_modbus(225,266,10))
    store_url("BAT","Status",bat_status,"%",current_time)
    if voltage:telegram_codes_volt  =[["32.7.0","spanning f1"],["52.7.0","spanning f2"],["72.7.0","spanning f3"]]
    if debug:
        print("PV power generated:",generated)
        print("battery power:",bat_power)
        print("From/To GRID:",consumed)
        print("Total consumed (incl battery):",all_consumed)
        print("Total energy consumed by house (excl battery)",home_consumed)
        print("Battery charged status %:",bat_status)
        print("----------------",current_time,"---------------------------------------------")
    time.sleep(15)
    
    
    