# TODO

This file tracks planned EMEIMG features, implementation work, and protocol changes. Items are ordered roughly by development priority for Pre-Alpha work.

## Priority TODO

### 1. Implement reader

Create or integrate software for receiving decoded JT65B text from WSJT-X and saving it locally for reconstruction.

The reader should listen for EMEIMG headers, packets, station ID traffic, and footers where applicable, then write the received packet stream into an `.emeimgout` file suitable for the reconstructor.

## Future TODO

### Implement `EMEIMG_Patchthrough.py`

Design a local-only patch-through system for simulating transmission and reception of EMEIMG data.

This tool is intended for experimental branches and development testing where packets need to move through the pipeline without being sent over the air. It should help validate constructor output, feeder behavior, reader behavior, and reconstructor compatibility before any OTA testing is considered.
### More advanced shapes

Expand the macro system to support a larger library of reusable advanced shapes.

Current planned shape macros:

- Planet
- Ringed Planet
- Earth

These should be implemented as compact packet-compatible macros wherever possible, rather than as large collections of primitive drawing commands.
