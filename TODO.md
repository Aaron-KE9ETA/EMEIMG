# TODO

This file tracks planned EMEIMG features, implementation work, and protocol changes. Items are ordered roughly by development priority for Pre-Alpha work.

## Priority TODO

### 1. Change header format

Reformat the EMEIMG header from:

```text
EMEIMGVVPE***
```

to:

```text
EMEIMGVVPGGGG
```

Where:

- `EMEIMG` is the protocol identifier.
- `VV` is the 2-character base-36 version number.
- `P` is the base-36 patch number.
- `GGGG` is the 4-character Maidenhead grid locator used for telemetry transparency.

The experimental flag should not be included inside the over-the-air packet. Experimental status should be tracked as local metadata only, so experimental builds are clearly marked but are not accidentally transmitted as released protocol traffic.

### 2. Implement `EMEIMG_Patchthrough.py`

Design a local-only patch-through system for simulating transmission and reception of EMEIMG data.

This tool is intended for experimental branches and development testing where packets need to move through the pipeline without being sent over the air. It should help validate constructor output, feeder behavior, reader behavior, and reconstructor compatibility before any OTA testing is considered.

### 3. Implement feeder

Create or integrate software for feeding EMEIMG packet commands into WSJT-X for transmission.

This may use an existing WSJT-X API, UDP interface, automation method, or a dedicated interfacing layer if no suitable existing option is available. The feeder should preserve packet order, metadata, station identification behavior, and any priority/repeat rules defined by the protocol.

### 4. Implement reader

Create or integrate software for receiving decoded JT65B text from WSJT-X and saving it locally for reconstruction.

The reader should listen for EMEIMG headers, packets, station ID traffic, and footers where applicable, then write the received packet stream into an `.emeimgout` file suitable for the reconstructor.

## Future TODO

### More advanced shapes

Expand the macro system to support a larger library of reusable advanced shapes.

Current planned shape macros:

- Planet
- Ringed Planet
- Earth

These should be implemented as compact packet-compatible macros wherever possible, rather than as large collections of primitive drawing commands.
