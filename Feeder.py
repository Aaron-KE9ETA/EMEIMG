'''
Created on May 25, 2026

@author: Aaron Cocanower KE9ETA
'''
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass
from pathlib import Path


BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Prototype delay.
# For real JT65B pacing, this would likely become ~60_000 ms or be driven by WSJT-X timing/API state.
TX_INTERVAL_MS = 1000

PRIORITY_REPEAT_COUNT = 3
STATION_ID_EVERY_N_TRANSMISSIONS = 10


@dataclass
class EMEIMGPacket:
    text: str
    priority: bool = False
    source_line: int = 0


@dataclass
class TransmissionItem:
    text: str
    source: str = "packet"


class EMEIMGFeeder(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("EMEIMG Feeder Prototype")
        self.geometry("900x620")
        self.minsize(760, 500)

        self.loaded_file_path: Path | None = None
        self.parsed_packets: list[EMEIMGPacket] = []
        self.transmission_queue: list[TransmissionItem] = []

        self.tx_index = 0
        self.tx_running = False
        self.tx_paused = False
        self.after_job = None

        self._build_gui()

    # ------------------------------------------------------------
    # GUI
    # ------------------------------------------------------------

    def _build_gui(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        controls = ttk.LabelFrame(main, text="Feeder Controls", padding=10)
        controls.pack(fill="x")

        ttk.Label(controls, text="Callsign:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.callsign_var = tk.StringVar()
        self.callsign_entry = ttk.Entry(controls, textvariable=self.callsign_var, width=18)
        self.callsign_entry.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=4)

        ttk.Label(controls, text="EMEIMG Version:").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
        self.version_var = tk.StringVar(value="1")
        self.version_entry = ttk.Entry(controls, textvariable=self.version_var, width=10)
        self.version_entry.grid(row=0, column=3, sticky="w", padx=(0, 18), pady=4)

        ttk.Label(controls, text="Image Number:").grid(row=0, column=4, sticky="w", padx=(0, 6), pady=4)
        self.image_number_var = tk.StringVar(value="00")
        self.image_number_combo = ttk.Combobox(
            controls,
            textvariable=self.image_number_var,
            values=self._generate_base36_image_numbers(),
            width=8,
            state="normal",
        )
        self.image_number_combo.grid(row=0, column=5, sticky="w", pady=4)

        file_row = ttk.Frame(controls)
        file_row.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(10, 4))
        file_row.columnconfigure(1, weight=1)

        ttk.Button(file_row, text="Open .emeimg File", command=self.open_emeimg_file).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )

        self.file_label_var = tk.StringVar(value="No file loaded")
        ttk.Label(file_row, textvariable=self.file_label_var).grid(row=0, column=1, sticky="w")

        button_row = ttk.Frame(controls)
        button_row.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(10, 0))

        self.transmit_button = ttk.Button(button_row, text="Transmit", command=self.start_transmit)
        self.transmit_button.pack(side="left", padx=(0, 8))

        self.pause_button = ttk.Button(button_row, text="Pause Transmit", command=self.toggle_pause, state="disabled")
        self.pause_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(button_row, text="Stop Transmit", command=self.stop_transmit, state="disabled")
        self.stop_button.pack(side="left", padx=(0, 8))

        self.queue_summary_var = tk.StringVar(value="Packets loaded: 0")
        ttk.Label(button_row, textvariable=self.queue_summary_var).pack(side="right")

        console_frame = ttk.LabelFrame(main, text="Console Output / WSJT-X API Stand-In", padding=10)
        console_frame.pack(fill="both", expand=True, pady=(12, 0))

        self.console = tk.Text(console_frame, wrap="none", height=20)
        self.console.pack(side="left", fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(console_frame, orient="vertical", command=self.console.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.console.configure(yscrollcommand=scrollbar_y.set)

        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(8, 0))

        ttk.Button(bottom, text="Clear Console", command=self.clear_console).pack(side="left")

    # ------------------------------------------------------------
    # File Parsing
    # ------------------------------------------------------------

    def open_emeimg_file(self):
        file_path = filedialog.askopenfilename(
            title="Open EMEIMG File",
            filetypes=[
                ("EMEIMG files", "*.emeimg"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        self.loaded_file_path = Path(file_path)

        try:
            self.parsed_packets = self.parse_emeimg_file(self.loaded_file_path)
        except Exception as exc:
            messagebox.showerror("Parse Error", f"Could not parse file:\n\n{exc}")
            return

        self.file_label_var.set(str(self.loaded_file_path))
        self.queue_summary_var.set(self._packet_summary_text())
        self.log(f"Loaded file: {self.loaded_file_path}")
        self.log(self._packet_summary_text())

    def parse_emeimg_file(self, path: Path) -> list[EMEIMGPacket]:
        packets: list[EMEIMGPacket] = []

        with path.open("r", encoding="utf-8") as f:
            for line_number, raw_line in enumerate(f, start=1):
                line = raw_line.strip()

                if not line:
                    continue

                if line.startswith("#") or line.startswith("//"):
                    continue

                priority = False

                # [PRIORITY] is metadata, not part of the actual transmitted packet.
                if line.upper().endswith("[PRIORITY]"):
                    priority = True
                    line = line[: -len("[PRIORITY]")].strip()

                if not line:
                    continue

                packets.append(
                    EMEIMGPacket(
                        text=line,
                        priority=priority,
                        source_line=line_number,
                    )
                )

        return packets

    # ------------------------------------------------------------
    # Transmission Queue Building
    # ------------------------------------------------------------

    def build_transmission_queue(self) -> list[TransmissionItem]:
        callsign = self.get_valid_callsign()
        version = self.get_valid_version()
        image_number = self.get_valid_image_number()

        station_id = f"{callsign} EMEIMG"
        version_packet = f"EMEIMGV{version}{image_number}"
        final_packet = f"{callsign} 73"

        queue: list[TransmissionItem] = []
        output_count = 0

        def append_with_station_id_spacing(text: str, source: str):
            nonlocal output_count

            # Keep every 10th console transmission as the station ID.
            if (output_count + 1) % STATION_ID_EVERY_N_TRANSMISSIONS == 0:
                queue.append(TransmissionItem(station_id, source="station-id"))
                output_count += 1

            queue.append(TransmissionItem(text, source=source))
            output_count += 1

        # Header ID, treated as priority.
        for _ in range(PRIORITY_REPEAT_COUNT):
            append_with_station_id_spacing(station_id, source="priority-header")

        # Version/image announcement, treated as priority.
        for _ in range(PRIORITY_REPEAT_COUNT):
            append_with_station_id_spacing(version_packet, source="priority-version-header")
                
        # Sort EMEIMG packets: priority first, preserving order within each group.
        priority_packets = [p for p in self.parsed_packets if p.priority]
        normal_packets = [p for p in self.parsed_packets if not p.priority]
        sorted_packets = priority_packets + normal_packets

        for packet in sorted_packets:
            repeat_count = PRIORITY_REPEAT_COUNT if packet.priority else 1

            for _ in range(repeat_count):
                source = "priority-packet" if packet.priority else "packet"
                append_with_station_id_spacing(packet.text, source=source)

        # Final 73, treated as priority.
        for _ in range(PRIORITY_REPEAT_COUNT):
            append_with_station_id_spacing(final_packet, source="priority-final")

        return queue

    # ------------------------------------------------------------
    # Transmit Controls
    # ------------------------------------------------------------

    def start_transmit(self):
        if self.tx_running:
            return

        if not self.parsed_packets:
            messagebox.showwarning("No Packets Loaded", "Open a .emeimg file before transmitting.")
            return

        try:
            self.transmission_queue = self.build_transmission_queue()
        except ValueError as exc:
            messagebox.showerror("Invalid Feeder Settings", str(exc))
            return

        self.tx_index = 0
        self.tx_running = True
        self.tx_paused = False

        self.transmit_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pause Transmit")
        self.stop_button.configure(state="normal")

        self.log("")
        self.log("=== TRANSMISSION STARTED ===")
        self.log(f"Queue length: {len(self.transmission_queue)} console transmissions")
        self.log("")

        self._transmit_next()

    def _transmit_next(self):
        if not self.tx_running:
            return

        if self.tx_paused:
            return

        if self.tx_index >= len(self.transmission_queue):
            self.tx_running = False
            self.tx_paused = False

            self.transmit_button.configure(state="normal")
            self.pause_button.configure(state="disabled", text="Pause Transmit")
            self.stop_button.configure(state="disabled")

            self.log("")
            self.log("=== TRANSMISSION COMPLETE ===")
            return

        item = self.transmission_queue[self.tx_index]
        display_number = self.tx_index + 1

        self.log(f"{display_number:04d}: {item.text}    [{item.source}]")

        self.tx_index += 1
        self.after_job = self.after(TX_INTERVAL_MS, self._transmit_next)

    def toggle_pause(self):
        if not self.tx_running:
            return

        self.tx_paused = not self.tx_paused

        if self.tx_paused:
            self.pause_button.configure(text="Resume Transmit")
            self.log("")
            self.log("=== TRANSMISSION PAUSED ===")
        else:
            self.pause_button.configure(text="Pause Transmit")
            self.log("")
            self.log("=== TRANSMISSION RESUMED ===")
            self._transmit_next()

    def stop_transmit(self):
        if self.after_job is not None:
            try:
                self.after_cancel(self.after_job)
            except tk.TclError:
                pass
            self.after_job = None

        self.tx_running = False
        self.tx_paused = False
        self.tx_index = 0

        self.transmit_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Pause Transmit")
        self.stop_button.configure(state="disabled")

        self.log("")
        self.log("=== TRANSMISSION STOPPED ===")

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------

    def get_valid_callsign(self) -> str:
        callsign = self.callsign_var.get().strip().upper()

        if not callsign:
            raise ValueError("Callsign is required.")

        # Conservative validation for prototype purposes.
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/")
        if any(ch not in allowed for ch in callsign):
            raise ValueError("Callsign may only contain letters, numbers, and slash.")

        return callsign

    def get_valid_version(self) -> str:
        version = self.version_var.get().strip().upper()

        if not version:
            raise ValueError("EMEIMG version number is required.")

        allowed = set(BASE36)
        if any(ch not in allowed for ch in version):
            raise ValueError("Version number should use Base-36 characters only: 0-9 and A-Z.")

        return version

    def get_valid_image_number(self) -> str:
        image_number = self.image_number_var.get().strip().upper()

        if len(image_number) != 2:
            raise ValueError("Image number must be exactly two Base-36 characters, from 00 to ZZ.")

        allowed = set(BASE36)
        if any(ch not in allowed for ch in image_number):
            raise ValueError("Image number must be Base-36: 00 through ZZ.")

        return image_number

    # ------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------

    def _generate_base36_image_numbers(self) -> list[str]:
        return [a + b for a in BASE36 for b in BASE36]

    def _packet_summary_text(self) -> str:
        total = len(self.parsed_packets)
        priority = sum(1 for p in self.parsed_packets if p.priority)
        normal = total - priority
        return f"Packets loaded: {total} | Priority: {priority} | Normal: {normal}"

    def log(self, message: str):
        self.console.insert("end", message + "\n")
        self.console.see("end")

    def clear_console(self):
        self.console.delete("1.0", "end")


if __name__ == "__main__":
    app = EMEIMGFeeder()
    app.mainloop()