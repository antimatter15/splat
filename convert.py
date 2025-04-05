# You can use this to convert a .ply file to a .splat file programmatically in python
# Alternatively you can drag and drop a .ply file into the viewer at https://antimatter15.com/splat

from plyfile import PlyData
import numpy as np
import argparse
from io import BytesIO


def process_ply_to_splat(ply_file_path, sh_order=3):
    """
    Processes a .ply file and writes a binary .splat file.
    
    The output per vertex will be:
      - Position: 3 floats (12 bytes)
      - Scales: 3 floats (12 bytes)
      - SH coefficients: depending on sh_order:
           order 0: 4 floats (f_dc_0, f_dc_1, f_dc_2, opacity)
           order 1: 12 floats (f_dc_* plus f_rest_0..f_rest_8)
           order 2: 27 floats (f_dc_* plus f_rest_0..f_rest_23)
           order 3 or higher: 48 floats (f_dc_* plus f_rest_0..f_rest_44)
      - Rotation: 4 bytes (quantized quaternion)
    """
    plydata = PlyData.read(ply_file_path)
    vert = plydata["vertex"]
    # Sort vertices by importance (as in original)
    sorted_indices = np.argsort(
        -np.exp(vert["scale_0"] + vert["scale_1"] + vert["scale_2"]) /
        (1 + np.exp(-vert["opacity"]))
    )
    buffer = BytesIO()
    
    # Determine coefficient count based on sh_order:
    if sh_order == 0:
        coeff_count = 4  # 3 f_dc values and opacity
    elif sh_order == 1:
        coeff_count = 12  # 3 + 9 = 12
    elif sh_order == 2:
        coeff_count = 27  # 3 + 24 = 27
    else:
        coeff_count = 48  # 3 + 45 = 48

    for idx in sorted_indices:
        v = plydata["vertex"][idx]
        # Position (3 floats)
        position = np.array([v["x"], v["y"], v["z"]], dtype=np.float32)
        # Scales (3 floats) - note: exponentiate as per original code
        scales = np.exp(np.array([v["scale_0"], v["scale_1"], v["scale_2"]], dtype=np.float32))
        # Rotation (4 floats) to be normalized and then quantized
        rot = np.array([v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]], dtype=np.float32)
        
        # Build SH coefficients array based on sh_order
        if sh_order == 0:
            # Only zeroth order coefficients and opacity.
            sh_coeffs = [v["f_dc_0"], v["f_dc_1"], v["f_dc_2"],
                         1 / (1 + np.exp(-v["opacity"]))]
        else:
            # Start with the zeroth order: f_dc_0, f_dc_1, f_dc_2
            sh_coeffs = [v["f_dc_0"], v["f_dc_1"], v["f_dc_2"]]
            # Determine additional coefficients to add
            if sh_order == 1:
                additional = 9  # Total = 3+9 = 12 coefficients.
            elif sh_order == 2:
                additional = 24  # Total = 3+24 = 27 coefficients.
            else:
                additional = 45  # Total = 3+45 = 48 coefficients.
            for i in range(additional):
                sh_coeffs.append(v[f"f_rest_{i}"])
            # Append opacity as the last coefficient
            sh_coeffs.append(1 / (1 + np.exp(-v["opacity"])))
            # Now, if sh_order==1, the total length is 3+9+1 = 13; 
            # if sh_order==2, 3+24+1 = 28; if sh_order>=3, 3+45+1 = 49.
            # However, to follow the convention:
            # For order 1, we want 12 coefficients; for order 2, 27; for order 3, 48.
            # So we remove the appended opacity if needed:
            target_total = {1: 12, 2: 27, 3: 48}
            # Use sh_order clamped to 3 for the target:
            target = target_total.get(min(sh_order, 3))
            # If our current length is more than target, drop the last element (opacity)
            if len(sh_coeffs) > target:
                sh_coeffs = sh_coeffs[:-1]
            else:
                # Otherwise, keep the appended opacity.
                pass

        # Write data in order:
        buffer.write(position.tobytes())       # 12 bytes
        buffer.write(scales.tobytes())         # 12 bytes
        # Write the SH coefficients as 32-bit floats
        buffer.write(np.array(sh_coeffs, dtype=np.float32).tobytes())
        # Write rotation (quantized to 4 uint8 values)
        normalized_rot = rot / np.linalg.norm(rot)
        quantized_rot = ((normalized_rot * 128) + 128).clip(0, 255).astype(np.uint8)
        buffer.write(quantized_rot.tobytes())
    
    return buffer.getvalue()

def save_splat_file(splat_data, output_path):
    with open(output_path, "wb") as f:
        f.write(splat_data)

def main():
    parser = argparse.ArgumentParser(description="Convert PLY files to SPLAT format with variable spherical harmonic order.")
    parser.add_argument("input_files", nargs="+", help="The input PLY files to process.")
    parser.add_argument("--output", "-o", default="output.splat", help="The output SPLAT file.")
    parser.add_argument("--sh_order", type=int, default=3,
                        help="Spherical harmonic order (0, 1, 2, or 3). Order 0 outputs 4 floats (RGB+opacity), order 1 outputs 12 floats, order 2 outputs 27 floats, and order 3 outputs 48 floats.")
    args = parser.parse_args()
    
    for input_file in args.input_files:
        print(f"Processing {input_file} with SH order {args.sh_order}...")
        splat_data = process_ply_to_splat(input_file, sh_order=args.sh_order)
        output_file = args.output if len(args.input_files) == 1 else input_file + ".splat"
        save_splat_file(splat_data, output_file)
        print(f"Saved {output_file}")

if __name__ == "__main__":
    main()