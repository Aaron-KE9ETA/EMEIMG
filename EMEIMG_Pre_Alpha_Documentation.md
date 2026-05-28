# EMEIMG Pre-Alpha Documentation

Created: May 27, 2026  
Updated: May 28, 2026  
Project Stage: Pre-Alpha  
Author: Aaron Cocanower / KE9ETA

## 1. Project Overview

EMEIMG is an experimental low-bandwidth vector image protocol for QRP Earth-Moon-Earth experimentation. It encodes simple drawing instructions as JT65B-compatible 13-character text packets so a receiving station can reconstruct a simple 720x480 image from symbolic packet instructions instead of from raw raster pixel data.

The design goal is not full raster image transfer. The design goal is to send a compact, openly documented instruction set that can reconstruct a simple, recognizable image using deterministic receiver-side rendering.

EMEIMG is intended to remain openly documented, non-encrypted, and auditable. The packet format, source code, examples, and reconstruction behavior should remain public so transmitted packets can be interpreted and reconstructed by third parties.

The project treats extremely constrained digital text payloads as an abstraction layer. Instead of attempting to push a full image through JT65B-sized text messages, EMEIMG transmits compact drawing instructions that allow the receiving system to rebuild a vector-style image locally.

## 2. Pre-Alpha Purpose

Pre-Alpha development exists to move EMEIMG from a self-contained prototype into a cleaner multi-program workflow suitable for Alpha development and controlled over-the-air testing.

The Pre-Alpha goals are:

- Stabilize the packet format.
- Add protocol metadata to files.
- Separate image construction, transmission feeding, receive-side collection, and reconstruction.
- Integrate the transmit-side workflow with WSJT-X.
- Prepare documentation detailed enough that another station or developer can understand the transmitted format.
- Keep experimental behavior clearly marked as experimental before OTA use.

The planned first OTA test on July 6, 2026, starting around 0000 EDT and running to approximately 0130 EDT, is intended to mark the formal transition point from Pre-Alpha development into Alpha development, assuming the tooling and documentation are ready.

## 3. Current Pre-Alpha Status Summary

### 3.1 Constructor

Status: Added to the Pre-Alpha branch.

The Constructor is the GUI-based image design and packet export stage of the EMEIMG pipeline. It allows the user to build a simple 720x480 vector-style image layer by layer. Each visual element is encoded as a 13-character EMEIMG packet and stored in the command list.

Current Constructor behavior:

- Provides a packet-first vector image editor.
- Supports the current shape and macro command set.
- Exports `.emeimg` files.
- Uses hard-coded header metadata in the code rather than adjustable GUI header fields.
- Uses a larger startup window / maximized behavior for usability.
- Uses a two-column shape button layout.
- Uses hard-coded UI section headers.
- Does not transmit packets.
- Does not interface with WSJT-X directly.

### 3.2 Feeder

Status: Implemented as the current Pre-Alpha transmit-side bridge.

`EMEIMG-Feeder.py` loads a prepared `.emeimg` file, generates a robust transmit queue, and feeds 13-character packet text into WSJT-X using the WSJT-X UDP FreeText interface.

Current Feeder behavior:

- Requires a callsign before loading an image file.
- Loads `.emeimg` files.
- Recognizes the EMEIMG header.
- Repeats the header as priority metadata at the beginning of the queue.
- Does not place the header into the body round-robin stream.
- Generates opening station ID packets.
- Generates a round-robin body packet stream.
- Repeats normal body packets two times.
- Repeats priority body packets three times.
- Inserts recurring station ID packets after every five body queue packets.
- Appends repeated EOF packets.
- Preserves trailing spaces in 13-character packet payloads.
- Uses WSJT-X UDP FreeText messages to populate Free Text / Tx5.
- Uses `Send=False` by default.
- Provides a guarded `Send=True` option behind an explicit safety checkbox.
- Provides a Halt Tx control.
- Provides logging and log export.

### 3.3 Reader

Status: Planned.

The Reader will be the receive-side collection program. Its job will be to collect decoded EMEIMG-related text output from WSJT-X or a WSJT-X-compatible workflow and write `.emeimgout` files for the Reconstructor.

The Reader is not yet specified as final software. Its exact WSJT-X output-reading method, log parsing method, GUI behavior, and malformed-line policy remain open design areas.

### 3.4 Reconstructor

Status: Updated for Pre-Alpha metadata handling and reconstruction from received packet files.

The Reconstructor loads `.emeimgout` files, validates the file metadata header, extracts valid drawing packets, removes exact duplicates, sorts packets by instruction index, renders the packet list onto the fixed canvas, and exports a PNG.

Current intended Reconstructor behavior:

- Supports the current `EMEIMGVVPGGGG` header format.
- Reads version, patch, and grid metadata.
- Warns if the file metadata does not match the Reconstructor's expected protocol version or patch.
- Allows the user to cancel or proceed when a mismatch warning is shown.
- Warns if header metadata may not belong to the current Reconstructor version.
- Does not silently render incompatible data without warning.
- Does not crash on malformed packet lines.
- Ignores transmit-layer metadata such as station ID, EOF, `[PRIORITY]`, `[DECODED]`, and `[NO DECODE]`.

## 4. Architecture Intent

The Pre-Alpha architecture separates the workflow into distinct roles.

### 4.1 Constructor

The Constructor decides what the image is.

It creates EMEIMG packet instructions from a visual editor and exports a `.emeimg` file.

### 4.2 Feeder

The Feeder helps send the packet text.

It loads a `.emeimg` file, builds the actual transmit queue, and feeds transmit-ready text into WSJT-X.

### 4.3 WSJT-X / JT65B Operating Path

WSJT-X handles the actual JT65B transmit/decode operating workflow.

EMEIMG does not replace WSJT-X modulation, timing, decoding, or radio control. It uses WSJT-X-compatible 13-character text messages as the transport path for EMEIMG packet text.

### 4.4 Reader

The Reader helps recover the received packet text.

It is planned to collect decoded EMEIMG-related text from WSJT-X output and write `.emeimgout` files.

### 4.5 Reconstructor

The Reconstructor decides what successfully recovered data reconstructs.

It loads `.emeimgout` files, validates metadata, parses valid packets, removes duplicates, sorts by instruction index, renders the image, and saves a PNG.

## 5. General Protocol Specification

### 5.1 Canvas

The fixed reconstructed image canvas is:

```text
Width  = 720 pixels
Height = 480 pixels
```

Base-36 equivalents:

```text
Width  = K0
Height = DC
```

Valid visible coordinate range:

```text
X: 00 through JZ  -> 0 through 719 decimal
Y: 00 through DB  -> 0 through 479 decimal
```

Geometry may extend beyond the visible canvas. Off-canvas drawing should not crash the software. It may be clipped by the image library.

### 5.2 Drawing Packet Length

Every EMEIMG drawing packet is exactly 13 characters.

### 5.3 General Drawing Packet Structure

```text
ICSXXXXXXXXXX
```

Field meaning:

```text
I = instruction index / render order
C = color code
S = shape code
X = shape-specific payload data
```

Character positions:

```text
packet[0]    -> instruction index
packet[1]    -> color code
packet[2]    -> shape code
packet[3:13] -> shape-specific payload
```

### 5.4 Instruction Index

`I` is a single Base-36 character.

Valid instruction index range:

```text
0 through Z
```

This provides 36 ordered drawing instructions per image.

Packets are rendered in ascending instruction index order, regardless of file order, receive order, or transmission order.

Exact duplicate drawing packets may be removed before rendering.

### 5.5 Base-36 Encoding

Base-36 digits:

```text
0 1 2 3 4 5 6 7 8 9 A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
```

Single-character fields can represent:

```text
0 through 35 decimal
```

Two-character fields can represent:

```text
00 through ZZ
0 through 1295 decimal
```

Two-character coordinate fields such as `XX` or `YY` are decoded as one two-character Base-36 number, not as two separate digits.

### 5.6 Text Packet Preservation Rule

Shape `0` uses the final six payload characters as literal text.

Those six characters may include spaces.

File readers must not use `line.strip()` before packet parsing because that can destroy meaningful trailing spaces inside Shape `0` packets and other padded packet payloads.

Recommended line cleanup:

```python
line = line.rstrip("\r\n")
```

Avoid:

```python
line = line.strip()
```

## 6. OTA Payload vs Local Metadata

EMEIMG distinguishes between over-the-air packet payload and local tooling metadata.

A transmitted EMEIMG drawing packet is exactly 13 characters.

Local metadata tags may be appended in files or shown in tool displays, but they are not part of the transmitted 13-character packet.

### 6.1 Priority Metadata

`[PRIORITY]` is not part of the 13-character EMEIMG drawing packet.

It is local metadata used by tooling to mark important packets for transmission scheduling.

A priority-tagged command line has this structure:

```text
<13-character EMEIMG packet>[PRIORITY]
```

The Feeder must not transmit `[PRIORITY]`.

Priority status affects repeat count only.

### 6.2 Experimental Metadata

`[EXPERIMENTAL]` is not part of the 13-character EMEIMG header or drawing packet.

Experimental status is local metadata outside the transmitted packet. It is used by tools to mark development files and help prevent accidental OTA use of experimental builds.

A locally tagged header may look like:

```text
EMEIMG000EN60[EXPERIMENTAL]
```

The transmitted header remains:

```text
EMEIMG000EN60
```

The experimental flag was intentionally removed from the 13-character header format. Experimental status belongs to local tooling and file metadata, not to the over-the-air packet payload.

For Pre-Alpha development, experimental files should be treated as local test files unless deliberately promoted for controlled test use.

### 6.3 Transmission Metadata

The following are not image drawing packets:

```text
[PRIORITY]
[EXPERIMENTAL]
[DECODED]
[NO DECODE]
console labels
wrapper quotes
wrapper commas
station ID packets
EOF packets
```

Tools may recognize and display these items, but the Reconstructor must not interpret them as image geometry.

## 7. Pre-Alpha Metadata Header

Pre-Alpha uses a 13-character protocol metadata header so tools can identify the EMEIMG protocol version, patch level, and transmitting grid square associated with a file.

### 7.1 Header Format

```text
EMEIMGVVPGGGG
```

Field meaning:

```text
EMEIMG = fixed identifier string
VV     = protocol version number, encoded as two Base-36 digits
P      = protocol patch number, encoded as one Base-36 digit
GGGG   = 4-character Maidenhead grid square
```

Character positions:

```text
header[0:6]   -> EMEIMG identifier
header[6:8]   -> VV version field
header[8]     -> P patch field
header[9:13]  -> GGGG grid square field
```

Current Pre-Alpha example:

```text
EMEIMG000EN60
```

Interpreted as:

```text
EMEIMG = EMEIMG header identifier
VV     = 00
P      = 0
GGGG   = EN60
```

### 7.2 Header Notes

The old header format is superseded:

```text
EMEIMGVVPE***
```

That older format contained an experimental flag and reserved spare characters. It should no longer be used as the current Pre-Alpha header format.

The current header uses the final four characters for grid transparency.

The experimental flag is local metadata only and should not be encoded into the 13-character OTA header.

### 7.3 Grid Field

`GGGG` is a four-character Maidenhead grid square.

Examples:

```text
EN60
EN70
FN20
```

The grid field provides telemetry transparency. It helps identify the general grid associated with the EMEIMG file or transmission without adding separate packet overhead.

Invalid or unrecognized grid values should trigger a warning.

### 7.4 Version and Patch Compatibility

The Reconstructor stores its own expected protocol version and patch number.

Before reconstruction, it compares the file header against its own expected version and patch.

Expected behavior:

1. If the header matches the Reconstructor version and patch, reconstruction may proceed normally.
2. If the header is valid but the version or patch does not match, the Reconstructor should show a warning popup.
3. The warning should explain that the file was created for a different EMEIMG version or patch and that rendering may be incorrect.
4. The user should be given `Cancel` and `Proceed` options.
5. If the user cancels, reconstruction stops.
6. If the user proceeds, the Reconstructor attempts to render using the current parser.

This policy allows development-time inspection of older or mismatched files without silently hiding compatibility risk.

## 8. File Types

### 8.1 `.emeimg`

Constructor output file.

The `.emeimg` file contains the EMEIMG metadata header plus drawing packet lines.

Typical structure:

```text
EMEIMG000EN60[EXPERIMENTAL]
<13-character EMEIMG packet>
<13-character EMEIMG packet>[PRIORITY]
<13-character EMEIMG packet>
```

Notes:

- The first line should be the EMEIMG header.
- `[EXPERIMENTAL]` may be appended as local metadata.
- `[PRIORITY]` may be appended to body packets as local metadata.
- Local metadata tags are not transmitted as packet payload.
- The Feeder strips recognized local metadata before validating and queueing the 13-character payload.

### 8.2 `.emeimgout`

Receiver-side / reconstruction input file.

The `.emeimgout` file is created from received or recovered packet text. In the final architecture, this will be created by the Reader.

Accepted structures may include plain packet lines or compatibility wrappers.

Examples:

```text
EMEIMG000EN60
0720000JZ811 
142006MJZDB1 
20AGB7L01    
```

Prototype-compatible wrapped lines may also be tolerated:

```text
"EMEIMG000EN60",
"0720000JZ811 ",
"142006MJZDB1 ",
"20AGB7L01    ",
```

Notes:

- Wrapper quotes and commas are not part of the packet.
- Station ID packets are not drawing packets.
- EOF packets are not drawing packets.
- Decode status tags are not drawing packets.
- The Reconstructor extracts recoverable 13-character header and body packets.

### 8.3 `.png`

Reconstructor output image.

The Reconstructor exports the final visible reconstructed image as a PNG file.

## 9. Color Codes

The color code is the second character in an EMEIMG drawing packet.

```text
0 = Black
1 = White
2 = Gray
3 = Red
4 = Green
5 = Blue
6 = Yellow
7 = Cyan
8 = Magenta
9 = Brown
A = Tan
B = Beige
C = Wheat
D = Sandybrown
E = Sienna
F = Chocolate
G = Gold
H = Crimson
I = Indigo
J = Hotpink
K = Orange
L = Purple
M = Lime
N = Aliceblue
O = Ivory
P = Lavender
Q = Mistyrose
R = Papayawhip
S = Seashell
T = Silver
U = Lightgray
V = Darkslategray
W = Dimgray
X-Z = Reserved / unused
```

Example:

```text
I C S XXXXXXXXXX
  ^
  color code
```

Reserved color values should not crash the renderer.

Recommended behavior:

```text
warn -> ignore packet or fall back to a safe default color -> continue
```

## 10. Shape Code Quick Reference

The shape code is the third character in an EMEIMG drawing packet.

```text
0 = 6-character string
1 = Line
2 = Rectangle
3 = Ellipse
4 = Triangle Outline
5 = Triangle Fill
6 = Arrow
7 = Star
8 = SemiCircle / Arc
9 = Yagi Antenna
A = Dish Antenna
B = Radio Transceiver
C = Radio Waves
D = Moon
E = DoubleBox
F-Z = Reserved / unused
```

Example:

```text
I C S XXXXXXXXXX
    ^
    shape code
```

Reserved shape values must not crash the Reconstructor.

Recommended behavior:

```text
warn -> ignore packet -> continue
```

## 11. Shape Packet Formats

### 11.1 Shape 0: 6-Character String

Format:

```text
IC0XXYY******
```

Fields:

```text
XX,YY  = text origin point
****** = six literal text characters
```

Behavior:

Draws a six-character text string at coordinate `XX,YY`.

Important:

- The text field may contain spaces.
- Do not strip trailing packet spaces before parsing.
- Constructor preview and Reconstructor rendering may not be perfectly 1:1 if different font rendering methods are used.

### 11.2 Shape 1: Line

Format:

```text
IC1XXYYxxyy**
```

Fields:

```text
XX,YY = first endpoint
xx,yy = second endpoint
**    = unused wildcard values
```

Behavior:

Draws a line from `XX,YY` to `xx,yy`.

### 11.3 Shape 2: Rectangle

Format:

```text
IC2XXYYxxyyF*
```

Fields:

```text
XX,YY = first corner
xx,yy = opposite corner
F     = fill flag
        0 = outline
        1 = filled
*     = unused wildcard value
```

Behavior:

Draws a rectangle using `XX,YY` and `xx,yy` as opposite corners.

Shape 2 replaces the earlier separate rectangle-outline and rectangle-fill split. Rectangle outline and fill are now selected using the `F` fill flag.

### 11.4 Shape 3: Ellipse

Format:

```text
IC3XXYYRrSF**
```

Fields:

```text
XX,YY = center point
R     = vertical radius
r     = horizontal radius
S     = scale factor
F     = fill flag
        0 = outline
        1 = filled
**    = unused wildcard values
```

Behavior:

Draws an ellipse centered at `XX,YY`.

Rendered radii:

```text
vertical radius   = R * S
horizontal radius = r * S
```

### 11.5 Shape 4: Triangle Outline

Format:

```text
IC4XXYYVLDROS
```

Fields:

```text
XX,YY = origin vertex
V     = downward vector for point 1
L     = leftward vector for point 1
D     = downward vector for point 2
R     = rightward vector for point 2
O     = orientation
S     = scale factor
```

Behavior:

Draws an outlined triangle.

Geometry before rotation and scaling:

```text
origin  = (XX, YY)
point 1 = (XX - L, YY + V)
point 2 = (XX + R, YY + D)
```

Orientation:

```text
0 = default
1 = 90 degrees clockwise
2 = 180 degrees
3 = 270 degrees clockwise
```

### 11.6 Shape 5: Triangle Fill

Format:

```text
IC5XXYYVLDROS
```

Fields:

Same fields as Shape 4.

Behavior:

Uses the same geometry as Shape 4, but draws a filled triangle.

### 11.7 Shape 6: Arrow

Format:

```text
IC6XXYYOS****
```

Fields:

```text
XX,YY = arrow tip / vertex
O     = orientation
S     = scale factor
****  = unused wildcard values
```

Behavior:

Draws a solid arrowhead at `XX,YY`, then draws a rectangular tail behind it.

Orientation:

```text
0 = points upward
1 = points right
2 = points downward
3 = points left
```

The old `R` arrow-size field is no longer used. Arrow size is controlled through the `S` scale factor.

### 11.8 Shape 7: Star

Format:

```text
IC7XXYYRS****
```

Fields:

```text
XX,YY = center point
R     = radius
S     = scale factor
****  = unused wildcard values
```

Behavior:

Draws a four-line star centered at `XX,YY`.

The star consists of:

```text
vertical line
horizontal line
diagonal NE/SW line
diagonal NW/SE line
```

Rendered radius:

```text
R * S
```

### 11.9 Shape 8: SemiCircle / Arc

Format:

```text
IC8XXYYRSOODD
```

Fields:

```text
XX,YY = center point
R     = radius
S     = scale factor
OO    = start angle in degrees, stored as two-character Base-36
DD    = angular distance in degrees, stored as two-character Base-36
```

Behavior:

Draws an arc centered at `XX,YY`.

Angle convention:

```text
0 degrees   = points directly right
90 degrees  = points upward
180 degrees = points left
270 degrees = points downward
```

Angles increase counterclockwise.

Common angle encodings:

```text
90 degrees  = 2I in Base-36
180 degrees = 50 in Base-36
270 degrees = 7I in Base-36
360 degrees = A0 in Base-36
```

### 11.10 Shape 9: Yagi Antenna

Format:

```text
IC9XXYYOS****
```

Fields:

```text
XX,YY = macro origin point
O     = orientation
S     = scale factor
****  = unused wildcard values
```

Behavior:

Draws a Yagi antenna macro.

Default geometry:

- Uses a diagonal boom.
- Draws several perpendicular elements spaced along the boom.
- Uses scale factor `S` to multiply the default macro size.

Orientation:

```text
0 = default
1 = 90 degrees clockwise
2 = 180 degrees
3 = 270 degrees clockwise
```

### 11.11 Shape A: Dish Antenna

Format:

```text
ICAXXYYOS****
```

Fields:

```text
XX,YY = dish center / origin point
O     = facing direction
S     = scale factor
****  = unused wildcard values
```

Behavior:

Draws a dish antenna macro.

Facing direction:

```text
0 = dish faces left
1 = dish faces right
```

The dish macro orientation is a left/right facing flip only.

### 11.12 Shape B: Radio Transceiver

Format:

```text
ICBXXYYS*****
```

Fields:

```text
XX,YY = macro origin point
S     = scale factor
***** = unused wildcard values
```

Behavior:

Draws a radio transceiver macro.

Notes:

The main radio body uses `XX,YY` as its top-left corner.

### 11.13 Shape C: Radio Waves

Format:

```text
ICCXXYYRSOODD
```

Fields:

```text
XX,YY = center point
R     = radius of first wave
S     = scale factor
OO    = start angle in degrees, stored as two-character Base-36
DD    = angular distance in degrees, stored as two-character Base-36
```

Behavior:

Draws three concentric arc segments centered at `XX,YY`.

Rendered wave radii:

```text
1 * R * S
3 * R * S
5 * R * S
```

### 11.14 Shape D: Moon

Format:

```text
ICDXXYYSK****
```

Fields:

```text
XX,YY = center point
S     = scale factor
K     = crater color
****  = unused wildcard values
```

Behavior:

Draws a filled moon centered at `XX,YY`.

Moon body:

```text
uses packet color C
```

Rendered moon radius:

```text
36 * S
```

Craters:

Draws deterministic outlined crater circles using crater color `K`.

Stretch goal:

Crescent Moon rendering is a stretch goal and is not required for the initial Moon macro implementation.

### 11.15 Shape E: DoubleBox

Format:

```text
ICEXXYYxxyyPP
```

Fields:

```text
XX,YY = first corner
xx,yy = opposite corner
PP    = percentage split position from the top, stored as two-character Base-36
```

Behavior:

Draws an outlined rectangle, then draws a horizontal divider line across the rectangle.

`PP` handling:

```text
1. Decode PP as a two-character Base-36 number.
2. Clamp the decoded value to 0 through 100 decimal.
3. Place the divider line P percent down from the top of the box.
```

Common percentage encodings:

```text
0%   = 00 in Base-36
25%  = 0P in Base-36
50%  = 1E in Base-36
75%  = 23 in Base-36
100% = 2S in Base-36
```

Important:

DoubleBox uses a two-character percentage field. A one-character percentage field is not sufficient for directly representing 0 through 100.

## 12. Constructor Documentation

### 12.1 Purpose

The Constructor is the image creation and `.emeimg` export tool.

It provides a GUI-based packet-first vector editor for building simple EMEIMG images as ordered JT65B-compatible drawing commands.

Users select colors, shapes, macro elements, and command parameters, then place elements onto the fixed 720x480 canvas. Each visual element is encoded as a 13-character EMEIMG packet and stored as a layer in the command list.

### 12.2 Current Constructor Role

The Constructor is responsible for:

1. Designing a simple vector-style EMEIMG image.
2. Encoding each image element as a packet command.
3. Managing command order / layers.
4. Marking critical or priority elements when needed.
5. Exporting the resulting `.emeimg` command file.
6. Supplying the input file used by the Feeder stage.

The Constructor does not:

- Transmit packets.
- Control WSJT-X.
- Receive decoded output.
- Reconstruct `.emeimgout` files.
- Schedule live transmissions.

### 12.3 Header Handling

Header metadata is hard-coded into the Constructor code and is not adjustable through GUI fields.

Current header format:

```text
EMEIMGVVPGGGG
```

Current example:

```text
EMEIMG000EN60
```

The intended design keeps version/header handling consistent with the Pre-Alpha pipeline while avoiding unnecessary controls in the GUI.

### 12.4 UI Updates

The Constructor UI has been updated for the Pre-Alpha branch to better support the expanded command set.

Current UI changes include:

- Maximized startup behavior instead of forced fullscreen.
- Normal desktop window controls are preserved.
- Larger fallback window geometry for systems that do not support maximize requests.
- Shape selection is organized as a two-column button list.
- Hard-coded section headers organize the interface.
- Header metadata is handled internally by code and is not adjustable through the GUI.

These changes are intended to make the Constructor more usable as the number of supported shapes, macros, and command options increases.

## 13. Feeder Documentation

### 13.1 Overview

`EMEIMG-Feeder.py` is the Pre-Alpha feeder module for the EMEIMG project.

Its role is to take a prepared `.emeimg` image instruction file, generate a robust transmit queue, and feed each 13-character packet into WSJT-X through the WSJT-X UDP interface.

The feeder acts as the transmit-side bridge between the EMEIMG packet file format and WSJT-X's Free Text / Tx5 message field.

The feeder does not reconstruct images and does not generate EMEIMG drawing commands. Those responsibilities belong to the Constructor and Reconstructor modules.

### 13.2 Purpose

The purpose of `EMEIMG-Feeder.py` is to automate the process of loading EMEIMG packets into WSJT-X in a controlled and repeatable way.

Manually copying each packet into WSJT-X would be error-prone and impractical for a full image transmission, especially when testing repeat counts, priority packets, round-robin ordering, and long-duration transmission behavior.

The feeder reduces that friction by creating a complete transmit queue and then loading packets into WSJT-X one at a time.

The feeder is not intended to be a fully unattended transmitter. In the current Pre-Alpha design, the feeder can automatically advance and load the next packet into WSJT-X every two minutes, but the operator remains responsible for station control, operating practice, frequency monitoring, legal compliance, and ensuring that transmissions are appropriate.

### 13.3 WSJT-X Integration

`EMEIMG-Feeder.py` communicates with WSJT-X using the WSJT-X UDP interface.

The feeder acts as the UDP server that WSJT-X reports to. Once WSJT-X sends heartbeat or status messages to the feeder, the feeder learns the WSJT-X instance ID and return UDP address. The feeder can then send FreeText messages back to WSJT-X.

The feeder uses the WSJT-X `FreeText` UDP message type to populate the WSJT-X Free Text / Tx5 field.

In normal Pre-Alpha operation, the feeder sends FreeText with `Send=False`. This means the packet is loaded into WSJT-X, but the feeder does not request WSJT-X to begin transmission automatically.

A separate `Send=True` path exists behind an explicit GUI safety checkbox. This is included for testing but is not the default operating model.

### 13.4 Required WSJT-X Configuration

Recommended local WSJT-X settings:

```text
UDP Server: 127.0.0.1
UDP Server port number: 2237
Accept UDP requests: enabled
```

The feeder should be started and the UDP listener should be running before relying on WSJT-X status or FreeText control.

A successful connection is indicated by heartbeat and/or status messages appearing in the feeder log.

If the feeder does not show heartbeat or status activity, it has not established UDP communication with WSJT-X.

### 13.5 Callsign Requirement

A callsign must be entered before loading an `.emeimg` file.

This is intentional. The feeder generates transmit-layer station identification packets from the callsign, and those packets are required as part of the current Pre-Alpha transmit structure.

The callsign is normalized to uppercase and validated before the file is loaded.

Current callsign validation expects a simple 3 to 6 character alphanumeric callsign. This fits the current 13-character Free Text packet structure when combined with the `EMEIMG` or `EOF73` suffix.

Examples:

```text
KE9ETA EMEIMG
KE9ETA EOF73
```

Both are padded internally to 13 characters for Free Text handling.

### 13.6 Transmit Queue Structure

When an `.emeimg` file is loaded, the feeder does not transmit the file line-by-line.

Instead, it generates a final transmit queue using this structure:

```text
3x [CALLSIGN] EMEIMG
3x EMEIMG header packet
round-robin body packet stream
[CALLSIGN] EMEIMG inserted after every 5 body queue packets
5x [CALLSIGN] EOF73
```

This structure is designed to improve recoverability, transparency, and receiver-side confidence.

The opening callsign packets identify the source and purpose of the transmission before image packet data begins.

The repeated EMEIMG header provides important protocol metadata multiple times before body packet decoding begins.

The body packet stream is round-robin scheduled to avoid putting all repeats of the same packet next to each other.

The recurring station ID packets ensure that long transmissions continue to carry station identification within the transmit stream.

The EOF packets are repeated five times because end-of-file detection is considered critical to receiver-side reconstruction and confidence.

### 13.7 Opening Station ID Packets

The feeder begins each generated transmit queue with three station identification packets.

Format:

```text
[CALLSIGN] EMEIMG
```

Example:

```text
KE9ETA EMEIMG
```

This packet is padded to 13 characters internally.

These opening packets are not read from the `.emeimg` file. They are generated by the feeder at load time using the callsign entered in the GUI.

The opening station ID packets serve as a clear preamble that the following transmission is an EMEIMG transmission.

### 13.8 Header Packet Handling

The `.emeimg` file contains an EMEIMG header packet.

Example:

```text
EMEIMG000EN60
```

The header contains protocol metadata and grid information.

The header is not treated as a normal body packet.

The feeder repeats the header three times immediately after the opening station ID packets.

The header is intentionally not included in the body packet round-robin stream.

This behavior ensures that the receiver has multiple early chances to recover the protocol header before body packets are processed.

Current opening structure:

```text
KE9ETA EMEIMG
KE9ETA EMEIMG
KE9ETA EMEIMG
EMEIMG000EN60
EMEIMG000EN60
EMEIMG000EN60
```

Important:

The header must not be round-robin scheduled with body packets. Header repetition belongs in the preamble, not in the body packet stream.

### 13.9 Body Packet Handling

All non-header image packets from the `.emeimg` file are treated as body packets.

Body packets are placed into a round-robin transmit queue.

Current repeat policy:

```text
Normal body packet:   2 transmissions
Priority body packet: 3 transmissions
```

The round-robin system avoids grouped repeats.

Instead of transmitting a packet twice or three times in a row, the feeder transmits all first-pass packets, then all second-pass packets, then any third-pass priority packets.

Example source packets:

```text
A normal
B priority
C normal
```

Generated body queue:

```text
A pass 1
B pass 1
C pass 1
A pass 2
B pass 2
C pass 2
B pass 3
```

This improves robustness during short decode outages. If a receiver misses a short block of transmissions, it is less likely to lose all repeats of the same packet.

### 13.10 Priority Packet Handling

Priority packets are marked in the `.emeimg` file using local metadata:

```text
[PRIORITY]
```

Example:

```text
142006MJZDB1 [PRIORITY]
```

The `[PRIORITY]` tag is not transmitted as part of the packet.

Priority packets are included in the round-robin body queue three times instead of two.

Priority status affects only transmit scheduling.

### 13.11 Experimental Metadata Handling

The `.emeimg` header line may include local experimental metadata:

```text
[EXPERIMENTAL]
```

Example:

```text
EMEIMG000EN60[EXPERIMENTAL]
```

The `[EXPERIMENTAL]` tag is not transmitted as part of the packet.

Experimental metadata is local only. The transmitted header remains the 13-character EMEIMG header:

```text
EMEIMG000EN60
```

Experimental metadata should be used by tools to clearly identify development files and reduce the chance of accidental OTA transmission of an experimental build.

### 13.12 Recurring Station ID Insertion

After the opening station ID and header preamble, the feeder inserts a station ID packet after every five body queue packets.

The recurring station ID format is the same as the opening station ID:

```text
[CALLSIGN] EMEIMG
```

Example:

```text
KE9ETA EMEIMG
```

This packet is inserted by the feeder and is not part of the `.emeimg` file.

Example body stream with station ID interval of five:

```text
Body packet 1
Body packet 2
Body packet 3
Body packet 4
Body packet 5
KE9ETA EMEIMG
Body packet 6
Body packet 7
Body packet 8
Body packet 9
Body packet 10
KE9ETA EMEIMG
```

This provides regular identification and context during long transmissions.

### 13.13 EOF Packet Handling

At the end of the transmit queue, the feeder appends five EOF packets.

Format:

```text
[CALLSIGN] EOF73
```

Example:

```text
KE9ETA EOF73
```

The EOF packet is padded internally to 13 characters.

EOF is repeated five times because it is a critical marker. The receiver needs a strong chance of detecting that the image transmission has ended. Missing EOF could leave the receiver unsure whether more packets are still expected.

The EOF packet is not part of the `.emeimg` file. It is generated by the feeder as transmit-layer control data.

Final queue ending:

```text
KE9ETA EOF73
KE9ETA EOF73
KE9ETA EOF73
KE9ETA EOF73
KE9ETA EOF73
```

### 13.14 Packet Padding and Display

EMEIMG packets are designed around 13-character Free Text payloads.

Some packets may contain trailing spaces as meaningful padding. The feeder preserves these spaces when sending packets to WSJT-X.

In the packet queue display, spaces may be shown using a visible placeholder such as:

```text
·
```

This is only for GUI readability. The placeholder is not transmitted. The actual packet still contains spaces.

Example displayed packet:

```text
20AGB7L01····
```

Actual transmitted packet:

```text
20AGB7L01    
```

This distinction matters because stripping trailing spaces can corrupt the intended 13-character packet format.

### 13.15 Auto-Feed Operation

The feeder includes an Auto-Feed mode.

Auto-Feed allows the operator to press one button and have the feeder load the next queued packet into WSJT-X every two minutes.

Auto-Feed behavior:

```text
1. Load current queue packet into WSJT-X Free Text / Tx5.
2. Advance to the next queue item.
3. Wait two minutes.
4. Repeat until the queue is complete.
```

Auto-Feed uses `Send=False` by default. This means it updates the WSJT-X Free Text field but does not force WSJT-X to transmit.

This design allows the operator to keep normal control of WSJT-X transmit enablement while reducing the burden of manually loading each packet.

Auto-Feed stops automatically when the end of the queue is reached. It can also be stopped manually.

### 13.16 Manual Feed Operation

The feeder also supports manual packet loading.

Manual controls include:

```text
Previous Packet
Next Packet
Load Current into WSJT-X
Load Current, Then Advance
```

Manual mode is useful for early testing, debugging, and confirming WSJT-X behavior before using Auto-Feed.

The recommended first test is to load a file, select the first queue item, and use `Load Current into WSJT-X` while watching the WSJT-X Free Text / Tx5 field.

### 13.17 Send=True Safety Gate

The feeder includes an optional `Send=True` FreeText mode.

This mode is disabled by default and requires an explicit checkbox before use.

The purpose of this safety gate is to prevent accidental transmit requests during testing.

Normal Pre-Alpha operation should use `Send=False`, allowing the feeder to populate WSJT-X while the operator remains responsible for transmit control.

The `Send=True` path should be tested only in a controlled local test environment before any OTA use.

### 13.18 Halt Tx Control

The feeder includes a Halt Tx button.

This sends a WSJT-X UDP HaltTx request to the observed WSJT-X peer.

The Halt Tx feature is intended as a safety and convenience control during testing.

It does not replace normal operator responsibility. The operator should still monitor WSJT-X, radio state, PTT behavior, and RF output directly.

### 13.19 Logging

The feeder logs important activity to the GUI log panel.

Logged events may include:

```text
UDP listener start / stop
WSJT-X heartbeat / status messages
Loaded file path
Rejected file lines
Generated queue size
Station ID insertion count
EOF count
FreeText send attempts
Auto-Feed start / stop events
Queue completion
UDP parse warnings
```

The log can be exported for test records.

Maintaining logs is recommended during Pre-Alpha testing because EMEIMG transmissions may last a long time and involve many repeated packets.

### 13.20 Rejected Lines

When loading an `.emeimg` file, the feeder rejects lines that cannot be normalized into valid 13-character packet payloads.

Common reasons for rejection include:

```text
unsupported characters
packet too long after metadata removal
malformed local metadata tags
unexpected text lines
invalid header
invalid body packet length
```

Blank lines and comment lines may be ignored.

Trailing spaces are preserved when needed.

The feeder strips recognized local metadata tags such as `[PRIORITY]` and `[EXPERIMENTAL]` before validating the actual packet payload.

### 13.21 Current Repeat Policy

Current Pre-Alpha repeat policy:

```text
Opening station ID:       3 transmissions
Header packet:            3 transmissions
Normal body packet:       2 transmissions
Priority body packet:     3 transmissions
Recurring station ID:     after every 5 body queue packets
EOF packet:               5 transmissions
```

This policy is designed for robustness rather than maximum speed.

The repeat policy may be revised during Alpha testing after practical decode-loss data is collected.

### 13.22 Example Queue Structure

Given a callsign of:

```text
KE9ETA
```

and a source `.emeimg` file containing:

```text
EMEIMG000EN60[EXPERIMENTAL]
0720000JZ811 
142006MJZDB1 [PRIORITY]
20AGB7L01    
30BGJ9501    
```

The feeder generates a queue shaped like:

```text
KE9ETA EMEIMG
KE9ETA EMEIMG
KE9ETA EMEIMG

EMEIMG000EN60
EMEIMG000EN60
EMEIMG000EN60

0720000JZ811 
142006MJZDB1 
20AGB7L01    
30BGJ9501    
0720000JZ811 

KE9ETA EMEIMG

142006MJZDB1 
20AGB7L01    
30BGJ9501    
142006MJZDB1 

KE9ETA EOF73
KE9ETA EOF73
KE9ETA EOF73
KE9ETA EOF73
KE9ETA EOF73
```

The exact queue depends on the number of body packets and which packets are marked priority.

## 14. Reader Documentation

### 14.1 Status

The Reader is planned but not yet finalized.

### 14.2 Purpose

The Reader is intended to be a separate receive-side program that collects decoded EMEIMG text output and creates `.emeimgout` files for the Reconstructor.

### 14.3 Planned Features

Planned Reader features:

- Receive or collect decoded text output from the operating workflow.
- Identify EMEIMG metadata and drawing packet lines.
- Identify station ID and EOF control messages.
- Preserve successfully recovered 13-character drawing packets.
- Preserve or recover the EMEIMG header.
- Write a `.emeimgout` file for the Reconstructor.
- Include metadata needed for Reconstructor version and patch validation.
- Avoid corrupting trailing spaces in packet payloads.

### 14.4 Not Yet Specified

The following Reader behavior is not yet finalized and should not be documented as implemented:

- Exact WSJT-X output reading method.
- Exact log parsing method.
- Exact GUI or command-line interface.
- Exact duplicate packet handling.
- Exact station/session handling.
- Exact malformed-line handling.
- Exact `.emeimgout` line formatting beyond Reconstructor compatibility requirements.

## 15. Reconstructor Documentation

### 15.1 Purpose

The Reconstructor rebuilds a final EMEIMG image from received or loaded EMEIMG packet data.

The Reconstructor does not create image geometry interactively.

It reads packet strings, validates file metadata, parses valid drawing packets, sorts them by instruction index, removes exact duplicates when appropriate, renders the image onto the fixed EMEIMG canvas, and saves the reconstructed image as a PNG file.

### 15.2 Accepted Input

The Reconstructor loads `.emeimgout` files.

Accepted line types may include:

```text
EMEIMGVVPGGGG
<13-character EMEIMG packet>
<13-character EMEIMG packet>[PRIORITY]
"PACKET",
[DECODED] PACKET
```

The Reconstructor should extract valid 13-character packet payloads from supported wrapper formats where possible.

### 15.3 Ignored Non-Image Data

The Reconstructor should not render:

```text
metadata wrappers
station ID packets
closing EOF / EOF73 packets
console labels
[DECODED]
[NO DECODE]
[PRIORITY]
[EXPERIMENTAL]
wrapper quotes
wrapper commas
```

### 15.4 Metadata Validation

The Reconstructor reads the metadata header from the `.emeimgout` file.

Expected current header format:

```text
EMEIMGVVPGGGG
```

Current example:

```text
EMEIMG000EN60
```

The Reconstructor compares:

```text
file VV against Reconstructor expected VV
file P  against Reconstructor expected P
```

If either the version or patch number does not match, the Reconstructor should warn the user.

The intended warning behavior is:

```text
This file was created for a different EMEIMG version or patch.
Rendering with this Reconstructor may cause errors or incorrect output.
Cancel or Proceed?
```

If the user selects `Cancel`, reconstruction stops.

If the user selects `Proceed`, reconstruction continues using the current parser.

### 15.5 Invalid Header Behavior

If the header is malformed, the Reconstructor should not crash.

Recommended behavior:

1. Display a warning explaining what is invalid.
2. Explain that rendering may fail or produce incorrect output.
3. Allow the user to cancel or proceed if enough packet data is still recoverable.
4. Continue only if the user explicitly proceeds.

Malformed header examples:

```text
EMEIMG0000***
EMEIMG0000***
EMEIMG0000
EMEIMG0000***
EMEIMG0000***
```

The older `EMEIMGVVPE***` format is no longer current. A file using the old header format should be treated as mismatched or legacy metadata.

### 15.6 Packet Handling

Each EMEIMG drawing packet is exactly 13 characters.

Packet format:

```text
ICSXXXXXXXXXX
```

Parser indexing:

```text
packet[0]    -> instruction index
packet[1]    -> color code
packet[2]    -> shape code
packet[3:13] -> shape-specific payload
```

### 15.7 Invalid Packet Behavior

Invalid packets must not crash the Reconstructor.

Recommended behavior:

```text
1. Print or display a warning.
2. Convert the packet into a VOID / no-op instruction or skip it.
3. Continue processing the remaining packets.
```

### 15.8 Unknown Shape Behavior

If a packet has valid length but uses an unknown or reserved shape code, the Reconstructor should not crash.

Recommended behavior:

```text
unknown shape -> warn -> ignore packet -> continue
```

### 15.9 Duplicate Packet Handling

Exact duplicate packets may appear because packets may be transmitted or recovered more than once.

The Reconstructor may remove exact duplicates before rendering.

Duplicate removal should compare the recovered 13-character drawing packet itself, not metadata or wrapper text.

### 15.10 Render Order

Packets are rendered by instruction index `I`, not by receive order or file order.

Recommended process:

```text
1. Load `.emeimgout` file.
2. Read and validate metadata header.
3. Remove metadata / wrappers from packet lines.
4. Recover 13-character drawing packets.
5. Remove exact duplicate drawing packets.
6. Parse packets.
7. Sort parsed packets by instruction index.
8. Render sorted packets to the canvas.
9. Save the output PNG.
```

### 15.11 Rendering Behavior

Rendering should be deterministic.

The same valid packet list and metadata should always produce the same output image.

The Reconstructor should not use random placement, random colors, or random geometry.

### 15.12 Reconstructor Should Not

The Reconstructor should not:

- Create new image geometry.
- Assign instruction indexes.
- Edit packet layers.
- Schedule transmissions.
- Control WSJT-X.
- Receive WSJT-X output.
- Transmit packets.
- Act as the Reader.

## 16. End-to-End Workflow

### 16.1 Build Image in Constructor

The user creates an image layer by layer using the Constructor.

Each visual element is encoded as a 13-character EMEIMG packet.

### 16.2 Export `.emeimg`

The Constructor exports the EMEIMG header and drawing packet lines.

The `.emeimg` file may include local metadata such as `[PRIORITY]` or `[EXPERIMENTAL]`.

### 16.3 Load `.emeimg` in Feeder

The Feeder loads the `.emeimg` file.

It validates packet payloads, strips local-only metadata, and builds a transmit queue.

### 16.4 Feed Packets to WSJT-X

The Feeder uses WSJT-X UDP FreeText messages to load each queue item into Free Text / Tx5.

Default behavior uses `Send=False`.

### 16.5 Transmit / Decode Through WSJT-X Operating Path

WSJT-X handles the JT65B transmit and decode workflow.

The operator remains responsible for transmit control, station identification, frequency monitoring, and legal operation.

### 16.6 Collect Received Packets Through Reader

The planned Reader collects decoded output and writes `.emeimgout` files.

Until the Reader is implemented, `.emeimgout` files may be created through a temporary or manual workflow.

### 16.7 Load `.emeimgout` in Reconstructor

The Reconstructor validates the metadata header, checks version and patch compatibility, extracts drawing packets, removes duplicates, parses geometry, sorts by instruction index, and renders the image.

### 16.8 Export PNG

The Reconstructor saves the final visible image as a PNG.

## 17. Implementation Notes

### 17.1 Parser Safety

Invalid packets should not crash any program.

Recommended behavior:

```text
bad packet -> warn -> return / skip VOID -> continue
```

### 17.2 Line Reading

Packet parsing should preserve literal spaces.

When reading packets from a file, remove newline characters only.

Recommended:

```python
line = line.rstrip("\r\n")
```

Avoid:

```python
line = line.strip()
```

### 17.3 Reserved Codes

Reserved colors and shapes should be handled gracefully.

Recommended behavior:

```text
warn -> ignore packet or use safe fallback -> continue
```

### 17.4 Zero Scale / Radius

Shape renderers should check for invalid zero or negative scale / radius values.

Recommended behavior:

```text
warn -> skip that shape -> continue
```

### 17.5 Determinism

Rendering must be deterministic.

Constructor preview and Reconstructor output should not depend on random values.

### 17.6 Deduplication

Deduplication should happen after metadata and wrapper removal.

Compare the exact recovered 13-character drawing packet.

### 17.7 Metadata Versioning

Compatibility-sensitive packet changes should increment the protocol version or patch number.

Examples of compatibility-sensitive changes:

- Changing a packet field meaning.
- Changing a shape's packet layout.
- Changing the header format.
- Changing color code definitions.
- Changing shape code assignments.
- Changing parser expectations in a way that older files may render differently.

### 17.8 Constructor / Reconstructor Preview Differences

The Constructor should aim to make previews as close to Reconstructor output as practical.

However, exact 1:1 preview and output may be difficult if the Constructor GUI renderer and Reconstructor image renderer use different font engines or drawing primitives.

Where possible, rendering math should be shared or mirrored between Constructor and Reconstructor to reduce surprises.

## 18. Pre-Alpha Safety Notes

`EMEIMG-Feeder.py` is a Pre-Alpha development tool.

It should be treated as experimental software.

Before any OTA use, the operator should verify:

```text
correct WSJT-X mode
correct frequency
correct audio routing
correct PTT behavior
correct callsign
correct packet queue
correct header packet
correct station identification behavior
correct EOF behavior
correct transmit enable state
local legality and band-plan appropriateness
```

The feeder is intended to support transparent, documented amateur-radio experimentation.

It is not intended to obscure meaning, encrypt traffic, or transmit undocumented payloads.

The EMEIMG protocol, packet format, source code, and reconstruction tools should remain publicly documented so that transmissions can be interpreted by others.

## 19. Recommended Local Feeder Test Procedure

Recommended local test procedure:

```text
1. Start WSJT-X.
2. Configure WSJT-X UDP reporting.
3. Start EMEIMG-Feeder.py.
4. Click Start Listener.
5. Confirm heartbeat / status messages appear.
6. Enter callsign.
7. Load an `.emeimg` file.
8. Confirm the generated transmit queue looks correct.
9. Confirm the header appears in the preamble, not in the body round-robin stream.
10. Use Load Current into WSJT-X.
11. Confirm WSJT-X Free Text / Tx5 updates.
12. Test Load Current, Then Advance.
13. Test Auto-Feed locally with transmit disabled.
14. Confirm packets advance every two minutes.
15. Confirm trailing spaces are preserved.
16. Export the feeder log.
17. Only after local validation, consider controlled OTA testing.
```

For early testing, transmit should remain disabled until WSJT-X field population and queue advancement behavior are confirmed.

## 20. Current Known Limitations

Current known limitations:

- The Reader is not yet finalized.
- The GUI assumes a local WSJT-X instance by default.
- Callsign validation is intentionally simple.
- The Feeder does not decode received WSJT-X messages into `.emeimgout` files.
- The Feeder does not verify actual RF transmission success.
- The Feeder does not confirm that WSJT-X transmitted the exact loaded text OTA.
- The Reconstructor warning/proceed behavior should be tested against malformed and mismatched headers.
- The Constructor preview may not always be pixel-identical to Reconstructor output.
- The repeat policy is conservative and may be revised after practical decode-loss data is collected.
- Pre-Alpha software relies on operator supervision for transmit safety.

## 21. Known Stretch Goals / Future Work

Known future work:

- Finalize the Reader.
- Decide the Reader's WSJT-X text retrieval method.
- Improve receive-side session handling.
- Improve malformed-header recovery behavior.
- Add more complete Reconstructor compatibility warnings.
- Improve Constructor / Reconstructor rendering consistency.
- Add additional macro shapes if needed and if shape-code space permits.
- Revisit repeat counts after practical local and OTA test data exists.
- Refine Alpha documentation after the first controlled OTA test.
- Continue keeping protocol behavior public and auditable.

## 22. Design Rationale

The EMEIMG Pre-Alpha design favors recoverability, transparency, and operational clarity over raw throughput.

The fixed 13-character packet size keeps the protocol aligned with JT65B-compatible text constraints.

The header gives receivers and tools protocol metadata before drawing packets are interpreted.

The grid field provides station/location transparency within the same 13-character metadata packet.

The Feeder repeats the header early because metadata recovery is critical.

The Feeder does not round-robin the header because header packets belong to the preamble, not to image body scheduling.

The round-robin body queue prevents all repeats of a packet from being lost during a short decode outage.

Priority packets provide additional redundancy for important commands without changing the packet format.

Recurring station ID packets maintain identification and context during long image sends.

EOF is repeated five times because a reliable end marker is important for receiver confidence.

Local metadata such as `[PRIORITY]` and `[EXPERIMENTAL]` provides useful development and scheduling information without changing the over-the-air packet payload.

## 23. Summary

EMEIMG Pre-Alpha currently consists of:

```text
Constructor   -> creates `.emeimg` image packet files
Feeder        -> builds a robust transmit queue and feeds WSJT-X
Reader        -> planned receive-side `.emeimgout` creator
Reconstructor -> renders recovered packets into PNG output
```

Current header format:

```text
EMEIMGVVPGGGG
```

Current example header:

```text
EMEIMG000EN60
```

Current Feeder queue structure:

```text
3x [CALLSIGN] EMEIMG
3x EMEIMG header
round-robin body packets
station ID after every 5 body packets
5x [CALLSIGN] EOF73
```

The header is repeated in the preamble and is not included in the body round-robin stream.

The protocol remains openly documented, non-encrypted, and auditable.

## End of Pre-Alpha Documentation
