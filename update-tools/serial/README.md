Serial DFU for Rigado Modules
=============================

This tool transfers new firmware images to the Rigado module over a
connected serial link.

## Requirements

The serial DFU script requires Python 3.x and the pyserial package.

## Script Usage

```
usage: dfu.py [-h] [-M NEWMAC] [-K NEWKEY] [-k OLDKEY] [-s SERIAL] [-b BAUD]
              [-p] [-i INFILE] [-v] [-vv VVERBOSE]

RigDFU2 Serial Updater

optional arguments:
  -h, --help            show this help message and exit
  -M NEWMAC, --newmac NEWMAC
                        new MAC address (6 octets, big-endian)
  -K NEWKEY, --newkey NEWKEY
                        new key (16 bytes, big-endian)
  -k OLDKEY, --oldkey OLDKEY
                        old key (16 bytes, big-endian)
  -s SERIAL, --serial SERIAL
                        serial port
  -b BAUD, --baud BAUD  serial baudrate [115200]
  -p, --patch           set when sending a patch file
  -i INFILE, --infile INFILE
                        packed data binary file to upload
  -v, --verbose         enable verbose level 1
  -vv VVERBOSE, --vverbose VVERBOSE
                        set verbose level (1,2)
```
  
* The `--infile` must be a file generated by `genimage`.  If the system has encryption enabled,
  `--infile` must also be encrypted with an appropriate key via the `signimage` tool.