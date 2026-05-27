# EMEIMG
Experimental low-bandwidth vector image protocol for QRP EME transmission, encoding drawing instructions as JT65B-compatible text packets for receiver-side reconstruction of simple digital images.

EMEIMG is an experimental amateur-radio image instruction protocol intended for openly documented, non-encrypted transmission of simple vector images using JT65B-compatible text packets. The protocol, source code, packet format, examples, and reconstruction tools are publicly available so transmitted packets can be interpreted and reconstructed by any interested station. EMEIMG is not intended to obscure message meaning, provide privacy, or carry commercial traffic.

## Vision

EMEIMG explores the idea that extremely low-bandwidth amateur radio modes do not need to transmit images as raw pixels to communicate visual meaning. Instead, a station can transmit a compact, publicly documented set of drawing instructions that allow receiving software to reconstruct a simple image from symbolic commands, shapes, macros, and metadata. The project is designed around JT65B-compatible message constraints, with an emphasis on transparency, reproducibility, and weak-signal robustness for potential Earth-Moon-Earth experimentation.

The broader vision of EMEIMG is to treat constrained digital radio payloads as an abstraction layer rather than a limitation. By sending meaning as structured instructions instead of bulk data, the format demonstrates how simple visual information can be carried through extremely narrow communication channels while remaining open, auditable, and reconstructable by third parties. EMEIMG is not intended as encryption or concealment, but as a documented experimental protocol for exploring macro-based image reconstruction in amateur radio.

## Pre-Alpha Branch

Pre-Alpha is the architectural preparation phase for EMEIMG. Its purpose is to define the module boundaries, file formats, metadata conventions, packet flow, and parser behavior needed before Alpha implementation begins. Pre-Alpha does not attempt to guarantee reliable over-the-air transmission; it prepares the project so Alpha can focus on implementation, integration, and end-to-end testing.
