# EMEIMG
Experimental low-bandwidth vector image protocol for QRP EME transmission, encoding drawing instructions as JT65B-compatible text packets for receiver-side reconstruction of simple digital images.

EMEIMG is an experimental amateur-radio image instruction protocol intended for openly documented, non-encrypted transmission of simple vector images using JT65B-compatible text packets. The protocol, source code, packet format, examples, and reconstruction tools are publicly available so transmitted packets can be interpreted and reconstructed by any interested station. EMEIMG is not intended to obscure message meaning, provide privacy, or carry commercial traffic.

Pre-Alpha is the architectural preparation phase for EMEIMG. Its purpose is to define the module boundaries, file formats, metadata conventions, packet flow, and parser behavior needed before Alpha implementation begins. Pre-Alpha does not attempt to guarantee reliable over-the-air transmission; it prepares the project so Alpha can focus on implementation, integration, and end-to-end testing.
