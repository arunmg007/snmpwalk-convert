#!/usr/bin/python3
import asyncio
import time
import re
import argparse
from argparse import RawTextHelpFormatter
from tqdm import tqdm
import json

# Getting the Arguments for the Program and also defining the help page
parser = argparse.ArgumentParser( description="Convert SNMPwalk to Support SNMP Simulation", formatter_class=RawTextHelpFormatter)
parser.add_argument('filename', type=str, help="SNMPwalk file to translate")
console_args = parser.parse_args()

# Global Dictonary for Data storage and retrieval. This is converted to a json file and will be avialable with filenam data-<filename>.json    
data = {
    'total_lines' : [],
    'unique_oids' : [],
    'error' : {},
    'dot1' : {},
    'results' : {},
    'timeticks_capture' : {},
    'integer' : {}
    # 'bits' : {},
    # 'object' : {'BITS:':'Hex-STRING:'},
    }

# Time capture for start of script
start = time.time()


# Convert HexaDecimal MAC/IPv6 to Decimal OID Format
def convert_hexa_to_oid(hex2dec):
    oid = ''
    count = 0
    for hexa in hex2dec.split(':'):
        dec = int(hexa,16)
        if count == len(hex2dec.split(':'))-1:
            oid += str(dec)
        else:
            oid += str(dec)+'.'
        count +=1
    return oid

# creating a function to replace the Hexa Perl Pack done by Net-SNMP snmpwalk. Not the best method, just giving it a try :D 
# However, snmpwalk to blame as still don't have clear idea on why they did this. However, using -Ob flag can help give a non packed OID output.
def replace_perl_pack(line):
    new_line = line
    if re.search(r'\.[\'"][\S]+[\'"].*=', line, flags=re.I):
        get_hexa_perl_pack = re.search(r'\.[\'"]([\S]+)[\'"].*=', line, flags=re.I).group(1)
        new_line = re.sub(r'[\'"][\S]+[\'"]',data['dot1'][get_hexa_perl_pack],line)
        return new_line
    return new_line

# Make line translations for certain OID conversions. This could have been also achieved by collecting the full MIB OID and using -Ob Flag,
# but that could create a huge list of snmptranslation tasks hence using this function to achieve some of them manually
def check_line_translation(line):
    new_line = line
    if re.search(r'ipv4', line, flags=re.I):
        # Net-SNMP SNMPWalk without -Ob flag, the OID indexs are broken down further. 
        # IP-FORWARD-MIB::inetCidrRouteAge.ipv4."0.0.0.0".24.2.0.0.ipv4."0.0.0.0" = Gauge32: 30242003
        new_line = line.replace('ipv4','1').replace('"','')
        return new_line
    elif re.search(r'ipv6', line, flags=re.I):
        # Net-SNMP SNMPWalk without -Ob flag, the OID indexs are broken down further. 
        # UDP-MIB::udpEndpointProcess.ipv6."00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00".65535.ipv6."00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00".0.1 = Gauge32: 594
        search_ipv6 = re.search(r'\"([\d:]+)\"', line, flags=re.I)
        if search_ipv6:
            ipv6 = search_ipv6.group(1)
            new_line = re.sub(r'\"[\d:]+\"',convert_hexa_to_oid(ipv6),line)
            new_line = new_line.replace('ipv6','2')
        else:
            new_line = new_line.replace('ipv6','2')
        return new_line
    elif re.search(r'inbound', line, flags=re.I):
        new_line = line.replace('inbound','1')
        return new_line
    elif re.search(r'outbound', line, flags=re.I):
        new_line = line.replace('outbound','2')
        return new_line
    else:
        return new_line

# Get all MIB names and create a Unique profile of the collected mibs, Some of the MIB's are fully collected Check data-<filename>.json for details
def get_snmp_mibname():
    with open(console_args.filename, 'r') as content:
        content_lines = content.readlines()
    filter_list = []
    for line in content_lines:
        if re.search(r'Timeticks:', line, flags=re.I):
            data['timeticks_capture'][line.split('=')[0].strip()] = re.search(r'Timeticks: .*\((\d+)\)',line,flags=re.I).group(1)
            filter_list.append(line.split('=')[0].strip())
        elif re.search(r'INTEGER:', line, flags=re.I):
            if re.search(r'INTEGER:.*\(.*\)', line, flags=re.I):
                data['integer'][line.split('=')[0].strip()] = re.search(r'INTEGER:.*\((.*)\)', line, flags=re.I).group(1)
                filter_list.append(line.split('.')[0].strip())
            else:
                filter_list.append(line.split('.')[0].strip())
        elif re.search(r'OID:', line, flags=re.I ):
            filter_list.append(line.split('.')[0])
            filter_list.append(check_line_translation(line.split('OID:')[1].strip()))
        elif re.search(r'dot1dTpFdbAddress', line, flags=re.I):
            # This is giong to be the most painful process
            # Due to the kind of characters in Perl Pack output 
            # We are going to guess this based on the available pack output
            # Insist on getting Net-SNMP Snmpwalk with -Ob flag
            # The possibility are that if a Mac Adderss with almost similar kind can get duplicated during OID conversion.
            snmp_hexa_perl_pack = re.search(r"\.\'([\S]+)\' = STRING:", line, flags=re.I).group(1)
            data['dot1'][snmp_hexa_perl_pack] = convert_hexa_to_oid(line.split('STRING:')[1].strip())
            filter_list.append(line.split('.')[0])
        elif re.search(r'=', line, flags=re.I):
            filter_list.append(line.split('.')[0])
    
    data['total_lines'].append(len(filter_list))
    unique_list = list(dict.fromkeys(filter_list)) 
    data['unique_oids'].append(len(unique_list)) 
    # return filter_list
    return unique_list

# Runs snmptranslate for MIB to OID asyncronously
async def run(cmd):
    command = f'snmptranslate -On -Pe -Ln -IR {cmd}'
    proc = await asyncio.create_subprocess_shell(command,stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr= await proc.communicate()
    if stdout:
        return (cmd,stdout.decode('ascii').replace('\n',''),0)
    elif stderr:
        return (cmd,stdout.decode('ascii').replace('\n',''),1)

# Gather the default 50 tasks created of OID Translations
async def process(tasks):
    responses = await asyncio.gather(*tasks)
    for response in responses:
        if response[2] == 0:
            data['results'][response[0]] =  response[1]
        else:
            data['results'][response[0]] =  response[0]
            data['error'][response[0]] =  response[1]
    return
            
# Get's the MIB names and Convert asyncronously using ayncio with 50 tasks at a time. Limit can be adjusted.
async def get_oids():
    commands = get_snmp_mibname()
    # Initializing TQDM Progress bar to know the actual status of snmptranslation, as this is the core tasks which would take time.
    pbar = tqdm(total=len(commands), desc='OIDs Converted') 
    limit = 50
    count = length = progress = 0
    tasks = []
    for command in commands:
        count +=1
        length +=1
        if count == limit or length == len(commands):
            tasks.append(asyncio.create_task(run(command)))
            await process(tasks)
            # TQDM Progress bar update for individual Tasks created.
            pbar.update()
            # progress = length
            tasks = []
            count = 0
        else:
            tasks.append(asyncio.create_task(run(command)))
            # TQDM Progress bar update for individual Tasks created.
            pbar.update()         
    # tasks = [asyncio.create_task(run(command)) for command in commands]
    # responses = await asyncio.gather(*tasks)
    pbar.close()
    return

# Gets the new File Created with replaced values.
def main():
    new_filename = 'converted-'+console_args.filename
    with open(console_args.filename, 'r') as content:
        read_lines = content.readlines()
    # dot1Addr = data['macaddress'].copy()
    # dot1Port = dot1Addr.copy()
    # dot1Status = dot1Port.copy()
    with open(new_filename,'w+') as new_content:
        for line in read_lines:
            if line.split('.')[0] in data['error'].keys():
                # Skipping Lines which hasn't got translated. Mostly due to missing MIB.
                pass
            elif re.search(r'Timeticks:',line, flags=re.I):
                # NET-SNMP walk
                # DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (6176550) 17:09:25.50
                # -ObentU output format of Timeticks
                # .1.3.6.1.2.1.1.3.0 = 8613902
                new_line = line.replace(line.split('=')[1].strip(),data['timeticks_capture'][line.split('=')[0].strip()]).replace(line.split('=')[0].strip(),data['results'][line.split('=')[0].strip()])
                new_content.write(new_line)
            elif re.search(r'INTEGER:', line, flags=re.I):
                if re.search(r'INTEGER:.*\(.*\)', line, flags=re.I):
                    # Net-SNMP SNMPWalk without -Ob flag
                    # IP-MIB::ipv6InterfaceForwarding.2097539 = INTEGER: notForwarding(2)
                    if re.search(r'dot1d|dot1q|ifRcvAddress', line, flags=re.I):
                        # Net-SNMP SNMPWalk without -Ob flag, the OID indexs are broken down further. 
                        # The bridge MIB uses mac2hex with a perl pack which doesnt come correctly in the output for re-translation
                        # Using -Ob can help during collection as well as during snmptranslate to re-translate if we have the correct pack data.
                        # -O OUTOPTS            Toggle various defaults controlling output display:
                        #                         b:  do not break OID indexes down
                        # BRIDGE-MIB::dot1dTpFdbStatus.'..f..%' = INTEGER: 365
                        # new_line = line.replace(line.split('=')[0].split('.',1)[1].strip(),dot1Status.pop(0)).replace(line.split('.')[0], data['results'][line.split('.')[0]])
                        new_line = replace_perl_pack(line)
                        new_line = new_line.replace(line.split('INTEGER:')[1].strip(),data['integer'][line.split('=')[0].strip()]).replace(line.split('.')[0], data['results'][line.split('.')[0]])
                    else:
                        new_line = line.replace(line.split('INTEGER:')[1].strip(),data['integer'][line.split('=')[0].strip()]).replace(line.split('.')[0], data['results'][line.split('.')[0]])
                        new_line = check_line_translation(new_line)
                    new_content.write(new_line)
                        
                else:
                    if re.search(r'dot1d|dot1q|ifRcvAddress', line, flags=re.I):
                        # Net-SNMP SNMPWalk without -Ob flag, the OID indexs are broken down further. 
                        # The bridge MIB uses mac2hex with a perl pack which doesnt come correctly in the output for re-translation
                        # Using -Ob can help during collection as well as during snmptranslate to re-translate if we have the correct pack data.
                        # -O OUTOPTS            Toggle various defaults controlling output display:
                        #                         b:  do not break OID indexes down
                        # BRIDGE-MIB::dot1dTpFdbPort.'..f..%' = INTEGER: learned(3)
                        # new_line = line.replace(line.split('=')[0].split('.',1)[1].strip(),dot1Port.pop(0)).replace(line.split('.')[0], data['results'][line.split('.')[0]])
                        new_line = replace_perl_pack(line)
                        new_line = new_line.replace(line.split('.')[0], data['results'][line.split('.')[0]])
                    else:
                        new_line = line.replace(line.split('.')[0], data['results'][line.split('.')[0]])
                        new_line = check_line_translation(new_line)
                    new_content.write(new_line)
            elif re.search(r'OID:',line, flags=re.I ):
                # NET-SNMP walk
                # RFC1213-MIB::sysObjectID.0 = OID: SNMPv2-SMI::enterprises.6027.1.3.23
                new_line = check_line_translation(line)
                if data['results'][new_line.split('OID:')[1].strip()] != new_line.split('OID:')[1].strip():
                    new_line = new_line.replace(new_line.split('OID:')[1].strip(),data['results'][new_line.split('OID:')[1].strip()])
                    new_line = new_line.replace(line.split('.')[0], data['results'][line.split('.')[0]])
                    new_content.write(new_line)
            elif re.search(r'Gauge32:|Counter32:', line, flags=re.I):
                if re.search(r'Gauge32: *\d+ .+$', line, flags=re.I):
                    # Net-SNMP Walk
                    # IP-MIB::ipv6InterfaceRetransmitTime.1275648000 = Gauge32: 0 milliseconds    
                    new_line = line.replace(line.split('.')[0], data['results'][line.split('.')[0]]).replace(line.split('Gauge32:')[1].strip(),line.split('Gauge32:')[1].strip().split(' ')[0].strip())
                    new_line = check_line_translation(new_line)
                    new_content.write(new_line)
                elif re.search(r'Counter32: *\d+ .+$', line, flags=re.I):
                    # Net-SNMP Walk
                    # BRIDGE-MIB::dot1dTpPortInFrames.1 = Counter32: 43065487 frames
                    new_line = line.replace(line.split('.')[0], data['results'][line.split('.')[0]]).replace(line.split('Counter32:')[1].strip(),line.split('Counter32:')[1].strip().split(' ')[0].strip())
                    new_line = check_line_translation(new_line)
                    new_content.write(new_line)
                else:
                    new_line = line.replace(line.split('.')[0], data['results'][line.split('.')[0]])
                    new_line = check_line_translation(new_line)
                    new_content.write(new_line)
            elif re.search(r'BITS:', line, flags=re.I):
                # NetMRI Legacy SNMPWalk
                # EtherLike-MIB::dot3ControlFunctionsSupported.2098051 = BITS: 80 pause(0)
                new_line = line.replace(line.split('BITS:')[1].strip(),line.split('BITS:')[1].strip().split(' ')[0].strip()).replace('BITS:','Hex-STRING:').replace(line.split('.')[0], data['results'][line.split('.')[0]])
                new_line = check_line_translation(new_line)
                new_content.write(new_line)
            elif re.search(r'dot1dTpFdbAddress|dot1dStaticAddress|dot1dStaticAllowedToGoTo', line, flags=re.I):
                # Net-SNMP SNMPWalk without -Ob flag, the OID indexs are broken down further. 
                # The bridge MIB uses mac2hex with a perl pack which doesnt come correctly in the output for re-translation
                # Using -Ob can help during collection as well as during snmptranslate to re-translate if we have the correct pack data.
                # -O OUTOPTS            Toggle various defaults controlling output display:
                #                         b:  do not break OID indexes down
                # BRIDGE-MIB::dot1dTpFdbAddress.'..f..%' = STRING: ff:ff:ff:ff:ff:ff
                # BRIDGE-MIB::dot1dStaticAddress.'4..;..'.0 = STRING: 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
                # BRIDGE-MIB::dot1dStaticAllowedToGoTo.'4..;..'.0 = Hex-STRING: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
                new_line = replace_perl_pack(line)
                new_line = new_line.replace(line.split('.')[0], data['results'][line.split('.')[0]])
                new_content.write(new_line) 
            elif re.search(r'=', line, flags=re.I):
                new_line = line.replace(line.split('.')[0], data['results'][line.split('.')[0]])
                new_line = check_line_translation(new_line)
                new_content.write(new_line)
            else:
                new_content.write(line)
    
if __name__ == "__main__":
    asyncio.run(get_oids())
    # with open('result.json', 'w+') as json_file:
    #     json.dump(data, json_file)
    main()
    data_file = 'data-'+console_args.filename.split('.')[0]+'.json'
    with open(data_file, 'w+') as json_file:
        json.dump(data, json_file, indent = 2, separators=(',',': '))

# End time capture for the Script
end = time.time()
# Getting Time difference
total_time = end - start
# Final Output
print("It took {}sec to convert {} lines & snmptranslate {} unique MIBs to OIDs\n{} OIDs not translated and skipped. Check results.json for Errors".format(total_time, data['total_lines'][0], data['unique_oids'][0], len(data['error'].keys())))
