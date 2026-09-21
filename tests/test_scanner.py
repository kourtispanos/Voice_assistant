import ipaddress
import socket

import pytest

import scanner


class FakeUdpSocket:
    def connect(self, addr):
        pass

    def getsockname(self):
        return ("192.168.1.50", 12345)

    def close(self):
        pass


def test_get_local_ip_range(monkeypatch):
    monkeypatch.setattr(scanner.socket, "socket", lambda *a, **k: FakeUdpSocket())
    result = scanner.get_local_ip_range()
    assert result == str(ipaddress.ip_network("192.168.1.50/24", strict=False))


def test_get_hostname_success(monkeypatch):
    monkeypatch.setattr(scanner.socket, "gethostbyaddr", lambda ip: ("my-host.local", [], [ip]))
    assert scanner.get_hostname("192.168.1.5") == "my-host.local"


def test_get_hostname_failure(monkeypatch):
    def raise_herror(ip):
        raise socket.herror("no host")

    monkeypatch.setattr(scanner.socket, "gethostbyaddr", raise_herror)
    assert scanner.get_hostname("192.168.1.5") == "Unknown"


class FakePortSocket:
    def __init__(self, open_ports):
        self._open = open_ports
        self.timeout = None

    def settimeout(self, t):
        self.timeout = t

    def connect_ex(self, addr):
        return 0 if addr[1] in self._open else 1

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def test_scan_ports(monkeypatch):
    open_ports = {22, 443}
    monkeypatch.setattr(scanner.socket, "socket", lambda *a, **k: FakePortSocket(open_ports))
    result = scanner.scan_ports("192.168.1.5", ports=[21, 22, 443, 3389])
    assert result == [22, 443]


def test_scan_ports_with_no_ports_returns_empty():
    assert scanner.scan_ports("192.168.1.5", ports=[]) == []


def test_is_port_open_closes_socket_even_when_connect_raises(monkeypatch):
    closed = []

    class ExplodingSocket(FakePortSocket):
        def connect_ex(self, addr):
            raise OSError("network down")

        def close(self):
            closed.append(True)

    monkeypatch.setattr(scanner.socket, "socket", lambda *a, **k: ExplodingSocket(set()))
    with pytest.raises(OSError):
        scanner.is_port_open("192.168.1.5", 80)
    assert closed == [True]


def test_analyze_ports_flags_risky_and_safe():
    findings = scanner.analyze_ports([22, 445])
    by_port = {f["port"]: f for f in findings}
    assert by_port[22]["service"] == "SSH"
    assert by_port[22]["risk"] is None
    assert by_port[445]["service"] == "SMB"
    assert "WannaCry" in by_port[445]["risk"]


def test_analyze_ports_unknown_port():
    findings = scanner.analyze_ports([9999])
    assert findings[0]["service"] == "Unknown"
    assert findings[0]["risk"] is None


class FakePacket:
    def __init__(self, psrc, hwsrc):
        self.psrc = psrc
        self.hwsrc = hwsrc


def test_discover_hosts(monkeypatch):
    fake_result = [(None, FakePacket("192.168.1.10", "aa:bb:cc"))]
    monkeypatch.setattr(scanner, "srp", lambda pkt, timeout, verbose: (fake_result, None))
    monkeypatch.setattr(scanner, "get_hostname", lambda ip: "resolved-host")

    devices = scanner.discover_hosts("192.168.1.0/24")
    assert devices == [{"ip": "192.168.1.10", "mac": "aa:bb:cc", "hostname": "resolved-host"}]


def test_run_full_scan_builds_report_and_restores_timeout(monkeypatch):
    monkeypatch.setattr(scanner, "get_local_ip_range", lambda: "192.168.1.0/24")
    monkeypatch.setattr(scanner, "discover_hosts", lambda ip_range: [
        {"ip": "192.168.1.5", "mac": "aa:bb", "hostname": "host1"},
    ])
    monkeypatch.setattr(scanner, "scan_ports", lambda ip: [445])

    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(None)  # simulate the process's normal default
    try:
        report = scanner.run_full_scan()

        assert report["ip_range"] == "192.168.1.0/24"
        assert len(report["devices"]) == 1
        device = report["devices"][0]
        assert device["ip"] == "192.168.1.5"
        assert device["open_ports"][0]["service"] == "SMB"

        # the scan must not leave a process-wide side effect behind
        assert socket.getdefaulttimeout() is None
    finally:
        socket.setdefaulttimeout(original_timeout)


def test_run_full_scan_restores_timeout_even_on_error(monkeypatch):
    def boom():
        raise RuntimeError("network unreachable")

    monkeypatch.setattr(scanner, "get_local_ip_range", boom)

    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(None)
    try:
        with pytest.raises(RuntimeError):
            scanner.run_full_scan()

        assert socket.getdefaulttimeout() is None
    finally:
        socket.setdefaulttimeout(original_timeout)
