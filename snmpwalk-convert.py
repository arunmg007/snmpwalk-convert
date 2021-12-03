#!/usr/bin/python3
import asyncio
import time
import re
import argparse
from argparse import RawTextHelpFormatter
from tqdm import tqdm

# Getting the Arguments for the Program and also defining the help page
parser = argparse.ArgumentParser( description="Convert SNMPwalk to Support SNMP Simulation", formatter_class=RawTextHelpFormatter)
parser.add_argument('filename', type=str, help="SNMPwalk file to translate")
console_args = parser.parse_args()
     
results = {} 
timeticks_capture = {}
total_lines = []

start = time.time()

def convert_ipv6_to_oid(ipv6):
    oid = ''
    count = 0
    for hexa in ipv6.split(':'):
        dec = int(hexa,16)
        if count == len(ipv6.split(':'))-1:
            oid += str(dec)
        else:
            oid += str(dec)+'.'
        count +=1
    return oid
    
# Get all MIB names and create a Unique profile of the collected mibs
def get_snmp_mibname():
    with open(console_args.filename, 'r') as content:
        content_lines = content.readlines()
    filter_list = []
    for line in content_lines:
        if re.search(r'Timeticks:',line, flags=re.I):
            timeticks_capture[line.split('=')[0].strip()] = re.search(r'Timeticks: .*\((\d+)\)',line,flags=re.I).group(1)
            filter_list.append(line.split('=')[0].strip())
        elif re.search(r'OID:',line, flags=re.I ):
            filter_list.append(line.split('.')[0])
            filter_list.append(line.split('OID:')[1].strip())
        elif re.search(r'=', line, flags=re.I):
            filter_list.append(line.split('.')[0])
    
    total_lines.append(len(filter_list))
    unique_list = list(dict.fromkeys(filter_list))    
    # return filter_list
    return unique_list

# Runs snmptranslate for MIB to OID asyncronously
async def run(cmd):
    command = f'snmptranslate -On -Pe -Ln -IR {cmd}'
    # command = f'snmptranslate -M <mib-path> -On -Pe -Ln -IR {cmd}'
    proc = await asyncio.create_subprocess_shell(command,stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr= await proc.communicate()
    if stdout:
        return (cmd,stdout.decode('ascii').replace('\n',''))
    elif stderr:
        error_file = 'error-'+console_args.filename
        async with open(error_file, 'a+') as error_lines:
            await error_lines.write(str(cmd)+str(stderr.decode('ascii').replace('\n','')))
        return (cmd,cmd)

async def process(tasks):
    responses = await asyncio.gather(*tasks)
    for response in responses:
        results[response[0]] =  response[1]
    return
            
# Get's the MIB names and Convert asyncronously using ayncio with 50 tasks at a time. Limit can be adjusted.
async def get_oids():
    commands = get_snmp_mibname()
    pbar = tqdm(total=len(commands), desc='OIDs Converted') 
    limit = 50
    count = length = progress = 0
    tasks = []
    for command in commands:
        count +=1
        length +=1
        if count == limit or length == len(commands):
            pbar.update(length-progress)
            progress = length
            tasks.append(asyncio.create_task(run(command)))
            await process(tasks)
            tasks = []
            count = 0
        else:
            tasks.append(asyncio.create_task(run(command)))         
    # tasks = [asyncio.create_task(run(command)) for command in commands]
    # responses = await asyncio.gather(*tasks)
    pbar.close()
    return

# Gets the new File Created with replaced values.
def main():
    new_filename = 'converted-'+console_args.filename
    with open(console_args.filename, 'r') as content:
        read_lines = content.readlines()
        
    with open(new_filename,'w+') as new_content:
        for line in read_lines:
            if re.search(r'Timeticks:',line, flags=re.I):
                new_line = line.replace(line.split('=')[1].strip(),timeticks_capture[line.split('=')[0].strip()]).replace(line.split('=')[0].strip(),results[line.split('=')[0].strip()])
                new_content.write(new_line)
            elif re.search(r'OID:',line, flags=re.I ):
                new_line = line.replace(line.split('.')[0], results[line.split('.')[0]]).replace(line.split('OID:')[1].strip(),results[line.split('OID:')[1].strip()])
                new_content.write(new_line)
            elif re.search(r'=', line, flags=re.I):
                new_line = line.replace(line.split('.')[0], results[line.split('.')[0]])
                if re.search(r'ipv4', new_line, flags=re.I):
                    new_line = new_line.replace('ipv4','1').replace('"','')
                    new_content.write(new_line)
                elif re.search(r'ipv6', new_line, flags=re.I):
                    search_ipv6 = re.search(r'\"([\d:]+)\"', new_line, flags=re.I)
                    if search_ipv6:
                        ipv6 = search_ipv6.group(1)
                        new_line = re.sub(r'\"[\d:]+\"',convert_ipv6_to_oid(ipv6),new_line)
                        new_line = new_line.replace('ipv6','2')
                        new_content.write(new_line)
                    else:
                        new_line = new_line.replace('ipv6','2')
                        new_content.write(new_line)
                else: 
                    new_content.write(new_line)  
    
if __name__ == "__main__":
    asyncio.run(get_oids())
    main()

end = time.time()
total_time = end - start
print("It took {} seconds to make {} lines with {} MIBs for snmptranslate OID calls".format(total_time, total_lines[0], len(results.keys())))
