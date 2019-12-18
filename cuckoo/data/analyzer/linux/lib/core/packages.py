def choose_package(file_type, file_name):
    """Choose analysis package due to file type and file extension.
    @param file_type: file type.
    @param file_name: file name.
    @return: package name or None.
    """
    if not file_type:
        return None

    file_name = file_name.lower()

    if file_name.endswith(".tar.xz"):
        return "pip"
    else
        return "generic"
