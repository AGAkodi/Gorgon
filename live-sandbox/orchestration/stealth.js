/**
 * Anti-fingerprinting and anti-bot stealth overrides.
 * Injected before any other page script runs to mask standard headless Chromium signatures.
 */
(function() {
    'use strict';

    // 1. Overwrite navigator.webdriver to false
    try {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
    } catch (e) {}

    // 2. Add realistic languages
    try {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    } catch (e) {}

    // 3. Set realistic platform (e.g. Win32 on Windows, MacIntel on macOS)
    try {
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });
    } catch (e) {}

    // 4. Mock window.chrome object (often checked by Cloudflare, Akamai, etc.)
    try {
        window.chrome = {
            app: {
                isInstalled: false,
                InstallState: {
                    DISABLED: 'disabled',
                    INSTALLED: 'installed',
                    NOT_INSTALLED: 'not_installed'
                },
                RunningState: {
                    CANNOT_RUN: 'cannot_run',
                    READY_TO_RUN: 'ready_to_run',
                    RUNNING: 'running'
                }
            },
            runtime: {
                OnInstalledReason: {
                    CHROME_UPDATE: 'chrome_update',
                    INSTALL: 'install',
                    SHARED_MODULE_UPDATE: 'shared_module_update',
                    UPDATE: 'update'
                },
                OnRestartRequiredReason: {
                    APP_UPDATE: 'app_update',
                    OS_UPDATE: 'os_update',
                    PERIODIC: 'periodic'
                },
                PlatformArch: {
                    ARM: 'arm',
                    ARM64: 'arm64',
                    MIPS: 'mips',
                    MIPS64: 'mips64',
                    X86_32: 'x86-32',
                    X86_64: 'x86-64'
                },
                PlatformNaclArch: {
                    ARM: 'arm',
                    MIPS: 'mips',
                    MIPS64: 'mips64',
                    X86_32: 'x86-32',
                    X86_64: 'x86-64'
                },
                PlatformOs: {
                    ANDROID: 'android',
                    CROS: 'cros',
                    LINUX: 'linux',
                    MAC: 'mac',
                    OPENBSD: 'openbsd',
                    WIN: 'win'
                },
                RequestUpdateCheckStatus: {
                    NO_UPDATE: 'no_update',
                    THROTTLED: 'throttled',
                    UPDATE_AVAILABLE: 'update_available'
                }
            }
        };
    } catch (e) {}

    // 5. Spoof plugins (headless typically has 0 plugins)
    try {
        const mockPlugins = [
            { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbgojcjbhgocagamgkbjboombapgj', description: 'Chrome PDF Viewer' }
        ];
        Object.defineProperty(navigator, 'plugins', {
            get: () => mockPlugins
        });
    } catch (e) {}

    // 6. Overwrite WebGL vendor/renderer to standard non-headless values
    try {
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Google Inc. (Intel)';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'ANANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, vs_5_0, ps_5_0)';
            }
            return getParameter.apply(this, arguments);
        };
    } catch (e) {}

    console.log('[Vetra Stealth] Anti-fingerprinting protections active.');
})();
