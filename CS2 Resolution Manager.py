import os
import time
import subprocess
import psutil
import win32api
import win32con
from tkinter import Tk, ttk, StringVar, IntVar, messagebox, END
from tkinter import DISABLED, NORMAL
from threading import Thread
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class Resolution:
    width: int
    height: int

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    def __eq__(self, other):
        if not isinstance(other, Resolution):
            return False
        return self.width == other.width and self.height == other.height

    def __hash__(self):
        return hash((self.width, self.height))

    @classmethod
    def from_str(cls, resolution_str: str) -> 'Resolution':
        width, height = map(int, resolution_str.split('x'))
        return cls(width, height)

class Settings:
    DEFAULT_RESOLUTION = Resolution(1920, 1440)
    SETTINGS_PATH = Path("settings/settings.txt")
    AUTO_LAUNCH_PATH = Path("settings/auto_launch.txt")
    CUSTOM_RESOLUTIONS_PATH = Path("settings/custom_resolutions.txt")

    @classmethod
    def load(cls) -> Optional[Resolution]:
        try:
            if not cls.SETTINGS_PATH.exists():
                return None
            content = cls.SETTINGS_PATH.read_text().strip()
            width, height = map(int, content.split(','))
            return Resolution(width, height)
        except (ValueError, OSError):
            return None

    @classmethod
    def save(cls, resolution: Resolution) -> None:
        cls.SETTINGS_PATH.parent.mkdir(exist_ok=True)
        cls.SETTINGS_PATH.write_text(f"{resolution.width},{resolution.height}")

    @classmethod
    def get_auto_launch(cls) -> bool:
        try:
            if not cls.AUTO_LAUNCH_PATH.exists():
                return False
            return cls.AUTO_LAUNCH_PATH.read_text().strip().lower() == "true"
        except:
            return False

    @classmethod
    def save_auto_launch(cls, auto_launch: bool) -> None:
        cls.AUTO_LAUNCH_PATH.parent.mkdir(exist_ok=True)
        cls.AUTO_LAUNCH_PATH.write_text(str(auto_launch).lower())

    @classmethod
    def load_custom_resolutions(cls) -> list[Resolution]:
        try:
            if not cls.CUSTOM_RESOLUTIONS_PATH.exists():
                return []
            resolutions = []
            content = cls.CUSTOM_RESOLUTIONS_PATH.read_text().strip()
            if not content:
                return []
            for line in content.split('\n'):
                width, height = map(int, line.split(','))
                resolutions.append(Resolution(width, height))
            return resolutions
        except:
            return []

    @classmethod
    def save_custom_resolutions(cls, resolutions: list[Resolution]) -> None:
        cls.CUSTOM_RESOLUTIONS_PATH.parent.mkdir(exist_ok=True)
        content = '\n'.join(f"{r.width},{r.height}" for r in resolutions)
        cls.CUSTOM_RESOLUTIONS_PATH.write_text(content)

class DisplayManager:
    NATIVE_RESOLUTION = Resolution(2560, 1440)

    @staticmethod
    def get_current_resolution() -> Resolution:
        dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
        return Resolution(dm.PelsWidth, dm.PelsHeight)

    @staticmethod
    def get_supported_resolutions() -> list[Resolution]:
        supported_resolutions = []
        i = 0
        while True:
            try:
                dm = win32api.EnumDisplaySettings(None, i)
                supported_resolutions.append(Resolution(dm.PelsWidth, dm.PelsHeight))
                i += 1
            except Exception:
                break
        return supported_resolutions

    @staticmethod
    def change_resolution(resolution: Resolution) -> None:
        dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
        dm.PelsWidth = resolution.width
        dm.PelsHeight = resolution.height
        dm.BitsPerPel = 32
        dm.DisplayFixedOutput = 0
        win32api.ChangeDisplaySettings(dm, win32con.CDS_UPDATEREGISTRY)

    @classmethod
    def restore_native(cls) -> None:
        cls.change_resolution(cls.NATIVE_RESOLUTION)

class CS2Manager:
    CONFIG_PATH = Path(r"C:\\Program Files (x86)\\Steam\\userdata")

    @staticmethod
    def is_running() -> bool:
        return any(proc.info['name'] == 'cs2.exe' for proc in psutil.process_iter(['name']))

    @staticmethod
    def close() -> None:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'cs2.exe':
                proc.terminate()
                break

    @staticmethod
    def launch() -> None:
        subprocess.Popen(["start", "steam://rungameid/730"], shell=True)
        time.sleep(5)

    def update_video_settings(self, resolution: Resolution) -> None:
        for user_dir in self.CONFIG_PATH.glob("*"):
            config_file = user_dir / "730" / "local" / "cfg" / "cs2_video.txt"
            if not config_file.exists():
                continue

            try:
                with open(config_file, 'r') as f:
                    lines = f.readlines()

                updated_lines = []
                for line in lines:
                    if '"setting.defaultres"' in line:
                        updated_lines.append(f'\t"setting.defaultres"\t\t"{resolution.width}"\n')
                    elif '"setting.defaultresheight"' in line:
                        updated_lines.append(f'\t"setting.defaultresheight"\t"{resolution.height}"\n')
                    elif '"setting.fullscreen"' in line:
                        updated_lines.append('\t"setting.fullscreen"\t\t"1"\n')
                    elif '"setting.fullscreenmode"' in line:
                        updated_lines.append('\t"setting.fullscreenmode"\t"1"\n')
                    elif '"setting.nowindowborder"' in line:
                        updated_lines.append('\t"setting.nowindowborder"\t"0"\n')
                    elif '"setting.defaultwindowedmode"' in line:
                        updated_lines.append('\t"setting.defaultwindowedmode"\t"0"\n')
                    else:
                        updated_lines.append(line)

                with open(config_file, 'w') as f:
                    f.writelines(updated_lines)
            except OSError:
                continue

class ResolutionUI:
    RESOLUTIONS = [
        Resolution(1920, 1440),
        Resolution(1280, 960),
        Resolution(1024, 768)
    ]

    def __init__(self):
        self.root = Tk()
        self.root.title("CS2 Resolution Manager")
        self.root.geometry("475x260")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TCheckbutton', padding=5)
        style.configure('TLabel', font=("Arial", 10))
        
        self.cs2_manager = CS2Manager()
        self.display_manager = DisplayManager()
        self.auto_launch = IntVar(value=Settings.get_auto_launch())
        self.custom_resolutions = Settings.load_custom_resolutions()
        self.setup_ui()

    def setup_ui(self) -> None:
        # Main container with 3-column grid
        main_container = ttk.Frame(self.root, padding="20")
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.grid_columnconfigure(2, weight=1)
        
        # Left section (settings)
        settings_frame = ttk.Frame(main_container)
        settings_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        
        # Center the title
        title_label = ttk.Label(settings_frame, text="Select Resolution:", font=("Arial", 10, "bold"))
        title_label.pack(pady=(0, 10), anchor="center")

        # Resolution dropdown - centered
        all_resolutions = sorted(set(self.RESOLUTIONS + self.custom_resolutions), 
                                key=lambda r: (-r.width, -r.height))

        # Load the last used resolution from settings
        last_used_resolution = Settings.load()
        if last_used_resolution is None or last_used_resolution not in all_resolutions:
            # Fallback to the highest resolution if no saved resolution exists
            last_used_resolution = all_resolutions[0]

        # Set the last used resolution as the default selection
        self.resolution_var = StringVar(value=str(last_used_resolution))
        self.resolution_dropdown = ttk.Combobox(
            settings_frame,
            values=[str(r) for r in all_resolutions],
            textvariable=self.resolution_var,
            width=15
        )
        self.resolution_dropdown.pack(pady=(0, 15), anchor="center")


        ttk.Separator(settings_frame, orient='horizontal').pack(fill='x', pady=15)

        # Custom resolution section - centered
        custom_label = ttk.Label(settings_frame, text="Add Custom Resolution:", font=("Arial", 10, "bold"))
        custom_label.pack(pady=(0, 10), anchor="center")

        # Custom resolution entries - centered
        custom_frame = ttk.Frame(settings_frame)
        custom_frame.pack(anchor="center", pady=(0, 10))
        
        ttk.Label(custom_frame, text="Width:").grid(row=0, column=0, padx=5)
        self.width_entry = ttk.Entry(custom_frame, width=8)
        self.width_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(custom_frame, text="Height:").grid(row=0, column=2, padx=5)
        self.height_entry = ttk.Entry(custom_frame, width=8)
        self.height_entry.grid(row=0, column=3, padx=5)

        # Add custom resolution button - centered
        ttk.Button(
            settings_frame,
            text="Add Custom Resolution",
            command=self.add_custom_resolution,
            width=22
        ).pack(pady=10, anchor="center")

        # Vertical separator
        ttk.Separator(main_container, orient='vertical').grid(row=0, column=1, sticky="ns", padx=20)

        # Right section (action buttons)
        actions_frame = ttk.Frame(main_container)
        actions_frame.grid(row=0, column=2, sticky="nsew")
        actions_frame.grid_rowconfigure(0, weight=1)  # Add space above
        actions_frame.grid_rowconfigure(4, weight=1)  # Add space below

        # Auto-launch checkbox - centered
        ttk.Checkbutton(
            actions_frame,
            text="Auto-launch game",
            variable=self.auto_launch,
            command=lambda: Settings.save_auto_launch(bool(self.auto_launch.get()))
        ).grid(row=1, column=0, pady=10)

        # Action buttons - centered and wider
        ttk.Button(
            actions_frame,
            text="Apply",
            command=self.apply_settings,
            width=20
        ).grid(row=2, column=0, pady=10)

        ttk.Button(
            actions_frame,
            text="Exit",
            command=self.exit_program,
            width=20
        ).grid(row=3, column=0, pady=10)

        # Configure the actions_frame's column to center its contents
        actions_frame.grid_columnconfigure(0, weight=1)

        # Start the monitoring thread
        Thread(target=self.monitor_cs2, daemon=True).start()

    def toggle_custom_resolution(self) -> None:
        if self.custom_enabled.get():
            self.resolution_dropdown.config(state=DISABLED)
            self.width_entry.config(state=NORMAL)
            self.height_entry.config(state=NORMAL)
        else:
            self.resolution_dropdown.config(state=NORMAL)
            self.width_entry.config(state=DISABLED)
            self.height_entry.config(state=DISABLED)

    def add_custom_resolution(self) -> None:
        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            new_resolution = Resolution(width, height)

            # Fetch supported resolutions
            supported_resolutions = self.display_manager.get_supported_resolutions()

            if new_resolution not in supported_resolutions:
                messagebox.showerror("Error", "The entered resolution is not supported by your monitor.\nPlease add this resolution in your GFX control panel.")
                return

            current_resolutions = [Resolution.from_str(r) for r in self.resolution_dropdown['values']]
            if new_resolution not in current_resolutions:
                current_resolutions.append(new_resolution)
                
                # Sort resolutions from highest to lowest
                current_resolutions.sort(key=lambda r: (-r.width, -r.height))
                
                # Update the dropdown with the sorted list
                self.resolution_dropdown['values'] = [str(r) for r in current_resolutions]
                self.custom_resolutions.append(new_resolution)
                Settings.save_custom_resolutions(self.custom_resolutions)
                
                # Set the dropdown to the newly added resolution
                self.resolution_var.set(str(new_resolution))

                self.width_entry.delete(0, END)
                self.height_entry.delete(0, END)
            else:
                messagebox.showwarning("Warning", "This resolution already exists in the list")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for width and height")


    def apply_settings(self) -> None:
        try:
            resolution = Resolution.from_str(self.resolution_var.get())
            Settings.save(resolution)
            self.display_manager.change_resolution(resolution)
            self.cs2_manager.update_video_settings(resolution)

            if self.cs2_manager.is_running():
                self.cs2_manager.close()
                self.cs2_manager.launch()
            else:
                self.cs2_manager.launch()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings: {str(e)}")

    def exit_program(self) -> None:
        current_resolution = self.display_manager.get_current_resolution()
        if current_resolution != self.display_manager.NATIVE_RESOLUTION:
            self.display_manager.restore_native()
        
        if self.cs2_manager.is_running():
            self.cs2_manager.close()
        
        self.root.destroy()
        os._exit(0)

    def monitor_cs2(self) -> None:
        launched = False
        while True:
            if self.cs2_manager.is_running():
                launched = True
            elif launched:
                self.display_manager.restore_native()
                os._exit(0)
            time.sleep(5)

    def run(self) -> None:
        self.root.mainloop()

def main():
    settings_dir = Path("settings")
    if not settings_dir.exists():
        settings_dir.mkdir()
        
    ui = ResolutionUI()
    
    if Settings.get_auto_launch():
        resolution = Settings.load()
        if resolution is not None:
            display_manager = DisplayManager()
            cs2_manager = CS2Manager()
            try:
                display_manager.change_resolution(resolution)
                cs2_manager.update_video_settings(resolution)
                cs2_manager.launch()
            except Exception as e:
                messagebox.showerror("Auto-Launch Error", 
                                   f"Failed to auto-launch with saved settings: {str(e)}")
    
    ui.run()

if __name__ == "__main__":
    main()