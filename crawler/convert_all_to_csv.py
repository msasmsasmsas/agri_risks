#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import re
from json_to_csv import json_files_to_csv

def main():
    # Пути к директориям
    input_dir = "../crawler/downloads"
    output_dir = "../crawler/downloads"
    
    # Проверяем существование директорий
    if not os.path.exists(input_dir):
        print(f"Директория {input_dir} не найдена")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Находим все JSON файлы с данными о болезнях, вредителях и сорняках
    categories = {
        "diseases": re.compile(r'diseases_.*\.json$'),
        "pests": re.compile(r'pests_.*\.json$'),
        "weeds": re.compile(r'weeds.*\.json$')
    }
    
    for category, pattern in categories.items():
        print(f"\nОбработка категории: {category}")
        
        # Конвертируем JSON файлы
        json_files_to_csv(input_dir, output_dir, pattern.pattern)
        
        # Объединяем все CSV для категории
        csv_files = []
        for file in os.listdir(output_dir):
            if file.endswith('.csv') and pattern.search(file.replace('.csv', '.json')):
                csv_files.append(os.path.join(output_dir, file))
        
        if csv_files:
            print(f"Объединение {len(csv_files)} CSV файлов для категории {category}")
            # Читаем и объединяем все CSV
            all_data = []
            for csv_file in tqdm(csv_files, desc=f"Чтение CSV файлов {category}"):
                try:
                    df = pd.read_csv(csv_file)
                    # Добавляем имя файла как источник
                    df['source_file'] = os.path.basename(csv_file)
                    all_data.append(df)
                except Exception as e:
                    print(f"Ошибка при чтении {csv_file}: {e}")
            
            if all_data:
                # Объединяем все данные
                combined_df = pd.concat(all_data, ignore_index=True)
                
                # Сохраняем объединенный файл
                output_path = os.path.join(output_dir, f"{category}_combined.csv")
                combined_df.to_csv(output_path, index=False, encoding='utf-8')
                print(f"Создан объединенный файл: {output_path} с {len(combined_df)} строками")
        else:
            print(f"Не найдены CSV файлы для категории {category}")
    
    print("\nКонвертация завершена")

if __name__ == "__main__":
    main()
