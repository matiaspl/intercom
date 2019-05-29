# intercom
A githubbed version of DIY intercom system based on Murmur voice chat server and headless Mumble client running on Raspberry Pi 3 based beltpacks. It has been developed in [Institutionen för Kultur och Media](https://www.arcada.fi/sv/forskning/institutionen-kultur-och-media), [Arcada UAS](https://www.arcada.fi/en), Finland and funded by the university fund for technical education and research, TUF (Fonden för teknisk utbildning och forskning).

For more in-depth information head to https://inside.arcada.fi/kultur-och-media/made-in-arcada-an-open-access-diy-intercom-system/

Since this project is based on unlicense license I thought saving it for future generations is worth 10 minutes of my time. I'm not an author nor am I in any way connected to the development (yet!). 

![Image](https://inside.arcada.fi/wp-content/uploads/2019/01/Nicke-intercom-650x348.png)

## What it's for
Providing communication for event production teams large and small with limited budget. Pro intercom solutions are very reliable but at the same time very expensive. Walkie-talkie PMR or UHF radios are OK and inexpensive, but they lack full-duplex partyline communication. And full duplex audio communication is a must for live TV production teams and for coordination teams on medium and large events. 

## How does it work
The soultion allows multichannel live full duplex communication over wifi networks utilizing [Mumble communication protocol](https://wiki.mumble.info/wiki/Protocol). The system has been tested with 12 beltpacks and 4 base stations, but should work with larger networks.
A single endpoint needs ~60 kb/s bandwidth, beltpacks are known to run for +18 hours on a single charge. Latency of 10-100 ms is to be expected.

## Room for improvements
- MPTCP and/or dual interface networking with gracefull failover (3G/4G + wifi)
- vibration alarm on call
- screensaver mode preventing OLED screen burn-in
- 'unlatch all' master base station button for rapid 'radio space' cleanup
- tally integration (vMix & ATEM)
