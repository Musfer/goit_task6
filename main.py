import os
from pathlib import Path
import sys
import shutil


root_folder_path = None

known_extensions = {
    "JPEG": "images", "PNG": "images", "JPG": "images", "SVG": "images", "BMP": "images",
    "AVI": "video", "MP4": "video", "MOV": "video", "MKV": "video",
    "DOC": "documents", "DOCX": "documents", "TXT": "documents",
    "PDF": "documents", "XLSX": "documents", "PPTX": "documents",
    "MP3": "audio", "OGG": "audio", "WAV": "audio", "AMR": "audio",
    "ZIP": "archives", "TAR.GZ": "archives", "GZ": "archives", "TAR": "archives",
    "TAR.XZ": "archives", "TAR.BZ": "archives"
}
extension_found = set()
unknown_extensions = set()
file_logs = {
    "images": [], "video": [], "documents": [], "audio": [], "archives": []
}
files_renamed = []

# begin create translator to cyrillic block
CYRILLIC_SYMBOLS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяєіїґ"
TRANSLATION = ("a", "b", "v", "g", "d", "e", "e", "j", "z", "i", "j", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u",
               "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya", "je", "i", "ji", "g")
TRANS = {}
for c, l in zip(CYRILLIC_SYMBOLS, TRANSLATION):
    TRANS[ord(c)] = l
    TRANS[ord(c.upper())] = l.upper()
# end create translator to cyrillic block


def translate(name):
    return name.translate(TRANS)


def define_extension(file_path):  # splits path/name.ext into Path(path), "name", "ext" tuple
    path, name = os.path.split(file_path)
    namelst = name.split(".")
    ext_num = 0
    while ".".join([j.upper() for j in namelst[-ext_num-1:]]) in known_extensions.keys():
        ext_num += 1
    ext = ".".join(namelst[-ext_num:])
    name = ".".join(namelst[:-ext_num])
    if not ext_num:
        ext = ".".join(namelst[1:]) or ""
        name = ".".join(namelst)
    return Path(path), name, ext


def move(src, path, newname, ext):  # src -> path/newname.ext or -> path/newname_count.ext if already exists
    count = 0
    global files_renamed
    while True:
        try:
            if count == 0:
                rename_to = path.joinpath(normalize(newname, ext))

            else:
                rename_to = path.joinpath(normalize(newname+"_"+str(count), ext))
            files_renamed.append(f"'{os.path.relpath(src, root_folder_path)}'  "
                                 + f"-> '{os.path.relpath(rename_to, root_folder_path)}'")
            os.rename(src, rename_to)
            return os.path.relpath(rename_to, root_folder_path)
        except FileExistsError:
            count += 1
        except Exception as err:
            print(err)
            break


def deal_with_archive(file, name):  # path_to_main_folder=root_folder_path
    # unzips archive "name" with path "file" to folder "root_path/archives/name"
    count = 0
    unzip_to_path = root_folder_path.joinpath("archives").joinpath(name)
    while unzip_to_path.exists():
        count += 1
        unzip_to_path = root_folder_path.joinpath("archives").joinpath(name + "_" + str(count))
    if count > 0:
        file_logs["archives"].append(str(file)[1+len(str(root_folder_path)):] + " (unpacked to) archives/"
                                     + name + f"_{count}")
    else:
        file_logs["archives"].append(
            str(file)[1 + len(str(root_folder_path)):] + " (unzipped to) archives/" + name)

    try:
        shutil.unpack_archive(file, unzip_to_path)
        os.remove(file)
    except Exception as err:
        print(f"Warning: can't unpack '{file}':")
        print(f"\t {err}")


def deal_with_file(path, name, ext):
    global file_logs
    global extension_found
    global unknown_extensions
    file_path = path.joinpath(normalize(name, ext))
    if ext.upper() in known_extensions.keys():
        extension_found.add(ext.upper())
        if known_extensions[ext.upper()] == "archives":
            deal_with_archive(file_path, name)
        else:
            pass
            movedto = move(file_path, root_folder_path.joinpath(known_extensions[ext.upper()]), name, ext)
            movedfrom = os.path.relpath(file_path, root_folder_path)
            file_logs[known_extensions[ext.upper()]].append(f"'{movedfrom}' moved to '{movedto}'")
    elif ext:
        unknown_extensions.add(ext.upper())


def sort_files(dirname, root_path=root_folder_path):
    rootdir = (dirname == root_path)   # rootdir is True is we are in main folder
    files_and_folders = os.listdir(dirname)
    for file in files_and_folders:
        file_path = dirname.joinpath(file)
        try:
            path, newname, ext = define_extension(file_path)
            move(file_path, path, newname, ext)  # renames file
            file_path = path.joinpath(normalize(newname, ext))
            if os.path.isfile(file_path):
                deal_with_file(path, newname, ext)

            elif os.path.isdir(file_path):
                # to not parse folders like "images" in the main folder
                if os.path.basename(file_path) not in set(known_extensions.values()) or not rootdir:
                    sort_files(file_path, root_path)
                    try:  # to delete folder if it's empty
                        os.rmdir(file_path)
                    except OSError:
                        pass
                    except Exception as err:
                        print(err)

            else:
                print(f"{file_path} is not a file nor a folder")
        except Exception as err:
            print(err)


def normalize(name, ext=""):
    newname = []
    for i in name:
        if i.isalpha() or i.isdigit():
            newname.append(i)
        else:
            newname.append("_")
    if ext:
        return translate("".join(newname))+"."+ext
    else:
        return translate("".join(newname))


def main():
    try:  # check if path  exists
        global root_folder_path
        root_folder_path = Path(sys.argv[1])
        root_folder_path = Path(os.path.abspath(root_folder_path))
    except IndexError:
        print("Worning: folder is not specified. To sort 'myfolder' try: python main.py myfolder")
        sys.exit()

    if not os.path.isdir(root_folder_path):  # check if path corresponds to folder
        print(f"'{root_folder_path}' is not a folder.")
        sys.exit()

    if not os.listdir(root_folder_path):  # check if folder is not empty
        print("Folder is empty.")
        sys.exit()

    print(f"Sorting '{root_folder_path}'")

    for type_of_files in set(known_extensions.values()):  # create folders like "images" if they do not exist
        try:
            os.mkdir(root_folder_path.joinpath(type_of_files))
        except OSError:
            pass

    sort_files(root_folder_path, root_folder_path)  # parsing the folder recursively

    with open(root_folder_path.joinpath("logs.txt"), "w", encoding="utf-8") as logs:  # printing logs
        print(f"Extentions found: {', '.join(extension_found)}", file=logs)
        print(f"Unknown extensions: {', '.join(unknown_extensions)}", file=logs)

        print("Files sorted:", file=logs)
        for files in file_logs.keys():
            print(f"\t{files}: ", file=logs)
            for i in file_logs[files]:
                print("\t\t"+i, file=logs)
    print(f"See logs in '{root_folder_path.joinpath('logs.txt')}'")


if __name__ == "__main__":
    main()
