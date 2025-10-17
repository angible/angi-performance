import math
import os
from typing import Union

import yaml
from ai_perception.detection.utils.ultralytics_utils import PredictorType
from ai_perception.helper.config_helper import CustomBaseSettings
from loguru import logger
from utils.roi_areas import RoIRegion


def load_ai_service_config(cfg_path):
    if cfg_path.endswith(".yaml"):
        with open(cfg_path) as fid:
            yaml_data = yaml.safe_load(fid)
            if yaml_data.get("cameras", None):
                cameras_dict = yaml_data.get("cameras")
                cameras_dict = yaml_data.get("cameras")
                logger.debug(f"before cameras dict {cameras_dict}")
                for cam_name, cam_config in cameras_dict.items():
                    cam_config = CVCaptureServiceConfig(**cam_config)
                    cam_config.dst_frame_width = (
                        cam_config.ori_frame_width + cam_config.default_barcode_width
                    )
                    cam_config.dst_frame_height = (
                        cam_config.ori_frame_height + cam_config.default_barcode_height
                    )
                    cameras_dict[cam_name] = cam_config
                logger.debug(f"after cameras dict {cameras_dict}")
                cameras = CameraConfig(cameras_config=cameras_dict)
                logger.debug(f"cameras {cameras}")
                yaml_data["cameras"] = cameras
        camera_name = os.getenv("CAMERA_NAME", None)
        rtsp_source = os.getenv("RTSP_SOURCE", None)
        inference_device = os.getenv("INFERENCE_DEVICE", None)
        if camera_name:
            if rtsp_source:
                cameras.cameras_config[camera_name].source = rtsp_source
            if inference_device:
                if inference_device not in ["intel:CPU", "intel:GPU", "intel:NPU"]:
                    raise ValueError("Invalid inference device, should be 'intel:CPU', 'intel:GPU', 'intel:NPU'")
                cameras.cameras_config[camera_name].inference_device = inference_device
        config = AIServiceConfig(**yaml_data)

        # Apply logger configuration if present
        if config.logger and config.logger.log_level:
            from utils.helper import MyLoguruLogger

            MyLoguruLogger.set_config_log_level(config.logger.log_level)

        return config
    else:  # should be endswith .env
        return AIServiceConfig(_env_file=cfg_path)


# todo: move it
class DetectionModelConfig(CustomBaseSettings):
    # CPU/0/1/2/3/...
    ai_model_device: str = "0"
    # file path
    ai_model_path: str = ""
    # inference params
    confidence_threshold: float = 0.6
    ai_model_format: str = "openvino"
    ai_result_dir: str = ""
    load_existed_results: bool = False
    load_existed_results_version: str = "v1"
    existed_ai_results_dir: str = ""
    # debug
    enable_inference_verbose: bool = False

    filtered_classes_names: list[str] | None = None

    two_stage_classify_enable: bool = True
    two_stage_classify_model_path: str = (
        "../../ai_model/classification/20240419_object_hands_openvino_model"
    )
    two_stage_classify_targets: list[str] | None = ["hand_product"]
    category_group_dict_index: int = 0

    clssify_model_with_embedding_enable: bool = False
    cls_scale_factor: float = 1.2
    # non-maximum merge
    non_max_merge_enable: bool = True
    non_max_merge_threshold: float = 0.7

    mask_border_width_list: list = [0, 0, 0, 0]
    categories: list = []
    filter_hands: bool = True

    detection_zip_password: str | None = "Angible123!"

    detection_temp_folder_suffix: str = "_angible"
    iou_threshold: float = 0.5
    padding_enable: bool = False
    bbox_scaling_enable: bool = False
    bbox_scaling_factor: float = 1.0

    predictor_type: str = PredictorType.DEFAULT.value  # numpy_postprocess, default, jde

    def get_ai_version_string(self) -> str:
        x = self.ai_model_path
        if x.endswith(".pt") or x.endswith(".engine") or x.endswith(".onnx"):
            v = os.path.basename(os.path.dirname(os.path.dirname(x)))
        else:
            x = os.path.basename(x)
            v = x.split("_object_hands_openvino_model")[0]
        return v

    @classmethod
    def from_yaml(cls, yaml_path):
        yaml_fpath = os.path.abspath(yaml_path)
        with open(yaml_fpath) as fid:
            yaml_data = yaml.safe_load(fid)
        return cls(**yaml_data)


class OdConfig(DetectionModelConfig):
    enable: bool = False


class TrackingServiceConfig(CustomBaseSettings):
    asso_func: str = "ciou"
    w_association_emb: float = 0.5
    max_age: float = 1  # 1 for 1 sec, 2 for sec
    min_hits: int = 1
    tracking_class_names: list[str] | None = None
    save_result_enable: bool = False
    export_track_result_path: str | None = "tracking_result"
    tracker_type: str = (
        "yolov7_tracker_ocsort"  # deepocsort or ocsort or masa or yolov7_tracker_ocsort
    )
    reid_model_weights: str = "../../ai_model/reid/osnet_x0_25_openvino_model"
    simple_annotation: bool = False
    asso_threshold: float = 0.3
    asso_threshold_second: float = 0.3
    od_tracker_type: str = "ocsort"
    track_detect_threshold: float = 0.15
    load_existed_results: bool = False
    load_existed_results_version: str = "v1"
    existed_ai_results_dir: str = ""
    use_sigmoid_to_normalize_cost: bool = True
    tracktrack_high_nms: float = 0.6
    tracktrack_low_nms: float = 0.3
    cmtrack_interval: float = 0.2


# todo: how to support arbitrary RoI definition?
class RoISetting(CustomBaseSettings):
    normalized_enable: bool = False
    scan: Union[RoIRegion, list, None] = RoIRegion(roi=[376, 225, 455, 288], thres=0.1)
    pack1: Union[RoIRegion, list, None] = RoIRegion(roi=[124, 20, 231, 217], thres=0.5)
    pack2: Union[RoIRegion, list, None] = RoIRegion(roi=[455, 4, 613, 233], thres=0.5)
    crop: Union[RoIRegion, list, None] = None
    table: Union[RoIRegion, list, None] = None


class MatchingConfig(CustomBaseSettings):
    MATURE_DWELL_WINDOW_SIZE: int = 3
    MATURE_SCAN_EVENT_MIN_FRAME: int = 6  # 0.4s @ 15fps
    MATURE_SCAN_EVENT_MIN_DISTANCE: float = (
        200  # minimum distance for scan event maturity
    )

    # Maximum number of unmatched events to keep in the sliding window
    OBJECT_WINDOW_SIZE: int = 10
    BARCODE_WINDOW_SIZE: int = 10
    # Matching Algorithm Parameters
    COST_THRESHOLD: float = (
        1000  # Maximum cost for a valid match. A key parameter for precision.
    )
    WEIGHT_DEAD_IN_TARGET: float = 100
    WEIGHT_TEMPORAL: float = 10  # Contribution of time difference to the total cost
    WEIGHT_ORDINAL: float = (
        1  # Contribution of sequence order difference to the total cost
    )
    # Expected delay range from video event to barcode event (in frames)
    EXPECTED_DELAY_FRAMES_MIN: float = -37
    EXPECTED_DELAY_FRAMES_MAX: float = 75
    # Frame-based TTL parameters (assuming 15 FPS)
    OBJECT_EVENT_TTL_FRAMES: int = 120  # 8 seconds at 15 FPS
    BARCODE_EVENT_TTL_FRAMES: int = 180  # 12 seconds at 15 FPS


class AlarmConfig(CustomBaseSettings):
    rule_1: bool = True
    rule_2: bool = True
    rule_3: bool = True
    rule_4: bool = True


class LogicConfig(CustomBaseSettings):
    barcode_calibrate_threshold: float = 0.5
    barcode_calibrate_threshold2: float = 1.34
    revive_cooldown_time: float = 0.5
    revive_threshold_iou: float = 0.5
    revive_threshold_dt: float = 0.5
    stitch_missing_item_dt: list[float, float] = [-1, 5]
    scanning_gun_radius: float = 1.5  # if an item's boundary reach 1.5x gun's box size, it is regarded as scanning
    bool_tracking121: bool = True
    tracking121_iou_thres: float = 0.3
    reset_count_duration: int = 4  # seconds
    track_died_check_shifting_frames: int = 45
    track_died_check_frames: int = 75
    barcode_matching_time_shifts: list[float] = [-1, -0.5, 0, 1, 2, 3, 4, 5]
    nonweighting_camera_list: list[str] = ['1189-ch03', '1007-ch03', 'cam3', 'cam9']
    barcode_delay_frames: int = 75
    moving_out_event_quick_survive_frames: int = 15 # 1s,
    missing_delay_min_frames: int = -20
    missing_delay_max_frames: int = 75
    mismatched_delay_min_frames: int = -45
    mismatched_delay_max_frames: int = 15
    moving_out_event_max_survive_frames: int | None = None
    matching_config: MatchingConfig = MatchingConfig()
    alarm_config: AlarmConfig = AlarmConfig()
    valid_scan_event_frames_diff: int = 60  # 4 seconds
    camera_delay_mapping: dict[str, int] = {
        "cam2": 75,
        "cam6": 75,
        "cam3": 75,
        "cam7": 75,
        "cam11": 75,
        "cam5": 75,
        "cam1": 75,
        "cam10": 75,
        "cam8": 75,
        "cam9": 75,
        "cam4": 75,
    }
    rule_zero_enable_camera_list: list[str] = [
        "cam1",
        "cam2",
        "cam3",
        "cam4",
        "cam5",
        "cam6",
        "cam7",
        "cam8",
        "cam9",
        "cam10",
        "cam11",
    ]

    def model_post_init(self, __context):
        self.moving_out_event_max_survive_frames = self.barcode_delay_frames


class AIMainSetting(CustomBaseSettings):
    version: str = "v1"
    detection: DetectionModelConfig = None
    od: Union[DetectionModelConfig, None] = None
    od_enable: bool = False
    tracking: TrackingServiceConfig = None
    tracking_od: TrackingServiceConfig = None
    roi: Union[RoISetting, None] = RoISetting()
    logic: LogicConfig = None
    weighting: bool = True
    hand_hold_class_agnostic_enable: bool = False


class VisualizerSetting(CustomBaseSettings):
    resize_preview_window: list = [1280, 720]
    change_preview_window_size: bool = True
    show_timestamps: bool = True
    display_show: bool = False
    show_id: bool = True
    show_traj: bool = True
    show_conf: bool = True
    show_ho: bool = True
    show_od: bool = False
    show_od_id: bool = False
    show_od_conf: bool = False
    show_od_name: bool = False
    show_roi_name: bool = False
    show_ho_non_matched_detections: bool = True
    show_od_non_matched_detections: bool = True
    attach_barcode_enable_in_vis: bool = False  # please set it True when in production, there are some bugs in the barcode attach feature when setting to False
    attach_side: str = "left"  # left or right
    attach_barcode_width: int = 250
    show_no_scan_info: bool = False
    show_nonweight_info: bool = False

    show_static_warning_event: bool = True


class CVWriterServiceConfig(CustomBaseSettings):
    frame_width: int = 0
    frame_height: int = 0
    camera_fps: int = 0

    env: str = ""
    cam: str = ""
    date: str = ""
    dump_root: str = "dump"
    dump_root_labeler: str = "dump"
    filename: str = ""

    write_raw: bool = True
    write_ai: bool = False
    max_streaming_frame: int = (
        15 * 60 * 60
    )  # reach frame limit, will switch to a new video

    write_segment_clip: bool = True
    clip_image_buffer: int = 15 * 30
    instant_clip_frame_num: int = 15 * 10

    write_video_enable: bool = True

    ai_dump_root: str = ""

    serial_cache_path: str = ""

    class Config:
        env_file = None

    def model_post_init(self, __context):
        # logic_v0.3.0_OD_v0.0.7
        import version

        tmp_dump_root = self.dump_root.replace("${date}", self.date).replace(
            "${cam}", self.cam
        )
        self.serial_cache_path = os.path.join(tmp_dump_root, "serials")
        self.dump_root = os.path.join(
            tmp_dump_root,
            f"logic_v{version.AI_LOGIC_VERSION}_HOD_{version.AI_HOD_VERSION}_TRACK_{version.AI_TRACK_VERSION}",
        )
        self.ai_dump_root = os.path.join(
            tmp_dump_root,
            f"HOD_v{version.AI_HOD_VERSION}_TRACK_{version.AI_TRACK_VERSION}",
        )


class CVCaptureServiceConfig(CustomBaseSettings):
    camera_name: str = ""
    mediamtx_barcode_output_path: str = ""
    mediamtx_ai_output_path: str = ""
    frame_width: int = 0
    frame_height: int = 0
    ori_frame_width: int = 640
    ori_frame_height: int = 480
    dst_frame_width: int = 640
    dst_frame_height: int = 480
    default_barcode_height: int = 0
    default_barcode_width: int = 0
    attach_barcode_enable: bool = False
    camera_fps: float = 0
    capture_buffer_size: int = 0
    limit_fps: float = 0
    resize_before_capture: bool = False

    source: Union[str, int] = 0  # todo: should this be writtern in config?

    start_timestamp: float = 0
    start_frame: int = 0
    end_frame: float = math.inf
    # todo: remove this
    corner_timestamp_enable: bool = False
    drop_frame_when_full: bool = False  # when queue is full, whether wait for queue to be empty or drop the frame
    inference_device: str = "AUTO"  # 'intel:CPU', 'intel:GPU', 'intel:NPU'
    ai_enable: bool = True

    ffmpeg_path: str = "/usr/lib/ffmpeg/7.0/bin/ffmpeg"
    codec: str = "hevc"
    hwaccel: str = "qsv"

    ai_model_path: str | None = None
    od_enable: bool | None = None

    use_dummy_image_as_source_enable: bool = False

    barcode_mode_enable: bool = True
    barcode_decode_type: str = "barcode"
    production_reproduce_mode: bool = False

    use_frame_index_as_scan_frame_index: bool = False

    video_parse_cache_root_dir: str = "/data/mnt/mnt_txdatas/video-result-cache"
    # video_parse_cache_dir: str = ""
    customer_region: str = "Central-TH"
    customer: str = "Central"
    store_name: str = "westgate"
    machine_name: str = "NUC009"


    class Config:
        env_file = None

    # def model_post_init(self, __context):
    #     self.video_parse_cache_dir = os.path.join(self.video_parse_cache_root_dir, self.customer_region, self.customer, self.store_name, self.machine_name)

class CameraConfig(CustomBaseSettings):
    cameras_config: dict[str, CVCaptureServiceConfig]


class ScoExternalConfig(CustomBaseSettings):
    mediamtx_playback_url: str = "http://host.docker.internal:9996"
    callback_url: str = (
        "http://host.docker.internal:10000/v1/ai-service/{sco_id}/alerts"
    )
    video_cut_before_duration: int = 3  # second
    video_cut_after_duration: int = 1  # second
    static_video_cut_before_duration: int = 10  # second
    static_video_cut_after_duration: int = 0  # second
    event_saving_folder: str = "/data/ai_events"
    timezone: str = "Asia/Taipei"
    video_cut_when_transaction_start: bool = False
    send_alert_enable: bool = True
    wait_before_cutting: int = (
        0  # seconds, wait before cut the video after the event is detected
    )
    filter_abnormal_video_duration_enable: bool = True
    abnormal_video_duration_threshold: int = 8  # seconds, if  (the real event duration) - (the video cut duration) > this threshold, the video will be filtered out)
    use_tracker_start_ts_as_clip_start_time: bool = False


class StorageMaintenanceConfig(CustomBaseSettings):
    target_folders: list[str] = ["/data/ai_events"]
    file_age_in_days: int = 3
    file_extension_list: list[str] = ["*.mp4", "*.json", "*.jpg"]

    class Config:
        env_file = None


class ExportConfig(CustomBaseSettings):
    od_export_enable: bool = True
    ho_export_enable: bool = True
    statistic_export_enable: bool = True
    generate_ai_results_enable: bool = False
    ai_export_results_path: str | None = None


class LoggerConfig(CustomBaseSettings):
    log_level: str = "INFO"  # TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR


class PipeLineConfig(CustomBaseSettings):
    pipeline_model_enable: bool = False
    global_serial_cache_path: str = (
        "/data/mnt/mnt_txdatas/txdetails/{}/{}/{}"
    )
    global_ai_artifact_data_path: str = (
        "/data/mnt/mnt_txdatas/ai-artifacts/{}/{}/{}/data"
    )
    global_ai_artifact_original_path: str = (
        "/data/mnt/mnt_txdatas/ai-artifacts/{}/{}/{}/original"
    )
    global_ai_e2e_dump_root: str = (
        "/data/mnt/mnt_txdatas/ai-artifacts/{}/{}/{}/e2e_results"
    )
    global_dump_root: str = ""
    customer: str = "Central"
    customer_regeion: str = "Central-TH"
    store_name: str = "westgate"
    machine_name: str = "NUC009"
    pipeline_e2e_version: str = ""

    def model_post_init(self, __context):
        import version

        self.global_serial_cache_path = self.global_serial_cache_path.format(
            self.customer_regeion, self.store_name, self.machine_name
        )
        self.global_ai_artifact_data_path = self.global_ai_artifact_data_path.format(
            self.customer_regeion, self.store_name, self.machine_name
        )
        self.global_ai_artifact_original_path = (
            self.global_ai_artifact_original_path.format(
                self.customer_regeion, self.store_name, self.machine_name
            )
        )
        self.global_ai_e2e_dump_root = self.global_ai_e2e_dump_root.format(
            self.customer_regeion, self.store_name, self.machine_name
        )
        self.global_ai_e2e_dump_root = os.path.join(
            self.global_ai_e2e_dump_root,
            f"LOGIC_v{version.AI_LOGIC_VERSION}_HOD_{version.AI_HOD_VERSION}_TRACK_{version.AI_TRACK_VERSION}",
        )
        self.pipeline_e2e_version = f"LOGIC_v{version.AI_LOGIC_VERSION}_HOD_{version.AI_HOD_VERSION}_TRACK_{version.AI_TRACK_VERSION}"

class AIServiceConfig(CustomBaseSettings):
    capture: CVCaptureServiceConfig = None
    cameras: CameraConfig = None
    writer: CVWriterServiceConfig = None
    ai: AIMainSetting = None
    visualizer: VisualizerSetting = None
    sco: ScoExternalConfig = None
    export: ExportConfig = ExportConfig()
    storage_maintenance: StorageMaintenanceConfig = StorageMaintenanceConfig()
    logger: LoggerConfig = LoggerConfig()
    pipeline: PipeLineConfig = PipeLineConfig()
