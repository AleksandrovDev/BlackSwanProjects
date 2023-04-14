import os


class Loader:
    def __init__(self):
        self.currentPath = os.path.dirname(os.path.abspath(__file__))
        try:
            sourceName = self.currentPath.split("\\")[-2]
        except:
            sourceName = self.currentPath.split("/")[-2]
        self.defaultProjectName = "template_for_fetchers"
        self.projectName = sourceName

    def __rename_files(self):
        old_names = [
            f"../{self.defaultProjectName}.py",
            f"../__{self.defaultProjectName}.py",
        ]
        new_names = [f"../{self.projectName}.py", f"../__{self.projectName}.py"]

        for old, new in zip(old_names, new_names):
            os.rename(old, new)

    def __update_import(self):
        with open(f"../__{self.projectName}.py", "r") as f:
            filedata = f.read()

        filedata = filedata.replace(f"{self.defaultProjectName}", f"{self.projectName}")

        with open(f"../__{self.projectName}.py", "w") as f:
            f.write(filedata)

    def loader_update_files(self):
        self.__rename_files()
        self.__update_import()


loader = Loader()

if __name__ == "__main__":
    loader.loader_update_files()
