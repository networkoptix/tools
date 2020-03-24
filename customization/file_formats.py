sources_extensions = ['.cpp', '.h', '.ui', '.qml']
def is_source_file(path):
    return any(path.endswith(ext) for ext in sources_extensions)

images_extensions = ['.png', '.gif', '.mkv', '.avi', '.png', '.jpg', '.jpeg']
def is_image_file(path):
    if '%' in path:
        return False
    return any(path.endswith(ext) and len(path) > len(ext) for ext in images_extensions)
