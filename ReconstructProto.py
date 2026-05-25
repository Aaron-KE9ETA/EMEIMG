"""
EMEIMG Reconstructor Prototype
Aaron Cocanower KE9ETA
"""

import math
import os
from tkinter import Tk, filedialog

from PIL import Image, ImageDraw, ImageFont

CANVAS_SIZE = (720, 480)
BACKGROUND = "white"
LINE_WIDTH = 3
PRIORITY_TAG = "[PRIORITY]"

TEXT_FONT_SIZE = 14

PALETTE = {
    "0": "black",
    "1": "white",
    "2": "gray",
    "3": "red",
    "4": "green",
    "5": "blue",
    "6": "yellow",
    "7": "cyan",
    "8": "magenta",
    "9": "brown",
    "A": "tan",
    "B": "beige",
    "C": "wheat",
    "D": "sandybrown",
    "E": "sienna",
    "F": "chocolate",
    "G": "gold",
    "H": "crimson",
    "I": "indigo",
    "J": "hotpink",
    "K": "orange",
    "L": "purple",
    "M": "lime",
    "N": "aliceblue",
    "O": "ivory",
    "P": "lavender",
    "Q": "mistyrose",
    "R": "papayawhip",
    "S": "seashell",
    "T": "silver",
    "U": "lightgray",
    "V": "darkslategray",
    "W": "dimgray",
}

SHAPES = {
    "0": "TEXT",
    "1": "LINE",
    "2": "RECTANGLE",
    "3": "ELLIPSE",
    "4": "TRIANGLE_OUTLINE",
    "5": "TRIANGLE_FILL",
    "6": "ARROW",
    "7": "STAR",
    "8": "ARC",
    "9": "YAGI",
    "A": "DISH",
    "B": "RADIO_TRANSCEIVER",
    "C": "RADIO_WAVES",
    "D": "MOON",
    "E": "DOUBLE_BOX",
}

MOON_CRATER_POINTS = {
    (1 / 5, 1 / 4, 3),
    (3 / 7, 5 / 8, 5),
    (1 / 4, 7 / 9, 4),
    (4 / 5, 2 / 7, 2),
    (7 / 12, 1 / 5, 6),
    (2 / 3, 2 / 5, 3),
    (5 / 8, 3 / 4, 4),
    (7 / 20, 3 / 7, 2),
    (3 / 20, 5 / 9, 5),
    (3 / 4, 3 / 5, 3)
}

def load_text_font():
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", TEXT_FONT_SIZE)
    except OSError:
        print("Warning: DejaVuSans-Bold.ttf not found, using default PIL font.")
        return ImageFont.load_default()


TEXT_FONT = load_text_font()

def b36(value):
    return int(value.upper(), 36)


def b36_pair(value):
    return int(value.upper(), 36)


def void_packet(packet, reason):
    print(f"Invalid packet ignored: {reason}: {repr(packet)}")
    return {
        "op": "VOID",
        "index": 35,
        "raw": packet,
    }


def rotate_vector(dx, dy, orientation):
    orientation = orientation % 4

    if orientation == 0:
        return dx, dy
    if orientation == 1:
        return -dy, dx
    if orientation == 2:
        return -dx, -dy
    return dy, -dx


def transform_points(points, x, y, orientation):
    transformed = []

    for px, py in points:
        dx, dy = rotate_vector(px, py, orientation)
        transformed.append((round(x + dx), round(y + dy)))

    return transformed


def select_input_file():
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    filename = filedialog.askopenfilename(
        title="Select .emeimgout file to reconstruct",
        filetypes=[
            ("EMEIMG output files", "*.emeimgout"),
            ("EMEIMG files", "*.emeimg"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()
    return filename


def unwrap_packet_line(line):
    line = line.rstrip("\r\n")

    if line == "":
        return None

    if line.startswith("#") or line.startswith("//"):
        return None

    if line.endswith(PRIORITY_TAG):
        line = line[:-len(PRIORITY_TAG)]

    # Feeder export style: "PACKET",
    if line.startswith('"') and line.endswith('",'):
        return line[1:-2]

    # Also tolerate: "PACKET"
    if line.startswith('"') and line.endswith('"'):
        return line[1:-1]

    return line


def load_commands_from_file(filename):
    commands = []

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            packet = unwrap_packet_line(line)

            if packet is None:
                continue

            commands.append(packet)

    print(f"Loaded {len(commands)} packet lines from {filename}")
    return commands


def load_commands():
    filename = select_input_file()

    if not filename:
        print("No file selected.")
        return [], None

    return load_commands_from_file(filename), filename


def parse(packet):
    packet = packet.rstrip("\r\n")

    if len(packet) != 13:
        return void_packet(packet, f"expected 13 chars, got {len(packet)}")

    try:
        instruction_index = b36(packet[0])
    except ValueError:
        return void_packet(packet, "bad instruction index")

    color_code = packet[1].upper()
    shape = packet[2].upper()
    data = packet[3:13]

    color = PALETTE.get(color_code, "black")

    try:
        if shape == "0":
            return {
                "op": "TEXT",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "text": data[4:10],
                "raw": packet,
            }

        if shape == "1":
            return {
                "op": "LINE",
                "index": instruction_index,
                "color": color,
                "x1": b36_pair(data[0:2]),
                "y1": b36_pair(data[2:4]),
                "x2": b36_pair(data[4:6]),
                "y2": b36_pair(data[6:8]),
                "raw": packet,
            }

        if shape == "2":
            return {
                "op": "RECTANGLE",
                "index": instruction_index,
                "color": color,
                "x1": b36_pair(data[0:2]),
                "y1": b36_pair(data[2:4]),
                "x2": b36_pair(data[4:6]),
                "y2": b36_pair(data[6:8]),
                "fill": b36(data[8]),
                "raw": packet,
            }

        if shape == "3":
            return {
                "op": "ELLIPSE",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "radius_h": b36(data[4]),  # vertical radius
                "radius_w": b36(data[5]),  # horizontal radius
                "scale": b36(data[6]),
                "fill": b36(data[7]),
                "raw": packet,
            }

        if shape == "4":
            return {
                "op": "TRIANGLE_OUTLINE",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "v": b36(data[4]),
                "l": b36(data[5]),
                "d": b36(data[6]),
                "r": b36(data[7]),
                "orientation": b36(data[8]),
                "scale": b36(data[9]),
                "raw": packet,
            }

        if shape == "5":
            return {
                "op": "TRIANGLE_FILL",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "v": b36(data[4]),
                "l": b36(data[5]),
                "d": b36(data[6]),
                "r": b36(data[7]),
                "orientation": b36(data[8]),
                "scale": b36(data[9]),
                "raw": packet,
            }

        if shape == "6":
            return {
                "op": "ARROW",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "orientation": b36(data[4]),
                "scale": b36(data[5]),
                "raw": packet,
            }

        if shape == "7":
            return {
                "op": "STAR",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "radius": b36(data[4]),
                "scale": b36(data[5]),
                "raw": packet,
            }

        if shape == "8":
            return {
                "op": "ARC",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "radius": b36(data[4]),
                "scale": b36(data[5]),
                "start_angle": b36_pair(data[6:8]),
                "arc_degrees": b36_pair(data[8:10]),
                "raw": packet,
            }

        if shape == "9":
            return {
                "op": "YAGI",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "orientation": b36(data[4]),
                "scale": b36(data[5]),
                "raw": packet,
            }

        if shape == "A":
            return {
                "op": "DISH",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "orientation": b36(data[4]),  # facing direction: 0 left, 1 right
                "scale": b36(data[5]),
                "raw": packet,
            }

        if shape == "B":
            return {
                "op": "RADIO_TRANSCEIVER",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "scale": b36(data[4]),
                "raw": packet,
            }

        if shape == "C":
            return {
                "op": "RADIO_WAVES",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "radius": b36(data[4]),
                "scale": b36(data[5]),
                "start_angle": b36_pair(data[6:8]),
                "arc_degrees": b36_pair(data[8:10]),
                "raw": packet,
            }

        if shape == "D":
            crater_color_code = data[5].upper()

            return {
                "op": "MOON",
                "index": instruction_index,
                "color": color,
                "x": b36_pair(data[0:2]),
                "y": b36_pair(data[2:4]),
                "scale": b36(data[4]),
                "crater_color": PALETTE.get(crater_color_code, "black"),
                "raw": packet,
            }

        if shape == "E":
            return {
                "op": "DOUBLE_BOX",
                "index": instruction_index,
                "color": color,
                "x1": b36_pair(data[0:2]),
                "y1": b36_pair(data[2:4]),
                "x2": b36_pair(data[4:6]),
                "y2": b36_pair(data[6:8]),
                "percent": b36_pair(data[8:10]),
                "raw": packet,
            }

        return void_packet(packet, f"unknown or reserved shape code {shape}")

    except ValueError as exc:
        return void_packet(packet, f"bad base-36 value ({exc})")


def render_text(parsed, draw):
    draw.text(
        (parsed["x"], parsed["y"]),
        parsed["text"],
        fill=parsed["color"],
        font=TEXT_FONT,
        anchor="lt",
    )


def render_line(parsed, draw):
    if parsed["x1"] == parsed["x2"] and parsed["y1"] == parsed["y2"]:
        print(f"Warning: zero-length line ignored: {parsed['raw']}")
        return

    draw.line(
        (parsed["x1"], parsed["y1"], parsed["x2"], parsed["y2"]),
        fill=parsed["color"],
        width=LINE_WIDTH,
    )


def render_rectangle(parsed, draw):
    left = min(parsed["x1"], parsed["x2"])
    right = max(parsed["x1"], parsed["x2"])
    top = min(parsed["y1"], parsed["y2"])
    bottom = max(parsed["y1"], parsed["y2"])

    if parsed["fill"] == 0:
        draw.rectangle(
            (left, top, right, bottom),
            outline=parsed["color"],
            width=LINE_WIDTH,
        )
    elif parsed["fill"] == 1:
        draw.rectangle(
            (left, top, right, bottom),
            fill=parsed["color"],
        )
    else:
        print(f"Warning: rectangle fill flag must be 0 or 1: {parsed['raw']}")


def render_ellipse(parsed, draw):
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale ellipse ignored: {parsed['raw']}")
        return

    if parsed["radius_h"] <= 0 or parsed["radius_w"] <= 0:
        print(f"Warning: zero-radius ellipse ignored: {parsed['raw']}")
        return

    rendered_h = parsed["radius_h"] * scale
    rendered_w = parsed["radius_w"] * scale

    box = (
        parsed["x"] - rendered_w,
        parsed["y"] - rendered_h,
        parsed["x"] + rendered_w,
        parsed["y"] + rendered_h,
    )

    if parsed["fill"] == 0:
        draw.ellipse(
            box,
            outline=parsed["color"],
            width=LINE_WIDTH,
        )
    elif parsed["fill"] == 1:
        draw.ellipse(
            box,
            fill=parsed["color"],
        )
    else:
        print(f"Warning: ellipse fill flag must be 0 or 1: {parsed['raw']}")


def render_triangle(parsed, draw, fill=False):
    x = parsed["x"]
    y = parsed["y"]
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale triangle ignored: {parsed['raw']}")
        return

    v = parsed["v"] * scale
    l = parsed["l"] * scale
    d = parsed["d"] * scale
    r = parsed["r"] * scale
    orientation = parsed["orientation"]

    p0 = (x, y)

    dx1, dy1 = rotate_vector(-l, v, orientation)
    dx2, dy2 = rotate_vector(r, d, orientation)

    p1 = (round(x + dx1), round(y + dy1))
    p2 = (round(x + dx2), round(y + dy2))

    points = [p0, p1, p2]

    if fill:
        draw.polygon(points, fill=parsed["color"])
    else:
        draw.polygon(points, outline=parsed["color"])


def render_arrow(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    scale = parsed["scale"]
    orientation = parsed["orientation"] % 4

    if scale <= 0:
        print(f"Warning: zero-scale arrow ignored: {parsed['raw']}")
        return

    head_half_width = 8 * scale
    head_height = 12 * scale
    tail_half_width = 4 * scale
    tail_height = 18 * scale

    head_points = [
        (0, 0),
        (-head_half_width, head_height),
        (head_half_width, head_height),
    ]

    tail_points = [
        (-tail_half_width, head_height),
        (tail_half_width, head_height),
        (tail_half_width, head_height + tail_height),
        (-tail_half_width, head_height + tail_height),
    ]

    draw.polygon(transform_points(head_points, x, y, orientation), fill=parsed["color"])
    draw.polygon(transform_points(tail_points, x, y, orientation), fill=parsed["color"])


def render_star(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    r = parsed["radius"]
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale star ignored: {parsed['raw']}")
        return

    if r <= 0:
        print(f"Warning: zero-radius star ignored: {parsed['raw']}")
        return

    radius = r * scale
    diag = round(radius / math.sqrt(2))

    draw.line((x, y - radius, x, y + radius), fill=parsed["color"], width=LINE_WIDTH)
    draw.line((x - radius, y, x + radius, y), fill=parsed["color"], width=LINE_WIDTH)
    draw.line((x - diag, y - diag, x + diag, y + diag), fill=parsed["color"], width=LINE_WIDTH)
    draw.line((x + diag, y - diag, x - diag, y + diag), fill=parsed["color"], width=LINE_WIDTH)


def build_arc_points(x, y, radius, start_angle, arc_degrees):
    points = []

    if arc_degrees <= 0:
        return points

    step = 5 if arc_degrees > 5 else 1
    current = 0

    while current < arc_degrees:
        angle = (start_angle + current) % 360
        theta = math.radians(angle)

        px = round(x + radius * math.cos(theta))
        py = round(y - radius * math.sin(theta))

        points.append((px, py))
        current += step

    final_angle = (start_angle + arc_degrees) % 360
    theta = math.radians(final_angle)
    final_point = (
        round(x + radius * math.cos(theta)),
        round(y - radius * math.sin(theta)),
    )

    if not points or points[-1] != final_point:
        points.append(final_point)

    return points


def draw_arc_line(draw, x, y, radius, start_angle, arc_degrees, color):
    arc_points = build_arc_points(x, y, radius, start_angle, arc_degrees)

    if len(arc_points) >= 2:
        draw.line(arc_points, fill=color, width=LINE_WIDTH)


def render_arc(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    r = parsed["radius"]
    scale = parsed["scale"]
    start_angle = parsed["start_angle"] % 360
    arc_degrees = max(0, min(360, parsed["arc_degrees"]))

    if scale <= 0:
        print(f"Warning: zero-scale arc ignored: {parsed['raw']}")
        return

    if r <= 0:
        print(f"Warning: zero-radius arc ignored: {parsed['raw']}")
        return

    if arc_degrees == 0:
        print(f"Warning: zero-degree arc ignored: {parsed['raw']}")
        return

    radius = r * scale
    draw_arc_line(draw, x, y, radius, start_angle, arc_degrees, parsed["color"])


def render_yagi(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    orientation = parsed["orientation"] % 4
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale yagi ignored: {parsed['raw']}")
        return

    start_local = (30 * scale, 0)
    end_local = (0, 100 * scale)

    dx1, dy1 = rotate_vector(start_local[0], start_local[1], orientation)
    dx2, dy2 = rotate_vector(end_local[0], end_local[1], orientation)

    draw.line(
        (round(x + dx1), round(y + dy1), round(x + dx2), round(y + dy2)),
        fill=parsed["color"],
        width=LINE_WIDTH,
    )

    ax = end_local[0] - start_local[0]
    ay = end_local[1] - start_local[1]

    length = math.sqrt(ax * ax + ay * ay)
    if length == 0:
        print(f"Warning: zero-length yagi axis ignored: {parsed['raw']}")
        return

    px = -ay / length
    py = ax / length

    element_length = 22 * scale
    half_elem = element_length / 2

    for i in range(1, 5):
        t = i / 5.0

        cx = start_local[0] + ax * t
        cy = start_local[1] + ay * t

        ex1 = cx - px * half_elem
        ey1 = cy - py * half_elem
        ex2 = cx + px * half_elem
        ey2 = cy + py * half_elem

        rdx1, rdy1 = rotate_vector(ex1, ey1, orientation)
        rdx2, rdy2 = rotate_vector(ex2, ey2, orientation)

        draw.line(
            (
                round(x + rdx1),
                round(y + rdy1),
                round(x + rdx2),
                round(y + rdy2),
            ),
            fill=parsed["color"],
            width=LINE_WIDTH,
        )


def render_dish(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    facing = parsed["orientation"] % 2
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale dish ignored: {parsed['raw']}")
        return

    radius = 40 * scale
    hub_radius = 5 * scale
    mast_length = 30 * scale

    # 0 = faces left, 1 = faces right
    flip = -1 if facing == 0 else 1

    arc_points = []
    for angle in range(90, 181, 5):
        theta = math.radians(angle)
        dx = round(radius * math.cos(theta)) * flip
        dy = round(radius * math.sin(theta))
        arc_points.append((x + dx, y + dy))

    if len(arc_points) >= 2:
        draw.line(arc_points, fill=parsed["color"], width=LINE_WIDTH)

    end1_dx = -radius * flip
    end1_dy = 0
    end2_dx = 0
    end2_dy = radius

    draw.line((x, y, x + end1_dx, y + end1_dy), fill=parsed["color"], width=LINE_WIDTH)
    draw.line((x, y, x + end2_dx, y + end2_dy), fill=parsed["color"], width=LINE_WIDTH)

    mid_local_x = round((-radius / math.sqrt(2)) * flip)
    mid_local_y = round(radius / math.sqrt(2))

    draw.line(
        (
            x + mid_local_x,
            y + mid_local_y,
            x + mid_local_x,
            y + mid_local_y + mast_length,
        ),
        fill=parsed["color"],
        width=LINE_WIDTH,
    )

    draw.ellipse(
        (
            x - hub_radius,
            y - hub_radius,
            x + hub_radius,
            y + hub_radius,
        ),
        fill=parsed["color"],
    )


def render_radio_transceiver(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale radio transceiver ignored: {parsed['raw']}")
        return

    body_w = 50 * scale
    body_h = 20 * scale

    knob_radius = 5 * scale
    knob_cx = x + (10 * scale)
    knob_cy = y + (10 * scale)

    screen_x1 = x + (25 * scale)
    screen_y1 = y + (5 * scale)
    screen_x2 = x + (45 * scale)
    screen_y2 = y + (15 * scale)

    draw.rectangle(
        (x, y, x + body_w, y + body_h),
        outline=parsed["color"],
        width=LINE_WIDTH,
    )

    draw.ellipse(
        (
            knob_cx - knob_radius,
            knob_cy - knob_radius,
            knob_cx + knob_radius,
            knob_cy + knob_radius,
        ),
        outline=parsed["color"],
        width=LINE_WIDTH,
    )

    draw.rectangle(
        (screen_x1, screen_y1, screen_x2, screen_y2),
        outline=parsed["color"],
        width=LINE_WIDTH,
    )


def render_radio_waves(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    r = parsed["radius"]
    scale = parsed["scale"]
    start_angle = parsed["start_angle"] % 360
    arc_degrees = max(0, min(360, parsed["arc_degrees"]))

    if scale <= 0:
        print(f"Warning: zero-scale radio waves ignored: {parsed['raw']}")
        return

    if r <= 0:
        print(f"Warning: zero-radius radio waves ignored: {parsed['raw']}")
        return

    if arc_degrees == 0:
        print(f"Warning: zero-degree radio waves ignored: {parsed['raw']}")
        return

    base_radius = r * scale
    spacing = 2 * r * scale

    radius1 = base_radius
    radius2 = base_radius + spacing
    radius3 = base_radius + (2 * spacing)

    draw_arc_line(draw, x, y, radius1, start_angle, arc_degrees, parsed["color"])
    draw_arc_line(draw, x, y, radius2, start_angle, arc_degrees, parsed["color"])
    draw_arc_line(draw, x, y, radius3, start_angle, arc_degrees, parsed["color"])


def render_moon(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    scale = parsed["scale"]
    moon_color = parsed["color"]
    crater_color = parsed["crater_color"]

    if scale <= 0:
        print(f"Warning: zero-scale moon ignored: {parsed['raw']}")
        return

    moon_radius = 36 * scale

    left = x - moon_radius
    top = y - moon_radius
    right = x + moon_radius
    bottom = y + moon_radius

    draw.ellipse(
        (left, top, right, bottom),
        fill=moon_color,
    )

    diameter = moon_radius * 2

    for fx, fy, base_radius in MOON_CRATER_POINTS:
        cx = left + round(diameter * fx)
        cy = top + round(diameter * fy)
        crater_radius = base_radius * scale

        draw.ellipse(
            (
                cx - crater_radius,
                cy - crater_radius,
                cx + crater_radius,
                cy + crater_radius,
            ),
            outline=crater_color,
            width=LINE_WIDTH,
        )

def render_double_box(parsed, draw):
    x1 = parsed["x1"]
    y1 = parsed["y1"]
    x2 = parsed["x2"]
    y2 = parsed["y2"]

    percent = max(0, min(100, parsed["percent"]))

    divider_y = y1 + round((y2 - y1) * percent / 100)

    draw.rectangle(
        (x1, y1, x2, y2),
        outline=parsed["color"],
        width=LINE_WIDTH,
    )

    draw.line(
        (x1, divider_y, x2, divider_y),
        fill=parsed["color"],
        width=LINE_WIDTH,
    )

def render(parsed, draw):
    op = parsed["op"]

    if op == "VOID":
        return

    if op == "TEXT":
        render_text(parsed, draw)
    elif op == "LINE":
        render_line(parsed, draw)
    elif op == "RECTANGLE":
        render_rectangle(parsed, draw)
    elif op == "ELLIPSE":
        render_ellipse(parsed, draw)
    elif op == "TRIANGLE_OUTLINE":
        render_triangle(parsed, draw, fill=False)
    elif op == "TRIANGLE_FILL":
        render_triangle(parsed, draw, fill=True)
    elif op == "ARROW":
        render_arrow(parsed, draw)
    elif op == "STAR":
        render_star(parsed, draw)
    elif op == "ARC":
        render_arc(parsed, draw)
    elif op == "YAGI":
        render_yagi(parsed, draw)
    elif op == "DISH":
        render_dish(parsed, draw)
    elif op == "RADIO_TRANSCEIVER":
        render_radio_transceiver(parsed, draw)
    elif op == "RADIO_WAVES":
        render_radio_waves(parsed, draw)
    elif op == "MOON":
        render_moon(parsed, draw)
    elif op == "DOUBLE_BOX":
        render_double_box(parsed, draw)
    else:
        print(f"Warning: unhandled operation ignored: {op}")


def deduplicate_commands(commands):
    seen = set()
    deduped = []

    for command in commands:
        if command not in seen:
            seen.add(command)
            deduped.append(command)

    return deduped


def main():
    commands, input_filename = load_commands()

    if not commands:
        print("No commands loaded; reconstruction cancelled.")
        return

    commands = deduplicate_commands(commands)

    parsed_commands = []
    for command in commands:
        parsed_commands.append(parse(command))

    parsed_commands.sort(key=lambda cmd: cmd["index"])

    img = Image.new("RGB", CANVAS_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(img)

    for parsed in parsed_commands:
        render(parsed, draw)

    if input_filename:
        base_name = os.path.splitext(os.path.basename(input_filename))[0]
        output_filename = f"{base_name}_reconstructed.png"
        output_path = os.path.join(os.path.dirname(input_filename), output_filename)
    else:
        output_path = "output_image.png"

    img.save(output_path)
    img.close()

    print(f"Image reconstruction complete: {output_path}")


if __name__ == "__main__":
    main()
