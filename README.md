<div align='center'>

<h1>Control Version Sync</h1>
<p>This script automates the setup of a service called "Yumi Sync Service" that monitors a file for changes, sending its data to a specified server. It installs necessary dependencies, creates the Python script for monitoring and sending data, sets up a systemd service for automatic execution, and starts and enables the service for continuous operation.</p>

</div>

### :gear: Installation

Step 1: Access Your SmartPad First, connect to your SmartPad using SSH. You will need to use the password for the pi user.

```bash
ssh pi@192.168.1.XX
```

Step 2: Ensure command line tools `git` and `make` are installed.

```bash
sudo apt update && sudo apt install --yes git make
```

Step 2: Clone the Repository Once connected, clone the repository containing the installation script. Navigate to the cloned repository directory.

```bash
git clone https://github.com/Yumi-Lab/YUMI_SYNC.git
```

Step 4: Change working directory by typing:

```bash
cd YUMI_SYNC
```

Step 5: Run the installation.

```bash
sudo make install
```

Step 5: Check the Service Status

```bash
sudo systemctl status yumi_sync
```

### :gear: Desinstallation

Step 1: Execute the Script Run the Uninstaller script.

```bash
make uninstall
```

_*NOTE:*_ You will be prompted for your `sudo` password!
