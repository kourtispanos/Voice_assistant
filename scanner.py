import socket
import ipaddress
import json
from datetime import datetime
from scapy.all import ARP, Ether, srp

def get_local_ip_range():
    """Automatically detects the local network's IP range using the
    default outbound route (avoids picking up virtual adapters like VirtualBox)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()

    network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
    return str(network)

def get_hostname(ip):
    """Tries to resolve a device's hostname. Returns 'Unknown' if not found."""
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except (socket.herror, socket.gaierror):
        return "Unknown"

def discover_hosts(ip_range):
    print(f"[*] Scanning {ip_range} for active devices...")

    arp = ARP(pdst=ip_range)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp

    result = srp(packet, timeout=3, verbose=0)[0]

    devices = []
    for sent, received in result:
        hostname = get_hostname(received.psrc)
        devices.append({"ip": received.psrc, "mac": received.hwsrc, "hostname": hostname})

    return devices

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 3306, 3389, 8080]

def scan_ports(ip, ports=COMMON_PORTS, timeout=0.5):
    """Checks which of the given ports are open on the target IP."""
    open_ports = []

    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        if result == 0:
            open_ports.append(port)
        sock.close()

    return open_ports

PORT_SERVICES = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    135: "MS RPC",
    139: "NetBIOS",
    443: "HTTPS",
    445: "SMB",
    3306: "MySQL",
    3389: "RDP",
    8080: "HTTP-Alt",
}

RISKY_PORTS = {
    21: "FTP transmits credentials in plain text",
    23: "Telnet is unencrypted — avoid if possible",
    135: "MS RPC can be an attack vector if exposed externally",
    139: "NetBIOS can leak information about the system",
    445: "SMB has a history of major vulnerabilities (e.g. WannaCry)",
    3389: "RDP is a common target for brute-force attacks",
}

def analyze_ports(open_ports):
    """Maps ports to service names and flags risky ones."""
    findings = []
    for port in open_ports:
        service = PORT_SERVICES.get(port, "Unknown")
        risk = RISKY_PORTS.get(port)
        findings.append({"port": port, "service": service, "risk": risk})
    return findings

def run_full_scan():
    """Runs the complete scan and returns a structured report."""
    ip_range = get_local_ip_range()
    hosts = discover_hosts(ip_range)

    report = {
        "scan_time": datetime.now().isoformat(),
        "ip_range": ip_range,
        "devices": []
    }

    for host in hosts:
        print(f"\n  IP: {host['ip']}  |  MAC: {host['mac']}  |  Name: {host['hostname']}")
        print(f"  [*] Scanning ports...")
        open_ports = scan_ports(host['ip'])
        findings = analyze_ports(open_ports) if open_ports else []

        for f in findings:
            if f["risk"]:
                print(f"  [!] Port {f['port']} ({f['service']}) — RISK: {f['risk']}")
            else:
                print(f"  [+] Port {f['port']} ({f['service']}) — OK")
        if not findings:
            print(f"  [-] No common open ports found")

        report["devices"].append({
            "ip": host["ip"],
            "mac": host["mac"],
            "hostname": host["hostname"],
            "open_ports": findings
        })

    return report

def save_report(report, filename="scan_report.json"):
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Report saved to {filename}")

if __name__ == "__main__":
    report = run_full_scan()
    print(f"\n[+] Found {len(report['devices'])} active devices")
    save_report(report)