# legacy-bmd-bootloader-tools

## Disclaimer
Copyright (C) u-blox 

u-blox reserves all rights in this deliverable (documentation, software, etc.,
hereafter “Deliverable”). 

u-blox grants you the right to use, copy, modify and distribute the
Deliverable provided hereunder for any purpose without fee.

THIS DELIVERABLE IS BEING PROVIDED "AS IS", WITHOUT ANY EXPRESS OR IMPLIED
WARRANTY. IN PARTICULAR, NEITHER THE AUTHOR NOR U-BLOX MAKES ANY
REPRESENTATION OR WARRANTY OF ANY KIND CONCERNING THE MERCHANTABILITY OF THIS
DELIVERABLE OR ITS FITNESS FOR ANY PARTICULAR PURPOSE.

In case you provide us a feedback or make a contribution in the form of a
further development of the Deliverable (“Contribution”), u-blox will have the
same rights as granted to you, namely to use, copy, modify and distribute the
Contribution provided to us for any purpose without fee.

# Bootloader Tools

This repository provides access to various tools for using the Rigado Secure Bootloader.

The Rigado Secure Bootloader provides an encryption scheme allowing module users to secure their 
firmware image during over-the-air and serial-wire transfer. This method works by first installing a 
private 128-bit key on each device. The update images are then encrypted using the key for the device. 
After transfer of the encrypyted image, the image is decrypted on the device side and validated 
using a checksum. If all checks pass, the new firmware image is flashed to the application bank on the device.

## Directory Structure

- Programming
  + This folder contains tools, scripts, and binaries for programming BMD series modules via a connected JLink programmer.

- OTA Image Tools
  + This folder contains tools for generating firmware update images including ecrypting images for secure data transfer.

- Update Tools
  + This folder contains scripts for performing Over-the-air and Serial updates.  
  Over-the-air updates are currently only available for OS X and Linux systems 
  that can run the Noble module for Node.js.

## Known Errata

RigDFU v3.2.1 as programmed at the factory has an issue that keeps it from being properly updated.  This only affects BLE or serial based updates of the Bootloader and/or Bootlaoder+SoftDevice.  To update v3.2.1 to another version of the bootloader, use the update binary found in the rigdfu_errata folder.  This folder contains an application that reconditions the factory image and updates the bootloader to v3.2.3.  This process must be followed to update any module with v3.2.1 to another version of the bootloader (such as 3.3.1 using SoftDevice S132 3.x.0).  If this update is not applied first, then device will require a JLink to recover.  
