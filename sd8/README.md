Softdevice 8.0.x Support
=========================

Required Resources
------------------

The following resources are required when using Softdevice 8.0.x:
* Total application image size of < 68 KB
* Total application storage space of < 4 KB
* Secure Bootloader requires 20 KB of storage space along with 2 KB for settings and information
storage (e.g. private key)

Application Setup
-----------------

The application must have an initial start location at 0x18000 which is currently the end of the
S110 soft device as of version 8.0.0.  Application settings are reserved at the start of memory
location 0x28C00 and has as size of 4 KB (1 page on the nrf51822 256KB part).  The remainder of
flash memory is used for swap space storage and the bootloader.

Memory Organization Table
-------------------------

| Application | Start Address | End Address | Size (Bytes) |
| :---------- | :-----------: | :---------: | :----------: |
| Softdevice 8.0.0 | 0x00000  | 0x17FFF | 98304 (0x18000) |
| User Application | 0x18000  | 0x28BFF | 68606 (0x10C00) |
| User Application Data<sup>1</sup> | 0x28C00 | 0x29BFF | 4096 (0x1000) |
| Bootloader Swap Space | 0x29C00 | 0x3A7FF | 68606 (0x10C00) |
| Bootloader | 0x3A800 | 0x3F7FF | 20408 (0x5000) |
| Bootloader Settings Data | 0x3F800 | 0x3FBFF | 1024 (0x400) |
| Rigado Bootloader Data | 0x3FC00 | 0x3FFFF | 1024 (0x400) |

<sup>1</sup> *User Application Data is maintained through application updates.*