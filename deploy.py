import os
import re
import json
import uuid
import argparse
import subprocess
import platform
from datetime import datetime

CONFIG_FILE = "config.json"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# =====================================================
# OUTPUT HELPERS
# =====================================================

def status(msg):
    print(f"{GREEN}[+] {msg}{RESET}")

def warn(msg):
    print(f"{YELLOW}[!] {msg}{RESET}")

def error(msg):
    print(f"{RED}[X] {msg}{RESET}")

def run(cmd, allow_fail=False):
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0 and not allow_fail:
        raise RuntimeError("Command failed.")


# =====================================================
# PLATFORM DETECTION
# =====================================================

def is_windows():
    return platform.system().lower().startswith("win")


# =====================================================
# SSH HELPERS
# =====================================================

def ssh_key_exists():
    return os.path.exists(os.path.expanduser("~/.ssh/id_ed25519"))

def install_ssh_key(user, ip):
    status("Installing SSH key on remote device...")

    if is_windows():
        cmd = f'type %USERPROFILE%\\.ssh\\id_ed25519.pub | ssh {user}@{ip} "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"'
    else:
        cmd = f'cat ~/.ssh/id_ed25519.pub | ssh {user}@{ip} "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"'

    run(cmd)

def ssh_test(user, ip):
    status("Testing SSH connection...")
    result = subprocess.run(f'ssh -o BatchMode=yes {user}@{ip} "echo ok"', shell=True)
    if result.returncode != 0:
        error("SSH connection failed.")
        exit()
    status("SSH connection successful.")

def sudo_already_configured(user, ip):
    result = subprocess.run(f'ssh {user}@{ip} "sudo -n true"', shell=True)
    return result.returncode == 0

def configure_remote_sudo(user, ip):
    confirm = input("\nAllow tool to configure passwordless sudo for deployment? (y/n): ").lower()
    if confirm != "y":
        warn("Skipping sudo configuration.")
        return

    sudo_rule = f"{user} ALL=(ALL) NOPASSWD: /bin/mv, /bin/chmod, /bin/systemctl"

    remote_cmd = f'''
echo "{sudo_rule}" | sudo tee /etc/sudoers.d/nmconnection-deployer > /dev/null &&
sudo chmod 440 /etc/sudoers.d/nmconnection-deployer
'''

    status("Configuring sudo rules on remote device...")
    run(f'ssh {user}@{ip} "{remote_cmd}"')


# =====================================================
# FILE HELPERS
# =====================================================

def sanitize_filename(name):
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', name)
    name = name.rstrip(". ")
    return name[:200]

def load_config():
    if not os.path.exists(CONFIG_FILE):
        error("No config.json found. Run --setup first.")
        exit()
    with open(CONFIG_FILE) as f:
        return json.load(f)

def collect_existing_ssids():
    existing = set()
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if file.endswith(".nmconnection"):
                existing.add(file.replace(".nmconnection", ""))
    return existing

def create_batch_folder():
    base = datetime.now().strftime("%Y-%m-%d")
    folder = base
    i = 2
    while os.path.exists(folder):
        folder = f"{base}_{i}"
        i += 1
    os.makedirs(folder)
    return folder


# =====================================================
# SETUP MODE
# =====================================================

def setup():
    print("\n=== WiFi NMConnection Deployer Setup ===\n")

    remote_ip = input("Remote device IP: ").strip()
    remote_user = input("Remote username: ").strip()
    potfile_name = input("Potfile name: ").strip()

    config = {
        "remote_ip": remote_ip,
        "remote_user": remote_user,
        "potfile_name": potfile_name,
        "remote_tmp": "/tmp",
        "remote_dest": "/etc/NetworkManager/system-connections"
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

    status("config.json created.")

    if not ssh_key_exists():
        status("Generating SSH key...")
        run("ssh-keygen -t ed25519")

    install_ssh_key(remote_user, remote_ip)
    ssh_test(remote_user, remote_ip)

    if sudo_already_configured(remote_user, remote_ip):
        status("Passwordless sudo already configured.")
    else:
        configure_remote_sudo(remote_user, remote_ip)

    status("Testing passwordless sudo...")
    run(f'ssh {remote_user}@{remote_ip} "sudo -n true"')

    status("Setup complete. Run with --deploy next.")


# =====================================================
# DEPLOY MODE
# =====================================================

def deploy():
    cfg = load_config()

    REMOTE_IP = cfg["remote_ip"]
    REMOTE_USER = cfg["remote_user"]
    input_file = cfg["potfile_name"]
    REMOTE_TMP = cfg["remote_tmp"]
    REMOTE_DEST = cfg["remote_dest"]

    ssh_test(REMOTE_USER, REMOTE_IP)

    if not os.path.exists(input_file):
        error(f"Potfile not found: {input_file}")
        exit()

    status("Scanning existing configs...")
    existing_ssids = collect_existing_ssids()
    date_folder = create_batch_folder()

    created = 0
    seen = set()

    with open(input_file, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(":")
            if len(parts) < 4:
                continue

            raw_ssid = parts[2]
            password = parts[3]
            safe_ssid = sanitize_filename(raw_ssid)

            if safe_ssid in existing_ssids or safe_ssid in seen:
                continue

            seen.add(safe_ssid)

            filename = os.path.join(date_folder, f"{safe_ssid}.nmconnection")
            connection_uuid = str(uuid.uuid4())

            content = f"""[connection]
id={raw_ssid}
uuid={connection_uuid}
type=wifi
interface-name=wlan0

[wifi]
mode=infrastructure
ssid={raw_ssid}

[wifi-security]
auth-alg=open
key-mgmt=wpa-psk
psk={password}

[ipv4]
method=auto

[ipv6]
addr-gen-mode=default
method=auto

[proxy]
"""

            with open(filename, "w", encoding="utf-8") as out:
                out.write(content)

            created += 1

    status(f"{created} new configs created.")

    if created == 0:
        warn("Nothing new to deploy.")
        return

    status("Uploading batch via SCP...")
    run(f'scp "{date_folder}/*.nmconnection" {REMOTE_USER}@{REMOTE_IP}:{REMOTE_TMP}/')

status("Installing configs on remote device...")

# Move files
run(f'ssh {REMOTE_USER}@{REMOTE_IP} "sudo mv {REMOTE_TMP}/*.nmconnection {REMOTE_DEST}/"')

# Fix permissions
run(f'ssh {REMOTE_USER}@{REMOTE_IP} "sudo chmod 600 {REMOTE_DEST}/*.nmconnection"')

# Verify
run(f'ssh {REMOTE_USER}@{REMOTE_IP} "nmcli -t -f NAME connection show"')


    status("Deployment successful.")


# =====================================================
# CLI ENTRYPOINT
# =====================================================

parser = argparse.ArgumentParser(description="WiFi NMConnection Deployment Tool")

parser.add_argument("--setup", action="store_true", help="First-time setup wizard")
parser.add_argument("--deploy", action="store_true", help="Generate and deploy configs")

args = parser.parse_args()

if args.setup:
    setup()
elif args.deploy:
    deploy()
else:
    print("\nUsage:")
    print("  python deploy.py --setup")
    print("  python deploy.py --deploy")
