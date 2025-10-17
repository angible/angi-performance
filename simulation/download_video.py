"""
Download video from Google Drive shareable link.
Requires: pip install gdown
"""

import gdown
import os
import re
import argparse
from loguru import logger

CAMERA_INFO = {
    "Central": {
        "westgate": {
            "cam1": "https://drive.google.com/file/d/1czXUKJGTUL88WgZmp8psNccUruwcYKMU/view?usp=sharing",
            "cam2": "https://drive.google.com/file/d/1uus7c_hA9N5GlPfFdBDgAZ6RaEhqoPbV/view?usp=sharing",
            "cam3": "https://drive.google.com/file/d/1PwNF2qEk1P_uZJgzXF3AySvvyRvhX-u6/view?usp=sharing",
            "cam4": "https://drive.google.com/file/d/1tMhtilVlWPWek1VtHXYh4GQjcT79Abev/view?usp=sharing",
            "cam5": "https://drive.google.com/file/d/1--dPvA2eTTrtE6-OUwqHr8EgrEHsnu7m/view?usp=sharing",
            "cam6": "https://drive.google.com/file/d/1iPzx8skcjQnW-d_WmLutwQda4ms-AogV/view?usp=sharing",
            "cam7": "https://drive.google.com/file/d/1wZNl731f-PX54nVmJuyEPczW6PR7nZDb/view?usp=sharing",

        }
    }
}


def get_camera_link(customer, store, camera):
    """
    Get Google Drive link from CAMERA_INFO dictionary.

    Args:
        customer: Customer name (e.g., 'Central')
        store: Store name (e.g., 'westgate')
        camera: Camera ID (e.g., 'cam1')

    Returns:
        Google Drive shareable link or None if not found
    """
    try:
        link = CAMERA_INFO[customer][store][camera]
        logger.info(f"Found link for {customer}/{store}/{camera}")
        return link
    except KeyError:
        logger.error(f"No link found for {customer}/{store}/{camera}")
        logger.info(f"Available customers: {list(CAMERA_INFO.keys())}")
        return None


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


def download_video(shareable_link, output_path="downloaded_video.mp4", overwrite=False):
    """
    Download a video from Google Drive with automatic MD5 verification and caching.
    
    Uses gdown.cached_download which automatically:
    - Checks if file exists
    - Verifies MD5 hash against Google Drive
    - Skips download if hash matches
    - Re-downloads if hash mismatches

    Args:
        shareable_link: Google Drive shareable link
        output_path: Local path where the video will be saved
        overwrite: Force download even if file exists

    Returns:
        Path to the downloaded file
    """
    try:
        file_id = extract_file_id(shareable_link)
        logger.info(f"Extracted file ID: {file_id}")

        # Construct the download URL
        download_url = f"https://drive.google.com/uc?id={file_id}"
        
        # Handle overwrite flag
        if overwrite and os.path.exists(output_path):
            logger.info("Overwrite flag set, removing existing file")
            os.remove(output_path)
        
        # Check if file exists before downloading
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"File already exists: {output_path} ({file_size:.2f} MB)")
            logger.info("Verifying integrity with MD5 check...")
        
        # Use cached_download for automatic MD5 verification
        # This will skip download if file exists and MD5 matches
        result_path = gdown.cached_download(
            download_url,
            path=output_path,
            quiet=False,
            postprocess=None
        )

        if result_path and os.path.exists(result_path):
            file_size = os.path.getsize(result_path) / (1024 * 1024)
            logger.success("✓ File ready (downloaded or verified)")
            logger.info(f"File: {result_path}")
            logger.info(f"Size: {file_size:.2f} MB")
            return result_path
        else:
            logger.error("Download failed - file not found")
            return None

    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None


if __name__ == "__main__":
    """
    python3 download_video.py --customer Central --store westgate --camera cam1 --output cam1.mp4
    """
    parser = argparse.ArgumentParser(
        description="Download video from Google Drive based on customer, store, and camera"
    )
    parser.add_argument(
        "--customer", required=True, help="Customer name (e.g., Central)"
    )
    parser.add_argument("--store", required=True, help="Store name (e.g., westgate)")
    parser.add_argument("--camera", required=True, nargs='+', help="Camera ID(s) (e.g., cam1 or cam1 cam2 cam3)")
    parser.add_argument(
        "--output",
        default="download_video",
        help="Output folder (default: downloaded_video.mp4)",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing file")

    args = parser.parse_args()

    # Process each camera
    cameras = args.camera if isinstance(args.camera, list) else [args.camera]
    failed_cameras = []
    
    for camera in cameras:
        logger.info(f"Processing camera: {camera}")
        
        # Get the Google Drive link from CAMERA_INFO
        shareable_link = get_camera_link(args.customer, args.store, camera)

        if not shareable_link:
            logger.error(f"Cannot proceed without a valid camera link for {camera}")
            failed_cameras.append(camera)
            continue

        # Download the video
        # Create camera directory if it doesn't exist
        camera_dir = camera
        os.makedirs(camera_dir, exist_ok=True)
        
        output_name = os.path.join(camera_dir, args.output)
        result = download_video(shareable_link, output_name, args.overwrite)

        if result:
            logger.success(f"Video successfully downloaded to: {result}")
        else:
            logger.error(f"Failed to download video for {camera}")
            failed_cameras.append(camera)
    
    # Final summary
    if failed_cameras:
        logger.error(f"Failed to download videos for: {', '.join(failed_cameras)}")
        exit(1)
    else:
        logger.success(f"All {len(cameras)} camera(s) downloaded successfully")
