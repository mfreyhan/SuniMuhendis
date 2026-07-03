import os
import glob
import json

def clean_client_errors():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    results_dir = os.path.join(repo_root, 'results')
    
    # Tüm JSONL dosyalarını bul (api_runs ve manual_runs dahil)
    pattern = os.path.join(results_dir, '**', '*.jsonl')
    jsonl_files = glob.glob(pattern, recursive=True)
    
    total_removed = 0
    total_kept = 0
    files_modified = 0
    
    print("Mevcut sonuç dosyaları taranıyor...")
    
    for filepath in jsonl_files:
        valid_lines = []
        removed_in_file = 0
        kept_in_file = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("status") == "client_error":
                        removed_in_file += 1
                        total_removed += 1
                    else:
                        valid_lines.append(line)
                        kept_in_file += 1
                        total_kept += 1
                except json.JSONDecodeError:
                    # JSON hatası olan raw satırları silmiyoruz
                    valid_lines.append(line)
                    kept_in_file += 1
                    total_kept += 1
        
        # Sadece client_error silindiyse dosyayı güncelle
        if removed_in_file > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in valid_lines:
                    f.write(line)
            files_modified += 1
            print(f"  [+] Temizlendi: {os.path.relpath(filepath, repo_root)} "
                  f"(-{removed_in_file} çöp, +{kept_in_file} geçerli)")
                  
    print("\n" + "="*30)
    print("TEMİZLİK ÖZETİ")
    print("="*30)
    print(f"Silinen 'client_error' sayısı : {total_removed}")
    print(f"Kalan geçerli koşu sayısı     : {total_kept}")
    print(f"Güncellenen dosya sayısı      : {files_modified}")
    print("="*30)

if __name__ == "__main__":
    clean_client_errors()
