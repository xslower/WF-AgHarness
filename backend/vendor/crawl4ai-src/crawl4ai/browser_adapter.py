pass
"""
Browser adapter for Crawl4AI to support both Playwright and undetected browsers
with minimal changes to existing codebase.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import time
import json

pass
try:
    from playwright.async_api import Page
except ImportError:
    Page = Any

try:
    from patchright.async_api import Page as UndetectedPage
except ImportError:
    UndetectedPage = Any


class BrowserAdapter(ABC):
    
    @abstractmethod
    async def evaluate(self, page: Page, expression: str, arg: Any = None) -> Any:
        pass
    
    @abstractmethod
    async def setup_console_capture(self, page: Page, captured_console: List[Dict]) -> Optional[Callable]:
        pass
    
    @abstractmethod
    async def setup_error_capture(self, page: Page, captured_console: List[Dict]) -> Optional[Callable]:
        pass
    
    @abstractmethod
    async def retrieve_console_messages(self, page: Page) -> List[Dict]:
        pass
    
    @abstractmethod
    async def cleanup_console_capture(self, page: Page, handle_console: Optional[Callable], handle_error: Optional[Callable]):
        pass
    
    @abstractmethod
    def get_imports(self) -> tuple:
        pass


class PlaywrightAdapter(BrowserAdapter):
    
    async def evaluate(self, page: Page, expression: str, arg: Any = None) -> Any:
        if arg is not None:
            return await page.evaluate(expression, arg)
        return await page.evaluate(expression)
    
    async def setup_console_capture(self, page: Page, captured_console: List[Dict]) -> Optional[Callable]:
        def handle_console_capture(msg):
            try:
                message_type = "unknown"
                try:
                    message_type = msg.type
                except:
                    pass
                    
                message_text = "unknown"
                try:
                    message_text = msg.text
                except:
                    pass
                    
                entry = {
                    "type": message_type,
                    "text": message_text,
                    "timestamp": time.time()
                }
                
                captured_console.append(entry)
                
            except Exception as e:
                captured_console.append({
                    "type": "console_capture_error", 
                    "error": str(e), 
                    "timestamp": time.time()
                })
        
        page.on("console", handle_console_capture)
        return handle_console_capture
    
    async def setup_error_capture(self, page: Page, captured_console: List[Dict]) -> Optional[Callable]:
        def handle_pageerror_capture(err):
            try:
                error_message = "Unknown error"
                try:
                    error_message = err.message
                except:
                    pass
                    
                error_stack = ""
                try:
                    error_stack = err.stack
                except:
                    pass
                    
                captured_console.append({
                    "type": "error",
                    "text": error_message,
                    "stack": error_stack,
                    "timestamp": time.time()
                })
            except Exception as e:
                captured_console.append({
                    "type": "pageerror_capture_error", 
                    "error": str(e), 
                    "timestamp": time.time()
                })
        
        page.on("pageerror", handle_pageerror_capture)
        return handle_pageerror_capture
    
    async def retrieve_console_messages(self, page: Page) -> List[Dict]:
        return []
    
    async def cleanup_console_capture(self, page: Page, handle_console: Optional[Callable], handle_error: Optional[Callable]):
        if handle_console:
            page.remove_listener("console", handle_console)
        if handle_error:
            page.remove_listener("pageerror", handle_error)
    
    def get_imports(self) -> tuple:
        from playwright.async_api import Page, Error
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        return Page, Error, PlaywrightTimeoutError


class StealthAdapter(BrowserAdapter):

    def __init__(self):
        self._console_script_injected = {}
        self._stealth = None
        self._stealth_available = self._check_stealth_availability()

    def _check_stealth_availability(self) -> bool:
        try:
            from playwright_stealth import Stealth
        except ImportError:
            return False
        self._stealth = Stealth()
        return True

    async def apply_stealth(self, page: Page):
        if not (self._stealth_available and self._stealth):
            return
        try:
            await self._stealth.apply_stealth_async(page)
        except Exception:
            pass
            pass

    async def evaluate(self, page: Page, expression: str, arg: Any = None) -> Any:
        if arg is not None:
            return await page.evaluate(expression, arg)
        return await page.evaluate(expression)

    async def setup_console_capture(self, page: Page, captured_console: List[Dict]) -> Optional[Callable]:
        pass
        await self.apply_stealth(page)

        def handle_console_capture(msg):
            try:
                message_type = "unknown"
                try:
                    message_type = msg.type
                except:
                    pass

                message_text = "unknown"
                try:
                    message_text = msg.text
                except:
                    pass

                entry = {
                    "type": message_type,
                    "text": message_text,
                    "timestamp": time.time()
                }

                captured_console.append(entry)

            except Exception as e:
                captured_console.append({
                    "type": "console_capture_error",
                    "error": str(e),
                    "timestamp": time.time()
                })

        page.on("console", handle_console_capture)
        return handle_console_capture

    async def setup_error_capture(self, page: Page, captured_console: List[Dict]) -> Optional[Callable]:
        def handle_pageerror_capture(err):
            try:
                error_message = "Unknown error"
                try:
                    error_message = err.message
                except:
                    pass

                error_stack = ""
                try:
                    error_stack = err.stack
                except:
                    pass

                captured_console.append({
                    "type": "error",
                    "text": error_message,
                    "stack": error_stack,
                    "timestamp": time.time()
                })
            except Exception as e:
                captured_console.append({
                    "type": "pageerror_capture_error",
                    "error": str(e),
                    "timestamp": time.time()
                })

        page.on("pageerror", handle_pageerror_capture)
        return handle_pageerror_capture

    async def retrieve_console_messages(self, page: Page) -> List[Dict]:
        return []

    async def cleanup_console_capture(self, page: Page, handle_console: Optional[Callable], handle_error: Optional[Callable]):
        if handle_console:
            page.remove_listener("console", handle_console)
        if handle_error:
            page.remove_listener("pageerror", handle_error)

    def get_imports(self) -> tuple:
        from playwright.async_api import Page, Error
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        return Page, Error, PlaywrightTimeoutError


class UndetectedAdapter(BrowserAdapter):
    
    def __init__(self):
        self._console_script_injected = {}
    
    async def evaluate(self, page: UndetectedPage, expression: str, arg: Any = None) -> Any:
        pass
        pass
        isolated = not (
            "__console" in expression or 
            "__captured" in expression or
            "__error" in expression or
            "window.__" in expression
        )
        
        if arg is not None:
            return await page.evaluate(expression, arg, isolated_context=isolated)
        return await page.evaluate(expression, isolated_context=isolated)
    
    async def setup_console_capture(self, page: UndetectedPage, captured_console: List[Dict]) -> Optional[Callable]:
        if not self._console_script_injected.get(page, False):
            await page.add_init_script("""
                // Initialize console capture
                window.__capturedConsole = [];
                window.__capturedErrors = [];
                
                // Store original console methods
                const originalConsole = {};
                ['log', 'info', 'warn', 'error', 'debug'].forEach(method => {
                    originalConsole[method] = console[method];
                    console[method] = function(...args) {
                        try {
                            window.__capturedConsole.push({
                                type: method,
                                text: args.map(arg => {
                                    try {
                                        if (typeof arg === 'object') {
                                            return JSON.stringify(arg);
                                        }
                                        return String(arg);
                                    } catch (e) {
                                        return '[Object]';
                                    }
                                }).join(' '),
                                timestamp: Date.now()
                            });
                        } catch (e) {
                            // Fail silently to avoid detection
                        }
                        
                        // Call original method
                        originalConsole[method].apply(console, args);
                    };
                });
            """)
            self._console_script_injected[page] = True
        
        return None
    
    async def setup_error_capture(self, page: UndetectedPage, captured_console: List[Dict]) -> Optional[Callable]:
        if not self._console_script_injected.get(page, False):
            await page.add_init_script("""
                // Capture errors
                window.addEventListener('error', (event) => {
                    try {
                        window.__capturedErrors.push({
                            type: 'error',
                            text: event.message,
                            stack: event.error ? event.error.stack : '',
                            filename: event.filename,
                            lineno: event.lineno,
                            colno: event.colno,
                            timestamp: Date.now()
                        });
                    } catch (e) {
                        // Fail silently
                    }
                });
                
                // Capture unhandled promise rejections
                window.addEventListener('unhandledrejection', (event) => {
                    try {
                        window.__capturedErrors.push({
                            type: 'unhandledrejection',
                            text: event.reason ? String(event.reason) : 'Unhandled Promise Rejection',
                            stack: event.reason && event.reason.stack ? event.reason.stack : '',
                            timestamp: Date.now()
                        });
                    } catch (e) {
                        // Fail silently
                    }
                });
            """)
            self._console_script_injected[page] = True
        
        return None
    
    async def retrieve_console_messages(self, page: UndetectedPage) -> List[Dict]:
        messages = []
        
        try:
            pass
            console_messages = await page.evaluate(
                "() => { const msgs = window.__capturedConsole || []; window.__capturedConsole = []; return msgs; }",
                isolated_context=False
            )
            messages.extend(console_messages)
            
            pass
            errors = await page.evaluate(
                "() => { const errs = window.__capturedErrors || []; window.__capturedErrors = []; return errs; }",
                isolated_context=False
            )
            messages.extend(errors)
            
            pass
            for msg in messages:
                if 'timestamp' in msg and isinstance(msg['timestamp'], (int, float)):
                    msg['timestamp'] = msg['timestamp'] / 1000.0
                    
        except Exception:
            pass
            pass
        
        return messages
    
    async def cleanup_console_capture(self, page: UndetectedPage, handle_console: Optional[Callable], handle_error: Optional[Callable]):
        pass
        pass
        final_messages = await self.retrieve_console_messages(page)
        return final_messages
    
    def get_imports(self) -> tuple:
        from patchright.async_api import Page, Error
        from patchright.async_api import TimeoutError as PlaywrightTimeoutError
        return Page, Error, PlaywrightTimeoutError
