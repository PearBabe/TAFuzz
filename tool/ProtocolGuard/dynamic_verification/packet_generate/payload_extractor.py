#!/usr/bin/python3

import sys
import os
import argparse
import pyshark # type: ignore

def main():
    parser = argparse.ArgumentParser(description="Extracts application layer payloads from a PCAP file for specific flows.")
    parser.add_argument('--input', help="Input file (PCAP)", required=True)
    parser.add_argument('--server-port', type=int, help="Server port number", required=True)
    parser.add_argument('--output', help="Output file to save binary/text payload. Defaults to <pcap_basename>.payload")
    parser.add_argument('--client-port', type=int, help="Optional: Specify a single client port to filter for. Captures both directions of this specific flow.")
    parser.add_argument('--direction', choices=['both', 'to-server', 'from-server'], 
                        default='both', help="Data direction to capture: 'both' (default), 'to-server' (client->server), 'from-server' (server->client)")
    # args.ignore_multiple_clients from original script is implicitly handled:
    # If client-port is not specified, data from all clients talking to server-port will be concatenated.
    # If client-port is specified, only that flow is captured.

    args = parser.parse_args()

    pcap_file = args.input
    server_port = args.server_port
    client_port_filter = args.client_port
    direction = args.direction

    if not os.path.exists(pcap_file):
        print(f"Error: Input file '{pcap_file}' not found.")
        sys.exit(1)

    if not (0 <= server_port <= 65535):
        print(f"Error: Invalid server port number {server_port}. Must be between 0 and 65535.")
        sys.exit(1)
    
    if client_port_filter is not None and not (0 <= client_port_filter <= 65535):
        print(f"Error: Invalid client port number {client_port_filter}. Must be between 0 and 65535.")
        sys.exit(1)

    output_file_name = args.output
    if output_file_name is None:
        base_name = os.path.splitext(os.path.basename(pcap_file))[0]
        # Add a more descriptive suffix if client_port is specified
        if client_port_filter is not None:
            output_file_name = f"{base_name}_server{server_port}_client{client_port_filter}.payload"
        else:
            output_file_name = f"{base_name}_server{server_port}.payload"

    # --- First pass to identify non-TCP/UDP highest layers for disabling (optional but recommended) ---
    print("INFO: First pass - identifying application protocols to disable for raw payload extraction...")
    
    # Build a display filter for the first pass to potentially speed it up
    # This filter helps limit packets pyshark initially processes deeply.
    display_filter_pass1 = f"tcp.port == {server_port} or udp.port == {server_port}"
    if client_port_filter:
        display_filter_pass1 = (
            f"(tcp.port == {server_port} and tcp.port == {client_port_filter}) or "
            f"(udp.port == {server_port} and udp.port == {client_port_filter})"
        )
        # A more precise BPF filter would be even better if IPs were known/used.
        # Example for BPF: f"port {server_port}"
        # For pyshark's display_filter, it's applied after packets are read by tshark.

    app_protocols_to_disable = set()
    try:
        # For very large files, you might want to limit the number of packets checked in this first pass
        # by adding e.g. packet_count=1000 to FileCapture.
        cap_check = pyshark.FileCapture(pcap_file, display_filter=display_filter_pass1, keep_packets=False)
        # Iterate through a limited number of packets for protocol discovery
        # This is a heuristic; for very diverse pcaps, more packets might be needed.
        # For now, let's process up to a certain number for discovery, e.g. 5000
        pkt_limit_for_discovery = 5000 
        for i, pkt_check in enumerate(cap_check):
            if i >= pkt_limit_for_discovery:
                print(f"INFO: First pass protocol discovery scanned {pkt_limit_for_discovery} packets (or EOF).")
                break
            pkt_highest_layer_name = pkt_check.highest_layer
            # Exclude common lower layers and generic data layer from disabling
            if pkt_highest_layer_name and pkt_highest_layer_name.upper() not in [
                "TCP", "UDP", "DATA", "ETH", "IP", "IPV6", "ICMP", "ARP", "DNS", # Keep DNS for now, can be app data
                "LOOPBACK", "NULL", "LINUX_SLL", "FRAME", "GENEVE", "VXLAN" # More link/tunneling layers
            ]:
                # Check if it's a real attribute representing a dissected layer
                if hasattr(pkt_check, pkt_highest_layer_name.lower()):
                    app_protocols_to_disable.add(pkt_highest_layer_name)
        cap_check.close()
    except Exception as e:
        print(f"Warning: Error during first pass for protocol discovery: {e}. Proceeding without disabling extra protocols.")
        app_protocols_to_disable.clear() # Clear if discovery failed

    custom_tshark_params = []
    if app_protocols_to_disable:
        print(f"INFO: Will attempt to disable dissection for: {', '.join(app_protocols_to_disable)}")
        for proto_name in app_protocols_to_disable:
            custom_tshark_params.extend(['--disable-protocol', proto_name.lower()])
    else:
        print("INFO: No specific application protocols identified to disable, or discovery skipped/failed. Relying on TCP/UDP payload.")
    
    # --- Second pass for actual data extraction ---
    override_prefs = {'tcp.desegment_tcp_streams': 'TRUE'} # Crucial for TCP reassembly
    print(f"INFO: Second pass - extracting data from '{pcap_file}' to '{output_file_name}'...")

    cap = None # Ensure cap is defined before try block
    try:
        cap = pyshark.FileCapture(
            input_file=pcap_file,
            override_prefs=override_prefs,
            custom_parameters=custom_tshark_params,
            keep_packets=False # Process packets one by one to save memory
        )
    except Exception as e:
        print(f"Error: Unable to open/parse PCAP file '{pcap_file}' in second pass: {e}")
        sys.exit(1)

    bytes_written = 0
    packets_contributed_payload = 0
    
    processed_packet_count = 0

    try:
        with open(output_file_name, "wb") as outfile:
            for pkt in cap:
                processed_packet_count += 1
                if processed_packet_count % 1000 == 0:
                    print(f"INFO: Processed {processed_packet_count} packets...")

                src_port, dst_port = None, None
                payload_bytes = None

                # Determine protocol and extract ports
                if "TCP" in pkt:
                    try:
                        src_port = int(pkt.tcp.srcport)
                        dst_port = int(pkt.tcp.dstport)
                    except AttributeError: # Should not happen if "TCP" in pkt is reliable
                        continue
                elif "UDP" in pkt:
                    try:
                        src_port = int(pkt.udp.srcport)
                        dst_port = int(pkt.udp.dstport)
                    except AttributeError:
                        continue
                else:
                    continue # Not a TCP or UDP packet

                # --- Flow Filtering Logic ---
                # We want to capture data if SERVER_PORT is either source or destination,
                # and if CLIENT_PORT_FILTER is set, the other port must match it.
                is_client_to_server = (dst_port == server_port) and \
                                      (client_port_filter is None or src_port == client_port_filter)
                is_server_to_client = (src_port == server_port) and \
                                      (client_port_filter is None or dst_port == client_port_filter)

                if direction == 'to-server' and not is_client_to_server:
                    continue
                if direction == 'from-server' and not is_server_to_client:
                    continue

                if not (is_client_to_server or is_server_to_client):
                    continue
                
                # --- Payload Extraction ---
                # Try to get payload from 'data' layer first (if high-level protocols were disabled)
                # Pyshark's 'data' layer often has its payload in 'data.data' (hex string) or 'data.binary_value'
                if hasattr(pkt, 'data'):
                    if hasattr(pkt.data, 'binary_value'): # Ideal if present
                        payload_bytes = pkt.data.binary_value
                    elif hasattr(pkt.data, 'data') and isinstance(pkt.data.data, str): # Hex string
                        payload_bytes = bytes.fromhex(pkt.data.data.replace(":", ""))
                    elif hasattr(pkt.data, 'payload') and isinstance(pkt.data.payload, str): # Another common hex string location
                        payload_bytes = bytes.fromhex(pkt.data.payload.replace(":", ""))
                
                # If no payload from 'data' layer, try transport layer payload directly
                if not payload_bytes:
                    if "TCP" in pkt and hasattr(pkt.tcp, 'payload') and pkt.tcp.payload:
                        payload_bytes = bytes.fromhex(pkt.tcp.payload.replace(":", ""))
                    elif "UDP" in pkt and hasattr(pkt.udp, 'payload') and pkt.udp.payload:
                        payload_bytes = bytes.fromhex(pkt.udp.payload.replace(":", ""))
                
                if payload_bytes:
                    outfile.write(payload_bytes)
                    bytes_written += len(payload_bytes)
                    packets_contributed_payload += 1
            
            print(f"INFO: Finished processing. Total packets scanned in second pass: {processed_packet_count}")

    except IOError as e:
        print(f"Error: Unable to write to output file '{output_file_name}': {e}")
        sys.exit(1)
    except Exception as e: # Catch other pyshark or processing errors
        print(f"An unexpected error occurred during packet processing: {e}")
        if hasattr(e, 'stderr'): # Pyshark TSharkCalledProcessError might have stderr
             print(f"TShark stderr: {e.stderr.decode(errors='ignore') if isinstance(e.stderr, bytes) else e.stderr}")
        sys.exit(1)
    finally:
        if cap:
            cap.close()

    if bytes_written == 0:
        print(f"Warning: No application layer data found matching the criteria for server port {server_port}" +
              (f" and client port {client_port_filter}" if client_port_filter else "") +
              f" in '{pcap_file}'. Output file '{output_file_name}' is empty.")
    else:
        print(f"Successfully extracted {bytes_written} bytes from {packets_contributed_payload} packet(s)/segment(s) "
              f"to '{output_file_name}'.")

if __name__ == "__main__":
    main()