#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KEY APPROVAL SYSTEM
"""

import os
import sys
import requests
import time
import json

# ===============================
# COLORS
# ===============================
black = "\033[0;30m"
red = "\033[0;31m"
bred = "\033[1;31m"
green = "\033[0;32m"
bgreen = "\033[1;32m"
yellow = "\033[0;33m"
byellow = "\033[1;33m"
blue = "\033[0;34m"
bblue = "\033[1;34m"
purple = "\033[0;35m"
bpurple = "\033[1;35m"
cyan = "\033[0;36m"
bcyan = "\033[1;36m"
white = "\033[0;37m"
reset = "\033[00m"

# ===============================
# CONFIGURATION
# ===============================

# Google Sheets CSV URL (သင့် sheet ID နဲ့ ပြင်ပါ)
SHEET_ID = "1TZQQDtenMG_X0iKpNqN_o86u4vFYZxg2V5WYVLQ2kYY"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# Local cache file for offline approval
LOCAL_KEYS_FILE = os.path.expanduser("~/.approved_keys.txt")

# ===============================
# CORE APPROVAL FUNCTIONS
# ===============================

def get_system_key():
    """
    ဒီ device ရဲ့ unique key ကို ထုတ်ပေးမယ်
    ဒီ key ကို Google Sheets မှာ ထည့်ထားမှ approved ဖြစ်မယ်
    """
    try:
        # Linux/Unix အတွက်
        uid = os.geteuid()
    except AttributeError:
        # Windows အတွက်
        uid = 1000
    
    try:
        username = os.getlogin()
    except:
        username = os.environ.get('USER', 'unknown')
    
    return f"{uid}{username}"

def fetch_authorized_keys():
    """
    Google Sheets ကနေ authorized keys တွေ ယူမယ်
    """
    keys = []
    
    # Try Google Sheets first
    try:
        response = requests.get(SHEET_CSV_URL, timeout=10)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # Skip empty lines and headers
                if line and not line.startswith('username') and not line.startswith('key'):
                    # CSV format: key, name, expiry
                    key = line.split(',')[0].strip().strip('"')
                    if key:
                        keys.append(key)
            
            # Save to local cache for offline use
            if keys:
                try:
                    with open(LOCAL_KEYS_FILE, 'w') as f:
                        f.write('\n'.join(keys))
                except:
                    pass
            
            return keys
            
    except requests.exceptions.RequestException as e:
        # Network error, try local cache
        pass
    
    # If online fails, try local cache
    try:
        if os.path.exists(LOCAL_KEYS_FILE):
            with open(LOCAL_KEYS_FILE, 'r') as f:
                keys = [line.strip() for line in f if line.strip()]
            return keys
    except:
        pass
    
    return keys

def check_approval():
    """
    Key approval စစ်ဆေးတဲ့ main function
    Return: True (approved) or False (not approved)
    """
    print(f"{bcyan}╔══════════════════════════════════════════════════════════════════╗")
    print(f"║                    KEY APPROVAL SYSTEM                               ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝{reset}")
    print(f"\n{bcyan}[!] Checking approval status...{reset}")
    
    # Get system key
    system_key = get_system_key()
    
    # Get authorized keys
    authorized_keys = fetch_authorized_keys()
    
    print(f"{white}[*] System Key: {system_key}{reset}")
    print(f"{white}[*] Authorized Keys: {len(authorized_keys)}{reset}")
    
    # Check if approved
    if system_key in authorized_keys:
        print(f"\n{bgreen}╔══════════════════════════════════════════════════════════════════╗")
        print(f"║                    ✓ KEY APPROVED ✓                                 ║")
        print(f"╚══════════════════════════════════════════════════════════════════╝{reset}")
        time.sleep(1.5)
        return True
    else:
        print(f"\n{bred}╔══════════════════════════════════════════════════════════════════╗")
        print(f"║                    ❌ KEY NOT APPROVED ❌                           ║")
        print(f"╚══════════════════════════════════════════════════════════════════╝{reset}")
        return False

def get_approval_message():
    """
    ရောင်းချသူဆက်သွယ်ရန် message ပြန်ပေးမယ်
    """
    return f"""
{bred}╔══════════════════════════════════════════════════════════════════╗
║                    ❌ KEY NOT APPROVED ❌                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  {yellow}To buy this tool, please contact:{reset}                                 ║
║                                                                  ║
║     {bcyan}📱 Telegram:{reset}  @paing07709                                      ║
║     {bcyan}📢 Channel:{reset}  t.me/Hacker07709                                 ║
║                                                                  ║
║  {yellow}Your Key: {get_system_key()}{reset}                                             ║
║  {yellow}Send this key to buy the tool{reset}                                        ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{reset}
"""

# ===============================
# ADMIN FUNCTIONS
# ===============================

def show_my_key():
    """Show current system key"""
    key = get_system_key()
    print(f"\n{green}[+] Your System Key: {key}{reset}")
    print(f"{yellow}[!] Send this key to @paing07709 to purchase{reset}")
    return key

def list_authorized_keys():
    """List all authorized keys"""
    keys = fetch_authorized_keys()
    print(f"\n{cyan}Authorized Keys ({len(keys)}):{reset}")
    print(f"{cyan}──────────────────────────────────────────────────{reset}")
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {key}")
    print(f"{cyan}──────────────────────────────────────────────────{reset}")

def add_authorized_key(key):
    """Add a key to local authorized list (admin use)"""
    try:
        with open(LOCAL_KEYS_FILE, 'a') as f:
            f.write(f"{key}\n")
        print(f"{green}[+] Key added: {key}{reset}")
        return True
    except Exception as e:
        print(f"{red}[!] Failed to add key: {e}{reset}")
        return False

# ===============================
# DECORATOR FOR EASY INTEGRATION
# ===============================

def require_approval(func):
    """
    Decorator - ဒါကို function ရှေ့မှာ @require_approval ထည့်ရင်
    approval မရှိရင် function ကို run ခွင့်မပြုဘူး
    """
    def wrapper(*args, **kwargs):
        if check_approval():
            return func(*args, **kwargs)
        else:
            print(get_approval_message())
            sys.exit(1)
    return wrapper

# ===============================
# MAIN APPROVAL CHECK (EASY TO USE)
# ===============================

def main():
    """
    Simple approval check - ဒါကို သင့် tool ရဲ့ အစမှာ ထည့်သုံးပါ
    """
    if check_approval():
        print(f"{bgreen}[+] You can run your tool now{reset}")
        return True
    else:
        print(get_approval_message())
        return False

# ===============================
# COMPATIBILITY FUNCTIONS FOR Leo.py
# ===============================

def get_device_id():
    """Get device ID for Leo.py compatibility"""
    return get_system_key()

def login(show_banner=False):
    """Login function for Leo.py compatibility"""
    if show_banner:
        print(f"{bcyan}╔══════════════════════════════════════════════════════════════════╗")
        print(f"║                    KEY APPROVAL SYSTEM                               ║")
        print(f"╚══════════════════════════════════════════════════════════════════╝{reset}")
        print(f"\n{bcyan}[!] Checking approval status...{reset}")
    
    system_key = get_system_key()
    authorized_keys = fetch_authorized_keys()
    
    print(f"{white}[*] Device ID: {system_key}{reset}")
    print(f"{white}[*] Authorized Keys: {len(authorized_keys)}{reset}")
    
    if system_key in authorized_keys:
        if show_banner:
            print(f"\n{bgreen}╔══════════════════════════════════════════════════════════════════╗")
            print(f"║                    ✓ KEY APPROVED ✓                                 ║")
            print(f"╚══════════════════════════════════════════════════════════════════╝{reset}")
        return True
    else:
        if show_banner:
            print(f"\n{bred}╔══════════════════════════════════════════════════════════════════╗")
            print(f"║                    ❌ KEY NOT APPROVED ❌                           ║")
            print(f"╚══════════════════════════════════════════════════════════════════╝{reset}")
            print(get_approval_message())
        return False

# ===============================
# COMMAND LINE INTERFACE
# ===============================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "--key":
            # Show current key
            show_my_key()
            
        elif cmd == "--list":
            # List authorized keys
            list_authorized_keys()
            
        elif cmd == "--add" and len(sys.argv) > 2:
            # Add key (admin)
            add_authorized_key(sys.argv[2])
            
        elif cmd == "--check":
            # Check approval
            check_approval()
            
        elif cmd == "--help":
            print(f"""
{cyan}Key Approval System - Usage:{reset}
  python3 Key_v2.py --key      # Show your system key
  python3 Key_v2.py --check    # Check if approved
  python3 Key_v2.py --list     # List authorized keys
  python3 Key_v2.py --add KEY  # Add a key (admin)
  python3 Key_v2.py            # Run normal check
""")
        else:
            print(f"{red}[!] Unknown command: {cmd}{reset}")
    else:
        # Normal approval check
        if main():
            print(f"\n{green}[+] You can run your tool here{reset}")
        else:
            sys.exit(1)
