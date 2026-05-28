#!/usr/bin/env python3
"""
EMEIMG-Feeder.py

Pre-Alpha EMEIMG feeder for WSJT-X.

Purpose:
    Load an .emeimg file and feed 13-character EMEIMG packets into WSJT-X's
    Free Text / Tx5 field using the WSJT-X UDP protocol.

Design:
    - Acts as the UDP server WSJT-X reports to.
    - Listens for WSJT-X Heartbeat and Status messages.
    - Learns WSJT-X instance ID and sender UDP address.
    - Sends FreeText messages back to WSJT-X.
    - Provides Halt Tx control.
    - Operator-gated by default: it loads text into WSJT-X but does not force
      automated transmit unless explicitly enabled in the GUI.

WSJT-X setup:
    File -> Settings -> Reporting
        UDP Server: 127.0.0.1
        UDP Server port number: 2237
        Enable "Accept UDP requests" if your WSJT-X version exposes that option.

Pre-Alpha safety posture:
    This tool is intended for local and controlled OTA testing.
    Confirm mode, frequency, station ID, timing, and Part 97 compliance yourself.
"""

import os
import re
import socket
import struct
import threading
import queue
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dataclasses import dataclass
from typing import Optional, Tuple, List


APP_NAME = "EMEIMG Feeder Pre-Alpha"
APP_VERSION = "v00 patch 0"

DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_BIND_PORT = 2237

WSJTX_MAGIC = 0xADBCCBDA
WSJTX_SCHEMA = 2

MSG_HEARTBEAT_OUT = 0
MSG_STATUS_OUT = 1
MSG_HALT_TX_IN = 8
MSG_FREE_TEXT_IN = 9

EMEIMG_PACKET_RE = re.compile(r"^[A-Z0-9*]{13}$")
EMEIMG_HEADER_RE = re.compile(r"^EMEIMG[A-Z0-9]{3}[A-R]{2}[0-9]{2}$")


# ---------------------------------------------------------------------------
# Minimal Qt QDataStream encoder / decoder for the WSJT-X UDP protocol
# ---------------------------------------------------------------------------

def pack_u8(value: int) -> bytes:
    return struct.pack(">B", value)


def pack_u32(value: int) -> bytes:
    return struct.pack(">I", value)


def pack_i32(value: int) -> bytes:
    return struct.pack(">i", value)


def pack_u64(value: int) -> bytes:
    return struct.pack(">Q", value)


def pack_bool(value: bool) -> bytes:
    # QDataStream serializes bool as one byte.
    return struct.pack(">?", bool(value))


def pack_utf8(value: str) -> bytes:
    """
    WSJT-X UDP 'utf8' string:
        quint32 byte length, followed by UTF-8 bytes.
    """
    if value is None:
        value = ""

    encoded = value.encode("utf-8")
    return pack_u32(len(encoded)) + encoded


class QDataReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def read(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise EOFError("Packet ended unexpectedly")
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out

    def u8(self) -> int:
        return struct.unpack(">B", self.read(1))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.read(4))[0]

    def i32(self) -> int:
        return struct.unpack(">i", self.read(4))[0]

    def u64(self) -> int:
        return struct.unpack(">Q", self.read(8))[0]

    def boolean(self) -> bool:
        return struct.unpack(">?", self.read(1))[0]

    def utf8(self) -> str:
        """
        WSJT-X UDP 'utf8' string:
        quint32 byte length, followed by UTF-8 bytes.
        """
        length = self.u32()

        if length == 0xFFFFFFFF:
             return ""

        raw = self.read(length)

        if not raw:
            return ""

        return raw.decode("utf-8", errors="replace")


@dataclass
class EMEIMGPacket:
    text: str
    priority: bool = False
    experimental: bool = False
    source_line: int = 0
    station_id: bool = False
    eof: bool = False


def build_round_robin_queue(
    packets: List[EMEIMGPacket],
    normal_repeat_count: int = 2,
    priority_repeat_count: int = 3,
) -> List[EMEIMGQueueItem]:
    """
    Build body packet queue in round-robin order.

    Repeat policy:
        Priority packet: 3 repeats
        Normal packet:   2 repeats

    Header packets should not be passed into this function.
    """

    queue_items: List[EMEIMGQueueItem] = []

    max_repeats = max(
        normal_repeat_count,
        priority_repeat_count,
    )

    for repeat_number in range(1, max_repeats + 1):
        for source_index, packet in enumerate(packets):
            repeat_total = priority_repeat_count if packet.priority else normal_repeat_count

            if repeat_number <= repeat_total:
                queue_items.append(
                    EMEIMGQueueItem(
                        packet=packet,
                        source_index=source_index,
                        repeat_number=repeat_number,
                        repeat_total=repeat_total,
                    )
                )

    return queue_items


@dataclass
class WSJTXStatus:
    instance_id: str = ""
    mode: str = ""
    tx_mode: str = ""
    tx_enabled: bool = False
    transmitting: bool = False
    decoding: bool = False
    de_call: str = ""
    de_grid: str = ""
    dx_call: str = ""
    dx_grid: str = ""
    tx_watchdog: bool = False
    sub_mode: str = ""
    fast_mode: bool = False
    tx_message: str = ""
    raw_summary: str = ""


@dataclass
class WSJTXPeer:
    address: Tuple[str, int]
    instance_id: str = ""
    last_seen: float = 0.0


def build_wsjtx_header(message_type: int) -> bytes:
    return pack_u32(WSJTX_MAGIC) + pack_u32(WSJTX_SCHEMA) + pack_u32(message_type)


def build_free_text_message(instance_id: str, text: str, send: bool) -> bytes:
    payload = build_wsjtx_header(MSG_FREE_TEXT_IN)
    payload += pack_utf8(instance_id)
    payload += pack_utf8(text)
    payload += pack_bool(send)
    return payload


def build_halt_tx_message(instance_id: str, auto_tx_only: bool) -> bytes:
    payload = build_wsjtx_header(MSG_HALT_TX_IN)
    payload += pack_utf8(instance_id)
    payload += pack_bool(auto_tx_only)
    return payload


def parse_wsjtx_packet(data: bytes) -> Tuple[int, int, Optional[WSJTXStatus], str]:
    """
    Returns:
        message_type, schema, status_or_none, human_summary
    """
    reader = QDataReader(data)

    magic = reader.u32()
    if magic != WSJTX_MAGIC:
        raise ValueError(f"Invalid WSJT-X magic: 0x{magic:08X}")

    schema = reader.u32()
    message_type = reader.u32()

    if message_type == MSG_HEARTBEAT_OUT:
        instance_id = reader.utf8()

        summary = f"Heartbeat from WSJT-X instance '{instance_id}', schema {schema}"

        # Later schemas may include max schema, version, revision.
        try:
            if reader.remaining() >= 4:
                max_schema = reader.u32()
                summary += f", max schema {max_schema}"
            if reader.remaining() >= 4:
                version = reader.utf8()
                if version:
                    summary += f", version {version}"
            if reader.remaining() >= 4:
                revision = reader.utf8()
                if revision:
                    summary += f", revision {revision}"
        except Exception:
            pass

        status = WSJTXStatus(instance_id=instance_id, raw_summary=summary)
        return message_type, schema, status, summary

    if message_type == MSG_STATUS_OUT:
        status = WSJTXStatus()

        try:
            status.instance_id = reader.utf8()
            _dial_freq = reader.u64()
            status.mode = reader.utf8()
            status.dx_call = reader.utf8()
            _report = reader.utf8()
            status.tx_mode = reader.utf8()
            status.tx_enabled = reader.boolean()
            status.transmitting = reader.boolean()
            status.decoding = reader.boolean()
            _rx_df = reader.u32() if reader.remaining() >= 4 else 0
            _tx_df = reader.u32() if reader.remaining() >= 4 else 0

            if reader.remaining() >= 4:
                status.de_call = reader.utf8()
            if reader.remaining() >= 4:
                status.de_grid = reader.utf8()
            if reader.remaining() >= 4:
                status.dx_grid = reader.utf8()
            if reader.remaining() >= 1:
                status.tx_watchdog = reader.boolean()
            if reader.remaining() >= 4:
                status.sub_mode = reader.utf8()
            if reader.remaining() >= 1:
                status.fast_mode = reader.boolean()

            # Skip optional version-dependent fields carefully.
            # Eventually one of these may be configuration name / tx message.
            optional_strings = []
            while reader.remaining() >= 4:
                before = reader.pos
                try:
                    s = reader.utf8()
                    optional_strings.append(s)
                except Exception:
                    reader.pos = before
                    break

            if optional_strings:
                status.tx_message = optional_strings[-1]

            summary = (
                f"Status: id='{status.instance_id}' "
                f"mode='{status.mode}' tx_mode='{status.tx_mode}' "
                f"tx_enabled={status.tx_enabled} transmitting={status.transmitting} "
                f"decoding={status.decoding} de='{status.de_call}' grid='{status.de_grid}'"
            )
            status.raw_summary = summary
            return message_type, schema, status, summary

        except Exception as exc:
            summary = f"Status parse warning: {exc}"
            return message_type, schema, None, summary

    return message_type, schema, None, f"WSJT-X message type {message_type}, schema {schema}"


# ---------------------------------------------------------------------------
# Packet loading / normalization
# ---------------------------------------------------------------------------

PACKET_ALLOWED_CHARS_RE = re.compile(r"^[A-Z0-9* ]{13}$")
LOCAL_TAG_RE = re.compile(r"\s*\[(PRIORITY|EXPERIMENTAL)\]\s*$", re.IGNORECASE)
CALLSIGN_RE = re.compile(r"^[A-Z0-9]{3,6}$")


@dataclass
class EMEIMGPacket:
    text: str
    priority: bool = False
    experimental: bool = False
    source_line: int = 0
    station_id: bool = False
    eof: bool = False


@dataclass
class EMEIMGQueueItem:
    packet: EMEIMGPacket
    source_index: int
    repeat_number: int
    repeat_total: int


def normalize_callsign(callsign: str) -> Optional[str]:
    callsign = callsign.strip().upper()

    if not CALLSIGN_RE.match(callsign):
        return None

    return callsign


def build_station_id_packet(callsign: str) -> EMEIMGPacket:
    text = f"{callsign} EMEIMG"

    if len(text) > 13:
        raise ValueError(
            f"Station ID packet is too long for 13 characters: {text!r}"
        )

    return EMEIMGPacket(
        text=text.ljust(13),
        priority=False,
        experimental=False,
        source_line=0,
        station_id=True,
        eof=False,
    )


def build_eof_packet(callsign: str) -> EMEIMGPacket:
    text = f"{callsign} EOF73"

    if len(text) > 13:
        raise ValueError(
            f"EOF packet is too long for 13 characters: {text!r}"
        )

    return EMEIMGPacket(
        text=text.ljust(13),
        priority=False,
        experimental=False,
        source_line=0,
        station_id=False,
        eof=True,
    )


def normalize_line_to_packet(line: str, line_no: int = 0) -> Optional[EMEIMGPacket]:
    raw = line.rstrip("\r\n")

    if not raw.strip():
        return None

    if raw.lstrip().startswith("#"):
        return None

    priority = False
    experimental = False

    while True:
        match = LOCAL_TAG_RE.search(raw)
        if not match:
            break

        tag = match.group(1).upper()

        if tag == "PRIORITY":
            priority = True
        elif tag == "EXPERIMENTAL":
            experimental = True

        raw = raw[:match.start()]

    if raw.endswith(","):
        raw = raw[:-1]

    left_stripped = raw.lstrip()

    if left_stripped.startswith('"') or left_stripped.startswith("'"):
        quote = left_stripped[0]
        quoted = left_stripped[1:]

        if quoted.endswith(quote):
            quoted = quoted[:-1]

        raw = quoted
    else:
        raw = left_stripped

    if len(raw) < 13:
        raw = raw.ljust(13)

    if len(raw) != 13:
        return None

    raw = raw.upper()

    if not PACKET_ALLOWED_CHARS_RE.match(raw):
        return None

    return EMEIMGPacket(
        text=raw,
        priority=priority,
        experimental=experimental,
        source_line=line_no,
        station_id=False,
        eof=False,
    )


def load_emeimg_packets(path: str) -> Tuple[List[EMEIMGPacket], List[str]]:
    packets: List[EMEIMGPacket] = []
    rejected: List[str] = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            packet = normalize_line_to_packet(line, line_no=line_no)

            if packet is None:
                if line.strip() and not line.lstrip().startswith("#"):
                    rejected.append(f"Line {line_no}: {line.rstrip()}")
                continue

            packets.append(packet)

    return packets, rejected


def build_transmit_queue_with_station_id(
    source_packets: List[EMEIMGPacket],
    callsign: str,
    normal_repeat_count: int = 2,
    priority_repeat_count: int = 3,
    header_repeat_count: int = 3,
    opening_station_id_count: int = 3,
    station_id_interval: int = 5,
    closing_eof_count: int = 5,
) -> List[EMEIMGQueueItem]:
    """
    Build final transmit queue:

    1. Start with N station ID packets.
    2. Send the EMEIMG header N times.
    3. Send body packets in round-robin order.
    4. Insert station ID after every `station_id_interval` body queue packets.
    5. End with N EOF packets.

    Header packets are intentionally NOT round-robin'd.
    """

    station_packet = build_station_id_packet(callsign)
    eof_packet = build_eof_packet(callsign)

    header_packets: List[EMEIMGPacket] = []
    body_packets: List[EMEIMGPacket] = []

    for packet in source_packets:
        if packet.text.startswith("EMEIMG"):
            header_packets.append(packet)
        else:
            body_packets.append(packet)

    body_queue = build_round_robin_queue(
        body_packets,
        normal_repeat_count=normal_repeat_count,
        priority_repeat_count=priority_repeat_count,
    )

    final_queue: List[EMEIMGQueueItem] = []

    def make_station_id_item() -> EMEIMGQueueItem:
        return EMEIMGQueueItem(
            packet=station_packet,
            source_index=0,
            repeat_number=0,
            repeat_total=0,
        )

    def make_header_item(packet: EMEIMGPacket, repeat_number: int, repeat_total: int) -> EMEIMGQueueItem:
        return EMEIMGQueueItem(
            packet=packet,
            source_index=source_packets.index(packet),
            repeat_number=repeat_number,
            repeat_total=repeat_total,
        )

    def make_eof_item() -> EMEIMGQueueItem:
        return EMEIMGQueueItem(
            packet=eof_packet,
            source_index=0,
            repeat_number=0,
            repeat_total=0,
        )

    # Opening station IDs
    for _ in range(opening_station_id_count):
        final_queue.append(make_station_id_item())

    # Header repeated as a solid preamble block, not round-robin
    for header_packet in header_packets:
        for repeat_number in range(1, header_repeat_count + 1):
            final_queue.append(
                make_header_item(
                    packet=header_packet,
                    repeat_number=repeat_number,
                    repeat_total=header_repeat_count,
                )
            )

    # Main body round-robin queue with station ID inserted every 5 body packets
    packets_since_station_id = 0

    for item in body_queue:
        final_queue.append(item)
        packets_since_station_id += 1

        if packets_since_station_id >= station_id_interval:
            final_queue.append(make_station_id_item())
            packets_since_station_id = 0

    # Closing EOF packets
    for _ in range(closing_eof_count):
        final_queue.append(make_eof_item())

    return final_queue


# ---------------------------------------------------------------------------
# GUI application
# ---------------------------------------------------------------------------

class EMEIMGFeederApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1060x720")

        self.sock: Optional[socket.socket] = None
        self.listener_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.gui_queue: queue.Queue = queue.Queue()

        self.peer: Optional[WSJTXPeer] = None
        self.status = WSJTXStatus()

        self.source_packets: List[EMEIMGPacket] = []
        self.packets: List[EMEIMGQueueItem] = []
        self.current_index = 0
        self.loaded_file = ""
        
        self.auto_feed_running = False
        self.auto_feed_after_id = None
        self.auto_feed_interval_ms = 120_000  # 2 minutes

        self.bind_host_var = tk.StringVar(value=DEFAULT_BIND_HOST)
        self.bind_port_var = tk.IntVar(value=DEFAULT_BIND_PORT)
        self.instance_id_var = tk.StringVar(value="WSJT-X")

        self.callsign_var = tk.StringVar(value="")

        self.send_true_var = tk.BooleanVar(value=False)
        self.auto_tx_only_var = tk.BooleanVar(value=False)

        self.file_var = tk.StringVar(value="No .emeimg file loaded")
        self.current_packet_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="UDP listener stopped")
        self.peer_var = tk.StringVar(value="No WSJT-X peer discovered")
        self.mode_var = tk.StringVar(value="Mode: unknown")
        self.tx_state_var = tk.StringVar(value="Tx: unknown")

        self._build_ui()
        self.root.after(100, self._process_gui_queue)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(
            outer,
            text=f"{APP_NAME} {APP_VERSION}",
            font=("TkDefaultFont", 16, "bold"),
        )
        header.pack(anchor="w")

        warning = ttk.Label(
            outer,
            text=(
                "Pre-Alpha experimental feeder. Default behavior loads FreeText into WSJT-X; "
                "operator remains responsible for transmit control, station ID, frequency use, and compliance."
            ),
            foreground="red",
        )
        warning.pack(anchor="w", pady=(2, 10))

        config = ttk.LabelFrame(outer, text="WSJT-X UDP")
        config.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(config, text="Bind host:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(config, textvariable=self.bind_host_var, width=16).grid(row=0, column=1, padx=6, pady=6)

        ttk.Label(config, text="Bind port:").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(config, textvariable=self.bind_port_var, width=8).grid(row=0, column=3, padx=6, pady=6)

        ttk.Label(config, text="WSJT-X instance ID:").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(config, textvariable=self.instance_id_var, width=20).grid(row=0, column=5, padx=6, pady=6)

        ttk.Button(config, text="Start Listener", command=self.start_listener).grid(row=0, column=6, padx=6, pady=6)
        ttk.Button(config, text="Stop Listener", command=self.stop_listener).grid(row=0, column=7, padx=6, pady=6)

        status_frame = ttk.LabelFrame(outer, text="Observed WSJT-X Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w", padx=6, pady=2)
        ttk.Label(status_frame, textvariable=self.peer_var).pack(anchor="w", padx=6, pady=2)
        ttk.Label(status_frame, textvariable=self.mode_var).pack(anchor="w", padx=6, pady=2)
        ttk.Label(status_frame, textvariable=self.tx_state_var).pack(anchor="w", padx=6, pady=2)

        file_frame = ttk.LabelFrame(outer, text=".emeimg Packet File")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(file_frame, textvariable=self.file_var).grid(
            row=0, column=0, columnspan=6, padx=6, pady=6, sticky="w"
        )

        ttk.Label(file_frame, text="Callsign:").grid(
             row=1, column=0, padx=6, pady=6, sticky="w"
        )

        ttk.Entry(file_frame, textvariable=self.callsign_var, width=12).grid(
            row=1, column=1, padx=6, pady=6, sticky="w"
        )

        ttk.Button(file_frame, text="Load .emeimg", command=self.load_file).grid(
            row=1, column=2, padx=6, pady=6
        )

        ttk.Button(file_frame, text="Previous Packet", command=self.previous_packet).grid(
            row=1, column=3, padx=6, pady=6
        )

        ttk.Button(file_frame, text="Next Packet", command=self.next_packet).grid(
            row=1, column=4, padx=6, pady=6
        )

        ttk.Button(file_frame, text="Reload File", command=self.reload_file).grid(
            row=1, column=5, padx=6, pady=6
        )
        
        
        send_frame = ttk.LabelFrame(outer, text="FreeText Send Control")
        send_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(send_frame, text="Current packet:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        packet_entry = ttk.Entry(send_frame, textvariable=self.current_packet_var, width=24, font=("TkDefaultFont", 13, "bold"))
        packet_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Button(send_frame, text="Load Current into WSJT-X", command=lambda: self.send_current_packet(send_flag=False)).grid(
            row=0, column=2, padx=6, pady=6
        )

        ttk.Checkbutton(
            send_frame,
            text="Allow Send=True request",
            variable=self.send_true_var,
        ).grid(row=0, column=3, padx=6, pady=6)

        ttk.Button(send_frame, text="Load Current + Send=True", command=self.send_current_packet_with_send_true).grid(
            row=0, column=4, padx=6, pady=6
        )

        ttk.Button(send_frame, text="Load Current, Then Advance", command=self.send_current_then_advance).grid(
            row=1, column=2, padx=6, pady=6
        )
        
        ttk.Button(send_frame, text="Start Auto-Feed", command=self.start_auto_feed).grid(
            row=2, column=2, padx=6, pady=6
        )
        
        ttk.Button(send_frame, text="Stop Auto-Feed", command=self.stop_auto_feed).grid(
            row=2, column=3, padx=6, pady=6
        )

        ttk.Checkbutton(
            send_frame,
            text="HaltTx auto-tx-only",
            variable=self.auto_tx_only_var,
        ).grid(row=1, column=3, padx=6, pady=6)

        ttk.Button(send_frame, text="HALT TX", command=self.halt_tx).grid(
            row=1, column=4, padx=6, pady=6
        )

        middle = ttk.Frame(outer)
        middle.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.LabelFrame(middle, text="Packet Queue")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self.packet_list = tk.Listbox(list_frame, height=18, exportselection=False)
        self.packet_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.packet_list.bind("<<ListboxSelect>>", self.on_packet_select)

        packet_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.packet_list.yview)
        packet_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.packet_list.configure(yscrollcommand=packet_scroll.set)

        log_frame = ttk.LabelFrame(middle, text="Log")
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self.log_text = tk.Text(log_frame, height=18, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        footer = ttk.Frame(outer)
        footer.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(footer, text="Export Attempt Log", command=self.export_log).pack(side=tk.LEFT)
        ttk.Button(footer, text="Quit", command=self.on_quit).pack(side=tk.RIGHT)

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def start_listener(self):
        if self.sock is not None:
            self.log("UDP listener already running.")
            return

        host = self.bind_host_var.get().strip()
        port = int(self.bind_port_var.get())

        try:
            self.stop_event.clear()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((host, port))
            self.sock.settimeout(0.5)

            self.listener_thread = threading.Thread(target=self._udp_listener_loop, daemon=True)
            self.listener_thread.start()

            self.status_var.set(f"UDP listener running on {host}:{port}")
            self.log(f"Started UDP listener on {host}:{port}")
            self.log("Set WSJT-X Reporting UDP Server to this host/port.")
        except Exception as exc:
            self.sock = None
            messagebox.showerror("UDP listener error", str(exc))
            self.log(f"Failed to start UDP listener: {exc}")

    def stop_listener(self):
        self.stop_event.set()

        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass

        self.sock = None
        self.status_var.set("UDP listener stopped")
        self.log("Stopped UDP listener.")

    def _udp_listener_loop(self):
        while not self.stop_event.is_set():
            try:
                if self.sock is None:
                    break

                data, addr = self.sock.recvfrom(65535)
                msg_type, schema, status, summary = parse_wsjtx_packet(data)

                self.peer = WSJTXPeer(address=addr, last_seen=time.time())

                if status:
                    if status.instance_id:
                        self.peer.instance_id = status.instance_id
                        self.status.instance_id = status.instance_id
                        self.instance_id_var.set(status.instance_id)

                    if msg_type == MSG_STATUS_OUT:
                        self.status = status

                self.gui_queue.put(("status", addr, status, summary))

            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as exc:
                self.gui_queue.put(("log", f"UDP parse/listen warning: {exc}"))

    def _process_gui_queue(self):
        while True:
            try:
                item = self.gui_queue.get_nowait()
            except queue.Empty:
                break

            kind = item[0]

            if kind == "log":
                self.log(item[1])

            elif kind == "status":
                _, addr, status, summary = item
                self.log(summary)

                self.peer_var.set(f"WSJT-X peer: {addr[0]}:{addr[1]}")

                if status:
                    mode_bits = []
                    if status.mode:
                        mode_bits.append(f"mode={status.mode}")
                    if status.sub_mode:
                        mode_bits.append(f"submode={status.sub_mode}")
                    if status.tx_mode:
                        mode_bits.append(f"tx_mode={status.tx_mode}")

                    self.mode_var.set("Mode: " + (" ".join(mode_bits) if mode_bits else "unknown"))

                    self.tx_state_var.set(
                        "Tx: "
                        f"enabled={status.tx_enabled} "
                        f"transmitting={status.transmitting} "
                        f"decoding={status.decoding} "
                        f"watchdog={status.tx_watchdog}"
                    )

        self.root.after(100, self._process_gui_queue)

    def load_file(self):
        callsign = normalize_callsign(self.callsign_var.get())

        if callsign is None:
             messagebox.showwarning(
                 "Callsign required",
                 "Enter your callsign before loading an .emeimg file.\n\n"
                 "For the current 13-character FreeText packet format, callsign should be 3–6 letters/numbers."
            )
             return

        self.callsign_var.set(callsign)

        path = filedialog.askopenfilename(
            title="Load EMEIMG packet file",
            filetypes=[
                ("EMEIMG files", "*.emeimg"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        self.loaded_file = path
        self._load_file_path(path)

    def reload_file(self):
        callsign = normalize_callsign(self.callsign_var.get())

        if callsign is None:
            messagebox.showwarning(
                "Callsign required",
                "Enter your callsign before reloading the .emeimg file."
            )
            return

        self.callsign_var.set(callsign)

        if not self.loaded_file:
             messagebox.showinfo("No file", "No .emeimg file is currently loaded.")
             return

        self._load_file_path(self.loaded_file)

    def _load_file_path(self, path: str):
        try:
            source_packets, rejected = load_emeimg_packets(path)
        except Exception as exc:
            messagebox.showerror("Load error", str(exc))
            self.log(f"Failed to load file: {exc}")
            return

        callsign = normalize_callsign(self.callsign_var.get())

        if callsign is None:
            messagebox.showwarning(
                "Callsign required",
                "Enter your callsign before loading an .emeimg file."
            )
            return

        self.source_packets = source_packets

        self.packets = build_transmit_queue_with_station_id(
            source_packets=self.source_packets,
            callsign=callsign,
            normal_repeat_count=2,
            priority_repeat_count=3,
            header_repeat_count=3,
            opening_station_id_count=3,
            station_id_interval=5,
            closing_eof_count=5,
        )

        self.current_index = 0

        self.packet_list.delete(0, tk.END)

        for queue_index, queue_item in enumerate(self.packets):
            packet = queue_item.packet

            if packet.station_id:
                prefix = "ID"
            elif packet.eof:
                prefix = "EOF"
            elif packet.text.startswith("EMEIMG"):
                prefix = "HEADER"
            else:
                prefix = "PKT"
    
            if packet.station_id:
                rr_text = "ID"
                src_text = "SRC ID"
            elif packet.eof:
                rr_text = "EOF"
                src_text = "SRC EOF"
            else:
                rr_text = f"RR {queue_item.repeat_number}/{queue_item.repeat_total}"
                src_text = f"SRC {queue_item.source_index + 1:04d}"

            tags = []
            if packet.experimental:
                tags.append("EXPERIMENTAL")
            if packet.priority:
                tags.append("PRIORITY")

            tag_text = f" [{' / '.join(tags)}]" if tags else ""

            # Use · to make padding spaces visible in the queue display only.
            visible_packet = packet.text.replace(" ", "·")

            self.packet_list.insert(
                tk.END,
                (
                    f"{queue_index + 1:04d}  "
                    f"{prefix}  "
                    f"{visible_packet}  "
                    f"{rr_text}  "
                    f"{src_text}"
                    f"{tag_text}"
                )
            )
            
        normal_count = sum(
            1 for packet in self.source_packets
            if not packet.priority and not packet.text.startswith("EMEIMG")
        )
        priority_count = sum(1 for packet in self.source_packets if packet.priority)
        header_count = sum(1 for packet in self.source_packets if packet.text.startswith("EMEIMG"))
        station_id_count = sum(1 for item in self.packets if item.packet.station_id)
        eof_count = sum(1 for item in self.packets if item.packet.eof)

        self.file_var.set(
            f"Loaded {len(self.source_packets)} source packets; "
            f"generated {len(self.packets)} transmit queue entries from {os.path.basename(path)}"
        )

        self.log(f"Loaded {len(self.source_packets)} source packets from {path}")
        self.log(
            f"Generated transmit queue: {len(self.packets)} total entries "
            f"({header_count} header x3, "
            f"({normal_count} normal x2, {priority_count} priority x3, "
            f"{station_id_count} station-ID insertions, "
            f"{eof_count} EOF transmissions)."
        )

        if rejected:
            self.log(f"Rejected {len(rejected)} non-packet lines.")
            for item in rejected[:10]:
                self.log(f"Rejected: {item}")
            if len(rejected) > 10:
                self.log("Additional rejected lines omitted from display.")

        if self.packets:
            self.set_current_index(0)
        else:
            self.current_packet_var.set("")

    def set_current_index(self, index: int):
        if not self.packets:
            self.current_index = 0
            self.current_packet_var.set("")
            return

        self.current_index = max(0, min(index, len(self.packets) - 1))
        queue_item = self.packets[self.current_index]
        self.current_packet_var.set(queue_item.packet.text)

        self.packet_list.selection_clear(0, tk.END)
        self.packet_list.selection_set(self.current_index)
        self.packet_list.activate(self.current_index)
        self.packet_list.see(self.current_index)

    def on_packet_select(self, event):
        selection = self.packet_list.curselection()
        if not selection:
            return
        self.set_current_index(selection[0])

    def previous_packet(self):
        self.set_current_index(self.current_index - 1)

    def next_packet(self):
        self.set_current_index(self.current_index + 1)

    def get_destination(self) -> Optional[Tuple[Tuple[str, int], str]]:
        if self.peer is None:
            messagebox.showwarning(
                "No WSJT-X peer",
                "No WSJT-X UDP heartbeat/status has been observed yet.\n\n"
                "Start the listener, then confirm WSJT-X is configured to report to this UDP port."
            )
            return None

        instance_id = self.instance_id_var.get().strip()
        if not instance_id:
            instance_id = self.status.instance_id or self.peer.instance_id or "WSJT-X"

        return self.peer.address, instance_id

    def send_udp_to_wsjtx(self, payload: bytes):
        if self.sock is None:
            messagebox.showwarning("Listener stopped", "Start the UDP listener first.")
            return False

        destination = self.get_destination()
        if not destination:
            return False

        addr, _instance_id = destination

        try:
            self.sock.sendto(payload, addr)
            return True
        except Exception as exc:
            messagebox.showerror("UDP send error", str(exc))
            self.log(f"UDP send error: {exc}")
            return False

    def validate_current_packet(self) -> Optional[str]:
        # Preserve trailing spaces. They are valid packet padding.
        packet = self.current_packet_var.get().upper()
        
        if len(packet) < 13:
             packet = packet.ljust(13)

        if len(packet) != 13:
             messagebox.showwarning(
                 "Invalid packet",
                 f"Current packet must be exactly 13 characters. Current length: {len(packet)}"
                 )
             return None

        if not PACKET_ALLOWED_CHARS_RE.match(packet):
             messagebox.showwarning(
                 "Invalid packet",
                 "Current packet contains unsupported characters.\n\n"
                 "Pre-Alpha feeder currently allows A-Z, 0-9, *, and spaces."
                )
             return None

        return packet

    def send_current_packet(self, send_flag: bool = False) -> bool:
        packet = self.validate_current_packet()
        if packet is None:
            return False

        destination = self.get_destination()
        if not destination:
            return False

        _addr, instance_id = destination

        payload = build_free_text_message(instance_id=instance_id, text=packet, send=send_flag)

        ok = self.send_udp_to_wsjtx(payload)
        if ok:
            queue_item = self.packets[self.current_index] if self.packets else None

            if queue_item:
                self.log(
                    f"FreeText sent to WSJT-X id='{instance_id}': "
                    f"text='{packet}', Send={send_flag}, "
                    f"queue_index={self.current_index + 1}/{len(self.packets)}, "
                    f"round_robin={queue_item.repeat_number}/{queue_item.repeat_total}, "
                    f"source_packet={queue_item.source_index + 1}"
                )
            else:
                self.log(
                    f"FreeText sent to WSJT-X id='{instance_id}': "
                    f"text='{packet}', Send={send_flag}"
                )
        return ok

    def send_current_packet_with_send_true(self):
        if not self.send_true_var.get():
            messagebox.showwarning(
                "Send=True disabled",
                "The Send=True request is disabled by default.\n\n"
                "Check 'Allow Send=True request' only when you intentionally want the feeder "
                "to ask WSJT-X to select/send the free-text message."
            )
            return

        self.send_current_packet(send_flag=True)

    def send_current_then_advance(self):
        ok = self.send_current_packet(send_flag=False)
        if ok and self.packets:
            self.set_current_index(self.current_index + 1)
    
    def start_auto_feed(self):
        """
        Start automatic packet loading.
    
        Every 2 minutes:
            - Load current queue packet into WSJT-X FreeText
            - Advance to the next queue item
    
        This uses Send=False intentionally. It populates WSJT-X but does not
        request transmit. Operator remains responsible for Enable Tx / OTA control.
            """

        if self.auto_feed_running:
            self.log("Auto-Feed is already running.")
            return

        if not self.packets:
            messagebox.showwarning(
                "No packets loaded",
                "Load an .emeimg file before starting Auto-Feed."
            )
            return

        if self.current_index >= len(self.packets):
            messagebox.showinfo(
                "Queue complete",
                "The packet queue is already complete."
            )
            return

        self.auto_feed_running = True
        self.log(
            f"Auto-Feed started: loading one packet every "
            f"{self.auto_feed_interval_ms // 1000} seconds."
        )

        # Fire immediately on first button press.
        self._auto_feed_tick()


    def stop_auto_feed(self):
        """
        Stop automatic packet loading.
        """
        
        self.auto_feed_running = False
        
        if self.auto_feed_after_id is not None:
            try:
                self.root.after_cancel(self.auto_feed_after_id)
            except Exception:
                pass

            self.auto_feed_after_id = None

        self.log("Auto-Feed stopped.")


    def _auto_feed_tick(self):
        """
        Internal timer callback for Auto-Feed.
        """

        if not self.auto_feed_running:
            return

        if not self.packets:
            self.stop_auto_feed()
            self.log("Auto-Feed stopped: no packets loaded.")
            return

        if self.current_index >= len(self.packets):
            self.stop_auto_feed()
            self.log("Auto-Feed complete: reached end of transmit queue.")
            messagebox.showinfo(
                "Auto-Feed complete",
                "Reached the end of the transmit queue."
            )
            return
        
        # Load current packet into WSJT-X with Send=False, then advance.
        ok = self.send_current_packet(send_flag=False)

        if ok:
            self.log(
                f"Auto-Feed loaded queue item "
                f"{self.current_index + 1}/{len(self.packets)}."
            )

            if self.current_index < len(self.packets) - 1:
                self.set_current_index(self.current_index + 1)
            else:
                self.current_index = len(self.packets)
                self.stop_auto_feed()
                self.log("Auto-Feed complete: final packet loaded.")
                messagebox.showinfo(
                    "Auto-Feed complete",
                    "Final packet loaded into WSJT-X."
                )
                return
        else:
            self.stop_auto_feed()
            self.log("Auto-Feed stopped because packet load failed.")
            return
        
        self.auto_feed_after_id = self.root.after(
            self.auto_feed_interval_ms,
            self._auto_feed_tick,
        )


    def halt_tx(self):
        destination = self.get_destination()
        if not destination:
            return

        _addr, instance_id = destination
        auto_tx_only = self.auto_tx_only_var.get()

        payload = build_halt_tx_message(instance_id=instance_id, auto_tx_only=auto_tx_only)
        ok = self.send_udp_to_wsjtx(payload)

        if ok:
            self.log(f"HaltTx sent to WSJT-X id='{instance_id}', auto_tx_only={auto_tx_only}")

    def export_log(self):
        path = filedialog.asksaveasfilename(
            title="Export feeder attempt log",
            defaultextension=".log",
            filetypes=[
                ("Log files", "*.log"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_text.get("1.0", tk.END))
            self.log(f"Exported log to {path}")
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))

    def on_quit(self):
        self.stop_auto_feed()
        self.stop_listener()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = EMEIMGFeederApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_quit)
    root.mainloop()


if __name__ == "__main__":
    main()