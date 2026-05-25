#!/usr/bin/env python3
"""
EMEIMG GUI Prototype
--------------------
A packet-first vector editor for building EMEIMG/JT65B-sized drawing commands.

Packet layout used by this prototype:
    [I][C][S][payload...]

    I = command order index, base-36, one character
    C = color code, one character
    S = shape code, one character

Coordinates use XXYY:
    XX = X coordinate, two base-36 characters, left padded with 0
    YY = Y coordinate, two base-36 characters, left padded with 0

Example text command:
    03000A00FKE9ETA
    I=0, C=3 red, S=0 text, X=00A, Y=00F, text=KE9ETA

Run:
    python ConstructorProto.py

Arch Linux Tk dependency:
    sudo pacman -Syu tk

Optional PNG export:
    pip install pillow
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None


BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CANVAS_W = 720
CANVAS_H = 480
PACKET_LEN = 13
DEFAULT_RADIUS = 35
DEFAULT_SCALE = 1
MAX_COMMANDS = 36
PRIORITY_TAG = "[PRIORITY]"


# Final color dictionary from the project notes.
COLOR_TABLE: Dict[str, Tuple[str, str]] = {
    "0": ("Black", "#000000"),
    "1": ("White", "#FFFFFF"),
    "2": ("Gray", "#808080"),
    "3": ("Red", "#FF0000"),
    "4": ("Green", "#00A000"),
    "5": ("Blue", "#0000FF"),
    "6": ("Yellow", "#FFFF00"),
    "7": ("Cyan", "#00FFFF"),
    "8": ("Magenta", "#FF00FF"),
    "9": ("Brown", "#8B4513"),
    "A": ("Tan", "#D2B48C"),
    "B": ("Beige", "#F5F5DC"),
    "C": ("Wheat", "#F5DEB3"),
    "D": ("Sandybrown", "#F4A460"),
    "E": ("Sienna", "#A0522D"),
    "F": ("Chocolate", "#D2691E"),
    "G": ("Gold", "#FFD700"),
    "H": ("Crimson", "#DC143C"),
    "I": ("Indigo", "#4B0082"),
    "J": ("Hotpink", "#FF69B4"),
    "K": ("Orange", "#FFA500"),
    "L": ("Purple", "#800080"),
    "M": ("Lime", "#00FF00"),
    "N": ("Aliceblue", "#F0F8FF"),
    "O": ("Ivory", "#FFFFF0"),
    "P": ("Lavender", "#E6E6FA"),
    "Q": ("Mistyrose", "#FFE4E1"),
    "R": ("Papayawhip", "#FFEFD5"),
    "S": ("Seashell", "#FFF5EE"),
    "T": ("Silver", "#C0C0C0"),
    "U": ("Lightgray", "#D3D3D3"),
    "V": ("Darkslategray", "#2F4F4F"),
    "W": ("Dimgray", "#696969"),
}


@dataclass(frozen=True)
class ShapeDef:
    code: str
    name: str
    needs_second_click: bool
    default_fill: Optional[int] = None
    macro: bool = False


# Current compact command order.
SHAPES: List[ShapeDef] = [
    ShapeDef("0", "Text 6-char", False),
    ShapeDef("1", "Line", True),
    ShapeDef("2", "Rectangle", True, default_fill=0),
    ShapeDef("3", "Ellipse", False, default_fill=0),
    ShapeDef("4", "Triangle Outline", False),
    ShapeDef("5", "Triangle Fill", False),
    ShapeDef("6", "Arrow", False),
    ShapeDef("7", "Star", False),
    ShapeDef("8", "SemiCircle / Arc", False),
    ShapeDef("9", "Yagi Antenna", False, macro=True),
    ShapeDef("A", "Dish Antenna", False, macro=True),
    ShapeDef("B", "Radio Transceiver", False, macro=True),
    ShapeDef("C", "Radio Waves", False, macro=True),
    ShapeDef("D", "Moon", False, macro=True),
    ShapeDef("E", "DoubleBox", True, macro=True),
]

SHAPE_CODES = {shape.code for shape in SHAPES}


class PacketError(ValueError):
    pass


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(n)))


def to_b36_1(n: int) -> str:
    """Encode 0..35 as one base-36 character."""
    n = clamp(n, 0, 35)
    return BASE36[n]


def from_b36_1(ch: str) -> int:
    """Decode one base-36 character."""
    ch = ch.upper()
    if ch not in BASE36:
        raise PacketError(f"Invalid base-36 character: {ch!r}")
    return BASE36.index(ch)


def to_b36_2(n: int) -> str:
    """Encode 0..1295 as two base-36 characters, left-padded with 0."""
    n = clamp(n, 0, 1295)
    return BASE36[n // 36] + BASE36[n % 36]


def from_b36_2(s: str) -> int:
    """Decode exactly two base-36 characters."""
    if len(s) != 2:
        raise PacketError(f"Expected two base-36 characters, got {s!r}")
    return from_b36_1(s[0]) * 36 + from_b36_1(s[1])


def encode_xy(x: int, y: int) -> str:
    """Encode pixel coordinates directly as XXYY.

    XX and YY are each two base-36 chars. A value like 5 becomes 05.
    """
    x = clamp(x, 0, CANVAS_W - 1)
    y = clamp(y, 0, CANVAS_H - 1)
    return to_b36_2(x) + to_b36_2(y)


def decode_xy(s: str) -> Tuple[int, int]:
    """Decode XXYY into integer pixel coordinates."""
    if len(s) != 4:
        raise PacketError(f"Expected four chars for XXYY, got {s!r}")
    x = from_b36_2(s[:2])
    y = from_b36_2(s[2:])
    return x, y


def clean_text_6(s: str) -> str:
    """Uppercase, restrict to base-36 plus spaces, and pad/truncate to six chars."""
    allowed = set(BASE36 + " ")
    s = s.upper()[:6]
    return "".join(ch if ch in allowed else " " for ch in s).ljust(6)


def pad_packet(s: str) -> str:
    """Pad unused packet space with literal spaces."""
    s = s.upper()
    if len(s) > PACKET_LEN:
        return s[:PACKET_LEN]
    return s.ljust(PACKET_LEN, " ")


def split_priority_tag(command: str) -> Tuple[str, bool]:
    """Return the 13-character packet text and whether it has PRIORITY_TAG.

    [PRIORITY] is protocol metadata, not part of the 13-character packet.
    """
    command = command.rstrip()
    if command.upper().endswith(PRIORITY_TAG):
        return command[: -len(PRIORITY_TAG)].rstrip(), True
    return command, False


def apply_priority_tag(packet: str, is_priority: bool) -> str:
    """Attach or remove the priority metadata tag without changing the packet."""
    packet, _ = split_priority_tag(packet)
    packet = pad_packet(packet)
    return f"{packet}{PRIORITY_TAG}" if is_priority else packet


def normalize_packet_order(packet: str, index: int) -> str:
    """Force packet[0] to match its layer/order index and preserve priority metadata."""
    if not 0 <= index < MAX_COMMANDS:
        raise PacketError("EMEIMG supports only 36 command order indexes, 0-Z.")
    packet, is_priority = split_priority_tag(packet)
    packet = pad_packet(packet)
    packet = to_b36_1(index) + packet[1:]
    return apply_priority_tag(packet, is_priority)


def rotate_point(px: float, py: float, ox: float, oy: float, turns: int) -> Tuple[float, float]:
    """Rotate a point around origin by 90-degree clockwise turns."""
    turns %= 4
    dx, dy = px - ox, py - oy
    for _ in range(turns):
        dx, dy = dy, -dx
    return ox + dx, oy + dy


def polygon_regular(cx: int, cy: int, radius: int, sides: int, rotation_deg: float = -90.0) -> List[Tuple[int, int]]:
    points = []
    for i in range(sides):
        a = math.radians(rotation_deg + 360 * i / sides)
        points.append((round(cx + math.cos(a) * radius), round(cy + math.sin(a) * radius)))
    return points


def draw_line(draw, p1, p2, color: str, width: int = 2, canvas_kind: str = "tk"):
    if canvas_kind == "tk":
        draw.create_line(*p1, *p2, fill=color, width=width)
    else:
        draw.line([p1, p2], fill=color, width=width)


def draw_arrow(draw, x: int, y: int, orientation: int, scale: int, fill: str, canvas_kind: str = "tk"):
    # Tip at x/y. Default points upward. Each orientation step rotates 90 degrees clockwise.
    s = max(1, scale)
    pts = [
        (x, y),
        (x - 8 * s, y + 18 * s),
        (x - 3 * s, y + 18 * s),
        (x - 3 * s, y + 45 * s),
        (x + 3 * s, y + 45 * s),
        (x + 3 * s, y + 18 * s),
        (x + 8 * s, y + 18 * s),
    ]
    pts = [rotate_point(px, py, x, y, orientation) for px, py in pts]
    if canvas_kind == "tk":
        draw.create_polygon(*pts, fill=fill, outline=fill)
    else:
        draw.polygon(pts, fill=fill, outline=fill)


def draw_star(draw, x: int, y: int, radius: int, scale: int, color: str, canvas_kind: str = "tk"):
    # Shape 7: four-line star centered at XXYY.
    # Rendered radius = R * S. Full line length is approximately 2 * R * S.
    r = max(1, radius) * max(1, scale)
    lines = [
        ((x, y - r), (x, y + r)),                  # vertical
        ((x - r, y), (x + r, y)),                  # horizontal
        ((x - r, y - r), (x + r, y + r)),          # NW/SE
        ((x + r, y - r), (x - r, y + r)),          # NE/SW
    ]
    for p1, p2 in lines:
        draw_line(draw, p1, p2, color, width=2, canvas_kind=canvas_kind)


def draw_yagi(draw, x: int, y: int, orientation: int, scale: int, color: str, canvas_kind: str = "tk"):
    # Default: origin is top-right corner of a 30x100 px bounding area.
    s = max(1, scale)
    axis_start = (x + 30 * s, y)
    axis_end = (x, y + 100 * s)
    ox, oy = x, y
    axis_start = rotate_point(*axis_start, ox, oy, orientation)
    axis_end = rotate_point(*axis_end, ox, oy, orientation)

    width = max(1, 2 * s)
    draw_line(draw, axis_start, axis_end, color, width, canvas_kind)

    for t in [0.15, 0.35, 0.55, 0.75]:
        ax = (1 - t) * (x + 30 * s) + t * x
        ay = (1 - t) * y + t * (y + 100 * s)
        p1 = (ax - 8 * s, ay - 3 * s)
        p2 = (ax + 8 * s, ay + 3 * s)
        p1 = rotate_point(*p1, ox, oy, orientation)
        p2 = rotate_point(*p2, ox, oy, orientation)
        draw_line(draw, p1, p2, color, width, canvas_kind)


def draw_dish(draw, x: int, y: int, orientation: int, scale: int, color: str, canvas_kind: str = "tk"):
    """Draw the dish antenna macro using the earlier proven geometry.

    Orientation is left/right only:
        orientation % 2 == 0 -> facing left
        orientation % 2 == 1 -> facing right
    """
    if scale <= 0:
        return

    facing = orientation % 2
    s = max(1, scale)
    radius = 40 * s
    hub_radius = 5 * s
    mast_length = 30 * s
    width = 3

    # facing 0 = left, facing 1 = right
    flip = -1 if facing == 0 else 1

    arc_points = []
    for angle in range(90, 181, 5):
        theta = math.radians(angle)
        dx = round(radius * math.cos(theta)) * flip
        dy = round(radius * math.sin(theta))
        arc_points.append((x + dx, y + dy))

    # Curved reflector bowl.
    for p1, p2 in zip(arc_points, arc_points[1:]):
        draw_line(draw, p1, p2, color, width=width, canvas_kind=canvas_kind)

    # Radial support lines from hub to arc endpoints.
    end1_dx = -radius * flip
    end1_dy = 0
    end2_dx = 0
    end2_dy = radius

    draw_line(draw, (x, y), (x + end1_dx, y + end1_dy), color, width=width, canvas_kind=canvas_kind)
    draw_line(draw, (x, y), (x + end2_dx, y + end2_dy), color, width=width, canvas_kind=canvas_kind)

    # Mast from midpoint of arc straight down.
    mid_local_x = round((-radius / math.sqrt(2)) * flip)
    mid_local_y = round(radius / math.sqrt(2))

    draw_line(
        draw,
        (x + mid_local_x, y + mid_local_y),
        (x + mid_local_x, y + mid_local_y + mast_length),
        color,
        width=width,
        canvas_kind=canvas_kind,
    )

    # Center hub circle.
    if canvas_kind == "tk":
        draw.create_oval(
            x - hub_radius,
            y - hub_radius,
            x + hub_radius,
            y + hub_radius,
            fill=color,
            outline=color,
        )
    else:
        draw.ellipse(
            (x - hub_radius, y - hub_radius, x + hub_radius, y + hub_radius),
            fill=color,
            outline=color,
        )


def draw_radio(draw, x: int, y: int, orientation: int, scale: int, color: str, canvas_kind: str = "tk"):
    """Draw the radio transceiver macro using the earlier proven geometry.

    Orientation is currently ignored and the radio is drawn in its default
    left-to-right layout.
    """
    if scale <= 0:
        return

    s = max(1, scale)
    body_w = 50 * s
    body_h = 20 * s

    knob_radius = 5 * s
    knob_cx = x + (10 * s)
    knob_cy = y + (10 * s)

    screen_x1 = x + (25 * s)
    screen_y1 = y + (5 * s)
    screen_x2 = x + (45 * s)
    screen_y2 = y + (15 * s)

    width = 3

    if canvas_kind == "tk":
        draw.create_rectangle(x, y, x + body_w, y + body_h, outline=color, width=width)
        draw.create_oval(
            knob_cx - knob_radius,
            knob_cy - knob_radius,
            knob_cx + knob_radius,
            knob_cy + knob_radius,
            outline=color,
            width=width,
        )
        draw.create_rectangle(screen_x1, screen_y1, screen_x2, screen_y2, outline=color, width=width)
    else:
        draw.rectangle((x, y, x + body_w, y + body_h), outline=color, width=width)
        draw.ellipse(
            (
                knob_cx - knob_radius,
                knob_cy - knob_radius,
                knob_cx + knob_radius,
                knob_cy + knob_radius,
            ),
            outline=color,
            width=width,
        )
        draw.rectangle((screen_x1, screen_y1, screen_x2, screen_y2), outline=color, width=width)


def draw_arc_line(draw, x: int, y: int, radius: int, start_angle: int, arc_degrees: int, color: str, canvas_kind: str = "tk"):
    """Draw an arc as a polyline so Tk and PIL use the same angle convention.

    Angle convention:
        0 degrees   = right
        90 degrees  = up
        180 degrees = left
        270 degrees = down
    """
    if radius <= 0:
        return

    start_angle %= 360
    arc_degrees = max(0, min(360, arc_degrees))
    if arc_degrees <= 0:
        return

    arc_points = []
    for angle in range(start_angle, start_angle + arc_degrees + 1, 5):
        theta = math.radians(angle % 360)
        px = round(x + radius * math.cos(theta))
        py = round(y - radius * math.sin(theta))
        arc_points.append((px, py))

    if len(arc_points) < 2:
        return

    if canvas_kind == "tk":
        for p1, p2 in zip(arc_points, arc_points[1:]):
            draw.create_line(*p1, *p2, fill=color, width=3)
    else:
        draw.line(arc_points, fill=color, width=3)


def draw_semicircle(draw, x: int, y: int, radius: int, scale: int, start_angle: int, arc_degrees: int, color: str, canvas_kind: str = "tk"):
    """Draw Shape 8 SemiCircle / Arc: [I][C]8XXYYRSOODD."""
    if scale <= 0 or radius <= 0:
        return
    rendered_radius = radius * scale
    draw_arc_line(draw, x, y, rendered_radius, start_angle, arc_degrees, color, canvas_kind)


def draw_radio_waves(draw, x: int, y: int, radius: int, scale: int, start_angle: int, arc_degrees: int, color: str, canvas_kind: str = "tk"):
    """Draw Shape C Radio Waves: [I][C]CXXYYRSOODD."""
    if scale <= 0 or radius <= 0:
        return

    arc_degrees = max(0, min(360, arc_degrees))
    if arc_degrees == 0:
        return

    start_angle %= 360
    base_radius = radius * scale
    spacing = 2 * radius * scale

    draw_arc_line(draw, x, y, base_radius, start_angle, arc_degrees, color, canvas_kind)
    draw_arc_line(draw, x, y, base_radius + spacing, start_angle, arc_degrees, color, canvas_kind)
    draw_arc_line(draw, x, y, base_radius + (2 * spacing), start_angle, arc_degrees, color, canvas_kind)


def draw_moon(draw, x: int, y: int, scale: int, moon_color: str, crater_color: str, canvas_kind: str = "tk"):
    """Draw a filled moon with outlined craters.

    Packet format:
        [I][C]DXXYYSK[spaces]

    C = moon body color
    S = scale
    K = crater color
    """
    if scale <= 0:
        return

    s = max(1, scale)
    moon_radius = 36 * s

    left = x - moon_radius
    top = y - moon_radius
    right = x + moon_radius
    bottom = y + moon_radius

    # Filled moon body.
    if canvas_kind == "tk":
        draw.create_oval(left, top, right, bottom, fill=moon_color, outline=moon_color, width=1)
    else:
        draw.ellipse((left, top, right, bottom), fill=moon_color, outline=moon_color)

    diameter = moon_radius * 2

    # Fixed crater pattern:
    # (x_fraction, y_fraction, crater_radius_at_scale_1)
    crater_points = [
        (1 / 5, 1 / 4, 3),
        (3 / 7, 5 / 8, 5),
        (1 / 4, 7 / 9, 4),
        (4 / 5, 2 / 7, 2),
        (7 / 12, 1 / 5, 6),
        (2 / 3, 2 / 5, 3),
        (5 / 8, 3 / 4, 4),
        (7 / 20, 3 / 7, 2),
        (3 / 20, 5 / 9, 5),
        (3 / 4, 3 / 5, 3),
    ]

    # Outlined crater circles.
    for fx, fy, base_radius in crater_points:
        cx = left + round(diameter * fx)
        cy = top + round(diameter * fy)
        crater_radius = base_radius * s

        if canvas_kind == "tk":
            draw.create_oval(
                cx - crater_radius,
                cy - crater_radius,
                cx + crater_radius,
                cy + crater_radius,
                outline=crater_color,
                width=3,
            )
        else:
            draw.ellipse(
                (
                    cx - crater_radius,
                    cy - crater_radius,
                    cx + crater_radius,
                    cy + crater_radius,
                ),
                outline=crater_color,
                width=3,
            )


def draw_double_box(draw, x1: int, y1: int, x2: int, y2: int, percent: int, color: str, canvas_kind: str = "tk"):
    p = clamp(percent, 0, 100)
    divider_y = y1 + round((y2 - y1) * p / 100)
    if canvas_kind == "tk":
        draw.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
        draw.create_line(x1, divider_y, x2, divider_y, fill=color, width=2)
    else:
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
        draw.line([(x1, divider_y), (x2, divider_y)], fill=color, width=2)


def validate_packet(packet: str):
    packet, _is_priority = split_priority_tag(packet)
    packet = pad_packet(packet)
    if len(packet) != PACKET_LEN:
        raise PacketError(f"Packet must be {PACKET_LEN} characters.")
    if packet[0] not in BASE36:
        raise PacketError("First character must be command order index 0-Z.")
    if packet[1] not in COLOR_TABLE:
        raise PacketError(f"Unknown color code {packet[1]!r}.")
    if packet[2] not in SHAPE_CODES:
        raise PacketError(f"Unknown shape code {packet[2]!r}.")


def render_packet(packet: str, target, canvas_kind: str = "tk"):
    """Render one 13-character packet onto a Tk Canvas or PIL ImageDraw.

    Layout is [I][C][S][payload...]. The order index is ignored by the renderer.
    Any trailing [PRIORITY] tag is metadata and is ignored by the renderer.
    """
    packet, _is_priority = split_priority_tag(packet)
    packet = pad_packet(packet)
    validate_packet(packet)

    order_code = packet[0]
    color_code = packet[1]
    shape = packet[2]
    color = COLOR_TABLE[color_code][1]

    # Payload starts at packet[3].
    if shape == "0":
        # [I][C]0XXYYTTTTTT
        x, y = decode_xy(packet[3:7])
        text = packet[7:13].rstrip()
        if canvas_kind == "tk":
            target.create_text(x, y, text=text, fill=color, anchor="nw", font=("TkDefaultFont", 14, "bold"))
        else:
            target.text((x, y), text, fill=color)

    elif shape == "1":
        # [I][C]1XXYYxxyy[space][space]
        x1, y1 = decode_xy(packet[3:7])
        x2, y2 = decode_xy(packet[7:11])
        draw_line(target, (x1, y1), (x2, y2), color, width=2, canvas_kind=canvas_kind)

    elif shape == "2":
        # [I][C]2XXYYxxyyF[space]
        x1, y1 = decode_xy(packet[3:7])
        x2, y2 = decode_xy(packet[7:11])
        fill_flag = packet[11] == "1"
        if canvas_kind == "tk":
            target.create_rectangle(x1, y1, x2, y2, outline=color, fill=color if fill_flag else "", width=2)
        else:
            target.rectangle([x1, y1, x2, y2], outline=color, fill=color if fill_flag else None, width=2)

    elif shape == "3":
        # [I][C]3XXYYRrSF[space][space]
        x, y = decode_xy(packet[3:7])
        rh = max(1, from_b36_1(packet[7]))
        rw = max(1, from_b36_1(packet[8]))
        scale = max(1, from_b36_1(packet[9]))
        fill_flag = packet[10] == "1"
        rx = rw * scale
        ry = rh * scale
        if canvas_kind == "tk":
            target.create_oval(x - rx, y - ry, x + rx, y + ry, outline=color, fill=color if fill_flag else "", width=2)
        else:
            target.ellipse([x - rx, y - ry, x + rx, y + ry], outline=color, fill=color if fill_flag else None, width=2)

    elif shape in {"4", "5"}:
        # [I][C]4/5XXYYOS[spaces]
        x, y = decode_xy(packet[3:7])
        orientation = from_b36_1(packet[7]) % 4
        scale = max(1, from_b36_1(packet[8]))
        pts = polygon_regular(x, y, 18 * scale, 3, rotation_deg=-90 + orientation * 90)
        if canvas_kind == "tk":
            target.create_polygon(*pts, outline=color, fill=color if shape == "5" else "", width=2)
        else:
            if shape == "5":
                target.polygon(pts, outline=color, fill=color)
            else:
                target.line(pts + [pts[0]], fill=color, width=2)

    elif shape == "6":
        # [I][C]6XXYYOS[spaces]
        x, y = decode_xy(packet[3:7])
        orientation = from_b36_1(packet[7]) % 4
        scale = max(1, from_b36_1(packet[8]))
        draw_arrow(target, x, y, orientation, scale, color, canvas_kind)

    elif shape == "7":
        # [I][C]7XXYYRS[spaces]
        x, y = decode_xy(packet[3:7])
        radius = max(1, from_b36_1(packet[7]))
        scale = max(1, from_b36_1(packet[8]))
        draw_star(target, x, y, radius, scale, color, canvas_kind)

    elif shape == "8":
        # [I][C]8XXYYRSOODD
        x, y = decode_xy(packet[3:7])
        radius = max(1, from_b36_1(packet[7]))
        scale = max(1, from_b36_1(packet[8]))
        start_angle = from_b36_2(packet[9:11])
        arc_degrees = from_b36_2(packet[11:13])
        draw_semicircle(target, x, y, radius, scale, start_angle, arc_degrees, color, canvas_kind)

    elif shape == "9":
        # [I][C]9XXYYOS[spaces]
        x, y = decode_xy(packet[3:7])
        orientation = from_b36_1(packet[7]) % 4
        scale = max(1, from_b36_1(packet[8]))
        draw_yagi(target, x, y, orientation, scale, color, canvas_kind)

    elif shape == "A":
        # [I][C]AXXYYOS[spaces]
        x, y = decode_xy(packet[3:7])
        orientation = from_b36_1(packet[7]) % 4
        scale = max(1, from_b36_1(packet[8]))
        draw_dish(target, x, y, orientation, scale, color, canvas_kind)

    elif shape == "B":
        # [I][C]BXXYYOS[spaces]
        x, y = decode_xy(packet[3:7])
        orientation = from_b36_1(packet[7]) % 4
        scale = max(1, from_b36_1(packet[8]))
        draw_radio(target, x, y, orientation, scale, color, canvas_kind)

    elif shape == "C":
        # [I][C]CXXYYRSOODD
        x, y = decode_xy(packet[3:7])
        radius = max(1, from_b36_1(packet[7]))
        scale = max(1, from_b36_1(packet[8]))
        start_angle = from_b36_2(packet[9:11])
        arc_degrees = from_b36_2(packet[11:13])
        draw_radio_waves(target, x, y, radius, scale, start_angle, arc_degrees, color, canvas_kind)

    elif shape == "D":
        # [I][C]DXXYYSK[spaces]
        x, y = decode_xy(packet[3:7])
        scale = max(1, from_b36_1(packet[7]))
        crater_color_code = packet[8].strip().upper() or "1"
        if crater_color_code not in COLOR_TABLE:
            crater_color_code = "1"
        crater_color = COLOR_TABLE[crater_color_code][1]
        draw_moon(target, x, y, scale, color, crater_color, canvas_kind)

    elif shape == "E":
        # [I][C]EXXYYxxyyP[space]
        x1, y1 = decode_xy(packet[3:7])
        x2, y2 = decode_xy(packet[7:11])
        percent = round(from_b36_1(packet[11]) / 35 * 100)
        draw_double_box(target, x1, y1, x2, y2, percent, color, canvas_kind)

    else:
        raise PacketError(f"Unknown shape code: {shape}")


class EMEIMGEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EMEIMG Packet-First GUI Prototype")
        self.geometry("1180x760")
        self.minsize(1000, 640)

        self.selected_color = "0"
        self.selected_shape = SHAPES[0]
        self.pending_first_click: Optional[Tuple[int, int]] = None
        self.commands: List[str] = []
        self.selected_layer_index: Optional[int] = None

        self.var_packet = tk.StringVar()
        self.var_text = tk.StringVar(value="KE9ETA")
        self.var_orientation = tk.IntVar(value=0)
        self.var_scale = tk.IntVar(value=DEFAULT_SCALE)
        self.var_radius_h = tk.IntVar(value=DEFAULT_RADIUS)
        self.var_radius_w = tk.IntVar(value=DEFAULT_RADIUS)
        self.var_start_angle = tk.IntVar(value=0)
        self.var_arc_degrees = tk.IntVar(value=180)
        self.var_fill = tk.IntVar(value=0)
        self.var_percent = tk.IntVar(value=50)
        self.var_crater_color = tk.StringVar(value="2")
        self.var_critical_element = tk.BooleanVar(value=False)
        self.var_status = tk.StringVar(value="Select color + shape, then click the canvas.")

        self._build_ui()
        self._refresh_controls_from_shape()
        self._render_all()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=6)
        left.grid(row=0, column=0, sticky="ns")
        left.rowconfigure(1, weight=1)

        ttk.Label(left, text="Shapes").grid(row=0, column=0, sticky="w")
        shape_frame = ttk.Frame(left)
        shape_frame.grid(row=1, column=0, sticky="ns")
        for i, shape in enumerate(SHAPES):
            btn = ttk.Button(shape_frame, text=f"{shape.code}  {shape.name}", command=lambda s=shape: self._select_shape(s))
            btn.grid(row=i, column=0, sticky="ew", pady=1)

        ttk.Label(left, text="Colors").grid(row=2, column=0, sticky="w", pady=(10, 0))
        color_frame = ttk.Frame(left)
        color_frame.grid(row=3, column=0, sticky="ew")
        for i, (code, (name, hex_color)) in enumerate(COLOR_TABLE.items()):
            b = tk.Button(
                color_frame,
                text=code,
                width=3,
                relief="raised",
                bg=hex_color,
                fg=self._readable_fg(hex_color),
                command=lambda c=code: self._select_color(c),
            )
            b.grid(row=i // 4, column=i % 4, padx=1, pady=1)

        center = ttk.Frame(self, padding=6)
        center.grid(row=0, column=1, sticky="nsew")
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)

        # Outer frame may expand with the window, but the actual editable canvas
        # stays fixed at CANVAS_W x CANVAS_H. This prevents Tk from showing a
        # larger white area than the protocol-editable image area.
        canvas_frame = tk.Frame(center, bg="#303030")
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_frame,
            width=CANVAS_W,
            height=CANVAS_H,
            bg="white",
            highlightthickness=1,
            highlightbackground="#999",
            bd=0,
        )
        self.canvas.grid(row=0, column=0)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        bottom = ttk.Frame(center)
        bottom.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.var_status).grid(row=0, column=0, sticky="w")
        ttk.Button(bottom, text="Clear Pending Click", command=self._clear_pending).grid(row=0, column=1, padx=4)
        ttk.Button(bottom, text="Render", command=self._render_all).grid(row=0, column=2, padx=4)
        ttk.Button(bottom, text="Export PNG", command=self._export_png).grid(row=0, column=3, padx=4)
        ttk.Button(bottom, text="Save Commands", command=self._save_commands).grid(row=0, column=4, padx=4)
        ttk.Button(bottom, text="Load Commands", command=self._load_commands).grid(row=0, column=5, padx=4)

        right = ttk.Frame(self, padding=6)
        right.grid(row=0, column=2, sticky="ns")
        right.rowconfigure(1, weight=1)

        ttk.Label(right, text="Layers / Packets").grid(row=0, column=0, sticky="w")
        self.layer_list = tk.Listbox(right, width=34, height=18)
        self.layer_list.grid(row=1, column=0, sticky="nsew")
        self.layer_list.bind("<<ListboxSelect>>", self._on_layer_select)

        layer_buttons = ttk.Frame(right)
        layer_buttons.grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(layer_buttons, text="Edit Selected", command=self._edit_selected_layer).grid(row=0, column=0, padx=2)
        ttk.Button(layer_buttons, text="Replace", command=self._replace_selected_layer).grid(row=0, column=1, padx=2)
        ttk.Button(layer_buttons, text="Delete", command=self._delete_selected_layer).grid(row=0, column=2, padx=2)

        controls = ttk.LabelFrame(right, text="Command Builder", padding=8)
        controls.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        controls.columnconfigure(1, weight=1)

        self.control_fields = {}

        def add_entry(key: str, label_text: str, variable: tk.Variable, width: int = 12, sticky: str = "w"):
            nonlocal row
            label = ttk.Label(controls, text=label_text)
            label.grid(row=row, column=0, sticky="w")
            widget = ttk.Entry(controls, textvariable=variable, width=width)
            widget.grid(row=row, column=1, sticky=sticky)
            self.control_fields[key] = (label, widget)
            row += 1
            return widget

        def add_spin(key: str, label_text: str, variable: tk.Variable, from_: int, to_: int):
            nonlocal row
            label = ttk.Label(controls, text=label_text)
            label.grid(row=row, column=0, sticky="w")
            widget = ttk.Spinbox(controls, textvariable=variable, from_=from_, to=to_, width=6)
            widget.grid(row=row, column=1, sticky="w")
            self.control_fields[key] = (label, widget)
            row += 1
            return widget

        row = 0
        self.lbl_selected = ttk.Label(controls, text="")
        self.lbl_selected.grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        add_entry("text", "Text", self.var_text, width=12, sticky="ew")
        add_spin("orientation", "Orientation 0-3", self.var_orientation, 0, 3)
        add_spin("scale", "Scale", self.var_scale, 1, 35)
        add_spin("radius_h", "Radius H / R", self.var_radius_h, 1, 35)
        add_spin("radius_w", "Radius W / r", self.var_radius_w, 1, 35)
        add_spin("start_angle", "Start Angle OO", self.var_start_angle, 0, 360)
        add_spin("arc_degrees", "Arc Degrees DD", self.var_arc_degrees, 0, 360)
        add_spin("fill", "Fill 0/1", self.var_fill, 0, 1)
        add_entry("crater_color", "Crater Color K", self.var_crater_color, width=6)
        add_spin("divider_percent", "Divider %", self.var_percent, 0, 100)

        self.chk_critical = ttk.Checkbutton(
            controls,
            text="Critical Element / Priority",
            variable=self.var_critical_element,
            command=self._update_packet_priority_from_checkbox,
        )
        self.chk_critical.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 2))
        row += 1

        ttk.Label(controls, text="Packet").grid(row=row, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.var_packet, width=22).grid(row=row, column=1, sticky="ew")
        row += 1

        packet_buttons = ttk.Frame(controls)
        packet_buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(packet_buttons, text="Add Command", command=self._add_packet_from_box).grid(row=0, column=0, padx=2)
        ttk.Button(packet_buttons, text="Render Packet", command=self._render_all).grid(row=0, column=1, padx=2)

    @staticmethod
    def _readable_fg(hex_color: str) -> str:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return "black" if lum > 150 else "white"

    def _get_crater_color_code(self) -> str:
        code = self.var_crater_color.get().strip().upper()
        if not code:
            return "2"
        if code not in COLOR_TABLE:
            return "2"
        return code

    def _packet_with_current_priority(self, packet: str) -> str:
        return apply_priority_tag(packet, self.var_critical_element.get())

    def _update_packet_priority_from_checkbox(self):
        raw = self.var_packet.get()
        if raw.strip():
            self.var_packet.set(self._packet_with_current_priority(raw))
        self._update_selected_label()

    def _select_color(self, code: str):
        self.selected_color = code
        self._update_selected_label()

    def _select_shape(self, shape: ShapeDef):
        self.selected_shape = shape
        self.pending_first_click = None
        self._refresh_controls_from_shape()
        self._update_selected_label()
        self._set_status(f"Selected {shape.code}: {shape.name}. Click canvas{' twice' if shape.needs_second_click else ''}.")

    def _refresh_controls_from_shape(self):
        if self.selected_shape.default_fill is not None:
            self.var_fill.set(self.selected_shape.default_fill)
        self._update_field_states()
        self._update_selected_label()

    def _relevant_fields_for_shape(self, shape_code: str) -> set[str]:
        # Raw packet text remains editable for every shape. This mapping only
        # controls the structured helper fields in the command builder.
        return {
            "0": {"text"},
            "1": set(),
            "2": {"fill"},
            "3": {"radius_h", "radius_w", "scale", "fill"},
            "4": {"orientation", "scale"},
            "5": {"orientation", "scale"},
            "6": {"orientation", "scale"},
            "7": {"radius_h", "scale"},
            "8": {"radius_h", "scale", "start_angle", "arc_degrees"},
            "9": {"orientation", "scale"},
            "A": {"orientation", "scale"},
            "B": {"scale"},
            "C": {"radius_h", "scale", "start_angle", "arc_degrees"},
            "D": {"scale", "crater_color"},
            "E": {"divider_percent"},
        }.get(shape_code, set())

    def _update_field_states(self):
        relevant = self._relevant_fields_for_shape(self.selected_shape.code)
        for key, (label, widget) in getattr(self, "control_fields", {}).items():
            enabled = key in relevant
            state = "normal" if enabled else "disabled"
            widget.configure(state=state)
            try:
                label.configure(foreground="" if enabled else "#888888")
            except tk.TclError:
                pass

    def _update_selected_label(self):
        color_name = COLOR_TABLE[self.selected_color][0]
        crater_code = self._get_crater_color_code()
        crater_name = COLOR_TABLE[crater_code][0]
        next_order = to_b36_1(len(self.commands)) if len(self.commands) < MAX_COMMANDS else "!"
        active = ", ".join(sorted(self._relevant_fields_for_shape(self.selected_shape.code))) or "canvas clicks only"
        priority_text = " | PRIORITY" if self.var_critical_element.get() else ""
        self.lbl_selected.configure(
            text=(
                f"Next I={next_order} | C={self.selected_color} {color_name} | "
                f"S={self.selected_shape.code} {self.selected_shape.name} | "
                f"Moon K={crater_code} {crater_name} | Active: {active}{priority_text}"
            )
        )

    def _set_status(self, msg: str):
        self.var_status.set(msg)

    def _clear_pending(self):
        self.pending_first_click = None
        self._set_status("Pending first click cleared.")
        self._render_all()

    def _on_canvas_motion(self, event):
        x = clamp(event.x, 0, CANVAS_W - 1)
        y = clamp(event.y, 0, CANVAS_H - 1)
        xy = encode_xy(x, y)
        self._set_status(
            f"Canvas px=({x},{y}) XXYY={xy} | next I={len(self.commands)} C={self.selected_color} S={self.selected_shape.code}"
        )

    def _on_canvas_click(self, event):
        if len(self.commands) >= MAX_COMMANDS:
            messagebox.showerror("Command limit reached", "EMEIMG command order index supports 36 commands: 0-Z.")
            return

        x = clamp(event.x, 0, CANVAS_W - 1)
        y = clamp(event.y, 0, CANVAS_H - 1)

        if self.selected_shape.needs_second_click:
            if self.pending_first_click is None:
                self.pending_first_click = (x, y)
                self._set_status("First point stored. Click second point.")
                self._render_all()
                self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="red", outline="red", tags="pending")
                return
            x1, y1 = self.pending_first_click
            self.pending_first_click = None
            packet = self._build_packet(x1, y1, x, y, index=len(self.commands))
        else:
            packet = self._build_packet(x, y, index=len(self.commands))

        packet = self._packet_with_current_priority(packet)
        self.var_packet.set(packet)
        self._set_status(f"Built packet: {packet!r}. Click Add Command to save as a layer.")
        self._render_preview_packet(packet)

    def _packet_prefix(self, index: int) -> str:
        if not 0 <= index < MAX_COMMANDS:
            raise PacketError("EMEIMG supports only 36 command order indexes, 0-Z.")
        order_char = to_b36_1(index)
        color_char = self.selected_color
        shape_char = self.selected_shape.code
        return f"{order_char}{color_char}{shape_char}"

    def _build_packet(self, x1: int, y1: int, x2: Optional[int] = None, y2: Optional[int] = None, index: int = 0) -> str:
        prefix = self._packet_prefix(index)
        shape = self.selected_shape.code
        xy1 = encode_xy(x1, y1)

        orientation = clamp(self.var_orientation.get(), 0, 3)
        scale = clamp(self.var_scale.get(), 1, 35)
        radius_h = clamp(self.var_radius_h.get(), 1, 35)
        radius_w = clamp(self.var_radius_w.get(), 1, 35)
        fill = clamp(self.var_fill.get(), 0, 1)
        percent = clamp(self.var_percent.get(), 0, 100)

        if shape == "0":
            # [I][C]0XXYYTTTTTT, exactly 13 chars when text is 6 chars.
            return f"{prefix}{xy1}{clean_text_6(self.var_text.get())}"

        if shape == "1":
            # [I][C]1XXYYxxyy[space][space]
            if x2 is None or y2 is None:
                raise PacketError("Line requires a second point.")
            return pad_packet(f"{prefix}{xy1}{encode_xy(x2, y2)}")

        if shape == "2":
            # [I][C]2XXYYxxyyF[space]
            if x2 is None or y2 is None:
                raise PacketError("Rectangle requires a second point.")
            return pad_packet(f"{prefix}{xy1}{encode_xy(x2, y2)}{fill}")

        if shape == "3":
            # [I][C]3XXYYRrSF[space][space]
            return pad_packet(
                f"{prefix}{xy1}{to_b36_1(radius_h)}{to_b36_1(radius_w)}{to_b36_1(scale)}{fill}"
            )

        if shape in {"4", "5", "6", "9", "A", "B"}:
            # [I][C]SXXYYOS[spaces]
            return pad_packet(f"{prefix}{xy1}{to_b36_1(orientation)}{to_b36_1(scale)}")

        if shape == "7":
            # [I][C]7XXYYRS[spaces]
            return pad_packet(f"{prefix}{xy1}{to_b36_1(radius_h)}{to_b36_1(scale)}")

        if shape == "8":
            # [I][C]8XXYYRSOODD
            start_angle = clamp(self.var_start_angle.get(), 0, 360)
            arc_degrees = clamp(self.var_arc_degrees.get(), 0, 360)
            return f"{prefix}{xy1}{to_b36_1(radius_h)}{to_b36_1(scale)}{to_b36_2(start_angle)}{to_b36_2(arc_degrees)}"

        if shape == "C":
            # [I][C]CXXYYRSOODD
            start_angle = clamp(self.var_start_angle.get(), 0, 360)
            arc_degrees = clamp(self.var_arc_degrees.get(), 0, 360)
            return f"{prefix}{xy1}{to_b36_1(radius_h)}{to_b36_1(scale)}{to_b36_2(start_angle)}{to_b36_2(arc_degrees)}"

        if shape == "D":
            # [I][C]DXXYYSK[spaces]
            crater_color = self._get_crater_color_code()
            return pad_packet(f"{prefix}{xy1}{to_b36_1(scale)}{crater_color}")

        if shape == "E":
            # [I][C]EXXYYxxyyP[space], P maps 0-Z to 0-100%.
            if x2 is None or y2 is None:
                raise PacketError("DoubleBox requires a second point.")
            pchar = to_b36_1(round(percent / 100 * 35))
            return pad_packet(f"{prefix}{xy1}{encode_xy(x2, y2)}{pchar}")

        raise PacketError(f"Unsupported shape: {shape}")

    def _add_packet_from_box(self):
        if len(self.commands) >= MAX_COMMANDS:
            messagebox.showerror("Command limit reached", "EMEIMG command order index supports 36 commands: 0-Z.")
            return

        raw = self.var_packet.get()
        if not raw.strip():
            messagebox.showerror("Invalid packet", "No packet has been built yet.")
            return

        packet = apply_priority_tag(raw, self.var_critical_element.get())
        packet = normalize_packet_order(packet, len(self.commands))

        try:
            validate_packet(packet)
        except PacketError as e:
            messagebox.showerror("Invalid packet", str(e))
            return

        self.commands.append(packet)
        self.var_packet.set(packet)
        self._refresh_layer_list()
        self._update_selected_label()
        self._render_all()
        self._set_status(f"Added layer {len(self.commands) - 1}: {packet!r}")

    def _refresh_layer_list(self):
        self.layer_list.delete(0, tk.END)
        for i, packet in enumerate(self.commands):
            base_packet, is_priority = split_priority_tag(packet)
            display_packet = pad_packet(base_packet).replace(" ", "·")
            if is_priority:
                display_packet += f" {PRIORITY_TAG}"
            self.layer_list.insert(tk.END, f"{i:02d}: {display_packet}")

    def _on_layer_select(self, _event=None):
        sel = self.layer_list.curselection()
        self.selected_layer_index = sel[0] if sel else None
        if self.selected_layer_index is not None:
            self.var_packet.set(self.commands[self.selected_layer_index])
            _packet, is_priority = split_priority_tag(self.commands[self.selected_layer_index])
            self.var_critical_element.set(is_priority)
            self._update_selected_label()
            self._render_all(upto=self.selected_layer_index)
            self._set_status(f"Previewing layers 0 through {self.selected_layer_index}.")

    def _edit_selected_layer(self):
        idx = self.selected_layer_index
        if idx is None:
            messagebox.showinfo("No layer selected", "Select a layer first.")
            return
        self.var_packet.set(self.commands[idx])
        _packet, is_priority = split_priority_tag(self.commands[idx])
        self.var_critical_element.set(is_priority)
        self._update_selected_label()
        self._set_status(f"Loaded layer {idx} into packet box. Edit text, then Replace.")

    def _replace_selected_layer(self):
        idx = self.selected_layer_index
        if idx is None:
            messagebox.showinfo("No layer selected", "Select a layer first.")
            return

        packet = apply_priority_tag(self.var_packet.get(), self.var_critical_element.get())
        packet = normalize_packet_order(packet, idx)
        try:
            validate_packet(packet)
        except PacketError as e:
            messagebox.showerror("Invalid packet", str(e))
            return

        self.commands[idx] = packet
        self.var_packet.set(packet)
        self._refresh_layer_list()
        self.layer_list.select_set(idx)
        self._render_all(upto=idx)
        self._set_status(f"Replaced layer {idx}: {packet!r}")

    def _renumber_commands(self):
        self.commands = [normalize_packet_order(packet, i) for i, packet in enumerate(self.commands[:MAX_COMMANDS])]

    def _delete_selected_layer(self):
        idx = self.selected_layer_index
        if idx is None:
            messagebox.showinfo("No layer selected", "Select a layer first.")
            return

        del self.commands[idx]
        self._renumber_commands()
        self.selected_layer_index = None
        self._refresh_layer_list()
        self._update_selected_label()
        self._render_all()
        self._set_status("Deleted selected layer and renumbered command order indexes.")

    def _render_preview_packet(self, packet: str):
        self._render_all()
        try:
            render_packet(packet, self.canvas, "tk")
        except PacketError as e:
            self._set_status(str(e))

    def _render_all(self, upto: Optional[int] = None):
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, CANVAS_W, CANVAS_H, fill="white", outline="")

        commands = self.commands if upto is None else self.commands[: upto + 1]
        for i, packet in enumerate(commands):
            try:
                render_packet(packet, self.canvas, "tk")
            except Exception as e:
                self._set_status(f"Render error on layer {i}: {e}")

        if self.pending_first_click is not None:
            x, y = self.pending_first_click
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="red", outline="red", tags="pending")

    def _save_commands(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".emeimg",
            filetypes=[("EMEIMG command files", "*.emeimg"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write("EMEIMGv1\n")
            for packet in self.commands:
                f.write(packet + "\n")
        self._set_status(f"Saved {len(self.commands)} commands to {path}")

    def _load_commands(self):
        path = filedialog.askopenfilename(
            filetypes=[("EMEIMG command files", "*.emeimg"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        loaded: List[str] = []
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line.strip() or line.strip().upper() == "EMEIMGV1" or line.lstrip().startswith("#"):
                    continue
                if len(loaded) >= MAX_COMMANDS:
                    messagebox.showwarning("Command limit", "Only the first 36 commands were loaded.")
                    break
                packet = line.rstrip()
                base_packet, is_priority = split_priority_tag(packet)
                packet = apply_priority_tag(base_packet, is_priority)
                try:
                    validate_packet(packet)
                    loaded.append(packet)
                except PacketError as e:
                    messagebox.showwarning("Skipped invalid line", f"{line!r}\n\n{e}")

        self.commands = loaded
        self._renumber_commands()
        self.selected_layer_index = None
        self._refresh_layer_list()
        self._update_selected_label()
        self._render_all()
        self._set_status(f"Loaded {len(loaded)} commands from {path} and normalized order indexes.")

    def _export_png(self):
        if Image is None or ImageDraw is None:
            messagebox.showerror("Pillow missing", "Install Pillow first: pip install pillow")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )
        if not path:
            return

        img = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
        draw = ImageDraw.Draw(img)
        for i, packet in enumerate(self.commands):
            try:
                render_packet(packet, draw, "pil")
            except Exception as e:
                messagebox.showerror("Export error", f"Layer {i}: {e}")
                return
        img.save(path)
        self._set_status(f"Exported PNG: {path}")


if __name__ == "__main__":
    app = EMEIMGEditor()
    app.mainloop()
