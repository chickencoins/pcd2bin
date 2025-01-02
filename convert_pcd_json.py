#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
convert_pcd_json.py

기능:
  1) PCD + JSON 라벨 -> PointPillars용 (BIN + TXT) 변환
  2) /lidar & /label 폴더에 000000.bin, 000000.txt 등 일관된 파일명으로 생성

사용 예:
  python3 convert_pcd_json.py \
    --pcd_path /home/user/temp/train/lidar \
    --json_path /home/user/temp/train/label \
    --out_dir /home/user/temp/train_processed

전제 조건:
  pip install open3d
  pip install numpy tqdm
"""

import os
import argparse
import errno
import json
import numpy as np
from tqdm import tqdm

try:
    import open3d as o3d
except ImportError:
    print("Open3D가 설치되어 있지 않습니다. 다음 명령으로 설치하세요:")
    print("  pip install open3d")
    exit(1)


def create_dir_if_not_exists(path):
    """디렉토리가 없으면 생성"""
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("Failed to create directory:", path)
            raise


def parse_json_label(json_path, categories):
    """
    JSON 라벨파일을 파싱하여
    [ (class_name, h, w, l, x, y, z, rotation_y), ... ] 리스트로 반환
    ※ KITTI-like 형식(3D 박스)으로 변환
    ※ position = [X, Y, Z], scale = [L, W, H], rotation = [Rx, Ry, Rz] 로 가정
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    annotation_list = []
    try:
        items = data["items"]
        for item in items:
            annos = item.get("annotations", [])
            for ann in annos:
                label_id = ann.get("label_id", -1)
                # JSON에 "label_id"가 categories["label"]["labels"] 리스트 인덱스와 동일하다고 가정
                class_name = categories[label_id] if 0 <= label_id < len(categories) else "Unknown"

                pos = ann.get("position", [0.0, 0.0, 0.0])
                rot = ann.get("rotation", [0.0, 0.0, 0.0])
                scale = ann.get("scale", [1.0, 1.0, 1.0])  # [L, W, H]

                # KITTI 형식은 [h, w, l, X, Y, Z, yaw] 순
                h = scale[2]
                w = scale[1]
                l = scale[0]
                x = pos[0]
                y = pos[1]
                z = pos[2]
                yaw = rot[2]  # 보통 z축 회전을 yaw로 가정

                annotation_list.append((class_name, h, w, l, x, y, z, yaw))
    except Exception as e:
        print(f"Error parsing JSON file {json_path}: {e}")

    return annotation_list


def write_label_txt(label_txt_path, annos):
    """
    annos: [ (class_name, h, w, l, x, y, z, yaw), ... ]
    KITTI-like 포맷으로 씁니다.
    <type> <truncated> <occluded> <alpha> <x1> <y1> <x2> <y2> <h> <w> <l> <X> <Y> <Z> <rotation_y>
    여기서는 2D bbox가 없으므로 (x1,y1,x2,y2) = (0,0,50,50) 등 임의값, alpha=0, truncated=0, occluded=0.
    """
    with open(label_txt_path, 'w', encoding='utf-8') as f:
        for anno in annos:
            class_name, h, w, l, X, Y, Z, yaw = anno
            truncated = 0
            occluded = 0
            alpha = 0
            x1, y1, x2, y2 = (0, 0, 50, 50)  # 가상값
            line = f"{class_name} {truncated} {occluded} {alpha} {x1} {y1} {x2} {y2} {h:.2f} {w:.2f} {l:.2f} {X:.2f} {Y:.2f} {Z:.2f} {yaw:.2f}\n"
            f.write(line)


def main():
    parser = argparse.ArgumentParser(description="Convert PCD + JSON -> BIN + TXT for PointPillars")
    parser.add_argument("--pcd_path", type=str,
                        default="/home/user/temp/train/lidar",
                        help="path to directory containing .pcd files")
    parser.add_argument("--json_path", type=str,
                        default="/home/user/temp/train/label",
                        help="path to directory containing .json label files")
    parser.add_argument("--out_dir", type=str,
                        default="/home/user/temp/train_processed",
                        help="output directory for .bin and .txt files")
    parser.add_argument("--intensity_scale", type=float,
                        default=256.0,
                        help="divide intensity by this scale factor (default=256)")
    args = parser.parse_args()

    print("=== Settings ===")
    print("pcd_path:", args.pcd_path)
    print("json_path:", args.json_path)
    print("out_dir:", args.out_dir)
    print("intensity_scale:", args.intensity_scale)
    print("================")

    # 1) 출력 디렉토리 생성
    lidar_out_dir = os.path.join(args.out_dir, "lidar")
    label_out_dir = os.path.join(args.out_dir, "label")
    create_dir_if_not_exists(lidar_out_dir)
    create_dir_if_not_exists(label_out_dir)

    # 2) JSON에 정의된 전체 클래스 이름을 파악하기 위해
    categories = []
    json_files = [f for f in os.listdir(args.json_path) if f.endswith(".json")]
    if len(json_files) < 1:
        print("No JSON files found in", args.json_path)
        return
    sample_json_path = os.path.join(args.json_path, json_files[0])
    with open(sample_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        try:
            raw_list = data["categories"]["label"]["labels"]
            for r in raw_list:
                categories.append(r["name"])  # ["사람", "손수레", ...]
        except Exception as e:
            print(f"Error extracting categories from {sample_json_path}: {e}")
    print("Detected categories:", categories)

    # 3) PCD 파일 목록을 가져오고, JSON을 매칭
    pcd_files = [f for f in os.listdir(args.pcd_path) if f.endswith(".pcd")]
    pcd_files.sort()

    print(f"Found {len(pcd_files)} PCD files.")
    idx = 0

    for pcd_fname in tqdm(pcd_files, desc="Converting PCD and JSON files"):
        base_name_with_img = os.path.splitext(pcd_fname)[0]  # e.g. MA_011_HR_20231110_PM_001_000_000_0000_IMG
        # JSON 파일명 매칭: _IMG 제거 후 _CUB 추가
        if base_name_with_img.endswith("_IMG"):
            base_name = base_name_with_img[:-4]  # Remove '_IMG'
        else:
            base_name = base_name_with_img  # 그대로 사용

        json_fname = f"{base_name}_CUB.json"

        pcd_path_full = os.path.join(args.pcd_path, pcd_fname)
        json_path_full = os.path.join(args.json_path, json_fname)

        # 1) pcd -> bin 변환
        try:
            pc = o3d.io.read_point_cloud(pcd_path_full)
            points = np.asarray(pc.points)  # (N, 3)
            # Intensity 값이 없을 경우, 0으로 채움
            if hasattr(pc, 'colors') and len(pc.colors) > 0:
                # Assuming intensity is mapped to one of the color channels, e.g., red
                intensity = np.asarray(pc.colors)[:, 0]
                intensity = intensity.astype(np.float32) * args.intensity_scale  # Scale back if needed
            else:
                intensity = np.zeros((points.shape[0],), dtype=np.float32)

            # Stack (x, y, z, intensity)
            points_32 = np.hstack((points, intensity.reshape(-1, 1))).astype(np.float32)

            bin_fname = f"{idx:06d}.bin"
            bin_path_full = os.path.join(lidar_out_dir, bin_fname)
            points_32.tofile(bin_path_full)
        except Exception as e:
            print(f"Error processing PCD file {pcd_path_full}: {e}")
            points_32 = np.zeros((1, 4), dtype=np.float32)  # Placeholder

        # 2) json -> txt 변환
        if os.path.exists(json_path_full):
            annos = parse_json_label(json_path_full, categories)
        else:
            # 해당 json이 없는 경우 처리
            print(f"Warning: JSON file {json_path_full} does not exist. Skipping annotations.")
            annos = []
        txt_fname = f"{idx:06d}.txt"
        txt_path_full = os.path.join(label_out_dir, txt_fname)
        write_label_txt(txt_path_full, annos)

        idx += 1

    print("Done. Converted", idx, "PCD files into .bin and created .txt labels.")
    print(f"Output structure is in: {args.out_dir}/lidar, {args.out_dir}/label")


if __name__ == "__main__":
    main()

