import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass
from pathlib import Path


BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Prototype delay.
# For real JT65B pacing, this would likely become ~60_000 ms
# or be driven by WSJT-X / MAP65 timing/API state.
TX_INTERVAL_MS = 1000

# Robustness / redundancy settings
PRIORITY_REPEAT_COUNT = 3
NON_PRIORITY_REPEAT_COUNT = 2

STATION_ID_EVERY_N_TRANSMISSIONS = 10
PRIORITY_TAG = "[PRIORITY]"


@dataclass
class EMEIMGPacket:
    text: str
    priority: bool = False
    source_line: int = 0


@dataclass
class TransmissionItem:
    text: str
    source: str = "packet"
    exportable: bool = False


class EMEIMGFeeder(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("EMEIMG Feeder Prototype")
        self.geometry("980x700")
        self.minsize(840, 560)

        self.loaded_file_path: Path | None = None
        self.parsed_packets: list[EMEIMGPacket] = []
        self.parse_warnings: list[str] = []

        self.transmission_queue: list[TransmissionItem] = []
        self.decoded_packets: list[str] = []

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

        ttk.Label(controls, text="Callsign:").grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=4
        )

        self.callsign_var = tk.StringVar()
        self.callsign_entry = ttk.Entry(
            controls,
            textvariable=self.callsign_var,
            width=18,
        )
        self.callsign_entry.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=4)

        ttk.Label(controls, text="EMEIMG Version:").grid(
            row=0, column=2, sticky="w", padx=(0, 6), pady=4
        )

        self.version_var = tk.StringVar(value="1")
        self.version_entry = ttk.Entry(
            controls,
            textvariable=self.version_var,
            width=10,
        )
        self.version_entry.grid(row=0, column=3, sticky="w", padx=(0, 18), pady=4)

        ttk.Label(controls, text="Image Number:").grid(
            row=0, column=4, sticky="w", padx=(0, 6), pady=4
        )

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

        ttk.Button(
            file_row,
            text="Open .emeimg File",
            command=self.open_emeimg_file,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.file_label_var = tk.StringVar(value="No file loaded")
        ttk.Label(file_row, textvariable=self.file_label_var).grid(
            row=0, column=1, sticky="w"
        )

        button_row = ttk.Frame(controls)
        button_row.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(10, 0))

        self.transmit_button = ttk.Button(
            button_row,
            text="Transmit",
            command=self.start_transmit,
        )
        self.transmit_button.pack(side="left", padx=(0, 8))

        self.pause_button = ttk.Button(
            button_row,
            text="Pause Transmit",
            command=self.toggle_pause,
            state="disabled",
        )
        self.pause_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(
            button_row,
            text="Stop Transmit",
            command=self.stop_transmit,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=(0, 8))

        self.queue_summary_var = tk.StringVar(value="Packets loaded: 0")
        ttk.Label(button_row, textvariable=self.queue_summary_var).pack(side="right")

        loss_row = ttk.Frame(controls)
        loss_row.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(10, 0))
        loss_row.columnconfigure(1, weight=1)

        ttk.Label(loss_row, text="Packet No Decode:").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )

        self.no_decode_var = tk.DoubleVar(value=0)
        self.no_decode_label_var = tk.StringVar(value="0%")

        self.no_decode_slider = ttk.Scale(
            loss_row,
            from_=0,
            to=100,
            variable=self.no_decode_var,
            command=self._update_no_decode_label,
        )
        self.no_decode_slider.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(loss_row, textvariable=self.no_decode_label_var, width=5).grid(
            row=0, column=2, sticky="e", padx=(0, 12)
        )

        self.export_button = ttk.Button(
            loss_row,
            text="Export Decoded Output",
            command=self.export_decoded_output,
            state="disabled",
        )
        self.export_button.grid(row=0, column=3, sticky="e")

        console_frame = ttk.LabelFrame(
            main,
            text="Console Output / WSJT-X API Stand-In",
            padding=10,
        )
        console_frame.pack(fill="both", expand=True, pady=(12, 0))

        self.console = tk.Text(console_frame, wrap="none", height=24)
        self.console.pack(side="left", fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(
            console_frame,
            orient="vertical",
            command=self.console.yview,
        )
        scrollbar_y.pack(side="right", fill="y")
        self.console.configure(yscrollcommand=scrollbar_y.set)

        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(8, 0))

        ttk.Button(bottom, text="Clear Console", command=self.clear_console).pack(
            side="left"
        )

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
            self.parsed_packets, self.parse_warnings = self.parse_emeimg_file(
                self.loaded_file_path
            )
        except Exception as exc:
            messagebox.showerror("Parse Error", f"Could not parse file:\n\n{exc}")
            return

        self.file_label_var.set(str(self.loaded_file_path))
        self.queue_summary_var.set(self._packet_summary_text())

        self.log("")
        self.log(f"Loaded file: {self.loaded_file_path}")
        self.log(self._packet_summary_text())

        if self.parse_warnings:
            self.log("")
            self.log("Parse warnings:")
            for warning in self.parse_warnings:
                self.log(f"  {warning}")

        self.export_button.configure(state="disabled")
        self.decoded_packets = []

    def parse_emeimg_file(self, path: Path) -> tuple[list[EMEIMGPacket], list[str]]:
        packets: list[EMEIMGPacket] = []
        warnings: list[str] = []

        with path.open("r", encoding="utf-8") as f:
            for line_number, raw_line in enumerate(f, start=1):
                # Remove newline characters only.
                # Do not strip trailing spaces from the actual 13-character packet.
                line = raw_line.rstrip("\r\n")

                if line.strip() == "":
                    continue

                if line.lstrip().startswith("#") or line.lstrip().startswith("//"):
                    continue

                priority = False

                # Normal Constructor format:
                # PACKET[PRIORITY]
                if line.upper().endswith(PRIORITY_TAG):
                    priority = True
                    line = line[: -len(PRIORITY_TAG)]

                # Also tolerate quoted/comma packet lines if accidentally loaded.
                # Example:
                # "IC2000014140*",
                stripped_for_wrapper_check = line.strip()

                if (
                    stripped_for_wrapper_check.endswith(",")
                    and stripped_for_wrapper_check.startswith('"')
                    and stripped_for_wrapper_check[-2:-1] == '"'
                ):
                    line = stripped_for_wrapper_check[1:-2]

                elif (
                    stripped_for_wrapper_check.startswith('"')
                    and stripped_for_wrapper_check.endswith('"')
                ):
                    line = stripped_for_wrapper_check[1:-1]

                if len(line) != 13:
                    warnings.append(
                        f"Line {line_number}: skipped malformed packet "
                        f"after metadata removal. Expected 13 characters, got {len(line)}."
                    )
                    continue

                packets.append(
                    EMEIMGPacket(
                        text=line,
                        priority=priority,
                        source_line=line_number,
                    )
                )

        return packets, warnings

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

        def append_with_station_id_spacing(
            text: str,
            source: str,
            exportable: bool = False,
        ):
            nonlocal output_count

            # Every 10th console transmission slot is the station ID.
            if (output_count + 1) % STATION_ID_EVERY_N_TRANSMISSIONS == 0:
                queue.append(
                    TransmissionItem(
                        text=station_id,
                        source="station-id",
                        exportable=False,
                    )
                )
                output_count += 1

            queue.append(
                TransmissionItem(
                    text=text,
                    source=source,
                    exportable=exportable,
                )
            )
            output_count += 1

        # Opening station ID header, treated as priority.
        for _ in range(PRIORITY_REPEAT_COUNT):
            append_with_station_id_spacing(
                station_id,
                source="priority-header",
                exportable=False,
            )

        # Version/image header, treated as priority.
        for _ in range(PRIORITY_REPEAT_COUNT):
            append_with_station_id_spacing(
                version_packet,
                source="priority-version-header",
                exportable=False,
            )

        # Priority packets first, preserving file order inside each group.
        priority_packets = [p for p in self.parsed_packets if p.priority]
        normal_packets = [p for p in self.parsed_packets if not p.priority]
        sorted_packets = priority_packets + normal_packets

        for packet in sorted_packets:
            repeat_count = (
                PRIORITY_REPEAT_COUNT
                if packet.priority
                else NON_PRIORITY_REPEAT_COUNT
            )

            for _ in range(repeat_count):
                source = "priority-packet" if packet.priority else "packet"

                append_with_station_id_spacing(
                    packet.text,
                    source=source,
                    exportable=True,
                )

        # Final 73, treated as priority.
        for _ in range(PRIORITY_REPEAT_COUNT):
            append_with_station_id_spacing(
                final_packet,
                source="priority-final",
                exportable=False,
            )

        return queue

    # ------------------------------------------------------------
    # Transmit Controls
    # ------------------------------------------------------------

    def start_transmit(self):
        if self.tx_running:
            return

        if not self.parsed_packets:
            messagebox.showwarning(
                "No Packets Loaded",
                "Open a .emeimg file before transmitting.",
            )
            return

        try:
            self.transmission_queue = self.build_transmission_queue()
        except ValueError as exc:
            messagebox.showerror("Invalid Feeder Settings", str(exc))
            return

        self.tx_index = 0
        self.tx_running = True
        self.tx_paused = False
        self.decoded_packets = []

        self.transmit_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pause Transmit")
        self.stop_button.configure(state="normal")
        self.export_button.configure(state="disabled")

        self.log("")
        self.log("=== TRANSMISSION STARTED ===")
        self.log(f"Queue length: {len(self.transmission_queue)} console transmissions")
        self.log(f"Packet no decode setting: {round(self.no_decode_var.get())}%")
        self.log(f"Priority repeat count: {PRIORITY_REPEAT_COUNT}")
        self.log(f"Non-priority repeat count: {NON_PRIORITY_REPEAT_COUNT}")
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

            if self.decoded_packets:
                self.export_button.configure(state="normal")

            self.log("")
            self.log("=== TRANSMISSION COMPLETE ===")
            self.log(f"Decoded exportable image packets: {len(self.decoded_packets)}")
            return

        item = self.transmission_queue[self.tx_index]
        display_number = self.tx_index + 1

        no_decode_percent = round(self.no_decode_var.get())
        no_decode = random.random() * 100 < no_decode_percent

        if no_decode:
            self.log(
                f"{display_number:04d}: {item.text}    "
                f"[{item.source}]    [NO DECODE]"
            )
        else:
            self.log(
                f"{display_number:04d}: {item.text}    "
                f"[{item.source}]    [DECODED]"
            )

            # Only real image packets are saved to the reconstructor test output.
            # Station ID, version header, and 73 are not exportable.
            if item.exportable:
                packet = item.text[:13]
                self.decoded_packets.append(packet)
                self.export_button.configure(state="normal")

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

        if self.decoded_packets:
            self.export_button.configure(state="normal")

        self.log("")
        self.log("=== TRANSMISSION STOPPED ===")
        self.log(f"Decoded exportable image packets so far: {len(self.decoded_packets)}")

    # ------------------------------------------------------------
    # Export
    # ------------------------------------------------------------

    def export_decoded_output(self):
        if not self.decoded_packets:
            messagebox.showwarning(
                "No Decoded Packets",
                "There are no successfully decoded image packets to export.",
            )
            self.log("")
            self.log("Export failed: decoded packet list is empty.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export Decoded EMEIMG Output",
            defaultextension=".emeimgout",
            initialfile="test.emeimgout",
            filetypes=[
                ("EMEIMG output files", "*.emeimgout"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        output_path = Path(file_path)

        with output_path.open("w", encoding="utf-8", newline="\n") as f:
            for packet in self.decoded_packets:
                # Correct export format:
                # "PACKET",
                #
                # No [PRIORITY]
                # No [DECODED]
                # No source labels
                # No station ID / version header / 73
                f.write(f'"{packet}",\n')

        self.log("")
        self.log(f"Exported decoded output: {output_path}")
        self.log(f"Exported packets: {len(self.decoded_packets)}")

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------

    def get_valid_callsign(self) -> str:
        callsign = self.callsign_var.get().strip().upper()

        if not callsign:
            raise ValueError("Callsign is required.")

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
            raise ValueError(
                "Version number should use Base-36 characters only: 0-9 and A-Z."
            )

        return version

    def get_valid_image_number(self) -> str:
        image_number = self.image_number_var.get().strip().upper()

        if len(image_number) != 2:
            raise ValueError(
                "Image number must be exactly two Base-36 characters, from 00 to ZZ."
            )

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

    def _update_no_decode_label(self, _value=None):
        percent = round(self.no_decode_var.get())
        self.no_decode_var.set(percent)
        self.no_decode_label_var.set(f"{percent}%")

    def log(self, message: str):
        self.console.insert("end", message + "\n")
        self.console.see("end")

    def clear_console(self):
        self.console.delete("1.0", "end")


if __name__ == "__main__":
    app = EMEIMGFeeder()
    app.mainloop()
