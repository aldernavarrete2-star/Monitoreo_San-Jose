(entorno_tesis) alder@raspberrypi:~ $ pip install requests
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Requirement already satisfied: requests in /usr/lib/python3/dist-packages (2.28.1)
(entorno_tesis) alder@raspberrypi:~ $ python monitoreo_yolo3.py
Cargando IA...
Neither CUDA nor MPS are available - defaulting to CPU. Note: This module is much faster with a GPU.
[1:32:27.839428120] [18910]  INFO Camera camera_manager.cpp:330 libcamera v0.5.2+99-bfd68f78
[1:32:27.846423566] [18923]  INFO RPI pisp.cpp:720 libpisp version v1.2.1 981977ff21f3 29-04-2025 (14:13:50)
[1:32:27.849222518] [18923]  INFO IPAProxy ipa_proxy.cpp:180 Using tuning file /usr/share/libcamera/ipa/rpi/pisp/imx477.json
[1:32:27.856177686] [18923]  INFO Camera camera_manager.cpp:220 Adding camera '/base/axi/pcie@1000120000/rp1/i2c@80000/imx477@1a' for pipeline handler rpi/pisp
[1:32:27.856215149] [18923]  INFO RPI pisp.cpp:1179 Registered camera /base/axi/pcie@1000120000/rp1/i2c@80000/imx477@1a to CFE device /dev/media0 and ISP device /dev/media1 using PiSP variant BCM2712_D0
[1:32:27.859746641] [18910]  INFO Camera camera.cpp:1215 configuring streams: (0) 640x480-RGB888/sRGB (1) 1332x990-BGGR_PISP_COMP1/RAW
[1:32:27.859909938] [18923]  INFO RPI pisp.cpp:1483 Sensor: /base/axi/pcie@1000120000/rp1/i2c@80000/imx477@1a - Selected sensor format: 1332x990-SBGGR12_1X12/RAW - Selected CFE format: 1332x990-PC1B/RAW
--- Sistema San José Activo ---
