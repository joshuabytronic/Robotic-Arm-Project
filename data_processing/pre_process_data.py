import os
import csv
import shutil

def convert_txt_to_csv(txt_file, csv_file):
    header_found = False
    header = []

    with open(txt_file, "r", encoding="utf-8") as infile, \
        open(csv_file, "w", newline="", encoding="utf-8") as outfile:

        writer = None

        for line in infile:
            line = line.strip()
            
            if not header_found and line.startswith("Date Time"):
                header_found = True
                header = [h.strip() for h in line.split("\t")]
                writer = csv.writer(outfile)
                writer.writerow(header)
                continue

            if header_found and line:
                fields = [f.strip() for f in line.split("\t")]
                fields = ["" if f == "- - -" else f for f in fields]
                writer.writerow(fields)

    print("CSV created:", csv_file)
    return csv_file


def main(temp_dir, data_dir, file_transfer):
    csv_file = None
    img_dir = os.path.join(data_dir, "raw")
    os.makedirs(img_dir, exist_ok=True)
    for filename in os.listdir(temp_dir):
        temp_path = os.path.join(temp_dir, filename)
        
        if filename.lower().endswith(".txt"):
            dest_path = os.path.join(data_dir, filename)
            base = os.path.splitext(filename)[0]
            csv_filename = base + ".csv"
            csv_path = os.path.join(data_dir, csv_filename)

            print(f"Converting {filename} → {csv_filename}")
            csv_file = convert_txt_to_csv(temp_path, csv_path)

            if file_transfer == "move":
                shutil.move(temp_path, dest_path)
            elif file_transfer == "copy":
                shutil.copy(temp_path, dest_path)

        elif filename.lower().endswith(".tiff"):
            dest_path = os.path.join(img_dir, filename)
            if file_transfer == "move":
                
                shutil.move(temp_path, dest_path)
            elif file_transfer == "copy":
                shutil.copy(temp_path, dest_path)


    if csv_file:
        return csv_file
    else:
        return None

    
    
