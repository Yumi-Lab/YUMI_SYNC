Step 1: Transfer the Script to Your SmartPad

First, make sure that the YUMI_ID.sh file is present on your local computer. Use the scp command to transfer the script to your SmartPad. Here's how to do it:

--scp yumi_sync_install.sh pi@192.168.1.XX:/home/pi/

This command copies the YUMI_ID.sh file to the home directory of the pi user on your SmartPad.

Step 2: Grant Execution Permissions

Now, connect to your SmartPad using SSH. You will need to use the password for the pi user.

--ssh pi@192.168.1.XX

Once connected, grant execution permissions to the script using the following command:

--chmod +x yumi_sync_install.sh

This will allow the script to be executed.

Step 3: Execute the Script
To run the script, use the following command:

--./yumi_sync_install.sh

The script will start running on your SmartPad.

Step 4: Check the Service Status

View the status of the service:

--sudo systemctl status control-version
