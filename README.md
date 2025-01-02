# AI허브 과수원 로봇 주행 데이터 KITTI 형식 변환기

이 프로젝트는 **AI허브**에서 제공하는 과수원 내 로봇 주행 데이터를 **KITTI 형식**에 맞게 변환하기 위한 코드입니다. 이 코드를 사용하면 **PCD 파일**과 **JSON 라벨** 파일을 **PointPillars** 모델에서 사용할 수 있는 **BIN** 및 **TXT** 파일로 변환할 수 있습니다.

## 프로젝트 설명

이 코드는 **PCD 파일**과 **JSON 라벨 파일**을 받아, KITTI 형식에 맞는 3D 객체 라벨 데이터와 **Lidar Point Cloud** 데이터를 생성합니다. 생성된 파일은 **PointPillars** 모델에서 사용할 수 있으며, 각각 **.bin** (포인트 클라우드)과 **.txt** (라벨) 형식으로 저장됩니다.

**아직 테스트조차 하지 않은 코드입니다.작동시 문제가 생길 수 있습니다.**

## 필수 라이브러리

이 코드를 실행하려면 다음 라이브러리들이 필요합니다. 아래 명령어를 통해 설치할 수 있습니다:

```bash
pip install open3d numpy tqdm
```
## 디렉토리 구조

터미널에서 다음 명령어를 실행하여 PCD 파일과 JSON 라벨을 KITTI 형식으로 변환할 수 있습니다.
```bash
/train_processed
  ├── /lidar      # .bin 포인트 클라우드 파일들
  └── /label      # .txt 라벨 파일들
```
## 사용 방법

터미널에서 다음 명령어를 실행하여 PCD 파일과 JSON 라벨을 KITTI 형식으로 변환할 수 있습니다.


```bash
python3 convert_pcd_json.py \
    --pcd_path \
    --json_path \
    --out_dir
```


