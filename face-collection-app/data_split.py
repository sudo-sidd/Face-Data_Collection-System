import os
import shutil
import re

# Define the base paths
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")
target_dir = os.path.join(base_dir, "counted_data")

# Define the patterns and their corresponding year folders
patterns = {
    "714022202": "3rd_year",
    "714023247": "2nd_year",
    "714024247": "1st_year"
}

def create_directory_structure():
    """Create the required directory structure if it doesn't exist"""
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")
    
    # Create year subdirectories
    for year_dir in patterns.values():
        year_path = os.path.join(target_dir, year_dir)
        if not os.path.exists(year_path):
            os.makedirs(year_path)
            print(f"Created directory: {year_path}")

def move_folders():
    """Move folders to their corresponding year directories"""
    folders = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]
    
    # Initialize counters
    moved_counts = {year: 0 for year in patterns.values()}
    merged_counts = {year: 0 for year in patterns.values()}
    skipped = 0
    
    for folder in folders:
        moved = False
        for pattern, year_dir in patterns.items():
            if folder.startswith(pattern):
                source = os.path.join(data_dir, folder)
                destination = os.path.join(target_dir, year_dir, folder)
                
                # Check if destination already exists
                if os.path.exists(destination):
                    print(f"Merging contents of {folder} into existing directory")
                    
                    # Copy all files and directories from source to destination
                    for item in os.listdir(source):
                        src_item = os.path.join(source, item)
                        dst_item = os.path.join(destination, item)
                        
                        if os.path.isdir(src_item):
                            # If directory exists, merge contents
                            if os.path.exists(dst_item):
                                for content in os.listdir(src_item):
                                    src_content = os.path.join(src_item, content)
                                    dst_content = os.path.join(dst_item, content)
                                    if os.path.exists(dst_content):
                                        print(f"  Skipping {content}: already exists in destination")
                                    else:
                                        if os.path.isdir(src_content):
                                            shutil.copytree(src_content, dst_content)
                                        else:
                                            shutil.copy2(src_content, dst_content)
                            else:
                                # If directory doesn't exist, copy the whole directory
                                shutil.copytree(src_item, dst_item)
                        else:
                            # If file already exists, skip
                            if os.path.exists(dst_item):
                                print(f"  Skipping file {item}: already exists in destination")
                            else:
                                shutil.copy2(src_item, dst_item)
                    
                    # Remove the source directory after merging
                    shutil.rmtree(source)
                    merged_counts[year_dir] += 1
                    moved = True
                    break
                else:
                    # Move the folder if destination doesn't exist
                    shutil.move(source, destination)
                    print(f"Moved {folder} to {year_dir}/")
                    moved_counts[year_dir] += 1
                    moved = True
                    break
        
        if not moved:
            print(f"Skipping {folder}: doesn't match any pattern")
            skipped += 1
    
    # Print summary
    print("\nMove operation completed!")
    print("Summary:")
    for year, count in moved_counts.items():
        print(f"  - {year}: {count} folders moved, {merged_counts[year]} folders merged")
    print(f"  - Skipped: {skipped} folders (no pattern match)")

def generate_reports():
    """Generate detailed reports for each year folder in counted_data directory"""
    import os

    counted_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "counted_data")
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    year_folders = [f for f in os.listdir(counted_data_dir) if os.path.isdir(os.path.join(counted_data_dir, f))]

    for year_folder in year_folders:
        year_path = os.path.join(counted_data_dir, year_folder)
        report = {
            "year": year_folder,
            "folders_with_video_and_subfolder_images": 0,
            "folders_with_video_and_subfolder_images_list": [],
            "folders_with_only_video": 0,
            "folders_with_only_video_list": [],
            "folders_with_neither": 0,
            "folders_with_neither_list": []
        }

        for folder in os.listdir(year_path):
            folder_path = os.path.join(year_path, folder)
            if os.path.isdir(folder_path):
                # Check for video files in the main folder
                has_video = any(file.endswith(('.mp4', '.avi', '.mov', '.mkv')) 
                               for file in os.listdir(folder_path) 
                               if os.path.isfile(os.path.join(folder_path, file)))
                
                # Check for images in subfolders
                has_subfolder_images = False
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    if os.path.isdir(item_path):
                        if any(file.endswith(('.jpg', '.jpeg', '.png', '.gif')) 
                              for file in os.listdir(item_path)
                              if os.path.isfile(os.path.join(item_path, file))):
                            has_subfolder_images = True
                            break

                if has_video and has_subfolder_images:
                    report["folders_with_video_and_subfolder_images"] += 1
                    report["folders_with_video_and_subfolder_images_list"].append(folder)
                elif has_video:
                    report["folders_with_only_video"] += 1
                    report["folders_with_only_video_list"].append(folder)
                else:
                    report["folders_with_neither"] += 1
                    report["folders_with_neither_list"].append(folder)

        report_file_path = os.path.join(reports_dir, f"{year_folder}_report.txt")
        with open(report_file_path, 'w') as report_file:
            report_file.write(f"Report for {year_folder}:\n\n")
            
            report_file.write(f"1. Folders with video files AND images in subfolders: {report['folders_with_video_and_subfolder_images']}\n")
            if report['folders_with_video_and_subfolder_images_list']:
                report_file.write("   Folders: " + ", ".join(report['folders_with_video_and_subfolder_images_list']) + "\n\n")
            else:
                report_file.write("   Folders: None\n\n")
            
            report_file.write(f"2. Folders with ONLY video files (no images in subfolders): {report['folders_with_only_video']}\n")
            if report['folders_with_only_video_list']:
                report_file.write("   Folders: " + ", ".join(report['folders_with_only_video_list']) + "\n\n")
            else:
                report_file.write("   Folders: None\n\n")
            
            report_file.write(f"3. Students who havent given video: {report['folders_with_neither']}\n")
            if report['folders_with_neither_list']:
                report_file.write("   Folders: " + ", ".join(report['folders_with_neither_list']) + "\n\n")
            else:
                report_file.write("   Folders: None\n\n")
        
        print(f"Generated report for {year_folder}")

if __name__ == "__main__":
    print("Starting data organization process...")
    create_directory_structure()
    move_folders()
    generate_reports()
    print("Data organization complete!")