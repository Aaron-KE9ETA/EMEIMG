# EMEIMG PRE-ALPHA DOCUMENTATION

Created: May 27, 2026  
Project Stage: Pre-Alpha  
Author: Aaron Cocanower KE9ETA

EMEIMG is an experimental low-bandwidth vector image protocol for QRP Earth-Moon-Earth experimentation. It encodes simple drawing instructions as JT65B-compatible 13-character text packets so a receiving station can reconstruct a simple 720x480 image from symbolic packet instructions rather than from raw raster pixel data.

The design goal is not full raster-image transfer. The design goal is to send a compact, openly documented instruction set that can reconstruct a simple, recognizable image using deterministic receiver-side rendering.

EMEIMG is intended to remain openly documented, non-encrypted, and auditable. The packet format, source code, examples, and reconstruction behavior should remain public so transmitted packets can be interpreted and reconstructed by third parties.



## PRE-ALPHA STATUS SUMMARY

Pre-Alpha development is intended to move the project from a self-contained prototype toward a cleaner multi-program workflow suitable for later Alpha development and eventual over-the-air testing.

Current Pre-Alpha status:

1. Constructor
    - Status: Prototype behavior still applies.
    - The Constructor has not yet been updated for Pre-Alpha.
    - It currently remains the packet-first image editor concept from the prototype stage.
    - Planned Pre-Alpha work: add protocol metadata/header support to exported `.emeimg` files.

2. Feeder
    - Status: Being redesigned for Pre-Alpha.
    - The Prototype Feeder documentation no longer describes the intended Pre-Alpha Feeder behavior.
    - The Pre-Alpha Feeder is intended to feed EMEIMG commands into WSJT-X or a WSJT-X-compatible operating workflow.
    - Detailed implementation behavior is not yet finalized and should not be treated as specified.

3. Reader
    - Status: Planned.
    - A separate receive-side program is planned to recover decoded text output and write `.emeimgout` files for the Reconstructor.
    - Detailed implementation behavior is not yet finalized and should not be treated as specified.

4. Interim Middleman Utility
    - Status: Possible planned support tool.
    - A temporary middleman program may be developed while the WSJT-X integration path is being learned.
    - This would exist only to bridge workflow gaps during development.
    - Detailed behavior is not yet finalized and should not be treated as specified.

5. Reconstructor
    - Status: Updated for Pre-Alpha metadata validation.
    - The Reconstructor stores its own expected protocol version and patch number.
    - It checks metadata in the `.emeimgout` file before attempting reconstruction.
    - If the file version or patch does not match the Reconstructor's expected version or patch, reconstruction should be cancelled to avoid rendering incompatible packet formats.



## PRE-ALPHA ARCHITECTURE INTENT

The Pre-Alpha architecture separates image construction, packet transmission, packet recovery, and image reconstruction into distinct roles.

Intended module roles:

1. Constructor
    Creates EMEIMG packet instructions from a visual editor and exports a `.emeimg` file.

2. Feeder
    Loads an EMEIMG packet file and feeds transmit-ready text commands into WSJT-X or a WSJT-X-compatible workflow.

3. WSJT-X / JT65B Operating Path
    Handles the actual JT65B transmit/decode workflow.

4. Reader
    Planned receive-side tool that collects decoded EMEIMG text output and writes a `.emeimgout` file.

5. Reconstructor
    Loads a `.emeimgout` file, validates its metadata, parses valid packet lines, removes duplicate drawing packets, sorts packets by instruction index, renders the image, and exports a PNG.

Important Pre-Alpha distinction:

The Prototype Feeder simulated transmission and receive success internally. The Pre-Alpha direction separates transmit-side feeding from receive-side collection. The future Reader program is expected to handle the receive-side `.emeimgout` creation role.



## GENERAL PROTOCOL SPECIFICATION

Canvas:

    The fixed reconstructed image canvas is:

        Width  = 720 pixels
        Height = 480 pixels

    Base-36 equivalents:

        Width  = K0
        Height = DC

    Valid visible coordinate range:

        X: 00 through JZ  -> 0 through 719 decimal
        Y: 00 through DB  -> 0 through 479 decimal

    Geometry may extend beyond the visible canvas. Off-canvas drawing should not crash the software; it may be clipped by the image library.

Drawing Packet Length:

    Every EMEIMG drawing packet is exactly 13 characters.

General Drawing Packet Structure:

    ICSXXXXXXXXXX

    Field meaning:

        I = instruction index / render order
        C = color code
        S = shape code
        X = shape-specific payload data

    Character positions:

        packet[0]    -> instruction index
        packet[1]    -> color code
        packet[2]    -> shape code
        packet[3:13] -> shape-specific payload

Instruction Index:

    I is a single Base-36 character.

    Valid instruction index range:

        0 through Z

    This gives 36 ordered drawing instructions per image.

    Packets are rendered in ascending instruction index order, regardless of file order, receive order, or transmission order.

    Exact duplicate drawing packets may be removed before rendering.

Base-36 Encoding:

    Most numeric fields are encoded in Base-36.

    Base-36 digits:

        0 1 2 3 4 5 6 7 8 9 A B C D E F G H I J K L M N O P Q R S T U V W X Y Z

    Single-character fields can represent:

        0 through 35 decimal

    Two-character fields can represent:

        00 through ZZ
        0 through 1295 decimal

    Two-character coordinate fields such as XX or YY are decoded as one two-character Base-36 number, not as two separate digits.

Text Packet Rule:

    Shape 0 uses the final six payload characters as literal text.

    Those six characters may include spaces.

    File readers must not use `line.strip()` before packet parsing, because that can destroy meaningful trailing spaces inside Shape 0 packets.

    Recommended line cleanup:

        line = line.rstrip("\r\n")

    Avoid:

        line = line.strip()

Priority Metadata Rule:

    [PRIORITY] is not part of the 13-character EMEIMG drawing packet.

    It is metadata used by tooling to mark important packets for transmission handling.

    A priority-tagged command line has this structure:

        <13-character EMEIMG packet>[PRIORITY]

    Preview renderers and the Reconstructor must ignore [PRIORITY] when drawing.

    The Feeder must not transmit [PRIORITY] as drawing packet data.



## PRE-ALPHA METADATA HEADER

Pre-Alpha introduces a protocol metadata header so tools can identify the EMEIMG protocol version and patch level associated with a file.

Header Format:

    EMEIMGVVPE***

Field Meaning:

    EMEIMG = fixed identifier string
    VV     = protocol version number, encoded as two Base-36 digits
    P      = protocol patch number, encoded as one Base-36 digit
    E      = experimental-version flag
    ***    = spare/reserved characters

Character Positions:

    header[0:6]   -> EMEIMG identifier
    header[6:8]   -> VV version field
    header[8]     -> P patch field
    header[9]     -> E experimental flag
    header[10:13] -> spare/reserved field

Current Pre-Alpha Example:

    EMEIMG0000***

Interpreted as:

    EMEIMG = EMEIMG header identifier
    VV     = 00
    P      = 0
    E      = 0
    ***    = reserved/spare

Compatibility Rule:

    The Reconstructor stores its own expected version and patch number.

    Before reconstruction, it compares the `.emeimgout` metadata header against its internal expected version and patch.

    If the file version or patch does not match the Reconstructor version or patch, reconstruction should be cancelled.

Experimental Flag:

    The E field marks experimental/local test builds.

    Release files should default E to 0.

    Experimental files may use this field during local development, but the exact long-term policy for experimental compatibility may be refined later.

Reserved Field:

    The final three characters are currently spare/reserved.

    They should not be assigned new meaning without updating this documentation and incrementing the appropriate version or patch field.



## FILE TYPES

`.emeimg`

    Constructor output file.

    Current status:
        The Constructor has not yet been updated for Pre-Alpha.

    Intended Pre-Alpha behavior:
        The file should contain protocol metadata plus drawing packet lines.

    Intended structure:
        EMEIMGVVPE***
        <13-character EMEIMG packet>
        <13-character EMEIMG packet>[PRIORITY]
        <13-character EMEIMG packet>

`.emeimgout`

    Receiver-side / reconstruction input file.

    Current Pre-Alpha Reconstructor expectation:
        The file should include a valid EMEIMG metadata header matching the Reconstructor's expected version and patch.

    Intended structure:
        EMEIMGVVPE***
        "PACKET",
        "PACKET",
        "PACKET",

    Notes:
        The quoted packet wrapper is tolerated for compatibility with existing prototype output style.
        The wrapper is not part of the 13-character drawing packet.

`.png`

    Reconstructor output image.

    The Reconstructor exports the final reconstructed visible image as a PNG file.



## COLOR CODES

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

Notes:

    The color code is the second character in the packet.

    Example:

        I C S XXXXXXXXXX
          ^
          color code

    Reserved color values should not crash the renderer.

    Recommended behavior:
        Warn and either ignore the packet or fall back to a safe default color.



## SHAPE CODE QUICK REFERENCE

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

Notes:

    Shape code is the third character in the packet.

    Example:

        I C S XXXXXXXXXX
            ^
            shape code

    Reserved shape values must not crash the Reconstructor.

    Recommended behavior:
        Warn and ignore the packet.



## SHAPE PACKET FORMATS

### 0: 6-Character String

    Format:
        IC0XXYY******

    Fields:
        XX,YY  = text origin point
        ****** = six literal text characters

    Behavior:
        Draws a six-character text string at coordinate XX,YY.

    Important:
        The text field may contain spaces.
        Do not strip trailing packet spaces before parsing.

### 1: Line

    Format:
        IC1XXYYxxyy**

    Fields:
        XX,YY = first endpoint
        xx,yy = second endpoint
        **    = unused wildcard values

    Behavior:
        Draws a line from XX,YY to xx,yy.

### 2: Rectangle

    Format:
        IC2XXYYxxyyF*

    Fields:
        XX,YY = first corner
        xx,yy = opposite corner
        F     = fill flag
                0 = outline
                1 = filled
        *     = unused wildcard value

    Behavior:
        Draws a rectangle using XX,YY and xx,yy as opposite corners.

### 3: Ellipse

    Format:
        IC3XXYYRrSF**

    Fields:
        XX,YY = center point
        R     = vertical radius
        r     = horizontal radius
        S     = scale factor
        F     = fill flag
                0 = outline
                1 = filled
        **    = unused wildcard values

    Behavior:
        Draws an ellipse centered at XX,YY.

    Rendered radii:
        vertical radius   = R * S
        horizontal radius = r * S

### 4: Triangle Outline

    Format:
        IC4XXYYVLDROS

    Fields:
        XX,YY = origin vertex
        V     = downward vector for point 1
        L     = leftward vector for point 1
        D     = downward vector for point 2
        R     = rightward vector for point 2
        O     = orientation
        S     = scale factor

    Behavior:
        Draws an outlined triangle.

    Geometry before rotation and scaling:
        origin  = (XX, YY)
        point 1 = (XX - L, YY + V)
        point 2 = (XX + R, YY + D)

    Orientation:
        0 = default
        1 = 90 degrees clockwise
        2 = 180 degrees
        3 = 270 degrees clockwise

### 5: Triangle Fill

    Format:
        IC5XXYYVLDROS

    Fields:
        Same fields as Shape 4.

    Behavior:
        Uses the same geometry as Shape 4, but draws a filled triangle.

### 6: Arrow

    Format:
        IC6XXYYOS****

    Fields:
        XX,YY = arrow tip / vertex
        O     = orientation
        S     = scale factor
        ****  = unused wildcard values

    Behavior:
        Draws a solid arrowhead at XX,YY, then draws a rectangular tail behind it.

    Orientation:
        0 = points upward
        1 = points right
        2 = points downward
        3 = points left

### 7: Star

    Format:
        IC7XXYYRS****

    Fields:
        XX,YY = center point
        R     = radius
        S     = scale factor
        ****  = unused wildcard values

    Behavior:
        Draws a four-line star centered at XX,YY.

    The star consists of:
        - vertical line
        - horizontal line
        - diagonal NE/SW line
        - diagonal NW/SE line

    Rendered radius:
        R * S

### 8: SemiCircle / Arc

    Format:
        IC8XXYYRSOODD

    Fields:
        XX,YY = center point
        R     = radius
        S     = scale factor
        OO    = start angle in degrees, stored as two-character Base-36
        DD    = angular distance in degrees, stored as two-character Base-36

    Behavior:
        Draws an arc centered at XX,YY.

    Angle convention:
        0 degrees points directly right.
        Angles increase counterclockwise.
        90 degrees points upward.
        180 degrees points left.
        270 degrees points downward.

    Common angle encodings:
        90 degrees  = 2I in Base-36
        180 degrees = 50 in Base-36
        270 degrees = 7I in Base-36
        360 degrees = A0 in Base-36

### 9: Yagi Antenna

    Format:
        IC9XXYYOS****

    Fields:
        XX,YY = macro origin point
        O     = orientation
        S     = scale factor
        ****  = unused wildcard values

    Behavior:
        Draws a Yagi antenna macro.

    Orientation:
        0 = default
        1 = 90 degrees clockwise
        2 = 180 degrees
        3 = 270 degrees clockwise

### A: Dish Antenna

    Format:
        ICAXXYYOS****

    Fields:
        XX,YY = dish center / origin point
        O     = facing direction
        S     = scale factor
        ****  = unused wildcard values

    Behavior:
        Draws a dish antenna macro.

    Facing direction:
        0 = dish faces left
        1 = dish faces right

### B: Radio Transceiver

    Format:
        ICBXXYYS*****

    Fields:
        XX,YY = macro origin point
        S     = scale factor
        ***** = unused wildcard values

    Behavior:
        Draws a radio transceiver macro.

    Notes:
        The main radio body uses XX,YY as its top-left corner.

### C: Radio Waves

    Format:
        ICCXXYYRSOODD

    Fields:
        XX,YY = center point
        R     = radius of first wave
        S     = scale factor
        OO    = start angle in degrees, stored as two-character Base-36
        DD    = angular distance in degrees, stored as two-character Base-36

    Behavior:
        Draws 3 concentric arc segments centered at XX,YY.

    Rendered wave radii:
        1 * R * S
        3 * R * S
        5 * R * S

### D: Moon

    Format:
        ICDXXYYSK****

    Fields:
        XX,YY = center point
        S     = scale factor
        K     = crater color
        ****  = unused wildcard values

    Behavior:
        Draws a filled moon centered at XX,YY.

    Moon body:
        Uses packet color C.

    Rendered moon radius:
        36 * S

    Craters:
        Draws deterministic outlined crater circles using color K.

    Stretch Goal:
        Crescent moon rendering is a stretch goal and is not required for the initial Moon macro.

### E: DoubleBox

    Format:
        ICEXXYYxxyyPP

    Fields:
        XX,YY = first corner
        xx,yy = opposite corner
        PP    = percentage split position from the top, stored as two-character Base-36

    Behavior:
        Draws an outlined rectangle, then draws a horizontal divider line across the rectangle.

    PP Handling:
        PP is decoded as Base-36, then clamped to the range 0-100 decimal.

    Common percentage encodings:
        0%   = 00 in Base-36
        25%  = 0P in Base-36
        50%  = 1E in Base-36
        75%  = 23 in Base-36
        100% = 2S in Base-36



## CONSTRUCTOR PROGRAM DOCUMENTATION

Status:

    The Constructor has not yet been updated for Pre-Alpha.

    Until that update is complete, Constructor behavior should be treated as Prototype-stage behavior.

Purpose:

    The Constructor is a packet-first visual editor for creating EMEIMG instruction files.

    The Constructor does not treat arbitrary GUI drawing objects as the primary source of truth. Each completed layer is stored as an EMEIMG packet string. The preview canvas is reconstructed by parsing and rendering the same packets that will later be saved and transmitted.

Current Prototype Behavior:

    - Provides a 720x480 editing canvas.
    - Allows the user to build an image layer by layer.
    - Encodes each layer as a 13-character EMEIMG drawing packet.
    - Assigns instruction indexes based on layer order.
    - Allows packet lines to be marked with [PRIORITY] metadata.
    - Exports a `.emeimg` file.

Pre-Alpha Update Needed:

    The Constructor should be updated to include EMEIMG metadata header support in exported `.emeimg` files.

    Intended header format:

        EMEIMGVVPE***

    Example current Pre-Alpha header:

        EMEIMG0000***

    Until this update is implemented, Constructor output may need to be manually adapted or processed by another tool before it fully matches the Pre-Alpha metadata expectations.

Constructor Output Format:

    Current Prototype output:

        <13-character EMEIMG packet>
        <13-character EMEIMG packet>[PRIORITY]

    Intended Pre-Alpha output:

        EMEIMGVVPE***
        <13-character EMEIMG packet>
        <13-character EMEIMG packet>[PRIORITY]

Priority Metadata:

    [PRIORITY] is not packet data.

    It must begin after the 13th drawing-packet character.

    The Reconstructor must ignore it for rendering.



## FEEDER PROGRAM DOCUMENTATION

Status:

    The Feeder is being redesigned for Pre-Alpha.

    The old Prototype Feeder simulated a transmission path and exported decoded test packets. That behavior should not be treated as the final Pre-Alpha Feeder design.

Pre-Alpha Purpose:

    The Pre-Alpha Feeder is intended to feed EMEIMG command text into WSJT-X or a WSJT-X-compatible workflow for JT65B transmission.

    The Feeder should be considered transmit-side tooling.

Planned Features:

    - Load an EMEIMG packet file.
    - Preserve 13-character drawing packets exactly.
    - Recognize or preserve protocol metadata needed by the transmission workflow.
    - Feed transmit-ready command text into WSJT-X or the selected WSJT-X operating path.
    - Support later refinement as the WSJT-X control method becomes better understood.

Not Yet Specified:

    The following Feeder behavior is not yet finalized and should not be documented as implemented:

    - Exact WSJT-X interface method.
    - Exact command injection method.
    - Exact timing control method.
    - Exact GUI behavior.
    - Exact error handling policy.
    - Exact station identification insertion strategy.
    - Exact handling of repeated packets or priority packets in the live WSJT-X workflow.
    - Exact export behavior, if any.

Superseded Prototype Behavior:

    The Prototype Feeder documentation described simulated no-decode events, internal decoded-output export, and console-based transmission testing.

    Those behaviors were useful for prototype robustness testing but are not the primary Pre-Alpha Feeder direction.



## READER PROGRAM DOCUMENTATION

Status:

    Planned.

Purpose:

    The Reader is intended to be a separate receive-side program that collects decoded EMEIMG text output and creates `.emeimgout` files for the Reconstructor.

Planned Features:

    - Receive or collect decoded text output from the operating workflow.
    - Identify EMEIMG metadata and drawing packet lines.
    - Preserve successfully recovered 13-character drawing packets.
    - Write a `.emeimgout` file for the Reconstructor.
    - Include metadata needed for Reconstructor version and patch validation.

Not Yet Specified:

    The following Reader behavior is not yet finalized and should not be documented as implemented:

    - Exact WSJT-X output reading method.
    - Exact log parsing method.
    - Exact GUI or command-line interface.
    - Exact duplicate packet handling.
    - Exact station/session handling.
    - Exact malformed-line handling.
    - Exact `.emeimgout` line formatting beyond Reconstructor compatibility requirements.



## INTERIM MIDDLEMAN UTILITY

Status:

    Possible planned development tool.

Purpose:

    A temporary middleman utility may be developed while the WSJT-X integration path is being learned.

    This utility would exist to bridge the gap between EMEIMG tooling and the eventual direct or semi-direct WSJT-X workflow.

Planned Role:

    - Help move EMEIMG command text into or out of the WSJT-X operating workflow during development.
    - Support manual or semi-automated Pre-Alpha testing.
    - Reduce friction while the final Feeder and Reader designs are still being determined.

Not Yet Specified:

    No permanent file format, interface, GUI, automation behavior, or protocol behavior is currently defined for this utility.

    It should not be treated as a stable part of the EMEIMG protocol until its purpose and behavior are formally defined.



## RECONSTRUCTOR PROGRAM DOCUMENTATION

Status:

    Updated for Pre-Alpha metadata validation.

Purpose:

    The Reconstructor rebuilds a final EMEIMG image from received or loaded EMEIMG packet data.

    The Reconstructor does not create image geometry interactively.

    It reads packet strings, validates file metadata, parses valid drawing packets, sorts them by instruction index, removes exact duplicates when appropriate, renders the image onto the fixed EMEIMG canvas, and saves the reconstructed image as a PNG file.

Pre-Alpha Metadata Validation:

    The Reconstructor stores its own expected protocol version and patch number.

    Before rendering, the Reconstructor reads the metadata header from the `.emeimgout` file.

    The Reconstructor compares:

        file VV against Reconstructor expected VV
        file P  against Reconstructor expected P

    If either the version or patch number does not match, reconstruction should be cancelled.

    This prevents older or incompatible packet formats from being rendered incorrectly by a newer or mismatched Reconstructor.

Expected Current Header:

    EMEIMG0000***

Accepted Input Line Formats:

    Metadata header:
        EMEIMGVVPE***

    Plain drawing packet:
        <13-character EMEIMG packet>

    Priority-tagged Constructor line:
        <13-character EMEIMG packet>[PRIORITY]

    Wrapped packet line:
        "PACKET",

Ignored Non-Image Data:

    The Reconstructor should not render:

        - metadata headers
        - station ID packets
        - closing 73 packets
        - console labels
        - [DECODED]
        - [NO DECODE]
        - [PRIORITY] metadata

Canvas:

    The Reconstructor creates a fixed output image canvas:

        Width  = 720 pixels
        Height = 480 pixels

    Background:

        white by default

Packet Handling:

    Each EMEIMG drawing packet is exactly 13 characters.

    Packet format:

        ICSXXXXXXXXXX

    Parser indexing:

        packet[0]    -> instruction index
        packet[1]    -> color code
        packet[2]    -> shape code
        packet[3:13] -> shape-specific payload

Invalid Packet Behavior:

    Invalid packets must not crash the Reconstructor.

    Recommended behavior:

        1. Print a warning to the terminal.
        2. Convert the packet into a VOID/no-op instruction or skip it.
        3. Continue processing the remaining packets.

Unknown Shape Behavior:

    If a packet has valid length but uses an unknown or reserved shape code, the Reconstructor should not crash.

    Recommended behavior:

        unknown shape -> print warning -> ignore packet

Duplicate Packet Handling:

    Exact duplicate packets may appear because packets may be transmitted or recovered more than once.

    The Reconstructor may remove exact duplicates before rendering.

    Duplicate removal should compare the recovered 13-character drawing packet itself, not metadata or wrapper text.

Render Order:

    Packets are rendered by instruction index I, not by receive order or file order.

    Recommended process:

        1. Load `.emeimgout` file.
        2. Read and validate metadata header.
        3. Remove metadata/wrappers from packet lines.
        4. Recover 13-character drawing packets.
        5. Remove exact duplicate drawing packets.
        6. Parse packets.
        7. Sort parsed packets by instruction index.
        8. Render sorted packets to the canvas.
        9. Save the output PNG.

Rendering Behavior:

    Rendering should be deterministic.

    The same valid packet list and metadata should always produce the same output image.

    The Reconstructor should not use random placement, random colors, or random geometry.

Output:

    The Reconstructor saves the final reconstructed image as a PNG file.

Reconstructor Should Not:

    - create new image geometry
    - assign instruction indexes
    - edit packet layers
    - schedule transmissions
    - control WSJT-X
    - receive WSJT-X output
    - transmit packets
    - act as the Reader



## PRE-ALPHA END-TO-END WORKFLOW

Current / Intended Workflow:

1. Build Image in Constructor

    The user creates an image layer by layer.

    Current status:
        Constructor remains Prototype-stage until updated.

2. Export `.emeimg`

    The Constructor exports drawing packets.

    Intended Pre-Alpha behavior:
        `.emeimg` files should include an EMEIMG metadata header.

3. Feed Packets Through Feeder

    The Feeder loads packet data and feeds command text into WSJT-X or a WSJT-X-compatible workflow.

    Current status:
        Feeder behavior is being redesigned and is not fully specified.

4. Transmit / Decode Through WSJT-X Operating Path

    WSJT-X or the selected operating workflow handles JT65B transmission and decode behavior.

5. Collect Received Packets Through Reader

    A planned Reader program collects decoded output and writes `.emeimgout` files.

    Current status:
        Reader is planned but not yet specified.

6. Load `.emeimgout` in Reconstructor

    The Reconstructor validates the metadata header, checks version and patch compatibility, extracts drawing packets, removes duplicates, parses geometry, sorts by instruction index, and renders the image.

7. Export PNG

    The Reconstructor saves the final visible image as a PNG.



## IMPORTANT SEPARATION OF ROLES

Constructor:

    Creates packet lines.
    Assigns instruction indexes.
    Lets the user build and preview the image.
    Optionally appends [PRIORITY] metadata.
    Exports `.emeimg` files.
    Pre-Alpha metadata output is planned but not yet implemented.

Feeder:

    Loads EMEIMG command data.
    Feeds transmit-ready text into WSJT-X or the selected WSJT-X-compatible workflow.
    Does not define the receive-side `.emeimgout` file by itself in the Pre-Alpha architecture.
    Detailed Pre-Alpha behavior is not yet finalized.

Reader:

    Planned receive-side component.
    Collects decoded text output.
    Writes `.emeimgout` files for the Reconstructor.
    Detailed behavior is not yet finalized.

Interim Middleman:

    Possible temporary utility.
    May support manual or semi-automated WSJT-X workflow bridging during development.
    Not a finalized protocol component.

Reconstructor:

    Reads `.emeimgout` files.
    Validates metadata version and patch.
    Ignores transmission metadata.
    Removes duplicate drawing packets.
    Sorts by instruction index.
    Reconstructs the image deterministically.
    Exports PNG.

Rule of Thumb:

    Constructor decides what the image is.

    Feeder helps send the packet text.

    Reader helps recover the received packet text.

    Reconstructor decides what successfully recovered data reconstructs.



## IMPLEMENTATION NOTES

General Parser Safety:

    Invalid packets should not crash any program.

    Recommended behavior:

        bad packet -> print warning -> return/skip VOID -> continue

Line Reading:

    Packet parsing should preserve literal spaces in Shape 0 text packets.

    When reading packets from a file, remove newline characters only.

    Recommended:

        line = line.rstrip("\r\n")

    Avoid:

        line = line.strip()

Reserved Codes:

    Reserved colors and shapes should be handled gracefully.

    Recommended behavior:

        warn -> ignore packet or use a safe fallback -> continue

Zero Scale / Radius:

    Shape renderers should check for invalid zero or negative scale/radius values.

    Recommended behavior:

        warn -> skip that shape -> continue

Determinism:

    Rendering must be deterministic.

    Constructor preview and Reconstructor output should not depend on random values.

Deduplication:

    Deduplication should happen after metadata/wrapper removal.

    Compare the exact recovered 13-character drawing packet.

Transmission Metadata:

    These labels are never part of image drawing packets:

        [PRIORITY]
        [DECODED]
        [NO DECODE]
        console labels
        wrapper quotes
        wrapper commas

Metadata Versioning:

    Compatibility-sensitive packet changes should increment the protocol version or patch number.

    The Reconstructor should refuse to reconstruct files whose version or patch does not match its expected values.

Known Stretch Goals / Future Work:

    - Constructor Pre-Alpha metadata export.
    - Feeder WSJT-X command feeding implementation.
    - Reader receive-side `.emeimgout` creation.
    - Optional interim middleman utility during WSJT-X integration development.
    - Additional macro shapes, if needed and if shape-code space permits.



## END OF PRE-ALPHA DOCUMENTATION
