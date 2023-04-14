import shutil
import os
from initial_load import loader
from distutils.dir_util import copy_tree


class Zipper:
    def __init__(self, projectName, filesToZip, initialVersion=1.0):
        self.projectName = projectName
        self.filesToZip = filesToZip
        self.current_version = initialVersion
        self.base_dir = os.path.join(loader.currentPath, "..")
        self.path = os.path.join(
            self.base_dir, self.projectName + f"_v{self.current_version}"
        )

    def create_new_version_zip(self):
        if not os.path.exists(self.path):
            os.mkdir(self.path)
            self.copy_required_files()
            self.make_zip()
            return
        else:
            self.increase_version()
            self.set_new_path()

            self.create_new_version_zip()

    def copy_required_files(self):
        for file in self.filesToZip:
            self.copy_single_element(file)

    def copy_single_element(self, element):
        typeOfElement = self.define_folder_or_file(element)
        if typeOfElement == "file":
            self.copy_single_file(element)
        if typeOfElement == "folder":
            self.copy_single_folder(element)

    @staticmethod
    def define_folder_or_file(element):
        if "." in element:
            return "file"

        return "folder"

    def copy_single_file(self, element):
        base_path = os.path.join(self.base_dir, element)
        shutil.copy(base_path, f"{self.path}")

    def copy_single_folder(self, element):
        fromPath = os.path.join(self.base_dir, element)
        targetPath = os.path.join("..", self.path, element)
        copy_tree(fromPath, targetPath)

    def make_zip(self):
        outputFileName = self.projectName + f"_v{self.current_version}"
        out = os.path.join(self.base_dir, outputFileName)
        shutil.make_archive(out, "zip", self.path)

    def increase_version(self):
        self.current_version = str(float(self.path.split("_v")[-1]) + 0.1)[:3]

    def set_new_path(self):
        self.path = self.path[:-3] + self.current_version


filesToZip = ["src", f"{loader.projectName}.py", f"__{loader.projectName}.py"]

zipper = Zipper(projectName=loader.projectName, filesToZip=filesToZip)
zipper.create_new_version_zip()
