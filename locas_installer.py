"""User friendly LocalAssistant automatic installer."""
import os
from pathlib import Path
import sys
import venv
import subprocess
import shutil

class Installer:
    """OOP friendly."""
    @staticmethod
    def draw_horizontal_line():
        """Decoratively draw a horizontal line (lol)"""
        print("=" * os.get_terminal_size().columns)

    @staticmethod
    def choose_env_path() -> Path:
        """Select .venv path to install into"""
        while True:
            input_path: str = input(
                f"\nPlease choose the path for LocalAssistant. [{os.getcwd()}]: "
            )
            if not input_path:
                env_path: Path = Path.cwd()
                break

            env_path: Path = Path(input_path)
            if env_path.exists():
                if input(
                    f"'{input_path}' is an existed folder, are you sure to use path? "
                     "(If you are updating LocalAssistant, go ahead!) (y/[N]): "
                ).lower() != 'y':
                    continue
            else:
                env_path.mkdir(parents=True)
            break
        print(f"Using '{input_path}'.")
        os.chdir(env_path)
        venv.create('.venv', with_pip=True, prompt='LocalAssistant')
        return env_path

    @staticmethod
    def choose_localassistant_version(env_path: Path) -> str:
        """Choose a version to install, default is the latest one."""
        print("\nChoosing version.")

        pip_cmd = [Installer.get_venv_python(env_path), "-m", "pip"]
        pip_available = False

        try:
            subprocess.run(
                pip_cmd + ["--version"], capture_output=True, text=True, check=True
            )
            pip_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        if not pip_available:
            for external_pip in ("pip", "pip3"):
                pip_path = shutil.which(external_pip)
                if not pip_path:
                    continue
                try:
                    subprocess.run(
                        [pip_path, "--version"], capture_output=True, text=True, check=True
                    )
                    pip_cmd = [pip_path]
                    pip_available = True
                    break
                except subprocess.CalledProcessError:
                    continue

        if not pip_available:
            try:
                subprocess.run(
                    [sys.executable, "-m", "ensurepip", "--upgrade"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                subprocess.run(pip_cmd + ["--version"], capture_output=True, text=True, check=True)
                pip_available = True
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    "Could not bootstrap pip. Install pip manually or use a Python build that "
                    "includes ensurepip."
                ) from exc

        version_process = subprocess.run(
            pip_cmd + ["index", "versions", "localassistant", "--pre"],
            capture_output=True,
            text=True,
            check=True,
        )

        version_process_stdout = version_process.stdout or ""
        if not version_process_stdout.strip():
            raise OSError("Cannot read the version. Please create an issue.")

        call_version: list = version_process_stdout.split()
        del version_process, version_process_stdout

        try:
            call_version =  call_version[:call_version.index("LATEST:")]
        except ValueError:
            pass

        try:
            install_index: int = call_version.index("INSTALLED:")
            install_version: str = call_version[install_index + 1]
            print(f'Detected installed LocalAssistant: v{install_version}.')
        except ValueError:
            install_index: int = len(call_version)

        pre_version: str = ""
        latest_version: str = ""

        version_list: list = call_version[(call_version.index("versions:") + 1):install_index]
        print(f"Available version: {' '.join(version_list)}")
        for version in version_list:
            if pre_version and latest_version:
                break
            elif "rc" in version and not pre_version:
                pre_version = version.replace(",", "")
            elif not latest_version:
                latest_version = version.replace(",", "")

        print(f"  Pre-release version: {pre_version}\n"
              f"  Latest version: {latest_version}")
        desire_version: str = ""
        while True:
            desire_version = input(f"Which version to install [{latest_version}]: ")
            if not desire_version:
                desire_version = latest_version
            if f"{desire_version}," in version_list:
                print(f'Installing LocalAssistant v{desire_version}.')
                break
            print(f'Invalid version: {desire_version}.')
        return desire_version

    @staticmethod
    def get_venv_python(env_path: Path) -> str:
        """Return the path to the venv Python executable."""
        if sys.platform == "win32":
            return str(env_path / ".venv" / "Scripts" / "python.exe")
        return str(env_path / ".venv" / "bin" / "python")

    @staticmethod
    def install_dependencies(version: str, env_path: Path):
        """Installing the dependencies (include localassistant) within the venv."""
        print("\nInstalling dependencies:")
        subprocess.run(
            [
                Installer.get_venv_python(env_path),
                "-m",
                "pip",
                "install",
                f"LocalAssistant=={version}",
                "--upgrade",
            ],
            check=True,
        )

    @staticmethod
    def setup_execute_file(env_path: Path) -> bool:
        """Setup the execute script so that localassistant can be used globally."""
        print("\nSetting up path.")

        if sys.platform == "win32":
            locas_executor: str = "locas.cmd"
            content_executor: str = (
                f"'{env_path.resolve() / '.venv' / 'Scripts' / 'activate'}' && locas %*"
            )
        else:
            locas_executor: str = "locas"
            content_executor: str = (
                f"source '{env_path.resolve() / '.venv' / 'bin' / 'activate'}' ; locas $@"
            )

        locas_executor_path: Path = env_path / locas_executor
        with locas_executor_path.open("w", encoding="utf-8") as f:
            f.write(content_executor)
            f.close()

        locas_existed = shutil.which("locas")
        if locas_existed and Path(locas_existed).parent == env_path:
            return True # already set the path, meaning this is just upgrading.

        if sys.platform == 'win32':
            subprocess.run(
                "powershell $old_path=[Environment]::GetEnvironmentVariable('path','user');"
               f"$new_path=$old_path+';'+'{env_path}';"
                "[Environment]::SetEnvironmentVariable('path',$new_path,'User');",
                check=True, shell=True
            )
        else:
            subprocess.run("chmod a+x locas", check=True, shell=True)
            rc_content: str = (
                f"\nexport LocalAssistant={env_path};"
                 "\nexport PATH=$LocalAssistant:$PATH"
            )
            if input("Detect Unix platform. Are you using bash? ([Y]/n): ").lower() == "n":
                print(
                    "If so, please manually paste the following into your shell startup file "
                   f"(eg: .zshrc, etc.):\n{rc_content}"
                )

            else:
                subprocess.run(f"echo '{rc_content}' >> ~/.bashrc;"
                                "source ~/.bashrc", check=True, shell=True)
        return False

    @staticmethod
    def setup_llama_cpp_bin_path(env_path: Path):
        """Llama.cpp bin path."""
        llama_path: str = input("\nPaste in the path to installed llama.cpp bin (.../build/bin): ")

        subprocess.run([
            Installer.get_venv_python(env_path),
            "-c", (
                "from localassistant.utils import Setting, SettingKey;"
                "setting = Setting();"
                "setting.data.update({"
                    f"SettingKey.LLAMA_CPP_BIN: '{llama_path}'"
                "});"
                "setting.update_setting_file()"

            )
        ], check=True)

    @staticmethod
    def setup_starter_models(env_path: Path):
        """The starter models that I always use."""
        if input("\nDo you want to install starter models ([Y]/n): ").lower() == "n":
            return

        subprocess.run([
            Installer.get_venv_python(env_path),
            "-c", (
                "from localassistant.models.download import download_starter_models;"
                "download_starter_models()"
            )
        ], check=True)

    @staticmethod
    def install():
        """The main function."""
        print('Welcome to LocalAssistant automatic installer.')
        assert sys.version_info.major >= 3 and sys.version_info.minor >= 14,(
           f"Python version is expected to be above 3.14, but got {sys.version.split()[0]} instead."
        )

        # Choose env path.
        Installer.draw_horizontal_line()
        env_path: Path = Installer.choose_env_path()

        # Choose version to install.
        Installer.draw_horizontal_line()
        version = Installer.choose_localassistant_version(env_path)

        # Installing dependencies.
        Installer.draw_horizontal_line()
        Installer.install_dependencies(version, env_path)

        # Setup stuffs.
        Installer.draw_horizontal_line()
        is_upgrade: bool = Installer.setup_execute_file(env_path)

        if not is_upgrade:
            # Setup llama.cpp path
            Installer.draw_horizontal_line()
            Installer.setup_llama_cpp_bin_path(env_path)

            # Install starters models
            Installer.draw_horizontal_line()
            Installer.setup_starter_models(env_path)

if __name__ == '__main__':
    Installer.install()
