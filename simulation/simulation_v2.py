#!/usr/bin/env python3
"""
RTSP Stream Simulator V2 - Refactored
Self-hosted RTSP server with QR code processing
"""

import cv2
import numpy as np
import subprocess
import threading
import queue
from collections import deque
import time
import sys
import argparse
import json
import requests
import uuid
import yaml
import os
import re
import gdown
from loguru import logger
from datetime import datetime, timezone
import pytz

import gi
gi.require_version('Gst', '1.0')  # noqa: E402
gi.require_version('GstRtspServer', '1.0')  # noqa: E402
from gi.repository import Gst, GstRtspServer, GLib  # noqa: E402

import schemas  # noqa: E402

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)


def draw_datetime_on_frame(frame, timestamp, position=(10, 40), font_scale=0.7, 
                           font_thickness=1, font_color=(0, 255, 255), 
                           bg_color=(0, 0, 0)):
    """
    Draw datetime on a video frame.
    
    Args:
        frame: The video frame (numpy array)
        timestamp: datetime object to display
        position: (x, y) position for text (default: (10, 40))
        font_scale: Font scale (default: 0.7)
        font_thickness: Font thickness (default: 1)
        font_color: Font color in BGR format (default: yellow)
        bg_color: Background color in BGR format (default: black)
    
    Returns:
        Modified frame with datetime drawn on it
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Format datetime as text
    datetime_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    # Get text size for background rectangle
    (text_width, text_height), baseline = cv2.getTextSize(
        datetime_text, font, font_scale, font_thickness
    )
    
    # Draw background rectangle
    cv2.rectangle(
        frame,
        (position[0] - 5, position[1] - text_height - 5),
        (position[0] + text_width + 5, position[1] + baseline + 5),
        bg_color,
        -1  # Filled rectangle
    )
    
    # Draw datetime text
    cv2.putText(
        frame,
        datetime_text,
        position,
        font,
        font_scale,
        font_color,
        font_thickness,
        cv2.LINE_AA
    )
    
    return frame


def get_current_timestamp(tz=None):
    """
    Get current timestamp in milliseconds.
    
    Args:
        tz: Optional timezone (pytz timezone object or datetime.timezone object). Defaults to UTC if None.
        
    Returns:
        int: Timestamp in milliseconds
    """
    if tz is None:
        tz = timezone.utc
    return int(datetime.now(tz).timestamp() * 1000)


class RTSPSimulatorV2:
    """Refactored RTSP Simulator with cleaner architecture"""
    
    def __init__(
        self,
        camera_name: str,
        video_path: str,
        rtsp_port: int,
        api_url: str,
        fps: int = 15,
        original_width: int = 640,
        original_height: int = 800,
        frame_width: int = 640,
        frame_height: int = 480,
        qrcode_size: int = 160,
        queue_size: int = 30,
        warmup_frames: int = 60,
        timezone_str: str = "UTC"
    ):
        self.camera_name = camera_name
        self.video_path = video_path
        self.rtsp_port = rtsp_port
        self.api_url = api_url
        self.fps = fps
        self.original_width = original_width
        self.original_height = original_height
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.qrcode_size = qrcode_size
        self.warmup_frames = warmup_frames
        
        # Timezone
        try:
            self.timezone = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{timezone_str}', falling back to UTC")
            self.timezone = pytz.UTC
        logger.info(f"Using timezone: {self.timezone}")
        
        # Shared data structures
        self.decode_queue = queue.Queue(maxsize=queue_size)  # VideoReader -> QRProcessor (frame1, frame2, sim_time)
        self.frame_buffer = deque(maxlen=queue_size)  # QRProcessor -> RTSP streaming (frame1, sim_time)
        self.frame_lock = threading.Lock()
        
        self.request_queue = queue.Queue(maxsize=100)  # QRProcessor -> API requests
        
        # Control
        self.stop_event = threading.Event()
        self.transaction_id = str(uuid.uuid4())
        
        # API URL mapping
        self.barcode_type_url_path: dict = {
            schemas.BarcodeType.TRANSACTION_STARTED: "/events/{sco_id}/transaction-started",
            schemas.BarcodeType.TRANSACTION_COMPLETED: "/events/{sco_id}/transaction-completed",
            schemas.BarcodeType.ITEM_ADDED: "/events/{sco_id}/item-added",
            schemas.BarcodeType.ITEM_REMOVED: "/events/{sco_id}/item-removed",
            schemas.BarcodeType.STATE: "/events/{sco_id}/states",
            schemas.BarcodeType.SCAN_STARTED: "/events/{sco_id}/scan-started",
            schemas.BarcodeType.SCAN_COMPLETED: "/events/{sco_id}/scan-completed",
            schemas.BarcodeType.WEIGHTING_SCALE_NOT_MATCHED: "/events/{sco_id}/weighting-scale-not-matched",
        }
        
        self.cam_sco_mapping: dict = {
            "cam1": "CFRW1CSCOPO6776",
            "cam2": "CFRW1CSCOPO6541",
            "cam3": "CFRW1CSCOPO1189",
            "cam4": "CFRW1CSCOPO6592",
            "cam5": "CFRW1CSCOPO6591",
            "cam6": "CFRW1CSCOPO6744",
            "cam7": "CFRW1CSCOPO6714",
            "cam8": "CFRW1CSCOPO8300",
            "cam9": "CFRW1CSCOPO1007",
            "cam10": "CFRW1CSCOPO8209",
            "cam11": "CFRW1CSCOPO8208",
        }
        self.sco_id = self.cam_sco_mapping.get(self.camera_name, None)
        if not self.sco_id:
            self.sco_id = "UNDEFINE_SCO_ID"
        
        # Statistics
        self.stats_lock = threading.Lock()
        self.stats = {
            'frames_read': 0,
            'qr_decoded': 0,
            'api_sent': 0,
            'frames_streamed': 0,
            'errors': 0
        }
        
        # FPS tracking
        self.decode_fps_counter = 0
        self.decode_fps_start = time.time()
        self.encode_fps_counter = 0
        self.encode_fps_start = time.time()
        
    def update_stats(self, key: str):
        """Thread-safe stats update"""
        with self.stats_lock:
            self.stats[key] += 1
    
    # ==================== Thread 1: Video Reader ====================
    def thread_video_reader(self):
        """
        Thread 1: Read video with ffmpeg and decode frames
        Reads original video (original_width x original_height) and crops into two parts:
        - Frame 1: Main video frame cropped to [:frame_height, :frame_width, :]
        - Frame 2: QR code region from original frame [original_height-qrcode_size:original_height, original_width-qrcode_size:original_width, :]
        """
        logger.info(f"[VideoReader] Starting video decoder: {self.video_path}")
        
        # FFmpeg command to read video and output raw frames
        ffmpeg_cmd = [
            'ffmpeg',
            '-re',  # Read input at native frame rate
            '-stream_loop', '-1',  # Loop video indefinitely
            '-i', self.video_path,
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-r', str(self.fps),
            '-'
        ]
        
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10**8
            )
            
            # Get video dimensions (use original dimensions for reading)
            frame_size = self.original_height * self.original_width * 3
            i = 0
            while not self.stop_event.is_set():
                raw_frame = process.stdout.read(frame_size)
                i += 1
                if len(raw_frame) != frame_size:
                    logger.warning("[VideoReader] End of stream or read error, restarting...")
                    process.terminate()
                    process.wait()
                    # Restart ffmpeg process
                    process = subprocess.Popen(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        bufsize=10**8
                    )
                    continue
                
                # Convert raw bytes to numpy array
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((self.original_height, self.original_width, 3)).copy()
                sim_time = get_current_timestamp(self.timezone)
                # Convert millisecond timestamp to datetime object for display (localized to timezone)
                frame = draw_datetime_on_frame(frame, datetime.fromtimestamp(sim_time / 1000, tz=self.timezone))
                # Crop frame 1: Main video frame to target dimensions
                # Crop from top-left (0, 0) to (frame_height, frame_width)
                frame1 = frame[:self.frame_height, :self.frame_width, :].copy()
                # frame_name = Path(f"debug/frame_{i}.jpg")
                # frame_name.parent.mkdir(parents=True, exist_ok=True)
                # cv2.imwrite(str(frame_name), frame1)
                # Crop frame 2: QR code region from original frame (bottom-right qrcode_size x qrcode_size)
                # From coordinates (original_height-qrcode_size, original_width-qrcode_size) to (original_height, original_width)
                frame2 = frame[
                    self.original_height-self.qrcode_size:self.original_height,
                    self.original_width-self.qrcode_size:self.original_width,
                    :
                ].copy()
                
                # Put both frames as tuple into decode queue
                try:
                    self.decode_queue.put((frame1, frame2, sim_time), timeout=1.0)
                    self.update_stats('frames_read')
                    self.update_decode_fps()  # Update decode FPS counter
                except queue.Full:
                    logger.warning("[VideoReader] Decode queue full, dropping frame")
                    continue
            
            process.terminate()
            process.wait()
            
        except Exception as e:
            logger.exception(f"[VideoReader] Error: {e}")
            self.update_stats('errors')
            self.stop_event.set()
        
        logger.info("[VideoReader] Video decoder stopped")
    
    # ==================== Thread 2: QR Processor ====================
    def thread_qr_processor(self):
        """
        Thread 2: Process QR codes and distribute frames
        - Decodes QR code from frame2
        - Sends QR data to request_queue (Thread3)
        - Sends frame1 to frame_buffer (Thread4 RTSP)
        """
        logger.info("[QRProcessor] Starting")
        
        detector = cv2.QRCodeDetector()
        frame_counter = 0
        qr_detect_times = []
        log_interval = 100  # Log stats every 100 frames
        
        while not self.stop_event.is_set():
            try:
                loop_start = time.time()
                
                # Get frames from VideoReader
                frame1, frame2, sim_time = self.decode_queue.get(timeout=1.0)
                frame_counter += 1
                
                # Monitor queue depth
                decode_queue_size = self.decode_queue.qsize()
                
                # Decode QR code from frame2 using OpenCV
                qr_start = time.time()
                qr_data = None
                try:
                    data, vertices_array, _ = detector.detectAndDecode(frame2)
                    qr_time = (time.time() - qr_start) * 1000  # ms
                    qr_detect_times.append(qr_time)
                    
                    if data:
                        # QR code detected and decoded
                        qr_data = data
                        self.update_stats('qr_decoded')
                        
                        # Try to parse as JSON
                        try:
                            qr_json = json.loads(qr_data)
                            qr_data = qr_json
                        except json.JSONDecodeError:
                            # Keep as string if not valid JSON
                            pass
                        
                        # Put to request queue for Thread3
                        try:
                            self.request_queue.put((qr_data, sim_time), timeout=0.5)
                        except queue.Full:
                            logger.warning("[QRProcessor] Request queue full, dropping QR data")
                
                except Exception as e:
                    # QR decode failed, skip
                    qr_time = (time.time() - qr_start) * 1000
                    qr_detect_times.append(qr_time)
                    logger.debug(f"[QRProcessor] QR decode exception: {e}")
                
                # Put frame1 to frame buffer for Thread4 (RTSP)
                # deque with maxlen automatically drops oldest when full
                lock_start = time.time()
                with self.frame_lock:
                    self.frame_buffer.append((frame1, sim_time))
                    frame_buffer_size = len(self.frame_buffer)
                lock_time = (time.time() - lock_start) * 1000  # ms
                
                loop_time = (time.time() - loop_start) * 1000  # ms
                
                # Log stats periodically
                if frame_counter % log_interval == 0:
                    avg_qr_time = sum(qr_detect_times) / len(qr_detect_times) if qr_detect_times else 0
                    max_qr_time = max(qr_detect_times) if qr_detect_times else 0
                    min_qr_time = min(qr_detect_times) if qr_detect_times else 0
                    logger.info(
                        f"[QRProcessor] Stats: "
                        f"DecodeQueue={decode_queue_size}, "
                        f"FrameBuffer={frame_buffer_size}, "
                        f"QR_Time(avg/min/max)={avg_qr_time:.1f}/{min_qr_time:.1f}/{max_qr_time:.1f}ms, "
                        f"Lock={lock_time:.1f}ms, "
                        f"Loop={loop_time:.1f}ms"
                    )
                    qr_detect_times = []  # Reset for next interval
                
            except queue.Empty:
                if frame_counter > 0:
                    logger.debug("[QRProcessor] Decode queue empty, waiting for frames...")
                continue
            except Exception as e:
                logger.error(f"[QRProcessor] Error: {e}")
                self.update_stats('errors')
        
        logger.info("[QRProcessor] Stopped")
    
    # ==================== Thread 3: API Sender ====================
    def thread_api_sender(self):
        """
        Thread 3: Send QR code data to API
        Pulls from request_queue and sends via RESTful API with 0.5s timeout
        """
        logger.info(f"[APISender] Starting: {self.api_url}")
        
        session = requests.Session()
        
        while not self.stop_event.is_set():
            try:
                # Get QR data from Thread2
                qr_data, sim_time = self.request_queue.get(timeout=1.0)
                
                # Parse QR code data
                if len(qr_data.split("|")) == 4:
                    (
                        timestamp,
                        global_frame_index,
                        scan_global_frame_index,
                        tx_action,
                    ) = qr_data.split("|")
                    
                    # Parse barcode type
                    barcode_type_name = schemas.BarcodeTypeId.get_name_by_id(int(tx_action))
                    barcode_type = schemas.BarcodeType.get_by_name(barcode_type_name)
                    
                    # Create request body
                    request_body = self._create_request_body(barcode_type, sim_time)
                    
                    if request_body:
                        # Send POST request with timeout
                        url = self.barcode_type_url_path.get(barcode_type)
                        url = url.format(sco_id=self.sco_id)
                        api_url = self.api_url + url
                        response = session.post(
                            api_url,
                            json=request_body.model_dump(),
                            timeout=0.5
                        )
                        response.raise_for_status()
                        self.update_stats('api_sent')
                    else:
                        logger.error(f"[APISender] Unknown barcode type: {barcode_type}")
                        self.update_stats('errors')
                # else:
                #     logger.warning(f"[APISender] Invalid QR data format: {qr_data}")
                #     self.update_stats('errors')
                    
            except queue.Empty:
                continue
            except requests.Timeout:
                logger.warning("[APISender] Request timeout (0.5s)")
                self.update_stats('errors')
            except requests.RequestException as e:
                logger.error(f"[APISender] Request error: {e}")
                self.update_stats('errors')
            except Exception as e:
                logger.exception(f"[APISender] Error: {e}")
                self.update_stats('errors')
        
        logger.info("[APISender] Stopped")
    
    def _create_request_body(self, barcode_type, sim_time):
        """
        Create request body based on barcode type.
        
        Returns:
            Request body object or None if barcode type is unknown
        """
        base_params = {
            'transaction_id': str(self.transaction_id),
            'timestamp': sim_time,
            'server_timestamp': sim_time,
        }
        
        if barcode_type == schemas.BarcodeType.TRANSACTION_STARTED:
            self.transaction_id = str(uuid.uuid4())
            return schemas.TransactionStartRequestBody(
                transaction_id=str(self.transaction_id),
                transaction_type="pending",
                total_items=0,
                status="started",
                timestamp=sim_time,
                server_timestamp=sim_time,
            )
        elif barcode_type == schemas.BarcodeType.TRANSACTION_COMPLETED:
            return schemas.TransactionCompleteRequestBody(
                status="ended",
                transaction_type="pending",
                **base_params
            )
        elif barcode_type == schemas.BarcodeType.ITEM_ADDED:
            return schemas.ItemAddRequestBody(
                item_id=str(uuid.uuid4()),
                item_name="item_name",
                item_price=100,
                item_quantity=1,
                transaction_type="pending",
                **base_params
            )
        elif barcode_type == schemas.BarcodeType.ITEM_REMOVED:
            return schemas.ItemRemoveRequestBody(
                item_id=str(uuid.uuid4()),
                item_name="item_name",
                item_price=100,
                item_quantity=1,
                transaction_type="pending",
                **base_params
            )
        elif barcode_type == schemas.BarcodeType.STATE:
            return schemas.StateRequestBody(
                # state="staff_mode_on",
                transaction_type="pending",
                reason="simulation",
                **base_params
            )
        elif barcode_type == schemas.BarcodeType.SCAN_STARTED:
            return schemas.ScanStartRequestBody(
                transaction_type="pending",
                **base_params
            )
        elif barcode_type == schemas.BarcodeType.SCAN_COMPLETED:
            return schemas.ScanCompletedRequestBody(
                transaction_type="pending",
                **base_params
            )
        elif barcode_type == schemas.BarcodeType.WEIGHTING_SCALE_NOT_MATCHED:
            return schemas.WeightingScaleNotMatchedRequestBody(
                state="weighting_scale_not_matched",
                transaction_type="pending",
                name="default",
                barcode="aabbabc",
                **base_params
            )
        else:
            return None
    
    # ==================== Thread 4: RTSP Server ====================
    def warmup_encoder(self):
        """Warmup x264 encoder before clients connect"""
        if self.warmup_frames <= 0:
            logger.info("[RTSPServer] Encoder warmup disabled")
            return
        
        logger.info(f"[RTSPServer] Starting encoder warmup ({self.warmup_frames} frames)...")
        
        try:
            # Create a dummy pipeline with same encoder settings
            warmup_pipeline_str = (
                f"appsrc name=warmup_src is-live=true format=time "
                f"caps=video/x-raw,format=BGR,width={self.frame_width},"
                f"height={self.frame_height},framerate={self.fps}/1 ! "
                f"videoconvert ! video/x-raw,format=I420 ! "
                f"x264enc speed-preset=ultrafast tune=zerolatency bitrate=2000 key-int-max=30 ! "
                f"fakesink"  # Discard output
            )
            warmup_pipeline = Gst.parse_launch(warmup_pipeline_str)
            warmup_src = warmup_pipeline.get_by_name("warmup_src")
            
            # Start pipeline
            warmup_pipeline.set_state(Gst.State.PLAYING)
            
            # Push frames for warmup (default 60 = 4 seconds @ 15fps)
            duration = Gst.SECOND // self.fps
            
            for i in range(self.warmup_frames):
                # Get a frame from buffer or create dummy frame
                with self.frame_lock:
                    if self.frame_buffer:
                        frame, _ = self.frame_buffer[-1]  # Use latest frame
                    else:
                        # Create black frame if buffer empty
                        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
                
                # Convert to GStreamer buffer
                data = frame.tobytes()
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                buf.fill(0, data)
                buf.pts = i * duration
                buf.dts = buf.pts
                buf.duration = duration
                
                # Push buffer
                ret = warmup_src.emit('push-buffer', buf)
                if ret != Gst.FlowReturn.OK:
                    break
                
                # Small delay to simulate real encoding
                time.sleep(0.01)
            
            # Send EOS and cleanup
            warmup_src.emit('end-of-stream')
            warmup_pipeline.set_state(Gst.State.NULL)
            
            logger.info(f"[RTSPServer] Encoder warmup completed ({self.warmup_frames} frames)")
            
        except Exception as e:
            logger.warning(f"[RTSPServer] Warmup failed (non-critical): {e}")
    
    def thread_rtsp_server(self):
        """Self-hosted RTSP server"""
        logger.info(f"[RTSPServer] Starting on port {self.rtsp_port}")
        
        Gst.init(None)
        
        # Warmup encoder before accepting connections
        self.warmup_encoder()
        
        # Create custom media factory adapted from SensorFactory for multi-client support
        class SimulatorMediaFactory(GstRtspServer.RTSPMediaFactory):
            def __init__(self, simulator: RTSPSimulatorV2):
                super().__init__()
                self.simulator = simulator
                self.fps = simulator.fps
                self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
                self.launch_string = (
                    'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME '
                    'caps=video/x-raw,format=BGR,width={},height={},framerate={}/1 '
                    '! videoconvert ! video/x-raw,format=I420 '
                    '! x264enc speed-preset=ultrafast tune=zerolatency '
                    '! rtph264pay config-interval=1 name=pay0 pt=96'
                ).format(simulator.frame_width, simulator.frame_height, self.fps)
                
                # Track per-client state - count is len(client_states)
                self.client_states = {}
                
            def on_need_data(self, src, length, client_id):
                """Callback when appsrc needs data - triggered by GStreamer"""
                # Get or initialize client state
                if client_id not in self.client_states:
                    self.client_states[client_id] = {
                        'number_frames': 0,
                        'last_sim_time': None
                    }
                
                client_state = self.client_states[client_id]
                
                try:
                    # Get latest frame from buffer (deque is thread-safe, no lock needed)
                    if not self.simulator.frame_buffer:
                        # No frame available yet
                        return
                    
                    # Get latest frame without removing it (broadcast to all clients)
                    frame, sim_time = self.simulator.frame_buffer[-1]
                    # logger.error(f"frame: {frame.shape}, sim_time: {sim_time}, client_state: {client_state}")
                    # Skip if we've already pushed this frame (deduplication)
                    # if sim_time == client_state['last_sim_time']:
                    #     return
                    
                    client_state['last_sim_time'] = sim_time
                    
                    # Convert frame to bytes
                    data = frame.tobytes()
                    buf = Gst.Buffer.new_allocate(None, len(data), None)
                    buf.fill(0, data)
                    buf.duration = self.duration
                    timestamp = client_state['number_frames'] * self.duration
                    buf.pts = buf.dts = int(timestamp)
                    buf.offset = timestamp
                    client_state['number_frames'] += 1
                    
                    retval = src.emit('push-buffer', buf)
                    
                    if retval == Gst.FlowReturn.OK:
                        self.simulator.update_stats('frames_streamed')
                        self.simulator.update_encode_fps()
                    else:
                        if retval != Gst.FlowReturn.FLUSHING:  # Ignore flushing (normal on disconnect)
                            logger.warning(f"[RTSPServer] Push buffer failed for client {client_id}: {retval}")
                        
                except Exception as e:
                    logger.error(f"[RTSPServer] Error in on_need_data for client {client_id}: {e}")
                    self.simulator.update_stats('errors')
                
            def do_create_element(self, url):
                """Create GStreamer pipeline element from launch string"""
                return Gst.parse_launch(self.launch_string)
            
            def on_media_unprepared(self, rtsp_media, client_id):
                """Cleanup when media is unprepared (client disconnects)"""
                if client_id in self.client_states:
                    del self.client_states[client_id]
                    logger.info(f"[RTSPServer] Client {client_id} disconnected, state cleaned up (remaining connections: {len(self.client_states)})")
            
            def do_configure(self, rtsp_media):
                """Configure the RTSP media - called for each new client"""
                # Generate unique client ID
                client_id = id(rtsp_media)
                
                # Reset frame counter for this client
                if client_id in self.client_states:
                    del self.client_states[client_id]
                self.client_states[client_id] = {
                    'number_frames': 0,
                    'last_sim_time': None
                }
                
                # Get appsrc element and connect need-data signal
                appsrc = rtsp_media.get_element().get_child_by_name('source')
                if appsrc:
                    appsrc.connect('need-data', self.on_need_data, client_id)
                    logger.info(f"[RTSPServer] Client {client_id} configured (total connections: {len(self.client_states)})")
                else:
                    logger.error("[RTSPServer] Failed to get appsrc element")
                
                # Connect unprepared signal for cleanup when client disconnects
                rtsp_media.connect('unprepared', self.on_media_unprepared, client_id)
                    
                # Clean up old client states (basic cleanup)
                if len(self.client_states) > 100:  # Prevent unbounded growth
                    # Remove oldest entries
                    oldest_keys = list(self.client_states.keys())[:50]
                    for key in oldest_keys:
                        if key != client_id:
                            del self.client_states[key]
        
        # Create server
        server = GstRtspServer.RTSPServer()
        server.set_service(str(self.rtsp_port))
        
        factory = SimulatorMediaFactory(self)
        
        # Add client connection handler to log IP
        def on_client_connected(rtsp_server, client):
            connection = client.get_connection()
            if connection:
                ip = connection.get_ip()
                logger.info(f"[RTSPServer] New client connected from IP: {ip}")
        
        server.connect("client-connected", on_client_connected)
        factory.set_shared(True)  # Each client gets its own pipeline and push thread
        
        rtsp_path = "/simulation"
        server.get_mount_points().add_factory(rtsp_path, factory)
        server.attach(None)
        
        logger.info(f"[RTSPServer] Ready at rtsp://0.0.0.0:{self.rtsp_port}{rtsp_path}")
        
        # Run main loop
        main_loop = GLib.MainLoop()
        try:
            main_loop.run()
        except Exception as e:
            logger.exception(f"[RTSPServer] Error: {e}")
            self.update_stats('errors')
        finally:
            main_loop.quit()
            server.get_mount_points().remove_factory(rtsp_path)
            logger.info("[RTSPServer] Stopped")
    
    # ==================== FPS Tracking ====================
    def update_decode_fps(self):
        """Track decode FPS"""
        self.decode_fps_counter += 1
        if self.decode_fps_counter >= 300:
            elapsed = time.time() - self.decode_fps_start
            fps = self.decode_fps_counter / elapsed
            logger.info(f"[GRAB FPS] {fps:.2f} fps ({self.decode_fps_counter} frames in {elapsed:.2f}s)")
            self.decode_fps_counter = 0
            self.decode_fps_start = time.time()
    
    def update_encode_fps(self):
        """Track encode FPS"""
        self.encode_fps_counter += 1
        if self.encode_fps_counter >= 300:
            elapsed = time.time() - self.encode_fps_start
            fps = self.encode_fps_counter / elapsed
            logger.info(f"[ENCODE FPS] {fps:.2f} fps ({self.encode_fps_counter} frames in {elapsed:.2f}s)")
            self.encode_fps_counter = 0
            self.encode_fps_start = time.time()
    
    # ==================== Main Control ====================
    def start(self):
        """Start all threads"""
        logger.info("=" * 60)
        logger.info("Starting RTSP Simulator V2")
        logger.info("=" * 60)
        logger.info(f"Video Source: {self.video_path}")
        logger.info(f"RTSP Port: {self.rtsp_port}")
        logger.info(f"API Endpoint: {self.api_url}")
        logger.info(f"FPS: {self.fps}")
        logger.info("=" * 60)
        
        threads = [
            threading.Thread(target=self.thread_video_reader, name="VideoReader", daemon=True),
            threading.Thread(target=self.thread_qr_processor, name="QRProcessor", daemon=True),
            threading.Thread(target=self.thread_api_sender, name="APISender", daemon=True),
            threading.Thread(target=self.thread_rtsp_server, name="RTSPServer", daemon=True),
        ]
        
        for t in threads:
            t.start()
            logger.info(f"Started thread: {t.name}")
        
        logger.info("All threads started successfully")
        
        # Keep main thread alive
        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.stop()
    
    def stop(self):
        """Stop all threads"""
        logger.info("Stopping simulator...")
        self.stop_event.set()
        time.sleep(2)
        logger.info("Simulator stopped")


def extract_file_id(url):
    """Extract file ID from Google Drive shareable link."""
    # Pattern for /file/d/{FILE_ID}/
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    # Pattern for id={FILE_ID}
    match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract file ID from URL: {url}")


def download_video_if_missing(video_path, google_drive_url):
    """
    Download video from Google Drive if it doesn't exist or MD5 verification fails.
    
    Uses gdown.cached_download which automatically:
    - Checks if file exists
    - Verifies MD5 hash against Google Drive
    - Skips download if hash matches
    - Re-downloads if hash mismatches or file is missing
    
    Args:
        video_path: Local path where the video should be
        google_drive_url: Google Drive shareable link
        
    Returns:
        True if video is available (exists with valid MD5), False otherwise
    """
    # Check if Google Drive URL is provided
    if not google_drive_url:
        # No URL provided, check if file exists locally
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path) / (1024 * 1024)
            logger.warning(f"Video file exists but no Google Drive URL for MD5 verification: {video_path} ({file_size:.2f} MB)")
            logger.warning("Proceeding without MD5 verification")
            return True
        else:
            logger.error(f"Video file not found and no Google Drive URL provided: {video_path}")
            return False
    
    # Check if video exists and log status
    if os.path.exists(video_path):
        file_size = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(f"Video file exists: {video_path} ({file_size:.2f} MB)")
        logger.info("Verifying MD5 hash with Google Drive...")
    else:
        logger.info(f"Video file not found: {video_path}")
        logger.info("Downloading from Google Drive...")
    
    try:
        # Extract file ID from URL
        file_id = extract_file_id(google_drive_url)
        logger.info(f"File ID: {file_id}")
        
        # Construct download URL
        download_url = f"https://drive.google.com/uc?id={file_id}"
        
        # Create directory if it doesn't exist
        video_dir = os.path.dirname(video_path)
        if video_dir:
            os.makedirs(video_dir, exist_ok=True)
        
        # Use cached_download which automatically handles MD5 verification
        # It will:
        # - Download if file doesn't exist
        # - Verify MD5 if file exists
        # - Re-download if MD5 doesn't match
        result_path = gdown.cached_download(
            download_url,
            path=video_path,
            quiet=False,
            postprocess=None
        )
        
        if result_path and os.path.exists(result_path):
            file_size = os.path.getsize(result_path) / (1024 * 1024)
            logger.success(f"✓ Video ready: {result_path} ({file_size:.2f} MB)")
            logger.success("✓ MD5 verification passed")
            return True
        else:
            logger.error("Download failed - file not found after download")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading/verifying video: {e}")
        return False


def load_config(config_path='/app/config.yaml'):
    """Load configuration from YAML file"""
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return None

def main():
    parser = argparse.ArgumentParser(
        description='RTSP Stream Simulator V2 - Configuration is loaded from config.yaml'
    )
    parser.add_argument('--config', default='/app/config.yaml', help='Path to configuration file (default: /app/config.yaml)')
    parser.add_argument('--cam', required=True, help='Camera name (must match a camera in config.yaml)')
    
    args = parser.parse_args()
    
    # Load config file
    config = load_config(args.config)
    if not config:
        logger.error(f"Configuration file not found: {args.config}")
        logger.error("Please ensure config.yaml exists and is properly formatted")
        sys.exit(1)
    
    # Get camera name
    camera_name = args.cam
    
    # Check if camera exists in config
    if 'cameras' not in config or camera_name not in config['cameras']:
        logger.error(f"Camera '{camera_name}' not found in configuration file")
        if 'cameras' in config:
            available = ', '.join(config['cameras'].keys())
            logger.error(f"Available cameras: {available}")
        sys.exit(1)
    
    # Load camera-specific config
    cam_config = config['cameras'][camera_name]
    defaults = config.get('defaults', {})
    
    # Get all settings from config
    video_path = cam_config.get('video')
    api_url = cam_config.get('api_url')
    google_drive_url = cam_config.get('google_drive_url')
    rtsp_port = cam_config.get('rtsp_port', 8554)
    fps = cam_config.get('fps', 15)
    original_width = defaults.get('original_width', 800)
    original_height = defaults.get('original_height', 640)
    frame_width = defaults.get('frame_width', 640)
    frame_height = defaults.get('frame_height', 480)
    qrcode_size = defaults.get('qrcode_size', 160)
    queue_size = defaults.get('queue_size', 30)
    warmup_frames = defaults.get('warmup_frames', 90)
    timezone_str = defaults.get('timezone', 'UTC')
    
    # Validate required parameters
    if not video_path:
        logger.error(f"'video' not configured for camera '{camera_name}' in config file")
        sys.exit(1)
    if not api_url:
        logger.error(f"'api_url' not configured for camera '{camera_name}' in config file")
        sys.exit(1)
    
    # Check video file and download if missing
    logger.info("Checking video file...")
    if not download_video_if_missing(video_path, google_drive_url):
        logger.error(f"Video file is not available and could not be downloaded: {video_path}")
        logger.error("Please ensure the video file exists or provide a valid Google Drive URL")
        sys.exit(1)
    
    # Log configuration
    logger.info("=" * 60)
    logger.info(f"Starting RTSP Simulator for camera: {camera_name}")
    logger.info("=" * 60)
    logger.info(f"Configuration file: {args.config}")
    logger.info(f"Video path: {video_path}")
    logger.info(f"API URL: {api_url}")
    logger.info(f"RTSP Port: {rtsp_port}")
    logger.info(f"FPS: {fps}")
    logger.info(f"Frame size: {frame_width}x{frame_height}")
    logger.info(f"QR code size: {qrcode_size}x{qrcode_size}")
    logger.info(f"Timezone: {timezone_str}")
    logger.info("=" * 60)
    
    simulator = RTSPSimulatorV2(
        camera_name=camera_name,
        video_path=video_path,
        rtsp_port=rtsp_port,
        api_url=api_url,
        fps=fps,
        original_width=original_width,
        original_height=original_height,
        frame_width=frame_width,
        frame_height=frame_height,
        qrcode_size=qrcode_size,
        queue_size=queue_size,
        warmup_frames=warmup_frames,
        timezone_str=timezone_str
    )
    
    simulator.start()


if __name__ == "__main__":
    main()
