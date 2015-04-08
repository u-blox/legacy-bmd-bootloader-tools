# OS X

This usage guide requires with use of the OS X package manager Brew and the OS X Terminal app.  You are free to use another
OS X package manager.  So long as it includes the necessary packages, then there should be no issues.
However, use of other package managers may not be supported.

If you are unfamiliar with Brew (or other OS X package managers), check it out at
http://brew.sh/.  If you do not have a package manager installed, follow the instructions
on the brew website.

> *The following examples will use the factory programmed MAC address and the key 00112233445566778899aabbccddeeff.*

Setup
-----
1. Install Node.js and the Node.js Package Manager:
    
      ```brew install node
      brew install npm```

      ```brew install python3```

2. Install Segger JLink tools:
    + https://www.segger.com/jlink-software.html 

2. Attach a JLink programmer to your Mac (either via USB directly with an eval board or your debugger)

Flash the Bootloader and S110 Softdevice 7.1.0
----------------------------------------------

Run the installer script:

```python3 program.py -sm -k 00112233445566778899aabbccddeeff```
        
> You may need to run with sudo

> This python script can be used anytime you need to completely erase a device and flash only
the bootloader and the softdevice to you module.

Flash your Application along with the Bootloader and S110 Softdevice 7.1.0
--------------------------------------------------------------------------

1. Copy the application binary generated by your build scripts to this folder. 
    + *WARNING: DO NOT USE THE BELOW IMAGE GENERATION TOOL TO CREATE THE BINARY!  THE OUTPUT WILL BE INCORRECT FOR LOADING VIA PROGRAMMER!*
2. Rename your application binary to application.bin.
3. Run the installer script as above but add the `-a` option:
    + ```python3 program.py -sm -k 00112233445566778899aabbccddeeff -a```

Generating Unsigned Application Binaries
----------------------------------------

To generate and unsigned binary, simply use the python script provided (genimage.py).  This script
prepends some information that informs bootloader about the size of the OTA update.  The script
takes in an intel hex file (generated by the Keil or GCC toolchains) and outputs a binary.

    python genimage.py -a blinky.hex -o blinky.bin

Once generated, this file can be used to perform an unsecured OTA update via the installed bootloader.

Generating Signed Application Binaries
--------------------------------------

To generate a signed binary, first following the steps in the previous section.  This step is required
for signed binary images.  Next, run the system approprite signimage executable and provide the key
with which to sign the image.  The private keys for signimage are 128-bit.

    signimage blinky.bin blinky_signed.bin 00112233445566778899aabbccddeeff
    
Installing your application over the air
----------------------------------------

1. Using terminal, navigate to the ble folder in bootloader-tools

2. Ensure the device you want to update is the only Rigado Bootloader device that is advertising

3. Install all required node modules

    ```npm install```
    
4. Use one of the following to install the OTA update:
  
  ```
  For unsigned binaries:
  sudo node dfu.js path/to/blinky.bin

  For signed binaries:
  sudo node dfu.js path/to/blinky_signed.bin
  ```
  
5. Wait for the update to complete and then verify operation

[Home](https://github.com/rigado/bootloader-tools/)