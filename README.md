# Ragnar-Network-Importer

A cross-platform CLI tool that automates creation and deployment of NetworkManager .nmconnection WiFi profiles from potfiles.

This tool is designed for fast, repeatable provisioning of WiFi access points to Linux devices (Raspberry Pi OS, Ubuntu, Debian, etc.) using SSH.

⚠️⚠️⚠️THIS IS FOR USE ON YOUR OWN NETWORKS. I AM NOT RESPONSIBLE FOR WHAT YOU DO WITH THIS SCRIPT⚠️⚠️⚠️

🚀 Features  
✅ Cross-platform (Windows / macOS / Linux)  
✅ Interactive setup wizard  
✅ Automatic SSH key creation & installation  
✅ Optional passwordless sudo configuration  
✅ Batch .nmconnection generation  
✅ Global duplicate detection  
✅ Automatic SSH connection testing  
✅ SCP upload + remote install  
✅ NetworkManager restart & verification  

⚙️ Requirements  
Python 3.10+  
OpenSSH installed on your system  
Target device running NetworkManager  
SSH access to target device  

📦 Installation  
Clone the repository:  
git clone https://github.com/YOURNAME/ragnar-network-importer.git  
cd ragnar-network-importer

No external Python dependencies are required.  

🧭 Quick Start  
1️⃣ First-time Setup  

Run the setup wizard:  

python deploy.py --setup  
  
The tool will:  
Ask for remote IP and username  
Generate an SSH key (if needed)  
Install the SSH key on the target device  
Optionally configure passwordless sudo  
Create your local config.json  

2️⃣ Deploy WiFi Configurations  
python deploy.py --deploy  

The deploy command will:  
  
Parse your potfile  
Generate new .nmconnection files  
Skip duplicates automatically  
Upload configs via SCP  
Install them on the remote system  
Restart NetworkManager  
Verify connections with nmcli  

📁 Project Structure  
wifi-nmconnection-deployer/  
│  
├── deploy.py  
├── README.md  
├── LICENSE  
├── .gitignore  
├── config_template.json  
└── examples/  

🔧 Configuration  

During setup, a config.json file is created locally.  

Example configuration:  
  
{  
  "remote_ip": "192.168.1.100",  
  "remote_user": "pi",  
  "potfile_name": "example.potfile",  
  "remote_tmp": "/tmp",  
  "remote_dest": "/etc/NetworkManager/system-connections"  
}  
  
⚠️ config.json is ignored by git and should never be committed.  
🧪 Potfile Format  
  
The tool expects lines structured like:  

field1:field2:SSID:PASSWORD  

Only the 3rd and 4th fields are used.  
  
🔐 Security Notes  
SSH keys are used instead of storing passwords.  
Sudo configuration is optional and requires user confirmation.  
The tool only grants limited sudo permissions:  
mv, chmod, systemctl  

🖥 Supported Platforms  
  
Windows  
macOS  
Linux  
  
Remote Device:  
  
Raspberry Pi OS  
Ubuntu  
Debian  
  
Any NetworkManager-based system  
  
🧰 Example Workflow  
python deploy.py --setup  
python deploy.py --deploy  
  
That’s it.  
  
🤝 Contributing  
Pull requests are welcome.  
Ideas for improvements:  
  
--dry-run mode  
SCP progress bar  
Remote OS auto-detection  
Packaging for PyPI  
  
📜 License  
  
MIT License  
