'''
Created on May 23, 2026

@author: Aaron Cocanower KE9ETA

'''
from PIL import Image, ImageDraw
import math

CANVAS_SIZE = (720, 480)
BACKGROUND = "white"

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

#Convert base-36 to dec
def b36(value):
    return int(value, 36)

def b36_pair(value):
    return int(value, 36)

def void_packet(packet, reason):
    print(f"Invalid packet ignored: {reason}: {packet}")
    return {
        "op": "VOID",
        "index": 35,
        "raw": packet,
    }

#intdef manual loading
def load_commands():
    return [
        "0030000K0DC00", #Filled Rectangle Black draw 0, black background
        "14300B9K0DC00",#Filled Rectangle green draw 1 0,405 to across screen for ground
        "210I0D0KE9ETA", #Callsign white draw 2
        "3G93G9LA10000", #Gold star draw 6 55,33 Dec draw 6 124,345
        "44CF59L010000", #Green Dish antenna scale 1 draw 3 454, 345 dec
        "5JC3G9L110000", #hot pink dish antenna scal 1 draw 4  125, 290 dec
        "6659021Z30000",#Moon standin 324 73 dec draw 5
        "7G91J0X520000", #Gold star draw 6 55,33 Dec draw 6
        "8G9HH0Y520000", #Gold star draw 7 629,35 dec draw 7
        "9G94F3R520000", #Gold star draw 8 159,135 dec draw 8
        "A1D0MBF100000", #white radio transciever draw 9 22,411 dec
        "B1DH3BF100000", #white radio transciever draw A 615,411 dec
        "C1E3Z99A1002N", #White waves draw B 143,333 dec
    ]

#Parsing commands
def parse(packet):
    packet = packet.rstrip("\r\n").upper()

    if len(packet) != 13:
        return void_packet(
            packet,
            f"expected 13 chars, got {len(packet)}"
            )
    instruction_index = b36(packet[0])
    color_code = packet[1]
    shape = packet[2]
    data = packet[3:13]

    color = PALETTE.get(color_code, "black")

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
            "op": "RECT_OUTLINE",
            "index": instruction_index,
            "color": color,
            "x1": b36_pair(data[0:2]),
            "y1": b36_pair(data[2:4]),
            "x2": b36_pair(data[4:6]),
            "y2": b36_pair(data[6:8]),
            "raw": packet,
        }

    if shape == "3":
        return {
            "op": "RECT_FILL",
            "index": instruction_index,
            "color": color,
            "x1": b36_pair(data[0:2]),
            "y1": b36_pair(data[2:4]),
            "x2": b36_pair(data[4:6]),
            "y2": b36_pair(data[6:8]),
            "raw": packet,
        }

    if shape == "4":
        return {
            "op": "CIRCLE_OUTLINE",
            "index": instruction_index,
            "color": color,
            "x": b36_pair(data[0:2]),
            "y": b36_pair(data[2:4]),
            "r": b36(data[4]),
            "scale": b36(data[5]),
            "raw": packet,
    }

    if shape == "5":
        return {
            "op": "CIRCLE_FILL",
            "index": instruction_index,
            "color": color,
            "x": b36_pair(data[0:2]),
            "y": b36_pair(data[2:4]),
            "r": b36(data[4]),
            "scale": b36(data[5]),
            "raw": packet,
        }

    if shape == "6":
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

    if shape == "7":
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

    if shape == "8":
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
        
    if shape == "9":
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
    
    if shape == "A":
        return {
            "op": "SEMICIRCLE",
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
    
    if shape == "B":
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

    if shape == "C":
        return {
            "op": "DISH",
            "index": instruction_index,
            "color": color,
            "x": b36_pair(data[0:2]),
            "y": b36_pair(data[2:4]),
            "orientation": b36(data[4]),
            "scale": b36(data[5]),
            "raw": packet,
        }
    
    if shape == "D":
        return {
            "op": "RADIO_TRANSCEIVER",
            "index": instruction_index,
            "color": color,
            "x": b36_pair(data[0:2]),
            "y": b36_pair(data[2:4]),
            "scale": b36(data[4]),
            "raw": packet,
    }
          
    if shape == "E":
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
          
    return {
        "op": "UNKNOWN",
        "index": instruction_index,
        "color": color,
        "shape": shape,
        "data": data,
        "raw": packet,
    }


def render(parsed, draw):
    op = parsed["op"]
    if op == "VOID":
        return
    
    elif op == "LINE":
        draw.line(
            (parsed["x1"], parsed["y1"], parsed["x2"], parsed["y2"]),
            fill=parsed["color"],
            width=3,
        )

    elif op == "RECT_OUTLINE":
        draw.rectangle(
            (parsed["x1"], parsed["y1"], parsed["x2"], parsed["y2"]),
            outline=parsed["color"],
            width=3,
        )

    elif op == "RECT_FILL":
        draw.rectangle(
            (parsed["x1"], parsed["y1"], parsed["x2"], parsed["y2"]),
            fill=parsed["color"],
        )

    elif op == "CIRCLE_OUTLINE":
        render_circle(parsed, draw, fill=False)

    elif op == "CIRCLE_FILL":
        render_circle(parsed, draw, fill=True)

    elif op == "TEXT":
        draw.text(
            (parsed["x"], parsed["y"]),
            parsed["text"],
            fill=parsed["color"],
        )

    elif op == "TRIANGLE_OUTLINE":
        render_triangle(parsed, draw, fill=False)

    elif op == "TRIANGLE_FILL":
        render_triangle(parsed, draw, fill=True)

    elif op == "ARROW":
        render_arrow(parsed, draw)
    
    elif op == "STAR":
        render_star(parsed, draw)
    
    elif op == "SEMICIRCLE":
        render_semicircle(parsed, draw)
    
    elif op == "YAGI":
        render_yagi(parsed, draw)
    
    
    elif op == "DISH":
        render_dish(parsed, draw)
    
    elif op == "RADIO_TRANSCEIVER":
        render_radio_transceiver(parsed, draw)
    
    elif op == "RADIO_WAVES":
        render_radio_waves(parsed, draw)
        
    elif op == "UNKNOWN":
        print(f"Unknown packet ignored: {parsed['raw']}")



#Helpers
def rotate_vector(dx, dy, orientation):
    orientation = orientation % 4

    if orientation == 0:      # no rotation
        return dx, dy

    elif orientation == 1:    # 90 degrees clockwise
        return -dy, dx

    elif orientation == 2:    # 180 degrees
        return -dx, -dy

    else:                     # 270 degrees clockwise
        return dy, -dx
    

def rotate_point(dx, dy, orientation):
    orientation = orientation % 4

    if orientation == 0:
        return dx, dy
    elif orientation == 1:
        return -dy, dx
    elif orientation == 2:
        return -dx, -dy
    else:
        return dy, -dx

def draw_arc_line(draw, x, y, radius, start_angle, arc_degrees, color):
    arc_points = []

    for angle in range(start_angle, start_angle + arc_degrees + 1, 5):
        theta = math.radians(angle % 360)

        px = round(x + radius * math.cos(theta))
        py = round(y - radius * math.sin(theta))

        arc_points.append((px, py))

    if len(arc_points) >= 2:
        draw.line(
            arc_points,
            fill=color,
            width=3,
        )

#Render macros
def render_circle(parsed, draw, fill=False):
    x = parsed["x"]
    y = parsed["y"]
    r = parsed["r"]
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale circle ignored: {parsed['raw']}")
        return

    if r <= 0:
        print(f"Warning: zero-radius circle ignored: {parsed['raw']}")
        return

    radius = r * scale

    box = (
        x - radius,
        y - radius,
        x + radius,
        y + radius,
    )

    if fill:
        draw.ellipse(box, fill=parsed["color"])
    else:
        draw.ellipse(box, outline=parsed["color"], width=3)
        

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

    p1 = (x + dx1, y + dy1)
    p2 = (x + dx2, y + dy2)

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

    size = 10 * scale

    head_length = size
    head_half_width = size // 2

    tail_length = size
    tail_half_width = max(1, size // 6)

    if orientation == 0:  # points up
        head = [
            (x, y),
            (x - head_half_width, y + head_length),
            (x + head_half_width, y + head_length),
        ]

        tail = [
            (x - tail_half_width, y + head_length),
            (x + tail_half_width, y + head_length),
            (x + tail_half_width, y + head_length + tail_length),
            (x - tail_half_width, y + head_length + tail_length),
        ]

    elif orientation == 1:  # points right
        head = [
            (x, y),
            (x - head_length, y - head_half_width),
            (x - head_length, y + head_half_width),
        ]

        tail = [
            (x - head_length, y - tail_half_width),
            (x - head_length, y + tail_half_width),
            (x - head_length - tail_length, y + tail_half_width),
            (x - head_length - tail_length, y - tail_half_width),
        ]

    elif orientation == 2:  # points down
        head = [
            (x, y),
            (x - head_half_width, y - head_length),
            (x + head_half_width, y - head_length),
        ]

        tail = [
            (x - tail_half_width, y - head_length),
            (x + tail_half_width, y - head_length),
            (x + tail_half_width, y - head_length - tail_length),
            (x - tail_half_width, y - head_length - tail_length),
        ]

    else:  # points left
        head = [
            (x, y),
            (x + head_length, y - head_half_width),
            (x + head_length, y + head_half_width),
        ]

        tail = [
            (x + head_length, y - tail_half_width),
            (x + head_length, y + tail_half_width),
            (x + head_length + tail_length, y + tail_half_width),
            (x + head_length + tail_length, y - tail_half_width),
        ]

    draw.polygon(tail, fill=parsed["color"])
    draw.polygon(head, fill=parsed["color"])
    
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

    # Vertical
    draw.line(
        (x, y - radius, x, y + radius),
        fill=parsed["color"],
        width=3,
    )

    # Horizontal
    draw.line(
        (x - radius, y, x + radius, y),
        fill=parsed["color"],
        width=3,
    )

    # Diagonal NW <-> SE
    draw.line(
        (x - diag, y - diag, x + diag, y + diag),
        fill=parsed["color"],
        width=3,
    )

    # Diagonal NE <-> SW
    draw.line(
        (x + diag, y - diag, x - diag, y + diag),
        fill=parsed["color"],
        width=3,
    )

def render_semicircle(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    r = parsed["radius"]
    scale = parsed["scale"]
    start_angle = parsed["start_angle"]
    arc_degrees = parsed["arc_degrees"]

    if scale <= 0:
        print(f"Warning: zero-scale semicircle ignored: {parsed['raw']}")
        return

    if r <= 0:
        print(f"Warning: zero-radius semicircle ignored: {parsed['raw']}")
        return

    radius = r * scale

    # Normalize angles
    start_angle = start_angle % 360
    arc_degrees = max(0, min(360, arc_degrees))

    if arc_degrees == 0:
        print(f"Warning: zero-degree semicircle ignored: {parsed['raw']}")
        return

    arc_points = []

    # Step through the arc counterclockwise
    for angle in range(start_angle, start_angle + arc_degrees + 1, 5):
        theta = math.radians(angle % 360)

        px = round(x + radius * math.cos(theta))
        py = round(y - radius * math.sin(theta))

        arc_points.append((px, py))

    # Ensure at least 2 points
    if len(arc_points) < 2:
        return

    draw.line(
        arc_points,
        fill=parsed["color"],
        width=3,
    )

def render_yagi(parsed, draw):
    x = parsed["x"]
    y = parsed["y"]
    orientation = parsed["orientation"] % 4
    scale = parsed["scale"]

    if scale <= 0:
        print(f"Warning: zero-scale yagi ignored: {parsed['raw']}")
        return

    # Default geometry relative to origin XX,YY
    start_local = (30 * scale, 0 * scale)
    end_local = (0 * scale, 100 * scale)

    # Rotate axis endpoints
    dx1, dy1 = rotate_point(start_local[0], start_local[1], orientation)
    dx2, dy2 = rotate_point(end_local[0], end_local[1], orientation)

    x1, y1 = x + dx1, y + dy1
    x2, y2 = x + dx2, y + dy2

    # Draw main boom/axis
    draw.line((x1, y1, x2, y2), fill=parsed["color"], width=3)

    # Axis vector in local coords
    ax = end_local[0] - start_local[0]
    ay = end_local[1] - start_local[1]

    length = math.sqrt(ax * ax + ay * ay)
    if length == 0:
        print(f"Warning: zero-length yagi axis ignored: {parsed['raw']}")
        return

    # Unit perpendicular vector
    px = -ay / length
    py = ax / length

    element_length = 22 * scale
    half_elem = element_length / 2

    # 4 evenly spaced elements
    for i in range(1, 5):
        t = i / 5.0

        cx = start_local[0] + ax * t
        cy = start_local[1] + ay * t

        ex1 = cx - px * half_elem
        ey1 = cy - py * half_elem
        ex2 = cx + px * half_elem
        ey2 = cy + py * half_elem

        rdx1, rdy1 = rotate_point(ex1, ey1, orientation)
        rdx2, rdy2 = rotate_point(ex2, ey2, orientation)

        draw.line(
            (x + rdx1, y + rdy1, x + rdx2, y + rdy2),
            fill=parsed["color"],
            width=3,
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

    # facing 0 = left
    # facing 1 = right
    flip = -1 if facing == 0 else 1

    arc_points = []

    # Left-facing default uses quadrant 3-ish visual:
    # arc spans from vertical lower point to horizontal left/right point.
    for angle in range(90, 181, 5):
        theta = math.radians(angle)

        dx = round(radius * math.cos(theta)) * flip
        dy = round(radius * math.sin(theta))

        arc_points.append((x + dx, y + dy))

    draw.line(
        arc_points,
        fill=parsed["color"],
        width=3,
    )

    # Radial support lines from hub to arc endpoints
    end1_dx = -radius * flip
    end1_dy = 0

    end2_dx = 0
    end2_dy = radius

    draw.line(
        (x, y, x + end1_dx, y + end1_dy),
        fill=parsed["color"],
        width=3,
    )

    draw.line(
        (x, y, x + end2_dx, y + end2_dy),
        fill=parsed["color"],
        width=3,
    )

    # Mast from midpoint of arc straight down
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
        width=3,
    )

    # Center hub circle
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

    # Main body
    draw.rectangle(
        (x, y, x + body_w, y + body_h),
        outline=parsed["color"],
        width=3,
    )

    # Knob
    draw.ellipse(
        (
            knob_cx - knob_radius,
            knob_cy - knob_radius,
            knob_cx + knob_radius,
            knob_cy + knob_radius,
        ),
        outline=parsed["color"],
        width=3,
    )

    # Screen
    draw.rectangle(
        (screen_x1, screen_y1, screen_x2, screen_y2),
        outline=parsed["color"],
        width=3,
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
    
#Phyton Run Stuff
def main():
    img = Image.new("RGB", CANVAS_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(img)

    commands = load_commands()

    parsed_commands = []

    for command in commands:
        parsed = parse(command)
        parsed_commands.append(parsed)

    parsed_commands = list({cmd["raw"]: cmd for cmd in parsed_commands}.values())
    parsed_commands.sort(key=lambda cmd: cmd["index"])

    for parsed in parsed_commands:
        render(parsed, draw)

    img.save("output_image.png")
    img.close()
    print("Image reconstruction complete.")


if __name__ == "__main__":
    main()
