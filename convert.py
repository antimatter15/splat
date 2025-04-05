# You can use this to convert a .ply file to a .splat file programmatically in python
# Alternatively you can drag and drop a .ply file into the viewer at https://antimatter15.com/splat

from plyfile import PlyData
import numpy as np
import argparse
from io import BytesIO


def process_ply_to_splat(ply_file_path):
    plydata = PlyData.read(ply_file_path)
    vert = plydata["vertex"]
    sorted_indices = np.argsort(
        -np.exp(vert["scale_0"] + vert["scale_1"] + vert["scale_2"])
        / (1 + np.exp(-vert["opacity"]))
    )
    buffer = BytesIO()
    for idx in sorted_indices:
        v = plydata["vertex"][idx]
        # Position (3 floats)
        position = np.array([v["x"], v["y"], v["z"]], dtype=np.float32)
        # Scales (3 floats, using exponentiation as in original)
        scales = np.exp(np.array([v["scale_0"], v["scale_1"], v["scale_2"]], dtype=np.float32))
        # Rotation (4 floats)
        rot = np.array([v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]], dtype=np.float32)
        
        # Build the full spherical harmonic coefficients array (48 floats)
        sh_coeffs = []
        # First three coefficients (f_dc_0, f_dc_1, f_dc_2)
        sh_coeffs.extend([v["f_dc_0"], v["f_dc_1"], v["f_dc_2"]])
        # Next 45 coefficients (f_rest_0 to f_rest_44)
        for i in range(45):
            sh_coeffs.append(v[f"f_rest_{i}"])
        sh_array = np.array(sh_coeffs, dtype=np.float32)
        
        # Write the data in order:
        buffer.write(position.tobytes())  # 12 bytes
        buffer.write(scales.tobytes())    # 12 bytes
        buffer.write(sh_array.tobytes())    # 48*4 = 192 bytes
        # Write rotation, quantized as before (4 bytes)
        buffer.write(
            ((rot / np.linalg.norm(rot)) * 128 + 128)
            .clip(0, 255)
            .astype(np.uint8)
            .tobytes()
        )


    return buffer.getvalue()


def save_splat_file(splat_data, output_path):
    with open(output_path, "wb") as f:
        f.write(splat_data)


def main():
    parser = argparse.ArgumentParser(description="Convert PLY files to SPLAT format.")
    parser.add_argument(
        "input_files", nargs="+", help="The input PLY files to process."
    )
    parser.add_argument(
        "--output", "-o", default="output.splat", help="The output SPLAT file."
    )
    args = parser.parse_args()
    for input_file in args.input_files:
        print(f"Processing {input_file}...")
        splat_data = process_ply_to_splat(input_file)
        output_file = (
            args.output if len(args.input_files) == 1 else input_file + ".splat"
        )
        save_splat_file(splat_data, output_file)
        print(f"Saved {output_file}")


if __name__ == "__main__":
    main()
