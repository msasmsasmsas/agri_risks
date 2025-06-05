#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
import argparse
from pathlib import Path
import re
from tqdm import tqdm

def extract_field_name(field_path, default_name=None):
    """Извлекает имя поля из пути JSON"""
    if not field_path:
        return default_name or "value"
    parts = field_path.split('.')
    return parts[-1]

def flatten_json(json_obj, prefix="", sep="."):
    """Преобразует вложенный JSON в плоскую структуру"""
    flattened = {}
    
    def _flatten(obj, current_prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{current_prefix}{sep}{key}" if current_prefix else key
                _flatten(value, new_prefix)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_prefix = f"{current_prefix}{sep}{i}" if current_prefix else str(i)
                _flatten(item, new_prefix)
        else:
            flattened[current_prefix] = obj
    
    _flatten(json_obj, prefix)
    return flattened

def json_files_to_csv(input_dir, output_dir, filter_pattern=None):
    """Конвертирует все JSON файлы в CSV"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Компилируем регулярное выражение если есть фильтр
    pattern = re.compile(filter_pattern) if filter_pattern else None
    
    json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        print(f"В директории {input_dir} не найдены JSON файлы")
        return
    
    for json_file in tqdm(json_files, desc="Обработка JSON файлов"):
        if pattern and not pattern.search(json_file.name):
            continue
        
        # Загружаем JSON
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Ошибка при чтении {json_file}: {e}")
            continue
        
        # Преобразуем данные в плоский DataFrame
        if isinstance(data, list):
            # Если это список объектов
            flat_data = []
            for item in data:
                flat_data.append(flatten_json(item))
            df = pd.DataFrame(flat_data)
        else:
            # Если это один объект
            flat_data = flatten_json(data)
            df = pd.DataFrame([flat_data])
        
        # Создаем имя выходного файла
        output_file = output_path / f"{json_file.stem}.csv"
        
        # Сохраняем в CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Создан файл: {output_file}")

def extract_nested_json(json_dir, field_pattern, output_csv, field_name=None):
    """
    Извлекает определенные поля из всех JSON файлов и создает единый CSV
    
    Args:
        json_dir: директория с JSON файлами
        field_pattern: путь к полю внутри JSON (можно использовать точечную нотацию)
        output_csv: путь к выходному CSV файлу
        field_name: название поля в выходном CSV
    """
    json_path = Path(json_dir)
    all_data = []
    
    # Разбиваем путь к полю на части
    field_parts = field_pattern.split('.')
    
    # Получаем название последнего поля если не указано
    if not field_name:
        field_name = extract_field_name(field_pattern, "value")
    
    json_files = list(json_path.glob("*.json"))
    
    for json_file in tqdm(json_files, desc=f"Извлечение поля {field_pattern}"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Извлекаем нужное поле
            current = data
            try:
                for part in field_parts:
                    if isinstance(current, list) and part.isdigit():
                        current = current[int(part)]
                    elif isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        # Если поле не найдено, пропускаем файл
                        current = None
                        break
            except (KeyError, IndexError, TypeError):
                current = None
            
            if current is not None:
                # Добавляем имя файла для отслеживания источника
                source_file = json_file.name
                
                # Если результат - список, добавляем каждый элемент
                if isinstance(current, list):
                    for item in current:
                        all_data.append({"source_file": source_file, field_name: item})
                else:
                    all_data.append({"source_file": source_file, field_name: current})
                
        except Exception as e:
            print(f"Ошибка при обработке {json_file}: {e}")
    
    # Сохраняем результаты
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"Создан файл: {output_csv} с {len(df)} строками")
    else:
        print(f"Не найдены данные для поля {field_pattern}")

def main():
    parser = argparse.ArgumentParser(description="Конвертация JSON файлов в CSV")
    parser.add_argument("--input_dir", default="../crawler/downloads", help="Директория с JSON файлами")
    parser.add_argument("--output_dir", default="../crawler/csv_output", help="Директория для сохранения CSV файлов")
    parser.add_argument("--filter", help="Регулярное выражение для фильтрации файлов")
    parser.add_argument("--field", help="Путь к полю внутри JSON для извлечения (например: data.items)")
    parser.add_argument("--output_csv", help="Имя выходного CSV файла для извлечения поля")
    parser.add_argument("--field_name", help="Название поля в выходном CSV")
    
    args = parser.parse_args()
    
    # Создаем выходную директорию если не существует
    os.makedirs(args.output_dir, exist_ok=True)
    
    if args.field and args.output_csv:
        # Извлечение конкретного поля из всех JSON
        extract_nested_json(
            args.input_dir, 
            args.field, 
            os.path.join(args.output_dir, args.output_csv),
            args.field_name
        )
    else:
        # Конвертация всех JSON в CSV
        json_files_to_csv(args.input_dir, args.output_dir, args.filter)

if __name__ == "__main__":
    main()
