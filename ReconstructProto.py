'''
Created on May 23, 2026

@author: Aaron Cocanower KE9ETA
'''
from PIL import Image, ImageDraw

'''
The Canvas is 720x480 or K0xDC Base-36

data structure
ICSXXXXXXXXXX
where:
I is index of instruction
C is color of instruction
S is 'Shape' or the type of instruction

X is the data spefications used to draw the image

index of instructions go from 0 to Z in base-36

Color is the index of the color to draw in, based off a predefined pallette, yet to be determined

Shape is a line, square, triangle, circle, etc or a predefined macro of those to create a more complex shape, ie Star, arrow, yagi, dish
shapes

defined data structures so far include

C:
0 Black
1 White
2 Dark Gray
3 Light Gray
4 Red

S:

0 6 char String
1 Line
2 Rectangle Outline
3 Rectangle Fill
4 Circle Outline
5 Circle Fill
6 Triangle Outline
7 Triangle Fill
8 Arrow
9 Star
A yagi antenna
B dish antenna
C Moon

Data Structures for shapes

0: 6 char string
IC0XXYY******
where XX YY are the coords on the canvas to draw the text that would fill the wild card space

1: Line
IC1XXYYxxyy**
draws a line from coords XX, YY to xx,yy * wild card spaces are unused

2: Rectangle Outline
IC2XXYYxxyy***
draws an outline Rectangle with opposite corners being coords XX, YY to xx,yy * wild card spaces are unused

3: Rectangle Fill
IC3XXYYxxyy***
draws an filled Rectangle with opposite corners being  coords XX, YY to xx,yy * wild card spaces are unused

4: Circle Outline
IC4XXYYR*****
draws a circle outline at XX, YY with Radius R

5: Circle Fill
IC5XXYYR*****
draws a filled circle at XX, YY with Radius R

6: Triangle outline
IC6XXYYVLDROS
Draws a vertex at XXYY

V and D are Axis Down how many units for two other points ( *, Y)
L and R are Axis Left and Right for for two other points ( X, *)
these points are married respective to how they are presented (V,L) (D,R)
These are vectors to be used later

O is the Orientation of the shape 0-4 starting origin vertex up, rotating 90 degress clockwise each step

S is scale, which is an integer multiplier to the vector

7: Triangle outline
IC6XXYYVLDROS
Draws a vertex at XXYY

V and D are Axis Down how many units for two other points ( *, Y)
L and R are Axis Left and Right for for two other points ( X, *)
these points are married respective to how they are presented (V,L) (D,R)
These are vectors to be used later

O is the Orientation of the shape 0-4 starting origin vertex up, rotating 90 degress clockwise each step

S is scale, which is an integer multiplier to the vector

8: Arrow
IC7XXYYOS****

Draws a solid Arrowhead at vertix XXYY, then a rectangle tail 

O is orientation, 0-4, 0 pointing upwards, each step 90 degrees clockwise
S is a scale factor
* are unused wild card values


9-B haven't been implemented yet


'''
from PIL import Image, ImageDraw

CANVAS_SIZE = (720, 480)
BACKGROUND = "white"

PALETTE = {
    0: "black",
    1: "white",
    2: "darkgray",
    3: "lightgray",
    4: "red",
}

def b36(value):
    return int(value, 36)

def b36_pair(value):
    return int(value, 36)

def load_commands():
    return [
        "3432020H05000",
        "1030000H0AF00",
        "220AAAAKE9ETA",
        "048A0A8640000",
    ]

def parse(packet):
    packet = packet.strip().upper()

    if len(packet) != 13:
        raise ValueError(f"Packet must be 13 characters, got {len(packet)}: {packet}")

    instruction_index = b36(packet[0])
    color_index = b36(packet[1])
    shape = packet[2]
    data = packet[3:13]

    color = PALETTE.get(color_index, "black")

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

    if op == "LINE":
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
        x = parsed["x"]
        y = parsed["y"]
        r = parsed["r"]

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            outline=parsed["color"],
            width=3,
        )

    elif op == "CIRCLE_FILL":
        x = parsed["x"]
        y = parsed["y"]
        r = parsed["r"]

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=parsed["color"],
        )

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

    elif op == "UNKNOWN":
        print(f"Unknown packet ignored: {parsed['raw']}")

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


if __name__ == "__main__":
    main()