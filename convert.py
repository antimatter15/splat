# You can use this to convert a .ply file to a .splat file programmatically in python
# Alternatively you can drag and drop a .ply file into the viewer at https://antimatter15.com/splat

from plyfile import PlyData
import numpy as np
import argparse
from io import BytesIO
import os
import struct


def process_ply_to_splat(ply_file_path, sh_order=0):
    """
    Convert a PLY file to SPLAT format with support for higher-order spherical harmonics.
    
    Args:
        ply_file_path: Path to the PLY file
        sh_order: Spherical harmonics order (0, 1, 2, or 3)
    
    Returns:
        Tuple of (splat_data, sh_data, max_sh_order)
    """
    plydata = PlyData.read(ply_file_path)
    vert = plydata["vertex"]
    
    # Sort gaussians by size and opacity for better rendering
    sorted_indices = np.argsort(
        -np.exp(vert["scale_0"] + vert["scale_1"] + vert["scale_2"])
        / (1 + np.exp(-vert["opacity"]))
    )
    
    # Main buffer for position, scale, color, and rotation
    buffer = BytesIO()
    
    # Buffer for SH coefficients
    sh_buffer = BytesIO()
    
    # Determine the actual max SH order available in the PLY file
    max_sh_order = 0
    sh_prefixes = {
        0: ["f_dc_"],
        1: ["f_dc_", "f_rest_"],
        2: ["f_dc_", "f_rest_"],
        3: ["f_dc_", "f_rest_"]
    }
    
    # Check which SH coefficients are available in the PLY file
    property_names = [p.name for p in vert.properties]
    
    # Count SH coefficients to determine the actual order
    sh_count = 0
    for name in property_names:
        if name.startswith("f_dc_") or name.startswith("f_rest_"):
            sh_count += 1
    
    # Calculate the actual max SH order based on coefficient count
    # SH coefficients per order: 0th=3, 1st=3+9=12, 2nd=3+9+15=27, 3rd=3+9+15+21=48
    if sh_count >= 48:
        max_sh_order = 3
    elif sh_count >= 27:
        max_sh_order = 2
    elif sh_count >= 12:
        max_sh_order = 1
    elif sh_count >= 3:
        max_sh_order = 0
    
    # Use the minimum of requested and available SH order
    effective_sh_order = min(sh_order, max_sh_order)
    print(f"Using SH order: {effective_sh_order} (max available: {max_sh_order})")
    
    # SH coefficient constants
    SH_C0 = 0.28209479177387814
    
    # Process each vertex
    for idx in sorted_indices:
        v = plydata["vertex"][idx]
        
        # Position, scale, rotation
        position = np.array([v["x"], v["y"], v["z"]], dtype=np.float32)
        scales = np.exp(
            np.array(
                [v["scale_0"], v["scale_1"], v["scale_2"]],
                dtype=np.float32,
            )
        )
        rot = np.array(
            [v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]],
            dtype=np.float32,
        )
        
        # Basic color and opacity (for backward compatibility)
        color = np.array(
            [
                0.5 + SH_C0 * v["f_dc_0"],
                0.5 + SH_C0 * v["f_dc_1"],
                0.5 + SH_C0 * v["f_dc_2"],
                1 / (1 + np.exp(-v["opacity"])),
            ]
        )
        
        # Write to main buffer
        buffer.write(position.tobytes())
        buffer.write(scales.tobytes())
        buffer.write((color * 255).clip(0, 255).astype(np.uint8).tobytes())
        buffer.write(
            ((rot / np.linalg.norm(rot)) * 128 + 128)
            .clip(0, 255)
            .astype(np.uint8)
            .tobytes()
        )
        
        # Process SH coefficients if needed
        if effective_sh_order >= 0:
            # 0th order (DC)
            sh_0 = np.array([v["f_dc_0"], v["f_dc_1"], v["f_dc_2"]], dtype=np.float32)
            # Convert to 16-bit signed integers (-32768 to 32767)
            sh_0_int = np.int16((sh_0 * 32768).clip(-32768, 32767))
            # Pack as two uint32 values (RGB)
            sh_0_packed = np.array([
                (int(sh_0_int[0]) & 0xFFFF) | ((int(sh_0_int[1]) & 0xFFFF) << 16),
                (int(sh_0_int[2]) & 0xFFFF) | (0 << 16),
                0,
                0
            ], dtype=np.uint32)
            sh_buffer.write(sh_0_packed.tobytes())
            
            # Higher order coefficients
            if effective_sh_order >= 1:
                # 1st order (3 coefficients, each with RGB)
                for i in range(3):
                    base_idx = i * 3
                    sh_coeff = np.array([
                        v.get(f"f_rest_{base_idx+0}", 0.0),
                        v.get(f"f_rest_{base_idx+1}", 0.0),
                        v.get(f"f_rest_{base_idx+2}", 0.0)
                    ], dtype=np.float32)
                    
                    sh_coeff_int = np.int16((sh_coeff * 32768).clip(-32768, 32767))
                    sh_coeff_packed = np.array([
                        (int(sh_coeff_int[0]) & 0xFFFF) | ((int(sh_coeff_int[1]) & 0xFFFF) << 16),
                        (int(sh_coeff_int[2]) & 0xFFFF) | (0 << 16),
                        0,
                        0
                    ], dtype=np.uint32)
                    sh_buffer.write(sh_coeff_packed.tobytes())
                
                if effective_sh_order >= 2:
                    # 2nd order (5 coefficients, each with RGB)
                    for i in range(5):
                        base_idx = 9 + i * 3  # After the 1st order coefficients
                        sh_coeff = np.array([
                            v.get(f"f_rest_{base_idx+0}", 0.0),
                            v.get(f"f_rest_{base_idx+1}", 0.0),
                            v.get(f"f_rest_{base_idx+2}", 0.0)
                        ], dtype=np.float32)
                        
                        sh_coeff_int = np.int16((sh_coeff * 32768).clip(-32768, 32767))
                        sh_coeff_packed = np.array([
                            (int(sh_coeff_int[0]) & 0xFFFF) | ((int(sh_coeff_int[1]) & 0xFFFF) << 16),
                            (int(sh_coeff_int[2]) & 0xFFFF) | (0 << 16),
                            0,
                            0
                        ], dtype=np.uint32)
                        sh_buffer.write(sh_coeff_packed.tobytes())
                    
                    if effective_sh_order >= 3:
                        # 3rd order (7 coefficients, each with RGB)
                        for i in range(7):
                            base_idx = 9 + 15 + i * 3  # After 1st and 2nd order coefficients
                            sh_coeff = np.array([
                                v.get(f"f_rest_{base_idx+0}", 0.0),
                                v.get(f"f_rest_{base_idx+1}", 0.0),
                                v.get(f"f_rest_{base_idx+2}", 0.0)
                            ], dtype=np.float32)
                            
                            sh_coeff_int = np.int16((sh_coeff * 32768).clip(-32768, 32767))
                            sh_coeff_packed = np.array([
                                (int(sh_coeff_int[0]) & 0xFFFF) | ((int(sh_coeff_int[1]) & 0xFFFF) << 16),
                                (int(sh_coeff_int[2]) & 0xFFFF) | (0 << 16),
                                0,
                                0
                            ], dtype=np.uint32)
                            sh_buffer.write(sh_coeff_packed.tobytes())

    return buffer.getvalue(), sh_buffer.getvalue(), effective_sh_order


def save_splat_files(splat_data, sh_data, sh_order, output_path):
    """
    Save the SPLAT and SH data to files.
    
    Args:
        splat_data: Main SPLAT data
        sh_data: SH coefficient data
        sh_order: SH order used
        output_path: Base path for output files
    """
    # Save main SPLAT file
    with open(output_path, "wb") as f:
        f.write(splat_data)
    
    # Save SH data if available
    if sh_order >= 0 and len(sh_data) > 0:
        sh_path = os.path.splitext(output_path)[0] + ".sh"
        with open(sh_path, "wb") as f:
            # Write header with SH order
            f.write(struct.pack('i', sh_order))
            # Write SH data
            f.write(sh_data)
        print(f"Saved SH data to {sh_path} (order {sh_order})")


def main():
    parser = argparse.ArgumentParser(description="Convert PLY files to SPLAT format with SH support.")
    parser.add_argument(
        "input_files", nargs="+", help="The input PLY files to process."
    )
    parser.add_argument(
        "--output", "-o", default="output.splat", help="The output SPLAT file."
    )
    parser.add_argument(
        "--sh_order", "-s", type=int, default=0, choices=[0, 1, 2, 3],
        help="Spherical harmonics order (0-3, default: 0)"
    )
    args = parser.parse_args()
    
    for input_file in args.input_files:
        print(f"Processing {input_file}...")
        splat_data, sh_data, effective_sh_order = process_ply_to_splat(input_file, args.sh_order)
        
        output_file = (
            args.output if len(args.input_files) == 1 else input_file + ".splat"
        )
        
        save_splat_files(splat_data, sh_data, effective_sh_order, output_file)
        print(f"Saved {output_file}")


if __name__ == "__main__":
    main()