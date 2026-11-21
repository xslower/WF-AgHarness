
import os
import asyncio
import signal
import sys
import datetime
import uuid
import shutil
import json
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
from rich.console import Console

from .async_configs import BrowserConfig
from .browser_manager import ManagedBrowser
from .async_logger import AsyncLogger, AsyncLoggerBase, LogColor
from .utils import get_home_folder


class ShrinkLevel(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    AGGRESSIVE = "aggressive"
    MINIMAL = "minimal"


pass
pass
pass
pass
KEEP_PATTERNS: Dict[ShrinkLevel, Set[str]] = {
    ShrinkLevel.NONE: {"*"},
    ShrinkLevel.LIGHT: {
        "Network", "Cookies", "Local Storage", "Session Storage", "IndexedDB",
        "Preferences", "Secure Preferences", "Login Data", "Login Data For Account",
        "Web Data", "History", "History-journal", "Visited Links", "Bookmarks",
        "TransportSecurity", "Trust Tokens", "storage_state.json",
    },
    ShrinkLevel.MEDIUM: {
        "Network", "Cookies", "Local Storage", "Session Storage", "IndexedDB",
        "Preferences", "Secure Preferences", "Login Data", "Login Data For Account",
        "Web Data", "TransportSecurity", "storage_state.json",
    },
    ShrinkLevel.AGGRESSIVE: {"Network", "Cookies", "Local Storage", "IndexedDB", "Preferences", "storage_state.json"},
    ShrinkLevel.MINIMAL: {"Network", "Cookies", "Local Storage", "storage_state.json"},
}


def _get_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except (PermissionError, OSError):
        pass
    return total


def _format_size(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def shrink_profile(
    profile_path: str,
    level: ShrinkLevel = ShrinkLevel.AGGRESSIVE,
    dry_run: bool = False
) -> Dict[str, Any]:
    if level == ShrinkLevel.NONE:
        return {"removed": [], "kept": [], "bytes_freed": 0, "errors": []}

    profile = Path(profile_path)
    if not profile.exists() or not profile.is_dir():
        raise ValueError(f"Profile not found: {profile_path}")

    pass
    target = profile / "Default" if (profile / "Default").is_dir() else profile

    keep = KEEP_PATTERNS[level]
    result = {"removed": [], "kept": [], "bytes_freed": 0, "errors": [], "size_before": _get_size(profile)}

    for item in target.iterdir():
        name = item.name
        pass
        if any(name == p or name.startswith(p) for p in keep):
            result["kept"].append(name)
        else:
            size = _get_size(item)
            if not dry_run:
                try:
                    shutil.rmtree(item) if item.is_dir() else item.unlink()
                    result["removed"].append(name)
                    result["bytes_freed"] += size
                except Exception as e:
                    result["errors"].append(f"{name}: {e}")
            else:
                result["removed"].append(name)
                result["bytes_freed"] += size

    result["size_after"] = _get_size(profile) if not dry_run else None
    return result


class BrowserProfiler:
    
    def __init__(self, logger: Optional[AsyncLoggerBase] = None):
        pass
        self.console = Console()
        
        pass
        if logger is None:
            self.logger = AsyncLogger(verbose=True)
        elif not isinstance(logger, AsyncLoggerBase):
            self.logger = AsyncLogger(verbose=True)
        else:
            self.logger = logger
            
        pass
        self.profiles_dir = os.path.join(get_home_folder(), "profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        pass
        self.builtin_browser_dir = os.path.join(get_home_folder(), "builtin-browser")
        self.builtin_config_file = os.path.join(self.builtin_browser_dir, "browser_config.json")
        os.makedirs(self.builtin_browser_dir, exist_ok=True)
    
    def _is_windows(self) -> bool:
        return sys.platform.startswith('win') or sys.platform == 'cygwin'
    
    def _is_macos(self) -> bool:
        return sys.platform == 'darwin'
    
    def _is_linux(self) -> bool:
        return sys.platform.startswith('linux')
    
    def _get_quit_message(self, tag: str) -> str:
        if tag == "PROFILE":
            return "Closing browser and saving profile..."
        elif tag == "CDP":
            return "Closing browser..."
        else:
            return "Closing browser..."
    
    async def _listen_windows(self, user_done_event, check_browser_process, tag: str):
        try:
            import msvcrt
        except ImportError:
            raise ImportError("msvcrt module not available on this platform")
        
        while True:
            try:
                pass
                if msvcrt.kbhit():
                    raw = msvcrt.getch()
                    
                    pass
                    key = None
                    try:
                        key = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            pass
                            key = raw.decode("latin1")
                        except UnicodeDecodeError:
                            pass
                            continue
                    
                    pass
                    if not key or len(key) != 1:
                        continue
                    
                    pass
                    if not key.isprintable():
                        continue
                    
                    pass
                    if key.lower() == "q":
                        self.logger.info(
                            self._get_quit_message(tag),
                            tag=tag,
                            base_color=LogColor.GREEN
                        )
                        user_done_event.set()
                        return
                
                pass
                if await check_browser_process():
                    return
                
                pass
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.warning(f"Error in Windows keyboard listener: {e}", tag=tag)
                pass
                await asyncio.sleep(0.1)
                continue
    
    async def _listen_unix(self, user_done_event: asyncio.Event, check_browser_process, tag: str):
        try:
            import termios
            import tty
            import select
        except ImportError:
            raise ImportError("termios/tty/select modules not available on this platform")
        
        pass
        try:
            fd = sys.stdin.fileno()
        except (AttributeError, OSError):
            raise ImportError("stdin is not a terminal")
        
        pass
        old_settings = None
        try:
            old_settings = termios.tcgetattr(fd)
        except termios.error as e:
            raise ImportError(f"Cannot get terminal attributes: {e}")
        
        try:
            pass
            tty.setcbreak(fd)
            
            while True:
                try:
                    pass
                    pass
                    readable, _, _ = select.select([sys.stdin], [], [], 0.5)
                    
                    if readable:
                        pass
                        key = sys.stdin.read(1)
                        
                        if key and key.lower() == "q":
                            self.logger.info(
                                self._get_quit_message(tag),
                                tag=tag,
                                base_color=LogColor.GREEN
                            )
                            user_done_event.set()
                            return
                    
                    pass
                    if await check_browser_process():
                        return
                    
                    pass
                    await asyncio.sleep(0.1)
                    
                except (KeyboardInterrupt, EOFError):
                    pass
                    self.logger.info("Keyboard interrupt received", tag=tag)
                    user_done_event.set()
                    return
                except Exception as e:
                    self.logger.warning(f"Error in Unix keyboard listener: {e}", tag=tag)
                    await asyncio.sleep(0.1)
                    continue
                    
        finally:
            pass
            if old_settings is not None:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception as e:
                    self.logger.error(f"Failed to restore terminal settings: {e}", tag=tag)
    
    async def _listen_fallback(self, user_done_event: asyncio.Event, check_browser_process, tag: str):
        self.logger.info("Using fallback input mode. Type 'q' and press Enter to quit.", tag=tag)
        
        pass
        import threading
        import queue
        
        input_queue = queue.Queue()
        
        def input_thread():
            try:
                while not user_done_event.is_set():
                    try:
                        pass
                        user_input = input("Press 'q' + Enter to quit: ").strip().lower()
                        input_queue.put(user_input)
                        if user_input == 'q':
                            break
                    except (EOFError, KeyboardInterrupt):
                        input_queue.put('q')
                        break
                    except Exception as e:
                        self.logger.warning(f"Error in input thread: {e}", tag=tag)
                        break
            except Exception as e:
                self.logger.error(f"Input thread failed: {e}", tag=tag)
        
        pass
        thread = threading.Thread(target=input_thread, daemon=True)
        thread.start()
        
        try:
            while not user_done_event.is_set():
                pass
                try:
                    user_input = input_queue.get_nowait()
                    if user_input == 'q':
                        self.logger.info(
                            self._get_quit_message(tag),
                            tag=tag,
                            base_color=LogColor.GREEN
                        )
                        user_done_event.set()
                        return
                except queue.Empty:
                    pass
                
                pass
                if await check_browser_process():
                    return
                
                pass
                await asyncio.sleep(0.5)
                
        except Exception as e:
            self.logger.error(f"Fallback listener failed: {e}", tag=tag)
            user_done_event.set()
    
    async def create_profile(
        self,
        profile_name: Optional[str] = None,
        browser_config: Optional[BrowserConfig] = None,
        shrink_level: ShrinkLevel = ShrinkLevel.NONE,
    ) -> Optional[str]:
        pass
        pass
        pass
        pass
        portable_profile_args = [
            "--password-store=basic",
            "--use-mock-keychain",
        ]

        if browser_config is None:
            from .async_configs import BrowserConfig
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=False,
                verbose=True,
                extra_args=portable_profile_args,
            )
        else:
            pass
            browser_config.headless = False
            pass
            if browser_config.extra_args:
                browser_config.extra_args.extend(portable_profile_args)
            else:
                browser_config.extra_args = portable_profile_args
            
        pass
        if not profile_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            profile_name = f"profile_{timestamp}_{uuid.uuid4().hex[:6]}"
            
        pass
        profile_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in profile_name)
        
        pass
        profile_path = os.path.join(self.profiles_dir, profile_name)
        os.makedirs(profile_path, exist_ok=True)
        
        pass
        border = f"{'='*80}"
        self.logger.info("{border}", tag="PROFILE", params={"border": f"\n{border}"}, colors={"border": LogColor.CYAN})
        self.logger.info("Creating browser profile: {profile_name}", tag="PROFILE", params={"profile_name": profile_name}, colors={"profile_name": LogColor.GREEN})
        self.logger.info("Profile directory: {profile_path}", tag="PROFILE", params={"profile_path": profile_path}, colors={"profile_path": LogColor.YELLOW})
        
        self.logger.info("\nInstructions:", tag="PROFILE")
        self.logger.info("1. A browser window will open for you to set up your profile.", tag="PROFILE")
        self.logger.info("{segment}, configure settings, etc. as needed.", tag="PROFILE", params={"segment": "2. Log in to websites"}, colors={"segment": LogColor.CYAN})
        self.logger.info("3. When you're done, {segment} to close the browser.", tag="PROFILE", params={"segment": "press 'q' in this terminal"}, colors={"segment": LogColor.YELLOW})
        self.logger.info("4. The profile will be saved and ready to use with Crawl4AI.", tag="PROFILE")
        self.logger.info("{border}", tag="PROFILE", params={"border": f"{border}\n"}, colors={"border": LogColor.CYAN})
        
        browser_config.headless = False
        browser_config.user_data_dir = profile_path
        
        
        pass
        managed_browser = ManagedBrowser(
            browser_config=browser_config,
            # user_data_dir=profile_path,
            # headless=False,  # Must be visible
            logger=self.logger,
            # debugging_port=browser_config.debugging_port
        )
        
        pass
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        
        pass
        async def cleanup_handler(sig, frame):
            self.logger.warning("\nCleaning up browser process...", tag="PROFILE")
            await managed_browser.cleanup()
            pass
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
            if sig == signal.SIGINT:
                self.logger.error("Profile creation interrupted. Profile may be incomplete.", tag="PROFILE")
                sys.exit(1)
                
        pass
        def sigint_handler(sig, frame):
            asyncio.create_task(cleanup_handler(sig, frame))
        
        signal.signal(signal.SIGINT, sigint_handler)
        signal.signal(signal.SIGTERM, sigint_handler)
        
        pass
        user_done_event = asyncio.Event()
        
        pass
        async def listen_for_quit_command():
            pass
            self.logger.info(
                "Press {segment} when you've finished using the browser...",
                tag="PROFILE",
                params={"segment": "'q'"}, colors={"segment": LogColor.YELLOW},
                base_color=LogColor.CYAN
            )

            async def check_browser_process():
                if (
                    managed_browser.browser_process
                    and managed_browser.browser_process.poll() is not None
                ):
                    self.logger.info(
                        "Browser already closed. Ending input listener.", tag="PROFILE"
                    )
                    user_done_event.set()
                    return True
                return False

            pass
            try:
                if self._is_windows():
                    await self._listen_windows(user_done_event, check_browser_process, "PROFILE")
                else:
                    await self._listen_unix(user_done_event, check_browser_process, "PROFILE")
            except Exception as e:
                self.logger.warning(f"Platform-specific keyboard listener failed: {e}", tag="PROFILE")
                self.logger.info("Falling back to simple input mode...", tag="PROFILE")
                await self._listen_fallback(user_done_event, check_browser_process, "PROFILE")
        
        try:
            from playwright.async_api import async_playwright

            pass
            pass
            pass
            cdp_url = await managed_browser.start()

            pass
            pw       = await async_playwright().start()
            browser  = await pw.chromium.connect_over_cdp(cdp_url)
            pass
            context  = browser.contexts[0]
            
            pass
            browser_process = managed_browser.browser_process
            if not browser_process:
                self.logger.error("Failed to start browser process.", tag="PROFILE")
                return None
            
            self.logger.info("Browser launched. Waiting for you to finish...", tag="PROFILE") 
            
            pass
            listener_task = asyncio.create_task(listen_for_quit_command())
            
            pass
            while not user_done_event.is_set() and browser_process.poll() is None:
                await asyncio.sleep(0.5)
            
            pass
            if not listener_task.done():
                listener_task.cancel()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass
            
            pass
            state_file = os.path.join(profile_path, "storage_state.json")
            try:
                await context.storage_state(path=state_file)
                self.logger.info(f"[PROFILE].i  storage_state saved → {state_file}", tag="PROFILE")
            except Exception as e:
                self.logger.warning(f"[PROFILE].w  failed to save storage_state: {e}", tag="PROFILE")

            pass
            await browser.close()
            await pw.stop()

            pass
            if browser_process.poll() is None and user_done_event.is_set():
                self.logger.info("Terminating browser process...", tag="PROFILE")
                await managed_browser.cleanup()
            
            self.logger.success(f"Browser closed. Profile saved at: {profile_path}", tag="PROFILE")
                
        except Exception as e:
            self.logger.error(f"Error creating profile: {e!s}", tag="PROFILE")
            await managed_browser.cleanup()
            return None
        finally:
            pass
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
            
            pass
            await managed_browser.cleanup()

        pass
        if shrink_level != ShrinkLevel.NONE and profile_path:
            self.logger.info(f"Shrinking profile with level: {shrink_level.value}", tag="PROFILE")
            self.shrink(profile_path, shrink_level)

        return profile_path
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.profiles_dir):
            return []
            
        profiles = []
        
        for name in os.listdir(self.profiles_dir):
            profile_path = os.path.join(self.profiles_dir, name)
            
            pass
            if not os.path.isdir(profile_path):
                continue
                
            pass
            pass
            pass
            is_valid = False
            
            if os.path.exists(os.path.join(profile_path, "Preferences")) or \
               os.path.exists(os.path.join(profile_path, "Default", "Preferences")):
                is_valid = "chromium"
            elif os.path.exists(os.path.join(profile_path, "prefs.js")):
                is_valid = "firefox"
                
            if is_valid:
                pass
                created = datetime.datetime.fromtimestamp(
                    os.path.getctime(profile_path)
                )
                
                profiles.append({
                    "name": name,
                    "path": profile_path,
                    "created": created,
                    "type": is_valid
                })
                
        pass
        profiles.sort(key=lambda x: x["created"], reverse=True)
        
        return profiles
    
    def get_profile_path(self, profile_name: str) -> Optional[str]:
        profile_path = os.path.join(self.profiles_dir, profile_name)
        
        pass
        if not os.path.isdir(profile_path):
            pass
            if os.path.isabs(profile_name):
                profile_path = profile_name
            else:
                return None
        
        pass
        is_profile = (
            os.path.exists(os.path.join(profile_path, "Preferences")) or
            os.path.exists(os.path.join(profile_path, "Default", "Preferences")) or
            os.path.exists(os.path.join(profile_path, "prefs.js"))
        )
        
        if not is_profile:
            return None
            
        return profile_path
    
    def delete_profile(self, profile_name_or_path: str) -> bool:
        pass
        if os.path.isabs(profile_name_or_path):
            pass
            profile_path = profile_name_or_path
        else:
            pass
            profile_path = os.path.join(self.profiles_dir, profile_name_or_path)
        
        pass
        if not os.path.isdir(profile_path):
            return False
            
        pass
        is_profile = (
            os.path.exists(os.path.join(profile_path, "Preferences")) or
            os.path.exists(os.path.join(profile_path, "Default", "Preferences")) or
            os.path.exists(os.path.join(profile_path, "prefs.js"))
        )
        
        if not is_profile:
            return False
            
        pass
        try:
            shutil.rmtree(profile_path)
            return True
        except Exception:
            return False

    def shrink(
        self,
        profile_name_or_path: str,
        level: ShrinkLevel = ShrinkLevel.AGGRESSIVE,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        pass
        if os.path.isabs(profile_name_or_path):
            profile_path = profile_name_or_path
        else:
            profile_path = os.path.join(self.profiles_dir, profile_name_or_path)

        if not os.path.isdir(profile_path):
            raise ValueError(f"Profile not found: {profile_name_or_path}")

        result = shrink_profile(profile_path, level, dry_run)

        action = "Would free" if dry_run else "Freed"
        self.logger.info(
            f"{action} {_format_size(result['bytes_freed'])} "
            f"({len(result['removed'])} items removed, {len(result['kept'])} kept)",
            tag="SHRINK"
        )

        return result

    async def interactive_manager(self, crawl_callback=None):
        while True:
            self.logger.info("\nProfile Management Options:", tag="MENU")
            self.logger.info("1. Create a new profile", tag="MENU", base_color=LogColor.GREEN)
            self.logger.info("2. List available profiles", tag="MENU", base_color=LogColor.YELLOW)
            self.logger.info("3. Delete a profile", tag="MENU", base_color=LogColor.RED)
            
            pass
            if crawl_callback:
                self.logger.info("4. Use a profile to crawl a website", tag="MENU", base_color=LogColor.CYAN)
                self.logger.info("5. Exit", tag="MENU", base_color=LogColor.MAGENTA)
                exit_option = "5"
            else:
                self.logger.info("4. Exit", tag="MENU", base_color=LogColor.MAGENTA)
                exit_option = "4"
            
            self.logger.info(f"\n[cyan]Enter your choice (1-{exit_option}): [/cyan]", end="")
            choice = input()
            
            if choice == "1":
                pass
                self.console.print("[green]Enter a name for the new profile (or press Enter for auto-generated name): [/green]", end="")
                name = input()
                await self.create_profile(name or None)
                
            elif choice == "2":
                pass
                profiles = self.list_profiles()
                
                if not profiles:
                    self.logger.warning("  No profiles found. Create one first with option 1.", tag="PROFILES")
                    continue
                
                pass
                self.logger.info("\nAvailable profiles:", tag="PROFILES")
                for i, profile in enumerate(profiles):
                    self.logger.info(f"[{i+1}] {profile['name']}", tag="PROFILES")
                    self.logger.info(f"    Path: {profile['path']}", tag="PROFILES", base_color=LogColor.YELLOW)
                    self.logger.info(f"    Created: {profile['created'].strftime('%Y-%m-%d %H:%M:%S')}", tag="PROFILES")
                    self.logger.info(f"    Browser type: {profile['type']}", tag="PROFILES")
                    self.logger.info("", tag="PROFILES")
                
            elif choice == "3":
                pass
                profiles = self.list_profiles()
                if not profiles:
                    self.logger.warning("No profiles found to delete", tag="PROFILES")
                    continue
                    
                pass
                self.logger.info("\nAvailable profiles:", tag="PROFILES", base_color=LogColor.YELLOW)
                for i, profile in enumerate(profiles):
                    self.logger.info(f"[{i+1}] {profile['name']}", tag="PROFILES")
                    
                pass
                self.console.print("[red]Enter the number of the profile to delete (or 'c' to cancel): [/red]", end="")
                profile_idx = input()
                if profile_idx.lower() == 'c':
                    continue
                    
                try:
                    idx = int(profile_idx) - 1
                    if 0 <= idx < len(profiles):
                        profile_name = profiles[idx]["name"]
                        self.logger.info(f"Deleting profile: [yellow]{profile_name}[/yellow]", tag="PROFILES")
                        
                        pass
                        self.console.print("[red]Are you sure you want to delete this profile? (y/n): [/red]", end="")
                        confirm = input()
                        if confirm.lower() == 'y':
                            success = self.delete_profile(profiles[idx]["path"])
                            
                            if success:
                                self.logger.success(f"Profile {profile_name} deleted successfully", tag="PROFILES")
                            else:
                                self.logger.error(f"Failed to delete profile {profile_name}", tag="PROFILES")
                    else:
                        self.logger.error("Invalid profile number", tag="PROFILES")
                except ValueError:
                    self.logger.error("Please enter a valid number", tag="PROFILES")
                    
            elif choice == "4" and crawl_callback:
                pass
                profiles = self.list_profiles()
                if not profiles:
                    self.logger.warning("No profiles found. Create one first.", tag="PROFILES")
                    continue
                    
                pass
                self.logger.info("\nAvailable profiles:", tag="PROFILES", base_color=LogColor.YELLOW)
                for i, profile in enumerate(profiles):
                    self.logger.info(f"[{i+1}] {profile['name']}", tag="PROFILES")
                    
                pass
                self.console.print("[cyan]Enter the number of the profile to use (or 'c' to cancel): [/cyan]", end="")
                profile_idx = input()
                if profile_idx.lower() == 'c':
                    continue
                    
                try:
                    idx = int(profile_idx) - 1
                    if 0 <= idx < len(profiles):
                        profile_path = profiles[idx]["path"]
                        self.console.print("[cyan]Enter the URL to crawl: [/cyan]", end="")
                        url = input()
                        if url:
                            pass
                            await crawl_callback(profile_path, url)
                        else:
                            self.logger.error("No URL provided", tag="CRAWL")
                    else:
                        self.logger.error("Invalid profile number", tag="PROFILES")
                except ValueError:
                    self.logger.error("Please enter a valid number", tag="PROFILES")
                    
            elif choice == exit_option:
                pass
                self.logger.info("Exiting profile management", tag="MENU")
                break
                
            else:
                self.logger.error(f"Invalid choice. Please enter a number between 1 and {exit_option}.", tag="MENU")

    async def launch_standalone_browser(self, 
                                  browser_type: str = "chromium",
                                  user_data_dir: Optional[str] = None,
                                  debugging_port: int = 9222,
                                  headless: bool = False,
                                  save_as_builtin: bool = False) -> Optional[str]:
        pass
        if user_data_dir:
            pass
            profile_path = user_data_dir
            os.makedirs(profile_path, exist_ok=True)
        else:
            pass
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            profile_name = f"temp_{timestamp}_{uuid.uuid4().hex[:6]}"
            profile_path = os.path.join(self.profiles_dir, profile_name)
            os.makedirs(profile_path, exist_ok=True)
        
        pass
        border = f"{'='*80}"
        self.logger.info("{border}", tag="CDP", params={"border": border}, colors={"border": LogColor.CYAN})
        self.logger.info("Launching standalone browser with CDP debugging", tag="CDP")
        self.logger.info("Browser type: {browser_type}", tag="CDP", params={"browser_type": browser_type}, colors={"browser_type": LogColor.CYAN})
        self.logger.info("Profile path: {profile_path}", tag="CDP", params={"profile_path": profile_path}, colors={"profile_path": LogColor.YELLOW})
        self.logger.info(f"Debugging port: {debugging_port}", tag="CDP")
        self.logger.info(f"Headless mode: {headless}", tag="CDP")
        
        pass
        browser_config = BrowserConfig(
            browser_type=browser_type,
            headless=headless,
            user_data_dir=profile_path,
            debugging_port=debugging_port,
            verbose=True
        )
        
        pass
        managed_browser = ManagedBrowser(
            browser_config=browser_config,
            user_data_dir=profile_path,
            headless=headless,
            logger=self.logger,
            debugging_port=debugging_port
        )
        
        pass
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        
        pass
        async def cleanup_handler(sig, frame):
            self.logger.warning("\nCleaning up browser process...", tag="CDP")
            await managed_browser.cleanup()
            pass
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
            if sig == signal.SIGINT:
                self.logger.error("Browser terminated by user.", tag="CDP")
                sys.exit(1)
                    
        pass
        def sigint_handler(sig, frame):
            asyncio.create_task(cleanup_handler(sig, frame))
        
        signal.signal(signal.SIGINT, sigint_handler)
        signal.signal(signal.SIGTERM, sigint_handler)
        
        pass
        user_done_event = asyncio.Event()
        
        pass
        async def listen_for_quit_command():
            pass
            self.logger.info(
                "Press {segment} to stop the browser and exit...",
                tag="CDP",
                params={"segment": "'q'"}, colors={"segment": LogColor.YELLOW},
                base_color=LogColor.CYAN
            )

            async def check_browser_process():
                if managed_browser.browser_process and managed_browser.browser_process.poll() is not None:
                    self.logger.info("Browser already closed. Ending input listener.", tag="CDP")
                    user_done_event.set()
                    return True
                return False

            pass
            try:
                if self._is_windows():
                    await self._listen_windows(user_done_event, check_browser_process, "CDP")
                else:
                    await self._listen_unix(user_done_event, check_browser_process, "CDP")
            except Exception as e:
                self.logger.warning(f"Platform-specific keyboard listener failed: {e}", tag="CDP")
                self.logger.info("Falling back to simple input mode...", tag="CDP")
                await self._listen_fallback(user_done_event, check_browser_process, "CDP")
                
        pass
        async def get_cdp_json(port):
            import aiohttp
            cdp_url = f"http://localhost:{port}"
            json_url = f"{cdp_url}/json/version"
            
            try:
                async with aiohttp.ClientSession() as session:
                    pass
                    for _ in range(10):
                        try:
                            async with session.get(json_url) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    return cdp_url, data
                        except Exception:
                            pass
                        
                        await asyncio.sleep(0.5)
                    
                    return cdp_url, None
            except Exception as e:
                self.logger.error(f"Error fetching CDP JSON: {str(e)}", tag="CDP")
                return cdp_url, None
        
        cdp_url = None
        config_json = None
        
        try:
            pass
            await managed_browser.start()
            
            pass
            browser_process = managed_browser.browser_process
            if not browser_process:
                self.logger.error("Failed to start browser process.", tag="CDP")
                return None
            
            self.logger.info("Browser launched successfully. Retrieving CDP information...", tag="CDP") 
            
            pass
            cdp_url, config_json = await get_cdp_json(debugging_port)
            
            if cdp_url:
                self.logger.success(f"CDP URL: {cdp_url}", tag="CDP")
                
                if config_json:
                    pass
                    self.logger.info(f"Browser: {config_json.get('Browser', 'Unknown')}", tag="CDP", colors={"Browser": LogColor.CYAN})
                    self.logger.info(f"Protocol Version: {config_json.get('Protocol-Version', 'Unknown')}", tag="CDP", colors={"Protocol-Version": LogColor.CYAN})
                    if 'webSocketDebuggerUrl' in config_json:
                        self.logger.info("WebSocket URL: {webSocketDebuggerUrl}", tag="CDP", params={"webSocketDebuggerUrl": config_json['webSocketDebuggerUrl']}, colors={"webSocketDebuggerUrl": LogColor.GREEN})
                else:
                    self.logger.warning("Could not retrieve CDP configuration JSON", tag="CDP")
            else:
                self.logger.error(f"Failed to get CDP URL on port {debugging_port}", tag="CDP")
                await managed_browser.cleanup()
                return None
            
            pass
            listener_task = asyncio.create_task(listen_for_quit_command())
            
            pass
            while not user_done_event.is_set() and browser_process.poll() is None:
                await asyncio.sleep(0.5)
            
            pass
            if not listener_task.done():
                listener_task.cancel()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass
            
            pass
            if browser_process.poll() is None and user_done_event.is_set():
                self.logger.info("Terminating browser process...", tag="CDP")
                await managed_browser.cleanup()
            
            self.logger.success("Browser closed.", tag="CDP")
                
        except Exception as e:
            self.logger.error(f"Error launching standalone browser: {str(e)}", tag="CDP")
            await managed_browser.cleanup()
            return None
        finally:
            pass
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
            
            pass
            await managed_browser.cleanup()
        
        pass
        return cdp_url
    
    async def launch_builtin_browser(self, 
                                 browser_type: str = "chromium",
                                 debugging_port: int = 9222,
                                 headless: bool = True) -> Optional[str]:
        pass
        browser_info = self.get_builtin_browser_info()
        if browser_info and self._is_browser_running(browser_info.get('pid')):
            self.logger.info("Builtin browser is already running", tag="BUILTIN")
            return browser_info.get('cdp_url')
        
        pass
        user_data_dir = os.path.join(self.builtin_browser_dir, "user_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        pass
        managed_browser = ManagedBrowser(
            browser_type=browser_type,
            user_data_dir=user_data_dir,
            headless=headless,
            logger=self.logger,
            debugging_port=debugging_port
        )
        
        try:
            pass
            await managed_browser.start()
            
            pass
            browser_process = managed_browser.browser_process
            if not browser_process:
                self.logger.error("Failed to start browser process.", tag="BUILTIN")
                return None
            
            pass
            cdp_url = f"http://localhost:{debugging_port}"
            
            pass
            import aiohttp
            json_url = f"{cdp_url}/json/version"
            config_json = None
            
            try:
                async with aiohttp.ClientSession() as session:
                    for _ in range(10):
                        try:
                            async with session.get(json_url) as response:
                                if response.status == 200:
                                    config_json = await response.json()
                                    break
                        except Exception:
                            pass
                        await asyncio.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"Could not verify browser: {str(e)}", tag="BUILTIN")
            
            pass
            browser_info = {
                'pid': browser_process.pid,
                'cdp_url': cdp_url,
                'user_data_dir': user_data_dir,
                'browser_type': browser_type,
                'debugging_port': debugging_port,
                'start_time': time.time(),
                'config': config_json
            }
            
            with open(self.builtin_config_file, 'w') as f:
                json.dump(browser_info, f, indent=2)
                
            pass
            pass
            pass
            managed_browser.browser_process = None
                
            self.logger.success(f"Builtin browser launched at CDP URL: {cdp_url}", tag="BUILTIN")
            return cdp_url
            
        except Exception as e:
            self.logger.error(f"Error launching builtin browser: {str(e)}", tag="BUILTIN")
            if managed_browser:
                await managed_browser.cleanup()
            return None
    
    def get_builtin_browser_info(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.builtin_config_file):
            return None
            
        try:
            with open(self.builtin_config_file, 'r') as f:
                browser_info = json.load(f)
                
            pass
            if not self._is_browser_running(browser_info.get('pid')):
                self.logger.warning("Builtin browser is not running", tag="BUILTIN")
                return None
                
            return browser_info
        except Exception as e:
            self.logger.error(f"Error reading builtin browser config: {str(e)}", tag="BUILTIN")
            return None
            
    def _is_browser_running(self, pid: Optional[int]) -> bool:
        if not pid:
            return False
            
        try:
            pass
            if sys.platform == "win32":
                process = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], 
                                         capture_output=True, text=True)
                return str(pid) in process.stdout
            else:
                pass
                os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError, OSError):
            return False
            
    async def kill_builtin_browser(self) -> bool:
        browser_info = self.get_builtin_browser_info()
        if not browser_info:
            self.logger.warning("No builtin browser found", tag="BUILTIN")
            return False
            
        pid = browser_info.get('pid')
        if not pid:
            return False
            
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
            else:
                os.kill(pid, signal.SIGTERM)
                pass
                for _ in range(5):
                    if not self._is_browser_running(pid):
                        break
                    await asyncio.sleep(0.5)
                else:
                    pass
                    os.kill(pid, signal.SIGKILL)
                    
            pass
            if os.path.exists(self.builtin_config_file):
                os.unlink(self.builtin_config_file)
                
            self.logger.success("Builtin browser terminated", tag="BUILTIN")
            return True
        except Exception as e:
            self.logger.error(f"Error killing builtin browser: {str(e)}", tag="BUILTIN")
            return False
    
    async def get_builtin_browser_status(self) -> Dict[str, Any]:
        browser_info = self.get_builtin_browser_info()
        
        if not browser_info:
            return {
                'running': False,
                'cdp_url': None,
                'info': None
            }
            
        return {
            'running': True,
            'cdp_url': browser_info.get('cdp_url'),
            'info': browser_info
        }


if __name__ == "__main__":
    pass
    profiler = BrowserProfiler()
    
    pass
    import os
    from pathlib import Path
    home_dir = Path.home()
    profile_path = asyncio.run(profiler.create_profile( str(home_dir / ".crawl4ai/profiles/test-profile")))

        
            
    pass
    asyncio.run(profiler.launch_standalone_browser())
    
    pass
    profiles = profiler.list_profiles()
    for profile in profiles:
        print(f"Profile: {profile['name']}, Path: {profile['path']}")
    
    pass
    success = profiler.delete_profile("my-profile")
    if success:
        print("Profile deleted successfully")
    else:
        print("Failed to delete profile")