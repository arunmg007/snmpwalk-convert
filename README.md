# snmpwalk-convert
Convert SNMP walk in MIB name to OID - This helps with snmpsim support which requires NetSNMP snmpwalk output with '-ObentU' Flag

# Sample
```
❯ snmpwalk-convert.py snmpwalk.txt
It took 1.142712116241455 seconds to make 17414 lines with 430 MIBs for snmptranslate OID calls
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
