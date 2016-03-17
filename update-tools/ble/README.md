BLE DFU for Linux and OSX
=========================

This tool transfers firmware images to the RigDFU bootloader via BLE,
using the Javascript library "noble":
  https://github.com/sandeepmistry/noble

Setup
-----

Install packages:

    sudo apt-get install nodejs node-gyp npm \
                         bluetooth bluez-utils libbluetooth-dev

On Ubuntu 12.04, you might need to get a newer nodejs with:

    sudo apt-get install python-software-properties
    sudo add-apt-repository ppa:chris-lea/node.js
    sudo apt-get install nodejs

Install required Node packages:

    npm install

Those will end up in the `node_modules/` subdirectory of your current dir.

Running
-------

You may need to run the tools with sudo, depending on OS setup etc.

To monitor BLE device advertisements:

    sudo node monitor.js

To perform an OTA firmware update:

  Usage: sudo node dfu.js [options] <data.bin>

  Options:

    -h, --help          output usage information
    -V, --version       output the version number
    -m, --mac <MAC>     Only update device with this MAC
    -K, --newkey <KEY>  Configure device: change key to KEY
    -M, --newmac <MAC>  Configure device: change MAC to MAC
    -t, --test          Just test connection, don't configure or send image
    <data.bin>          Packed data file to send

* `data.bin` is a raw binary file containing the header, encryption
   info, and image data, as generated by the `genimage` tool.

* If the target device is configured with an encryption key, the output
  of `genimage` must have been encrypted and signed with `signimage`
  for that particular key.

* Use `--mac` to limit the updating to a device with a particular MAC.
  If not specified, any device with the right service UUID and name
  (RigDfu) will be updated.  This option does not currently work on
  OS X, since the reported bluetooth device UUID does not match the
  device's MAC address.

* The `--newkey` option is only available if a key has not been
  programmed to the device.  This script, currently, cannot be
  used to change the key on the device.

* The `--newmac` option is only available if a key has not been
  programmed to the device.  This script, currently, cannot be
  used to change the MAC address if a key has already been
  programmed.