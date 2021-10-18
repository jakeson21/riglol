# riglol 1.1.2
Original source code: http://gotroot.ca/rigol/riglol-archives/riglol-1.1.2.tar.gz

* Updated to support DG1000z series AWG's to add 16M memory option
* Updates to `riglol.c` are based on **[this post](https://www.eevblog.com/forum/testgear/need-help-hacking-dp832-for-multicolour-option/msg2470974/#msg2470974)**

## Build
``` bash
mkdir build
cd build
cmake ..
make
```

To generate the key you'll need to get your serial Number `<sn>`.
```
cd src
./riglol <sn> JNBE
$ <28-character key>
```

Take the resulting 28 character aplha-numeric key `<key>` and issue the SCPI command `:LICense:INSTall <key>`.
Now, under the `Utility>System Info` menu you should see `Arb16M:Official`.

* These instructions worked on a DG1022Z with software version 03.01.12

## Upgrade to DG1062Z
* To "upgrade" to a 1062Z, follow the directions **[here](https://www.eevblog.com/forum/testgear/rigol-dg1022z-function-generator-hack/msg2436027/#msg2436027)**
  1. Place **[this file](https://www.eevblog.com/forum/testgear/need-help-hacking-dp832-for-multicolour-option/?action=dlattach;attach=696567)** onto a FAT32 formatted USB drive
     * **[The original post](https://www.eevblog.com/forum/testgear/need-help-hacking-dp832-for-multicolour-option/msg2320485/#msg2320485)** with the attachment and a description of it
  2. Insert the drive into the scope (even while already powered on)
  3. Send the SCPI command `:PROJ:STAT MODEL,DG1062Z`
  4. Send the SCPI command `*IDN?` to confirm
  5. Cycle power and confirm in the `Utility>System Info` menu
