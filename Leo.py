#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruijie WiFi Real Device Monitor v5.0
Shows Real Device Info • Real Gateway • Real SSID • Real Ping
"""

import requests
import re
import urllib3
import time
import threading
import random
import sys
import os
import subprocess
import socket
import netifaces
import psutil
import json
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime
import platform

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===============================
# CONFIGURATION
# ===============================
PING_THREADS = 5
PING_INTERVAL = 0.1
CHECK_INTERVAL = 2
MAX_RETRIES = 3

# ===============================
# COLOR SYSTEM
# ===============================
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ===============================
# GLOBAL VARIABLES (REAL DATA)
# ===============================
stop_event = threading.Event()
lock = threading.Lock()

# Real Device Info
device_info = {
    'hostname': platform.node(),
    'os': platform.system(),
    'os_version': platform.version(),
    'architecture': platform.machine(),
    'processor': platform.processor(),
    'python_version': platform.python_version()
}

# Real Network Info
network_info = {
    'interfaces': [],
    'mac_addresses': {},
    'ip_addresses': {},
    'default_gateway': '',
    'dns_servers': [],
    'wifi_ssid': 'Not Connected',
    'wifi_signal': 0,
    'wifi_frequency': '',
    'wifi_security': ''
}

# Real Connection Info
connection_info = {
    'connected': False,
    'session_id': '',
    'gateway_ip': '',
    'gateway_port': '',
    'gateway_mac': '',
    'gateway_model': '',
    'ping_count': 0,
    'ping_success': 0,
    'ping_fail': 0,
    'avg_response_time': 0,
    'bytes_sent': 0,
    'bytes_received': 0,
    'start_time': time.time(),
    'last_ping_time': 0,
    'current_ping_ms': 0
}

# Real Ping History (last 10 pings)
ping_history = []

# ===============================
# REAL DEVICE INFO COLLECTION
# ===============================

def get_real_device_info():
    """Get real device information"""
    global device_info
    
    # Get more detailed device info
    try:
        if platform.system() == "Windows":
            import wmi
            c = wmi.WMI()
            for system in c.Win32_ComputerSystem():
                device_info['manufacturer'] = system.Manufacturer
                device_info['model'] = system.Model
                break
        elif platform.system() == "Linux":
            # Try to get from /proc
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    device_info['model'] = f.read().strip()
    except:
        pass
    
    return device_info

def get_real_network_interfaces():
    """Get real network interfaces"""
    interfaces = []
    try:
        for iface in netifaces.interfaces():
            if iface != 'lo':  # Skip loopback
                addrs = netifaces.ifaddresses(iface)
                info = {'name': iface}
                
                # Get MAC
                if netifaces.AF_LINK in addrs:
                    info['mac'] = addrs[netifaces.AF_LINK][0]['addr']
                    network_info['mac_addresses'][iface] = info['mac']
                
                # Get IP
                if netifaces.AF_INET in addrs:
                    info['ip'] = addrs[netifaces.AF_INET][0]['addr']
                    info['netmask'] = addrs[netifaces.AF_INET][0]['netmask']
                    network_info['ip_addresses'][iface] = info['ip']
                
                interfaces.append(info)
    except:
        pass
    
    network_info['interfaces'] = interfaces
    return interfaces

def get_real_wifi_info():
    """Get real WiFi connection info"""
    try:
        if platform.system() == "Windows":
            # Windows - netsh command
            result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], 
                                   capture_output=True, text=True, timeout=5)
            output = result.stdout
            
            # Get SSID
            ssid_match = re.search(r'SSID\s*:\s*(.+)', output)
            if ssid_match:
                network_info['wifi_ssid'] = ssid_match.group(1).strip()
            
            # Get Signal
            signal_match = re.search(r'Signal\s*:\s*(\d+)%', output)
            if signal_match:
                network_info['wifi_signal'] = int(signal_match.group(1))
            
            # Get Frequency
            freq_match = re.search(r'Radio\s*type\s*:\s*(.+)', output)
            if freq_match:
                network_info['wifi_frequency'] = freq_match.group(1).strip()
                
        elif platform.system() == "Linux":
            # Linux - iwconfig command
            result = subprocess.run(['iwconfig', 'wlan0'], 
                                   capture_output=True, text=True, timeout=5)
            output = result.stdout
            
            # Get SSID
            ssid_match = re.search(r'ESSID:"([^"]+)"', output)
            if ssid_match:
                network_info['wifi_ssid'] = ssid_match.group(1)
            
            # Get Signal
            signal_match = re.search(r'Signal level=(-?\d+)', output)
            if signal_match:
                # Convert dBm to percentage
                dbm = int(signal_match.group(1))
                if dbm >= -50:
                    network_info['wifi_signal'] = 100
                elif dbm <= -90:
                    network_info['wifi_signal'] = 0
                else:
                    network_info['wifi_signal'] = 2 * (dbm + 90)
            
            # Get Frequency
            freq_match = re.search(r'Frequency[=:](\d+\.\d+)', output)
            if freq_match:
                network_info['wifi_frequency'] = freq_match.group(1) + ' GHz'
                
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-I'], 
                                   capture_output=True, text=True, timeout=5)
            output = result.stdout
            
            ssid_match = re.search(r'SSID:\s*(.+)', output)
            if ssid_match:
                network_info['wifi_ssid'] = ssid_match.group(1).strip()
            
            signal_match = re.search(r'CtlRSSI:\s*(-?\d+)', output)
            if signal_match:
                dbm = int(signal_match.group(1))
                network_info['wifi_signal'] = min(100, max(0, (dbm + 100) * 2))
                
    except Exception as e:
        pass
    
    return network_info['wifi_ssid']

def get_real_gateway_info():
    """Get real default gateway"""
    try:
        gateways = netifaces.gateways()
        if 'default' in gateways and netifaces.AF_INET in gateways['default']:
            network_info['default_gateway'] = gateways['default'][netifaces.AF_INET][0]
    except:
        pass
    return network_info['default_gateway']

def get_real_dns_servers():
    """Get real DNS servers"""
    dns_servers = []
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['nslookup', 'localhost'], 
                                   capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'Server' in line or 'Address' in line:
                    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match:
                        dns_servers.append(ip_match.group(1))
        else:
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        dns_servers.append(line.split()[1])
    except:
        pass
    
    network_info['dns_servers'] = dns_servers
    return dns_servers

# ===============================
# REAL PING FUNCTION
# ===============================

def real_ping(host, count=1):
    """Send real ICMP ping and return result"""
    try:
        if platform.system() == "Windows":
            cmd = ['ping', '-n', str(count), '-w', '1000', host]
        else:
            cmd = ['ping', '-c', str(count), '-W', '1', host]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        
        # Parse response time
        if platform.system() == "Windows":
            time_match = re.search(r'time[=<](\d+)', result.stdout, re.IGNORECASE)
        else:
            time_match = re.search(r'time[=<](\d+\.?\d*)', result.stdout, re.IGNORECASE)
        
        if time_match:
            return True, float(time_match.group(1))
        else:
            return False, 0
    except:
        return False, 0

# ===============================
# REAL GATEWAY DISCOVERY
# ===============================

def discover_gateway_mac(ip):
    """Get MAC address of gateway using ARP"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['arp', '-a', ip], 
                                   capture_output=True, text=True, timeout=2)
            mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', result.stdout)
            if mac_match:
                return mac_match.group(0)
        else:
            result = subprocess.run(['arp', '-n', ip], 
                                   capture_output=True, text=True, timeout=2)
            mac_match = re.search(r'([0-9a-f]{2}[:]){5}[0-9a-f]{2}', result.stdout.lower())
            if mac_match:
                return mac_match.group(0)
    except:
        pass
    return "Unknown"

def identify_gateway_model(ip, port):
    """Try to identify gateway model"""
    try:
        # Try to get HTTP server header
        r = requests.get(f"http://{ip}:{port}", timeout=2, verify=False)
        server = r.headers.get('Server', '')
        
        if 'ruijie' in server.lower():
            return f"Ruijie {server}"
        elif 'mikrotik' in server.lower():
            return f"MikroTik {server}"
        elif 'cisco' in server.lower():
            return f"Cisco {server}"
        elif 'huawei' in server.lower():
            return f"Huawei {server}"
        elif 'zte' in server.lower():
            return f"ZTE {server}"
        else:
            # Check HTML title
            title_match = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
            if title_match:
                return title_match.group(1)
    except:
        pass
    return "Unknown Gateway"

# ===============================
# PING THREAD WITH REAL DATA
# ===============================

def real_ping_thread(auth_link, sid):
    """Ping thread with real data collection"""
    global connection_info, ping_history
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; RealPing/1.0)',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    })
    
    while not stop_event.is_set():
        try:
            start = time.time()
            
            # Send HTTP ping to auth link
            timestamp = int(time.time() * 1000)
            ping_url = f"{auth_link}&_={timestamp}&r={random.randint(1000,9999)}"
            
            r = session.get(ping_url, timeout=2, verify=False)
            end = time.time()
            
            response_time = (end - start) * 1000  # Convert to ms
            
            with lock:
                connection_info['ping_count'] += 1
                connection_info['last_ping_time'] = time.time()
                connection_info['current_ping_ms'] = response_time
                
                if r.status_code == 200:
                    connection_info['ping_success'] += 1
                    connection_info['bytes_sent'] += len(r.request.body or '')
                    connection_info['bytes_received'] += len(r.content)
                    
                    # Update average
                    total = connection_info['ping_success']
                    current_avg = connection_info['avg_response_time']
                    connection_info['avg_response_time'] = (current_avg * (total-1) + response_time) / total
                else:
                    connection_info['ping_fail'] += 1
                
                # Keep last 10 pings in history
                ping_history.append({
                    'time': datetime.now().strftime('%H:%M:%S.%f')[:-3],
                    'ms': response_time,
                    'success': r.status_code == 200
                })
                if len(ping_history) > 10:
                    ping_history.pop(0)
            
        except Exception as e:
            with lock:
                connection_info['ping_fail'] += 1
                connection_info['current_ping_ms'] = 0
                
                ping_history.append({
                    'time': datetime.now().strftime('%H:%M:%S.%f')[:-3],
                    'ms': 0,
                    'success': False
                })
                if len(ping_history) > 10:
                    ping_history.pop(0)
        
        time.sleep(PING_INTERVAL)

# ===============================
# REAL STATUS DISPLAY
# ===============================

def draw_ping_graph(history):
    """Draw ASCII graph of ping times"""
    if not history:
        return "No ping data"
    
    max_ms = max([h['ms'] for h in history if h['success']] or [1])
    graph_width = 40
    
    graph = ""
    for h in history:
        if h['success']:
            bars = int((h['ms'] / max_ms) * graph_width) if max_ms > 0 else 1
            bar = "█" * min(bars, graph_width)
            color = GREEN if h['ms'] < 50 else YELLOW if h['ms'] < 100 else RED
            graph += f"{color}{bar}{RESET}\n"
        else:
            graph += f"{RED}X{RESET}\n"
    
    return graph

def status_display():
    """Real-time status display with real data"""
    while not stop_event.is_set():
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Update real-time data
        get_real_wifi_info()
        current_time = time.time()
        uptime = current_time - connection_info['start_time']
        
        with lock:
            success_rate = (connection_info['ping_success'] / max(connection_info['ping_count'], 1)) * 100
            total_bytes = connection_info['bytes_sent'] + connection_info['bytes_received']
            speed = total_bytes / uptime if uptime > 0 else 0
        
        # ==================== DEVICE INFO SECTION ====================
        print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════╗
║                    REAL DEVICE INFORMATION                          ║
╠══════════════════════════════════════════════════════════════════════╣{RESET}""")
        
        print(f"  Hostname     : {WHITE}{device_info['hostname']}{RESET}")
        print(f"  OS           : {WHITE}{device_info['os']} {device_info['os_version'][:30]}{RESET}")
        print(f"  Architecture : {WHITE}{device_info['architecture']}{RESET}")
        print(f"  Processor    : {WHITE}{device_info['processor'][:40]}{RESET}")
        print(f"  Python       : {WHITE}{device_info['python_version']}{RESET}")
        
        # ==================== NETWORK INFO SECTION ====================
        print(f"""
{BOLD}{CYAN}╠══════════════════════════════════════════════════════════════════════╣
║                    REAL NETWORK INFORMATION                         ║
╠══════════════════════════════════════════════════════════════════════╣{RESET}""")
        
        # WiFi Info
        wifi_color = GREEN if network_info['wifi_signal'] > 70 else YELLOW if network_info['wifi_signal'] > 40 else RED
        bars = "█" * (network_info['wifi_signal'] // 10) + "░" * (10 - (network_info['wifi_signal'] // 10))
        
        print(f"  WiFi SSID    : {WHITE}{network_info['wifi_ssid']}{RESET}")
        print(f"  Signal       : {wifi_color}{bars} {network_info['wifi_signal']}%{RESET}")
        print(f"  Frequency    : {WHITE}{network_info['wifi_frequency'] or 'N/A'}{RESET}")
        
        # Interface Info
        for iface in network_info['interfaces']:
            if 'ip' in iface and iface['name'] != 'lo':
                print(f"\n  Interface {iface['name']}:")
                print(f"    IP Address : {WHITE}{iface['ip']}{RESET}")
                print(f"    MAC Address: {WHITE}{iface.get('mac', 'N/A')}{RESET}")
                print(f"    Netmask    : {WHITE}{iface.get('netmask', 'N/A')}{RESET}")
        
        # Gateway Info
        print(f"\n  Default Gateway : {WHITE}{network_info['default_gateway'] or 'N/A'}{RESET}")
        print(f"  DNS Servers     : {WHITE}{', '.join(network_info['dns_servers']) or 'N/A'}{RESET}")
        
        # ==================== CONNECTION INFO SECTION ====================
        print(f"""
{BOLD}{CYAN}╠══════════════════════════════════════════════════════════════════════╣
║                    REAL CONNECTION STATUS                            ║
╠══════════════════════════════════════════════════════════════════════╣{RESET}""")
        
        conn_status = GREEN + "● CONNECTED" if connection_info['connected'] else RED + "○ DISCONNECTED"
        print(f"  Status       : {BOLD}{conn_status}{RESET}")
        
        if connection_info['connected']:
            print(f"  Session ID   : {YELLOW}{connection_info['session_id']}{RESET}")
            print(f"  Gateway IP   : {CYAN}{connection_info['gateway_ip']}{RESET}")
            print(f"  Gateway Port : {CYAN}{connection_info['gateway_port']}{RESET}")
            print(f"  Gateway MAC  : {DIM}{connection_info['gateway_mac']}{RESET}")
            print(f"  Gateway Model: {WHITE}{connection_info['gateway_model']}{RESET}")
            
            print(f"\n  Uptime       : {WHITE}{int(uptime//3600):02d}:{int((uptime%3600)//60):02d}:{int(uptime%60):02d}{RESET}")
            print(f"  Ping Count   : {BLUE}{connection_info['ping_count']}{RESET}")
            print(f"  Success Rate : {GREEN if success_rate > 90 else YELLOW if success_rate > 70 else RED}{success_rate:.1f}%{RESET}")
            print(f"  Avg Response : {GREEN if connection_info['avg_response_time'] < 50 else YELLOW if connection_info['avg_response_time'] < 100 else RED}{connection_info['avg_response_time']:.1f} ms{RESET}")
            print(f"  Current Ping : {GREEN if connection_info['current_ping_ms'] < 50 else YELLOW if connection_info['current_ping_ms'] < 100 else RED}{connection_info['current_ping_ms']:.1f} ms{RESET}")
            print(f"  Data Transfer: {WHITE}{total_bytes/1024:.1f} KB ({speed/1024:.1f} KB/s){RESET}")
        
        # ==================== PING HISTORY GRAPH ====================
        if connection_info['connected'] and ping_history:
            print(f"""
{BOLD}{CYAN}╠══════════════════════════════════════════════════════════════════════╣
║                    REAL PING HISTORY (last 10)                     ║
╠══════════════════════════════════════════════════════════════════════╣{RESET}""")
            
            print("  Time        ms  Graph")
            print("  " + "-" * 50)
            
            for h in ping_history[-10:]:
                time_str = h['time']
                ms_str = f"{h['ms']:.1f}" if h['success'] else "FAIL"
                ms_color = GREEN if h['ms'] < 50 else YELLOW if h['ms'] < 100 else RED if h['success'] else RED
                
                # Graph bar
                if h['success']:
                    bars = "█" * min(int(h['ms'] / 5), 20)
                    graph = f"{ms_color}{bars}{RESET}"
                else:
                    graph = f"{RED}✗{RESET}"
                
                print(f"  {time_str}  {ms_color}{ms_str:>6}{RESET}  {graph}")
        
        print(f"""
{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════╝{RESET}
{DIM}Real Device Data • Real Network Info • Real Ping • {time.strftime('%Y-%m-%d %H:%M:%S')}{RESET}
""")
        
        time.sleep(1)

# ===============================
# MAIN CONNECTION FUNCTION
# ===============================

def start_connection():
    """Main connection function with real data collection"""
    global connection_info
    
    print(f"{CYAN}[*] Collecting real device information...{RESET}")
    get_real_device_info()
    get_real_network_interfaces()
    get_real_gateway_info()
    get_real_dns_servers()
    
    session = requests.Session()
    test_url = "http://connectivitycheck.gstatic.com/generate_204"
    
    while not stop_event.is_set():
        try:
            r = requests.get(test_url, allow_redirects=True, timeout=5)
            
            # Check if already connected to internet
            if r.url == test_url:
                try:
                    requests.get("http://www.google.com", timeout=2)
                    with lock:
                        connection_info['connected'] = True
                    time.sleep(5)
                    continue
                except:
                    pass
            
            # Found captive portal
            portal_url = r.url
            parsed_portal = urlparse(portal_url)
            portal_host = f"{parsed_portal.scheme}://{parsed_portal.netloc}"
            
            print(f"\n{GREEN}[+] Real Captive Portal Found: {portal_url}{RESET}")
            
            # Get session ID
            r1 = session.get(portal_url, verify=False, timeout=10)
            path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
            next_url = urljoin(portal_url, path_match.group(1)) if path_match else portal_url
            r2 = session.get(next_url, verify=False, timeout=10)
            
            sid = parse_qs(urlparse(r2.url).query).get('sessionId', [None])[0]
            if not sid:
                sid_match = re.search(r'sessionId=([a-zA-Z0-9]+)', r2.text)
                sid = sid_match.group(1) if sid_match else None
            
            if sid:
                # Try voucher API
                voucher_api = f"{portal_host}/api/auth/voucher/"
                try:
                    v_res = session.post(voucher_api, 
                                       json={'accessCode': '123456', 'sessionId': sid, 'apiVersion': 1}, 
                                       timeout=3)
                    print(f"{GREEN}[+] Voucher API: {v_res.status_code}{RESET}")
                except:
                    print(f"{YELLOW}[!] Voucher API not required{RESET}")
                
                # Get gateway info
                params = parse_qs(parsed_portal.query)
                gw_addr = params.get('gw_address', ['192.168.60.1'])[0]
                gw_port = params.get('gw_port', ['2060'])[0]
                auth_link = f"http://{gw_addr}:{gw_port}/wifidog/auth?token={sid}&phonenumber=12345"
                
                # Get real gateway info
                gateway_mac = discover_gateway_mac(gw_addr)
                gateway_model = identify_gateway_model(gw_addr, gw_port)
                
                with lock:
                    connection_info['connected'] = True
                    connection_info['session_id'] = sid
                    connection_info['gateway_ip'] = gw_addr
                    connection_info['gateway_port'] = gw_port
                    connection_info['gateway_mac'] = gateway_mac
                    connection_info['gateway_model'] = gateway_model
                    connection_info['start_time'] = time.time()
                
                print(f"{GREEN}[+] Session ID: {YELLOW}{sid}{RESET}")
                print(f"{GREEN}[+] Gateway: {CYAN}{gw_addr}:{gw_port}{RESET}")
                print(f"{GREEN}[+] Gateway MAC: {DIM}{gateway_mac}{RESET}")
                print(f"{GREEN}[+] Gateway Model: {WHITE}{gateway_model}{RESET}")
                
                # Start ping threads
                print(f"{MAGENTA}[*] Starting {PING_THREADS} real ping threads...{RESET}")
                for _ in range(PING_THREADS):
                    t = threading.Thread(target=real_ping_thread, 
                                        args=(auth_link, sid), 
                                        daemon=True)
                    t.start()
                
                # Monitor connection
                while not stop_event.is_set():
                    try:
                        requests.get("http://www.google.com", timeout=2)
                        time.sleep(5)
                    except:
                        print(f"{YELLOW}[!] Connection lost!{RESET}")
                        with lock:
                            connection_info['connected'] = False
                        break
                        
        except Exception as e:
            if not stop_event.is_set():
                time.sleep(2)

# ===============================
# MAIN FUNCTION
# ===============================

def main():
    """Main entry point"""
    try:
        # Check requirements
        required_packages = ['netifaces', 'psutil']
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                print(f"{YELLOW}[!] Installing {package}...{RESET}")
                os.system(f'pip install {package}')
        
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"""
{BOLD}{GREEN}╔══════════════════════════════════════════════════════════════════╗
║                                                                      ║
║           REAL DEVICE MONITOR FOR RUIJIE WIFI v5.0                  ║
║                                                                      ║
║           • Real Device Info    • Real Gateway Info                 ║
║           • Real WiFi SSID      • Real Ping Times                    ║
║           • Real MAC Addresses  • Real Signal Strength              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝{RESET}
""")
        
        time.sleep(2)
        
        # Start status display
        status_thread = threading.Thread(target=status_display, daemon=True)
        status_thread.start()
        
        # Start connection
        start_connection()
        
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[!] Shutting down...{RESET}")
        stop_event.set()
        time.sleep(1)
        print(f"{GREEN}[+] Clean exit{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
# ===============================
# KEY APPROVAL SYSTEM
# ===============================

import Key_v2

def check_approval_before_start():
    """Check if device is approved before running main tool"""
    if Key_v2.check_approval():
        print(f"{GREEN}✓ Device approved! Running main tool...{RESET}")
        return True
    else:
        print(f"{YELLOW}⚠ Device not approved. Starting approval process...{RESET}")
        approved = Key_v2.login(show_banner=True)
        if approved:
            print(f"{GREEN}✓ Approval successful! Now running Leo.py{RESET}")
            return True
        else:
            print(f"{RED}✗ Approval failed. Please contact owner to add your device ID to Google Sheets.{RESET}")
            print(f"{CYAN}Your Device ID: {Key_v2.get_device_id()}{RESET}")
            return False

# ===============================
# MAIN ENTRY POINT
# ===============================

if __name__ == "__main__":
    if check_approval_before_start():
        get_real_device_info()
        get_real_network_interfaces()
        get_real_wifi_info()
        get_real_gateway_info()
        get_real_dns_servers()
        status_display()
    else:
        print(f"{RED}Exiting...{RESET}")
        sys.exit(1)
