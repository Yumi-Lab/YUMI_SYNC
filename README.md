<div align='center'>

<h1>Control Version Sync</h1>
<p>This script automates the setup of a service called "Yumi Sync Service" that monitors a file for changes, sending its data to a specified server. It installs necessary dependencies, creates the Python script for monitoring and sending data, sets up a systemd service for automatic execution, and starts and enables the service for continuous operation.</p>

</div>

### :gear: Installation

Step 1: Access Your SmartPad First, connect to your SmartPad using SSH. You will need to use the password for the pi user.
```bash
ssh pi@192.168.1.XX
```
Step 2: Clone the Repository Once connected, clone the repository containing the installation script. Navigate to the cloned repository directory.
```bash
git clone https://github.com/Yumi-Lab/YUMI_SYNC.git
```

```bash
cd YUMI_SYNC
```

Step 3: Grant Execution Permissions Grant execution permissions to the installation script.
```bash
chmod +x install.sh
```
Step 4: Execute the Script Run the installation script.
```bash
sudo ./install.sh
```
Step 5: Check the Service Status
```bash
sudo systemctl status yumi_sync
```


### :gear: Desinstallation

Step 1: Grant Execution Permissions Grant execution permissions to the Uninstaller script.
```bash
sudo chmod +x uninstaller.sh
```
Step 2: Execute the Script Run the Uninstaller script.
```bash
sudo ./uninstaller.sh
```
Step 3: Check the Service Status
```bash
sudo systemctl status yumi_sync
```
