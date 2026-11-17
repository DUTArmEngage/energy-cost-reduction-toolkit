# PROJECT BRIEF

## Design, Simulation and Implementation of an IoT-Based Energy Cost Reduction and Load Scheduling System (ECRT)

### 1. Project Background

The increasing cost of electricity has created a need for more effective energy-management solutions, particularly in residential and small-scale commercial environments. Many electrical appliances operate without considering electricity tariff periods, resulting in higher electricity costs when energy-intensive appliances are used during peak-demand periods.

The proposed Energy Cost Reduction Toolkit (ECRT) is an Internet of Things (IoT)-based energy monitoring and load scheduling system designed to address this challenge. The system will monitor overall electricity consumption, calculate energy costs according to configured Time-of-Use (ToU) tariffs and automatically manage selected electrical appliances to reduce electricity expenses.

The project combines energy measurement, embedded control, wireless networking and intelligent scheduling to provide users with better visibility and control over their electricity consumption.

### 2. Problem Statement

Conventional household electrical systems provide limited automation for managing electricity consumption according to changing tariff periods. Users often operate appliances without considering the difference between peak, standard and off-peak electricity rates.

This can result in unnecessarily high electricity bills, particularly when flexible, energy-intensive appliances operate during expensive tariff periods.

There is therefore a need for an affordable and intelligent energy-management system that can monitor electricity consumption, calculate associated costs and automatically schedule selected appliances according to electricity tariffs and user-defined operating requirements.

### 3. Project Aim

The main aim of this project is to design, simulate and develop an IoT-based Energy Cost Reduction Toolkit that monitors electricity consumption and intelligently schedules selected household appliances to reduce electricity costs through tariff-aware load management.

### 4. Project Objectives

The specific objectives are to:

1. Design an energy-monitoring system capable of measuring voltage, current, active power and accumulated energy consumption.
2. Develop an Arduino-based controller to acquire energy measurements and manage four independently controlled appliance channels.
3. Integrate a Raspberry Pi 3B+ to process energy data, calculate electricity costs and implement automated load scheduling.
4. Develop a communication interface between the Arduino and Raspberry Pi for exchanging measurement data and control commands.
5. Implement a configurable Time-of-Use tariff model to identify peak, standard and off-peak electricity periods.
6. Develop a monitoring dashboard to display energy consumption, estimated electricity costs and appliance operating status.
7. Simulate the proposed system using MATLAB/Simulink and validate its control and scheduling logic.
8. Evaluate the system through experimental testing, focusing on measurement accuracy, communication performance, energy consumption and potential cost savings.

### 5. Proposed System Design and Methodology

The ECRT will use a two-controller architecture consisting of an Arduino Pro Mini (3.3 V, ATmega328P) and a Raspberry Pi 3B+.

The Arduino will function as the local hardware controller. It will receive electrical measurements from a PZEM-004T V4 energy meter with a 100 A current transformer, process keypad inputs, update a 1602 I2C LCD and manage four independent appliance-control outputs through a 12 V four-channel relay interface.

The Raspberry Pi 3B+ will serve as the main processing and IoT platform. It will receive measurement data directly from the Arduino through a USB-to-serial communication interface. Python will be used to process energy measurements, calculate electricity costs and implement the tariff-based scheduling algorithm. The Raspberry Pi's built-in Wi-Fi will provide network connectivity, while Node-RED will be used to develop a graphical dashboard for monitoring and system interaction. SQLite may be used for historical data storage.

The ESP8266 communication module originally considered in the design has been removed because the Raspberry Pi 3B+ already provides Wi-Fi connectivity. This simplifies the system architecture, reduces component requirements and eliminates an unnecessary communication stage.

The proposed development methodology will consist of the following stages:

- **Stage 1: System design:** Develop the system architecture, hardware specifications, component selection and electrical interface design.
- **Stage 2: Hardware development:** Assemble and test the low-voltage control circuit, including the Arduino, Raspberry Pi, LCD, keypad and relay interface.
- **Stage 3: Energy monitoring:** Integrate the PZEM-004T V4 meter and develop the measurement acquisition functionality.
- **Stage 4: Software development:** Develop the Arduino firmware and Raspberry Pi Python applications for communication, tariff calculations and load scheduling.
- **Stage 5: IoT dashboard development:** Implement the Node-RED dashboard for real-time monitoring and system control.
- **Stage 6: Simulation and validation:** Use MATLAB/Simulink to evaluate the proposed scheduling algorithm and system behaviour.
- **Stage 7: System integration and testing:** Integrate the hardware and software components and conduct controlled experiments to evaluate system performance.

### 6. Expected Outcomes

The expected outcome is a functional ECRT prototype capable of monitoring aggregate electricity consumption, calculating estimated electricity costs and automatically scheduling four selected appliance channels according to configurable electricity tariff periods.

The system is expected to provide users with real-time energy information, improved visibility of electricity usage and the ability to shift flexible appliance operation away from expensive tariff periods.

The project will evaluate both energy reduction and electricity cost reduction. These are separate performance measures because shifting appliance operation to cheaper tariff periods can reduce electricity costs without necessarily reducing total energy consumption.

The final evaluation will compare baseline and managed operating conditions using measured energy consumption, estimated electricity costs, appliance operating schedules and communication performance.

### 7. Project Scope and Limitations

The project will focus on a single aggregate electricity measurement point and four independently controlled appliance channels. Since only one PZEM energy meter will be used, the system will measure the combined consumption of the monitored supply rather than provide individual energy measurements for each appliance.

The proposed hardware includes an Arduino Pro Mini, Raspberry Pi 3B+, PZEM-004T V4, 12 V four-channel relay board, 1602 I2C LCD, 4×4 keypad and associated power-supply and switching components.

The final appliance selection, contactor arrangement, relay interface and electrical protection requirements will be confirmed during detailed hardware design. Mains-voltage installation and commissioning will require review and installation by an appropriately qualified electrical professional. Initial development and testing will be conducted using safe low-voltage arrangements.

### 8. Significance of the Project

The ECRT project demonstrates how embedded systems, IoT technologies and intelligent scheduling can be combined to improve electricity management. It provides a practical approach to monitoring electricity consumption and managing flexible electrical loads based on tariff information.

The proposed system also demonstrates the potential of low-cost computing platforms to support automated energy-management applications. Its modular design provides opportunities for future improvements, including additional measurement points, expanded appliance control and more advanced optimisation algorithms.

**Keywords:** Internet of Things (IoT), Energy Management, Time-of-Use Tariffs, Load Scheduling, Arduino, Raspberry Pi, Energy Monitoring, Demand-Side Management.