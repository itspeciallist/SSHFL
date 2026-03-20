#!/usr/bin/env python3
"""
SSH Server Manager - Full Automation Script
Supports: Ubuntu/Debian, RHEL/CentOS/Fedora, Arch Linux
"""

import subprocess
import os
import sys
import platform
import socket
import re
import shutil
from pathlib import Path


# ─────────────────────────────────────────────
#  COLORS
# ─────────────────────────────────────────────
class Color:
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

def c(text, color):
    return f"{color}{text}{Color.RESET}"

def success(msg): print(c(f"  ✔  {msg}", Color.GREEN))
def error(msg):   print(c(f"  ✘  {msg}", Color.RED))
def warn(msg):    print(c(f"  ⚠  {msg}", Color.YELLOW))
def info(msg):    print(c(f"  ℹ  {msg}", Color.CYAN))


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def run(cmd, capture=True, sudo=False):
    if sudo and os.geteuid() != 0:
        cmd = "sudo " + cmd
    result = subprocess.run(
        cmd, shell=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True
    )
    return result

def require_root():
    if os.geteuid() != 0:
        warn("Some operations require root/sudo privileges.")

def pause():
    input(c("\n  Press Enter to continue...", Color.YELLOW))

def clear():
    os.system("clear" if os.name != "nt" else "cls")

def detect_os():
    """Detect Linux distribution."""
    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
        if "ubuntu" in content or "debian" in content:
            return "debian"
        elif "fedora" in content or "rhel" in content or "centos" in content or "rocky" in content:
            return "rhel"
        elif "arch" in content or "manjaro" in content:
            return "arch"
    except FileNotFoundError:
        pass
    return "unknown"

def get_ssh_service_name():
    """Return correct service name for this distro."""
    distro = detect_os()
    return "sshd" if distro == "rhel" else "ssh"

SSHD_CONFIG = "/etc/ssh/sshd_config"


# ─────────────────────────────────────────────
#  BANNER
# ─────────────────────────────────────────────
def banner():
    clear()
    print(c("""
╔══════════════════════════════════════════════════════╗
║          🔐  SSH SERVER MANAGER  v1.0                ║
║          Linux SSH Automation & Configuration        ║
╚══════════════════════════════════════════════════════╝
""", Color.CYAN + Color.BOLD))

def section(title):
    print(c(f"\n{'─'*54}", Color.BLUE))
    print(c(f"  {title}", Color.BOLD + Color.WHITE))
    print(c(f"{'─'*54}", Color.BLUE))


# ─────────────────────────────────────────────
#  1. INSTALL SSH SERVER
# ─────────────────────────────────────────────
def install_ssh():
    section("Install OpenSSH Server")
    distro = detect_os()
    info(f"Detected OS family: {distro}")

    cmds = {
        "debian": "apt-get update -y && apt-get install -y openssh-server",
        "rhel":   "dnf install -y openssh-server",
        "arch":   "pacman -S --noconfirm openssh",
    }

    if distro == "unknown":
        error("Could not detect your Linux distribution.")
        pause(); return

    cmd = cmds[distro]
    info(f"Running: {cmd}")
    result = run(cmd, capture=False, sudo=True)
    if result.returncode == 0:
        success("OpenSSH Server installed successfully!")
    else:
        error("Installation failed. Try running with sudo.")
    pause()


# ─────────────────────────────────────────────
#  2. SERVICE CONTROL
# ─────────────────────────────────────────────
def service_menu():
    svc = get_ssh_service_name()
    while True:
        banner()
        section("SSH Service Control")
        options = [
            ("1", "Start SSH service"),
            ("2", "Stop SSH service"),
            ("3", "Restart SSH service"),
            ("4", "Enable SSH on boot"),
            ("5", "Disable SSH on boot"),
            ("6", "Check service status"),
            ("0", "Back"),
        ]
        for key, label in options:
            print(f"    {c(key, Color.YELLOW)}  {label}")

        choice = input(c("\n  Select: ", Color.CYAN)).strip()

        actions = {
            "1": f"systemctl start {svc}",
            "2": f"systemctl stop {svc}",
            "3": f"systemctl restart {svc}",
            "4": f"systemctl enable {svc}",
            "5": f"systemctl disable {svc}",
            "6": f"systemctl status {svc}",
        }

        if choice == "0":
            break
        elif choice in actions:
            result = run(actions[choice], capture=(choice != "6"), sudo=True)
            if choice == "6":
                run(actions[choice], capture=False, sudo=True)
            elif result.returncode == 0:
                success("Done!")
            else:
                error(result.stderr.strip() or "Command failed.")
            pause()


# ─────────────────────────────────────────────
#  3. FIREWALL
# ─────────────────────────────────────────────
def firewall_menu():
    while True:
        banner()
        section("Firewall Configuration")
        options = [
            ("1", "Allow SSH (UFW)"),
            ("2", "Deny SSH (UFW)"),
            ("3", "Allow SSH (firewalld)"),
            ("4", "Remove SSH (firewalld)"),
            ("5", "Show UFW status"),
            ("6", "Show firewalld status"),
            ("0", "Back"),
        ]
        for key, label in options:
            print(f"    {c(key, Color.YELLOW)}  {label}")

        choice = input(c("\n  Select: ", Color.CYAN)).strip()

        cmds = {
            "1": "ufw allow ssh",
            "2": "ufw deny ssh",
            "3": "firewall-cmd --permanent --add-service=ssh && firewall-cmd --reload",
            "4": "firewall-cmd --permanent --remove-service=ssh && firewall-cmd --reload",
            "5": "ufw status verbose",
            "6": "firewall-cmd --list-all",
        }

        if choice == "0":
            break
        elif choice in cmds:
            result = run(cmds[choice], capture=False, sudo=True)
            pause()


# ─────────────────────────────────────────────
#  4. CONFIGURATION EDITOR
# ─────────────────────────────────────────────
def read_config_value(key):
    result = run(f"grep -i '^{key}' {SSHD_CONFIG}")
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split()[1]
    return "not set"

def set_config_value(key, value):
    """Set or update a key in sshd_config."""
    # Check if key exists (commented or not)
    result = run(f"grep -i '^#\\?{key}' {SSHD_CONFIG}")
    if result.returncode == 0:
        cmd = f"sed -i 's|^#\\?{key}.*|{key} {value}|I' {SSHD_CONFIG}"
    else:
        cmd = f"echo '{key} {value}' >> {SSHD_CONFIG}"
    return run(cmd, sudo=True)

def config_menu():
    while True:
        banner()
        section("SSH Configuration Editor")

        port         = read_config_value("Port")
        root_login   = read_config_value("PermitRootLogin")
        pass_auth    = read_config_value("PasswordAuthentication")
        max_tries    = read_config_value("MaxAuthTries")
        pubkey_auth  = read_config_value("PubkeyAuthentication")
        x11          = read_config_value("X11Forwarding")

        print(f"""
    Current Settings ({c(SSHD_CONFIG, Color.YELLOW)}):
    ┌────────────────────────────────────────┐
    │  Port                : {c(port, Color.CYAN)}
    │  PermitRootLogin     : {c(root_login, Color.CYAN)}
    │  PasswordAuth        : {c(pass_auth, Color.CYAN)}
    │  MaxAuthTries        : {c(max_tries, Color.CYAN)}
    │  PubkeyAuthentication: {c(pubkey_auth, Color.CYAN)}
    │  X11Forwarding       : {c(x11, Color.CYAN)}
    └────────────────────────────────────────┘

    {c("1", Color.YELLOW)}  Change SSH Port
    {c("2", Color.YELLOW)}  Toggle PermitRootLogin
    {c("3", Color.YELLOW)}  Toggle PasswordAuthentication
    {c("4", Color.YELLOW)}  Set MaxAuthTries
    {c("5", Color.YELLOW)}  Toggle PubkeyAuthentication
    {c("6", Color.YELLOW)}  Toggle X11Forwarding
    {c("7", Color.YELLOW)}  Apply Hardened Security Preset
    {c("8", Color.YELLOW)}  Open config in nano
    {c("0", Color.YELLOW)}  Back
""")
        choice = input(c("  Select: ", Color.CYAN)).strip()

        if choice == "0":
            break

        elif choice == "1":
            new_port = input("  Enter new port (1-65535): ").strip()
            if new_port.isdigit() and 1 <= int(new_port) <= 65535:
                set_config_value("Port", new_port)
                success(f"Port set to {new_port}")
            else:
                error("Invalid port number.")

        elif choice == "2":
            val = input("  PermitRootLogin [yes/no/prohibit-password]: ").strip()
            if val in ("yes", "no", "prohibit-password"):
                set_config_value("PermitRootLogin", val)
                success(f"PermitRootLogin set to {val}")
            else:
                error("Invalid value.")

        elif choice == "3":
            val = input("  PasswordAuthentication [yes/no]: ").strip()
            if val in ("yes", "no"):
                set_config_value("PasswordAuthentication", val)
                success(f"PasswordAuthentication set to {val}")
            else:
                error("Invalid value.")

        elif choice == "4":
            val = input("  MaxAuthTries (e.g. 3): ").strip()
            if val.isdigit():
                set_config_value("MaxAuthTries", val)
                success(f"MaxAuthTries set to {val}")
            else:
                error("Must be a number.")

        elif choice == "5":
            val = input("  PubkeyAuthentication [yes/no]: ").strip()
            if val in ("yes", "no"):
                set_config_value("PubkeyAuthentication", val)
                success(f"PubkeyAuthentication set to {val}")

        elif choice == "6":
            val = input("  X11Forwarding [yes/no]: ").strip()
            if val in ("yes", "no"):
                set_config_value("X11Forwarding", val)
                success(f"X11Forwarding set to {val}")

        elif choice == "7":
            warn("Applying hardened security preset...")
            hardened = {
                "PermitRootLogin": "no",
                "PasswordAuthentication": "no",
                "MaxAuthTries": "3",
                "PubkeyAuthentication": "yes",
                "X11Forwarding": "no",
                "LoginGraceTime": "30",
                "AllowAgentForwarding": "no",
                "PermitEmptyPasswords": "no",
            }
            for key, val in hardened.items():
                set_config_value(key, val)
                info(f"  {key} → {val}")
            success("Hardened preset applied! Remember to restart SSH.")

        elif choice == "8":
            run(f"nano {SSHD_CONFIG}", capture=False, sudo=True)

        pause()


# ─────────────────────────────────────────────
#  5. KEY MANAGEMENT
# ─────────────────────────────────────────────
def key_menu():
    while True:
        banner()
        section("SSH Key Management")
        options = [
            ("1", "Generate new SSH key pair (ed25519)"),
            ("2", "Generate new SSH key pair (RSA 4096)"),
            ("3", "Copy public key to remote server"),
            ("4", "View your public key"),
            ("5", "List authorized_keys"),
            ("6", "Add a public key to authorized_keys"),
            ("7", "Revoke / remove a key from authorized_keys"),
            ("0", "Back"),
        ]
        for key, label in options:
            print(f"    {c(key, Color.YELLOW)}  {label}")

        choice = input(c("\n  Select: ", Color.CYAN)).strip()

        if choice == "0":
            break

        elif choice == "1":
            email = input("  Enter label/email for key: ").strip()
            path  = input(f"  Save to [{Path.home()}/.ssh/id_ed25519]: ").strip()
            path  = path or f"{Path.home()}/.ssh/id_ed25519"
            run(f'ssh-keygen -t ed25519 -C "{email}" -f "{path}"', capture=False)

        elif choice == "2":
            email = input("  Enter label/email for key: ").strip()
            path  = input(f"  Save to [{Path.home()}/.ssh/id_rsa]: ").strip()
            path  = path or f"{Path.home()}/.ssh/id_rsa"
            run(f'ssh-keygen -t rsa -b 4096 -C "{email}" -f "{path}"', capture=False)

        elif choice == "3":
            user_host = input("  Enter user@host (e.g. ubuntu@192.168.1.10): ").strip()
            key_path  = input(f"  Public key path [{Path.home()}/.ssh/id_ed25519.pub]: ").strip()
            key_path  = key_path or f"{Path.home()}/.ssh/id_ed25519.pub"
            run(f'ssh-copy-id -i "{key_path}" {user_host}', capture=False)

        elif choice == "4":
            for pub in Path(f"{Path.home()}/.ssh").glob("*.pub"):
                print(c(f"\n  {pub}:", Color.YELLOW))
                print(pub.read_text())

        elif choice == "5":
            auth_keys = Path(f"{Path.home()}/.ssh/authorized_keys")
            if auth_keys.exists():
                lines = auth_keys.read_text().strip().split("\n")
                for i, line in enumerate(lines, 1):
                    print(c(f"  [{i}] ", Color.YELLOW) + line[:80] + "...")
            else:
                warn("No authorized_keys file found.")

        elif choice == "6":
            pub_key = input("  Paste the public key to add: ").strip()
            auth_keys = Path(f"{Path.home()}/.ssh/authorized_keys")
            auth_keys.parent.mkdir(parents=True, exist_ok=True)
            with open(auth_keys, "a") as f:
                f.write(pub_key + "\n")
            run(f"chmod 600 {auth_keys}")
            success("Key added to authorized_keys.")

        elif choice == "7":
            auth_keys = Path(f"{Path.home()}/.ssh/authorized_keys")
            if not auth_keys.exists():
                error("No authorized_keys file found."); pause(); continue
            lines = auth_keys.read_text().strip().split("\n")
            for i, line in enumerate(lines, 1):
                print(c(f"  [{i}] ", Color.YELLOW) + line[:70] + "...")
            idx = input("  Enter line number to remove: ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(lines):
                lines.pop(int(idx) - 1)
                auth_keys.write_text("\n".join(lines) + "\n")
                success("Key removed.")
            else:
                error("Invalid selection.")

        pause()


# ─────────────────────────────────────────────
#  6. MONITORING & STATUS
# ─────────────────────────────────────────────
def monitor_menu():
    while True:
        banner()
        section("Monitoring & Status")
        options = [
            ("1", "Show current SSH connections"),
            ("2", "Show SSH login attempts (last 20)"),
            ("3", "Show failed login attempts"),
            ("4", "Show server IP addresses"),
            ("5", "Check SSH port listening"),
            ("6", "View SSH logs (live tail)"),
            ("7", "Show logged-in users"),
            ("0", "Back"),
        ]
        for key, label in options:
            print(f"    {c(key, Color.YELLOW)}  {label}")

        choice = input(c("\n  Select: ", Color.CYAN)).strip()

        if choice == "0":
            break

        elif choice == "1":
            section("Active SSH Connections")
            run("ss -tnp | grep :22", capture=False)

        elif choice == "2":
            section("Recent SSH Login Attempts")
            result = run("journalctl -u ssh -n 20 --no-pager 2>/dev/null || grep 'sshd' /var/log/auth.log | tail -20")
            print(result.stdout)

        elif choice == "3":
            section("Failed Login Attempts")
            result = run("grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -20 || journalctl -u ssh --no-pager | grep 'Failed' | tail -20")
            print(result.stdout or "No failed attempts found or log not accessible.")

        elif choice == "4":
            section("Server IP Addresses")
            run("ip -4 addr show | grep inet", capture=False)

        elif choice == "5":
            section("SSH Port Listening")
            run("ss -tlnp | grep ssh", capture=False)
            port = read_config_value("Port")
            info(f"Configured SSH port: {port}")

        elif choice == "6":
            info("Press Ctrl+C to stop tailing logs...")
            try:
                run("journalctl -u ssh -f --no-pager 2>/dev/null || tail -f /var/log/auth.log", capture=False)
            except KeyboardInterrupt:
                pass

        elif choice == "7":
            section("Currently Logged-in Users")
            run("who", capture=False)
            run("w", capture=False)

        pause()


# ─────────────────────────────────────────────
#  7. BACKUP & RESTORE
# ─────────────────────────────────────────────
def backup_menu():
    backup_dir = Path.home() / "ssh_backups"
    backup_dir.mkdir(exist_ok=True)

    while True:
        banner()
        section("Backup & Restore")
        options = [
            ("1", f"Backup sshd_config → {backup_dir}"),
            ("2", "Restore sshd_config from backup"),
            ("3", "List available backups"),
            ("0", "Back"),
        ]
        for key, label in options:
            print(f"    {c(key, Color.YELLOW)}  {label}")

        choice = input(c("\n  Select: ", Color.CYAN)).strip()

        if choice == "0":
            break

        elif choice == "1":
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = backup_dir / f"sshd_config_{ts}.bak"
            result = run(f"cp {SSHD_CONFIG} {dest}", sudo=True)
            run(f"chmod 644 {dest}", sudo=True)
            if result.returncode == 0:
                success(f"Backup saved: {dest}")
            else:
                error("Backup failed.")

        elif choice == "2":
            backups = sorted(backup_dir.glob("sshd_config_*.bak"))
            if not backups:
                warn("No backups found."); pause(); continue
            for i, b in enumerate(backups, 1):
                print(f"    {c(str(i), Color.YELLOW)}  {b.name}")
            idx = input("  Enter number to restore: ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(backups):
                src = backups[int(idx) - 1]
                result = run(f"cp {src} {SSHD_CONFIG}", sudo=True)
                if result.returncode == 0:
                    success(f"Restored from {src.name}")
                    warn("Restart SSH to apply: systemctl restart ssh")
                else:
                    error("Restore failed.")
            else:
                error("Invalid selection.")

        elif choice == "3":
            backups = sorted(backup_dir.glob("sshd_config_*.bak"))
            if backups:
                for b in backups:
                    print(f"    {c('•', Color.GREEN)} {b}")
            else:
                warn("No backups found.")

        pause()


# ─────────────────────────────────────────────
#  8. SYSTEM INFO
# ─────────────────────────────────────────────
def show_system_info():
    banner()
    section("System & SSH Information")
    svc = get_ssh_service_name()

    hostname = run("hostname").stdout.strip()
    distro   = detect_os()
    kernel   = run("uname -r").stdout.strip()
    uptime   = run("uptime -p").stdout.strip()
    ssh_ver  = run("ssh -V 2>&1").stderr.strip() or run("ssh -V").stdout.strip()
    svc_stat = run(f"systemctl is-active {svc}").stdout.strip()
    port     = read_config_value("Port")
    root_log = read_config_value("PermitRootLogin")
    pass_aut = read_config_value("PasswordAuthentication")

    # Get local IPs
    ips = run("hostname -I").stdout.strip()

    status_color = Color.GREEN if svc_stat == "active" else Color.RED

    print(f"""
  ┌─────────────────────────────────────────────────┐
  │  Hostname      : {c(hostname, Color.CYAN)}
  │  OS Family     : {c(distro, Color.CYAN)}
  │  Kernel        : {c(kernel, Color.CYAN)}
  │  Uptime        : {c(uptime, Color.CYAN)}
  │  IP Addresses  : {c(ips, Color.CYAN)}
  ├─────────────────────────────────────────────────┤
  │  SSH Version   : {c(ssh_ver, Color.YELLOW)}
  │  Service Name  : {c(svc, Color.YELLOW)}
  │  Service Status: {c(svc_stat.upper(), status_color)}
  │  SSH Port      : {c(port, Color.YELLOW)}
  ├─────────────────────────────────────────────────┤
  │  PermitRoot    : {c(root_log, Color.YELLOW)}
  │  PasswordAuth  : {c(pass_aut, Color.YELLOW)}
  └─────────────────────────────────────────────────┘
""")
    pause()


# ─────────────────────────────────────────────
#  MAIN MENU
# ─────────────────────────────────────────────
def main_menu():
    require_root()
    while True:
        banner()
        print(f"""
    {c("1", Color.YELLOW)}  Install OpenSSH Server
    {c("2", Color.YELLOW)}  Service Control          (start/stop/enable)
    {c("3", Color.YELLOW)}  Firewall Configuration   (UFW / firewalld)
    {c("4", Color.YELLOW)}  SSH Configuration Editor (sshd_config)
    {c("5", Color.YELLOW)}  Key Management           (generate/copy/revoke)
    {c("6", Color.YELLOW)}  Monitoring & Status      (connections/logs)
    {c("7", Color.YELLOW)}  Backup & Restore         (sshd_config)
    {c("8", Color.YELLOW)}  System & SSH Info
    {c("0", Color.RED)}  Exit
""")
        choice = input(c("  ➤  Select an option: ", Color.CYAN + Color.BOLD)).strip()

        menu_map = {
            "1": install_ssh,
            "2": service_menu,
            "3": firewall_menu,
            "4": config_menu,
            "5": key_menu,
            "6": monitor_menu,
            "7": backup_menu,
            "8": show_system_info,
        }

        if choice == "0":
            print(c("\n  Goodbye! 👋\n", Color.GREEN))
            sys.exit(0)
        elif choice in menu_map:
            menu_map[choice]()
        else:
            warn("Invalid option. Please try again.")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if sys.platform == "win32":
        error("This script is designed for Linux only.")
        sys.exit(1)
    main_menu()
