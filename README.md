# snmpwalk-convert
Convert SNMP walk with MIB names to OID 

Helps with [snmpsim](https://github.com/etingof/snmpsim) simulation which requires NetSNMP::snmpwalk output with '-ObentU' Flag for conversion.

# Dependency

snmptranslator tool from [Net-SNMP from Github](https://github.com/net-snmp/net-snmp) and MIB files from different members

Replace line 54 to support Custom MIB Path
```
command = f'snmptranslate -On -Pe -Ln -IR {cmd}'
to
command = f'snmptranslate -M <mib-path> -On -Pe -Ln -IR {cmd}'
```

# Sample
```
❯ ./snmpwalk-convert.py snmpwalk.txt
OIDs Converted: 100%|████████████████████| 430/430 [00:01<00:00, 339.31it/s]
It took 1.444321632385254 seconds to convert 17414 lines and snmptranslate 430 unique MIBs to OIDs
```

```
❯ head snmpwalk.txt

##################################################################### 
snmpwalk -v2c -c community xx.xx.xx.xx .1.3 >> snmpwalk.txt
#####################################################################

SNMPv2-MIB::sysDescr.0 = STRING: Palo Alto Networks xx-xxxx series firewall
SNMPv2-MIB::sysObjectID.0 = OID: SNMPv2-SMI::enterprises.25461.2.3.23
DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (0) 0:00:00.00
SNMPv2-MIB::sysContact.0 = STRING: xxx
SNMPv2-MIB::sysName.0 = STRING: xx-xxx-xxxxxx
```

```
❯ head converted-snmpwalk.txt
.1.3.6.1.2.1.1.1.0 = STRING: Palo Alto Networks xx-xxxx series firewall
.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.25461.2.3.23
.1.3.6.1.2.1.1.3.0 = 0
.1.3.6.1.2.1.1.4.0 = STRING: xxx
.1.3.6.1.2.1.1.5.0 = STRING: xx-xxx-xxxxxx
.1.3.6.1.2.1.1.6.0 = STRING: xx-xxx
.1.3.6.1.2.1.1.7.0 = INTEGER: 127
.1.3.6.1.2.1.1.8.0 = 0
.1.3.6.1.2.1.2.1.0 = INTEGER: 326
.1.3.6.1.2.1.2.2.1.1.1 = INTEGER: 1
```
