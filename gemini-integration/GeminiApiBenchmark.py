"""
Module for evaluating the performance and cost of using the Gemini API.
"""

import os
import time
import logging
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import random
from PIL import Image
import numpy as np
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

from gemini_client import GeminiClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gemini-integration/benchmark.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gemini_benchmark")

# Константы
BENCHMARK_RESULTS_DIR = Path("gemini-integration/benchmark_results")
BENCHMARK_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def get_random_images(num_images: int = 10) -> List[Path]:
    """
    Gets a random set of images for testing.

    Args:
        num_images: Number of images to sample.

    Returns:
        List of paths to random images.
    """
    # Check several possible paths to images
    possible_paths = [
        Path("crawler/download/images/diseases/pea"),  # Конкретная папка с изображениями гороха
        Path("crawler/download/images/diseases/potato"),  # Конкретная папка с изображениями картофеля
        Path("crawler/download/images/diseases/vineyard"),  # Конкретная папка с изображениями винограда
        Path("crawler/download/images"),  # Общая папка изображений
        Path("crawler/downloads/images"),  # Альтернативный путь
        Path("crawler/download/images/diseases"),  # Папка с болезнями
        Path("crawler/download/images/pests")  # Папка с вредителями
    ]

    # Collect all existing paths
    existing_paths = [path for path in possible_paths if path.exists()]

    if not existing_paths:
        logger.warning(f"None of the image directories exist. Checked paths: {possible_paths}")
        logger.info("Make sure you've run the crawler to download images before running the benchmark.")
        return []

    # Get all images from all existing directories
    all_images = []
    for images_dir in existing_paths:
        logger.info(f"Searching for images in: {images_dir}")
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
            # Use ** for recursive search in all subfolders
            found_images = list(images_dir.glob(f"**/{ext}"))
            all_images.extend(found_images)
            if found_images:
                logger.info(f"Found {len(found_images)} images with extension {ext} in {images_dir}")

    if not all_images:
        logger.warning("No images found in the specified directories.")
        return []

    logger.info(f"Total of {len(all_images)} images found in all directories")

    # If there are fewer images than needed, return all
    if len(all_images) <= num_images:
        return all_images

    # Otherwise select random ones
    selected_images = random.sample(all_images, num_images)
    logger.info(f"Randomly selected {len(selected_images)} images for testing")
    return selected_images

def create_test_image(directory: Path, filename: str, size: tuple = (800, 600), color: tuple = (255, 255, 255)) -> Path:
    """
    Creates a test image in the specified directory with simulated crop disease patterns.

    Args:
        directory: Directory to save the image in
        filename: Name of the file
        size: Image dimensions (width, height)
        color: Background color in RGB (green for plant)

    Returns:
        Path to the created image
    """
    directory.mkdir(parents=True, exist_ok=True)

    # Create a base green image (like a leaf)
    img = Image.new('RGB', size, color=(50, 150, 50))
    pixels = np.array(img)

    # Add some texture to make it look like a plant leaf
    noise = np.random.randint(0, 25, (size[1], size[0], 3), dtype=np.uint8)
    pixels = np.clip(pixels + noise - 10, 0, 255).astype(np.uint8)

    # Add simulated disease spots
    num_spots = random.randint(5, 20)
    for _ in range(num_spots):
        # Random position
        x = random.randint(0, size[0]-1)
        y = random.randint(0, size[1]-1)

        # Random spot size
        spot_size = random.randint(10, 50)

        # Random spot color (brown/yellow/rust colors for disease)
        spot_color = random.choice([
            (139, 69, 19),    # Brown
            (160, 82, 45),    # Sienna
            (205, 133, 63),   # Peru
            (210, 180, 140),  # Tan
            (184, 134, 11),   # DarkGoldenrod
            (178, 34, 34),    # Firebrick (for rust)
            (165, 42, 42)     # Brown
        ])

        # Draw a circle-ish spot
        for i in range(size[1]):
            for j in range(size[0]):
                dist = np.sqrt((i - y)**2 + (j - x)**2)
                if dist < spot_size:
                    # Fade effect at the edges
                    alpha = max(0, 1 - dist/spot_size)
                    if random.random() < alpha:
                        # Add some noise to make it look natural
                        noise = np.random.randint(-20, 20, 3)
                        color_with_noise = np.clip(np.array(spot_color) + noise, 0, 255)
                        pixels[i, j] = color_with_noise

    img = Image.fromarray(pixels)
    file_path = directory / filename
    img.save(file_path)
    logger.info(f"Created test image with simulated crop disease: {file_path}")
    return file_path

def create_test_images(num_images: int = 5) -> List[Path]:
    """
    Creates test images for benchmarking if no real images exist.

    Args:
        num_images: Number of images to create

    Returns:
        List of paths to created test images
    """
    test_dir = Path("crawler/download/images/test_benchmark")
    test_dir.mkdir(parents=True, exist_ok=True)

    images = []
    colors = [(50, 150, 50), (60, 140, 60), (45, 160, 45), (55, 145, 55), (65, 135, 55)]

    for i in range(num_images):
        color = colors[i % len(colors)]  # Cycle through colors
        img_path = create_test_image(test_dir, f"test_image_{i+1}.jpg", color=color)
        images.append(img_path)

    logger.info(f"Created {len(images)} test images in {test_dir}")
    return images

def run_benchmark(
    client: GeminiClient,
    images: List[Path],
    save_results: bool = True
) -> Dict[str, Any]:
    """
    Runs the Gemini API benchmark.

    Args:
        client: Gemini API client.
        images: List of paths to images for testing.
        save_results: Flag for saving results.

    Returns:
        Dictionary with benchmark results.
    """
    logger.info(f"Starting benchmark on {len(images)} images")

    results = {
        "total_images": len(images),
        "total_time": 0,
        "avg_time_per_image": 0,
        "success_count": 0,
        "error_count": 0,
        "details": []
    }

    for i, image_path in enumerate(images):
        logger.info(f"Processing image {i+1}/{len(images)}: {image_path}")
        
        start_time = time.time()
        
        try:
            # Анализируем изображение
            response = client.analyze_image(image_path)
            
            # Записываем результат
            success = "error" not in response
            
            if success:
                results["success_count"] += 1
            else:
                results["error_count"] += 1
            
            # Вычисляем время выполнения
            elapsed_time = time.time() - start_time
            
            # Сохраняем детали
            detail = {
                "image_path": str(image_path),
                "success": success,
                "elapsed_time": elapsed_time,
                "response": response
            }
            
            results["details"].append(detail)
            results["total_time"] += elapsed_time
            
            logger.info(f"Image processed in {elapsed_time:.2f} seconds. Success: {success}")

            # Small delay between requests
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            
            results["error_count"] += 1
            results["details"].append({
                "image_path": str(image_path),
                "success": False,
                "elapsed_time": time.time() - start_time,
                "error": str(e)
            })
    
    # Calculate average time per image
    if results["total_images"] > 0:
        results["avg_time_per_image"] = results["total_time"] / results["total_images"]

    # Estimate cost
    # Gemini Pro Vision: $0.0025 per 1000 characters (text) + $0.0025 per image
    # https://ai.google.dev/gemini-api/pricing
    estimated_cost = results["total_images"] * 0.0025  # $0.0025 per image
    results["estimated_cost"] = estimated_cost

    logger.info(f"Benchmark completed. Average time: {results['avg_time_per_image']:.2f} seconds. Success: {results['success_count']}/{results['total_images']}")
    logger.info(f"Estimated cost: ${estimated_cost:.4f}")
    
    # Сохраняем результаты
    if save_results:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        results_path = BENCHMARK_RESULTS_DIR / f"benchmark_{timestamp}.json"
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {results_path}")

        # Create CSV with main metrics
        metrics_path = BENCHMARK_RESULTS_DIR / f"metrics_{timestamp}.csv"
        metrics = {
            "total_images": [results["total_images"]],
            "total_time": [results["total_time"]],
            "avg_time_per_image": [results["avg_time_per_image"]],
            "success_count": [results["success_count"]],
            "error_count": [results["error_count"]],
            "success_rate": [results["success_count"] / results["total_images"] if results["total_images"] > 0 else 0],
            "estimated_cost": [estimated_cost]
        }

        pd.DataFrame(metrics).to_csv(metrics_path, index=False)
        logger.info(f"Metrics saved to {metrics_path}")
    
    return results

def create_test_image(directory: Path, filename: str, size: tuple = (800, 600), color: tuple = (255, 255, 255)) -> Path:
    """
    Creates a test image in the specified directory with simulated crop disease patterns.

    Args:
        directory: Directory to save the image in
        filename: Name of the file
        size: Image dimensions (width, height)
        color: Background color in RGB (green for plant)

    Returns:
        Path to the created image
    """
    directory.mkdir(parents=True, exist_ok=True)

    # Create a base green image (like a leaf)
    img = Image.new('RGB', size, color=(50, 150, 50))
    pixels = np.array(img)

    # Add some texture to make it look like a plant leaf
    noise = np.random.randint(0, 25, (size[1], size[0], 3), dtype=np.uint8)
    pixels = np.clip(pixels + noise - 10, 0, 255).astype(np.uint8)

    # Add simulated disease spots
    num_spots = random.randint(5, 20)
    for _ in range(num_spots):
        # Random position
        x = random.randint(0, size[0]-1)
        y = random.randint(0, size[1]-1)

        # Random spot size
        spot_size = random.randint(10, 50)

        # Random spot color (brown/yellow/rust colors for disease)
        spot_color = random.choice([
            (139, 69, 19),    # Brown
            (160, 82, 45),    # Sienna
            (205, 133, 63),   # Peru
            (210, 180, 140),  # Tan
            (184, 134, 11),   # DarkGoldenrod
            (178, 34, 34),    # Firebrick (for rust)
            (165, 42, 42)     # Brown
        ])

        # Draw a circle-ish spot
        for i in range(size[1]):
            for j in range(size[0]):
                dist = np.sqrt((i - y)**2 + (j - x)**2)
                if dist < spot_size:
                    # Fade effect at the edges
                    alpha = max(0, 1 - dist/spot_size)
                    if random.random() < alpha:
                        # Add some noise to make it look natural
                        noise = np.random.randint(-20, 20, 3)
                        color_with_noise = np.clip(np.array(spot_color) + noise, 0, 255)
                        pixels[i, j] = color_with_noise

    img = Image.fromarray(pixels)
    file_path = directory / filename
    img.save(file_path)
    logger.info(f"Created test image with simulated crop disease: {file_path}")
    return file_path

def create_test_images(num_images: int = 5) -> List[Path]:
    """
    Creates test images for benchmarking if no real images exist.

    Args:
        num_images: Number of images to create

    Returns:
        List of paths to created test images
    """
    test_dir = Path("crawler/download/images/test_benchmark")
    test_dir.mkdir(parents=True, exist_ok=True)

    images = []
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]

    for i in range(num_images):
        color = colors[i % len(colors)]  # Cycle through colors
        img_path = create_test_image(test_dir, f"test_image_{i+1}.jpg", color=color)
        images.append(img_path)

    logger.info(f"Created {len(images)} test images in {test_dir}")
    return images

def main():
    """
    Main function to run the benchmark.
    """
    # Get API key from .env file
    api_key = os.environ.get("GEMINI_API_KEY")

    # Initialize client
    client = GeminiClient(api_key)

    # Get random images for testing
    images = get_random_images(10)  # Test on 10 random images

    if not images:
        logger.warning("No images found in the crawler directories.")
        logger.info("Creating test images for benchmark...")
        images = create_test_images(5)  # Create 5 test images

        if not images:
            logger.error("Failed to create test images. Aborting benchmark.")
            return
        else:
            logger.info(f"Successfully created {len(images)} test images for benchmark.")

    # Run benchmark
    run_benchmark(client, images)

if __name__ == "__main__":
    main()