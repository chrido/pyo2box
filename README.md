pyo2box
==============

Provides an API to derive information from a O2 Box 1421.
Tested with Python 3.


**get_wireless_devices**<br>
Returns a list of namedtuples with the currently connected devices. The entries contain the link_rate, mac and signal.


Dependencies
------------

Usage
```python
o2box = O2Box('192.168.1.1', 'yourpassword')

for dev in o2box.get_wireless_devices():
    print(dev)

```

Supported routers
-----------------
* O2 Box 1421 - https://hilfe.o2online.de/docs/DOC-1332
