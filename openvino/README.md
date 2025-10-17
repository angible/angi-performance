## OpenVINO Docker Deployment

### Install NPU driver in host first

### Install IGPU driver in host first

### Install docker and docker compose


### Pull docker image
```bash
docker pull ghcr.io/joesu-angible/angi-performance/openvino-gpu-npu
docker tag ghcr.io/joesu-angible/angi-performance/openvino-gpu-npu openvino-gpu-npu
```

### Export AI Model
```bash
docker run --rm -it --entrypoint "" -v $(pwd)/ai_model:/host --workdir /app/project openvino-gpu-npu bash -c "python3 scripts/jde/export.py --model ../ai_model/detection_hod_jde/v0.2.1_640_fp16/best.pt --format openvino --imgsz 640,640 --half && cp ../ai_model/detection_hod_jde/v0.2.1_640_fp16/metadata.yaml ../ai_model/detection_hod_jde/v0.2.1_640_fp16/best_openvino_model/ && cp -r ../ai_model/detection_hod_jde /host/"
```

### Configure RTSP Source (Optional)

Set the RTSP server IP address (default: 10.10.70.105):
```bash
export RTSP_HOST=192.168.1.100
```

### Configure Inference Device (Optional)

Set the inference device for each camera. Valid values: `intel:GPU`, `intel:NPU`, `intel:CPU`

**Default configuration:**
- CAM1: intel:GPU
- CAM2: intel:NPU
- CAM3: intel:GPU
- CAM4: intel:NPU
- CAM5: intel:GPU
- CAM6: intel:GPU
- CAM7: intel:CPU

**Override specific cameras:**
```bash
export INFERENCE_DEVICE_CAM1=intel:NPU
export INFERENCE_DEVICE_CAM2=intel:GPU
export INFERENCE_DEVICE_CAM7=intel:GPU
```

**Or create a `.env` file in the same directory:**
```bash
cat > .env << EOF
RTSP_HOST=10.10.70.105
INFERENCE_DEVICE_CAM1=intel:NPU
INFERENCE_DEVICE_CAM2=intel:GPU
INFERENCE_DEVICE_CAM3=intel:GPU
INFERENCE_DEVICE_CAM4=intel:NPU
INFERENCE_DEVICE_CAM5=intel:GPU
INFERENCE_DEVICE_CAM6=intel:GPU
INFERENCE_DEVICE_CAM7=intel:CPU
EOF
```

### Run AI Service
```bash
export RTSP_HOST=10.10.70.105 && docker compose -f docker-compose.openvino.dev.yml up -d --force-recreate
```