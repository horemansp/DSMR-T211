import schedule
import time
import serial
from datetime import datetime
import requests

#Read DSRM port P1
#example type: sagemcom T211 3phase P1 type 5b (should also work for S211 single phase)

savemye_url = 'http://192.168.1.230/savemye/api/store.php'

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate = 115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
    )
#telegram_codes_2 =[["1.7.0","Real time verbruik"],["2.7.0","Real time injectie"],["96.14.0","Tarief"],["1.8.1","Energie verbruik t1"],["1.8.2","Energie verbruik t2"],["2.8.1","Energie injectie t1"],["2.8.2","Energie injectie t2"]]
telegram_codes  =[["1.7.0","Real time verbruik"],["2.7.0","Real time injectie"]]
telegram_codes_2 =[["1.8.1","Energie verbruik hoog tarief"],["1.8.2","Energie verbruik laag tarief"],["2.8.1","Energie injectie hoog tarief"],
                  ["2.8.2","Energie injectie laag tarief"]]

def store_url(sensor, description, value, metric, timestamp):
    try:
        url = savemye_url
        myobj = {'sensor' : sensor,'description': description, 'value':value, 'metric': metric, 'timestamp':timestamp}
        x = requests.post(url, data = myobj)
        print(x)
    except requests.RequestException as e:
        print(e)

def telegram(telegram_codes_record):
    for codes_teller in range(len(telegram_codes_record)):
        for teller in range(23):
            telegram_line=str(ser.readline())
            stop_str = telegram_line.rfind("(")
            telegram_code = telegram_line[6:stop_str]
            #print(telegram_code)
            #print(telegram_line)
            if (telegram_code == telegram_codes_record[codes_teller][0]):
                #vind de startpositie van de ( in de text
                #print(telegram_line, end=' ')
                start_str = telegram_line.rfind("(")+1
                if ("*" in telegram_line):
                    stop_str = telegram_line.rfind("*")
                    telegram_value = telegram_line[start_str:stop_str]
                    #print("value="+ telegram_value, end=' ')
                    start_str = telegram_line.rfind("*")+1
                    stop_str = telegram_line.rfind(")")
                    telegram_metric = telegram_line[start_str:stop_str]
                    #print(" Metric=" + telegram_metric, end=' ')
                else:
                    stop_str = telegram_line.rfind(")")
                    telegram_value = telegram_line[start_str:stop_str]
                    #print("value="+ telegram_value, end=' ')
                    telegram_metric = "none"
                    #print(" Metric=" + telegram_metric, end=' ')
                
                print("DSMR"+telegram_codes_record[codes_teller][0],telegram_codes_record[codes_teller][1]," Value=" + telegram_value,"timestamp=" + str(datetime.now()))
                store_url(("DSMR"+telegram_codes_record[codes_teller][0]), telegram_codes_record[codes_teller][1],telegram_value, telegram_metric, datetime.now())
                #return_str = ["dsrm",telegram_value,telegram_metric,datetime.now()]
                
                

schedule.every(15).seconds.do(telegram, telegram_codes)
schedule.every(5).minutes.do(telegram, telegram_codes_2)
#schedule.every().day.at("01:20").do(telegram)

while True:
    schedule.run_pending()
    time.sleep(1)