// AQI Passkey Authentication - Browser Integration
// Load this script in your HTML: <script src="aqi-passkey-auth.js"></script>

class AQIPasskeyAuth {
    constructor(apiBaseUrl = '/api/auth') {
        this.apiBaseUrl = apiBaseUrl;
        this.webauthnLoaded = false;
    }

    async loadWebAuthn() {
        if (this.webauthnLoaded) return;

        try {
            const webauthn = await import('https://cdn.jsdelivr.net/npm/@github/webauthn-json/dist/esm/webauthn-json.browser-ponyfill.js');
            this.create = webauthn.create;
            this.get = webauthn.get;
            this.parseCreationOptionsFromJSON = webauthn.parseCreationOptionsFromJSON;
            this.parseRequestOptionsFromJSON = webauthn.parseRequestOptionsFromJSON;
            this.webauthnLoaded = true;
        } catch (error) {
            console.error('Failed to load WebAuthn library:', error);
            throw new Error('WebAuthn not supported');
        }
    }

    async registerPasskey(userId, userEmail) {
        try {
            await this.loadWebAuthn();

            // Start registration
            const response = await fetch(`${this.apiBaseUrl}/register-passkey`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, email: userEmail })
            });

            const data = await response.json();

            if (data.status !== 'registration_initiated') {
                throw new Error(data.message || 'Registration failed');
            }

            // Create credential
            const creationOptions = this.parseCreationOptionsFromJSON(data.challenge_options);
            const credential = await this.create(creationOptions);

            // Complete registration
            const verifyResponse = await fetch(`${this.apiBaseUrl}/verify-passkey`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    credential: credential
                })
            });

            const verifyData = await verifyResponse.json();
            return verifyData;

        } catch (error) {
            console.error('Passkey registration failed:', error);
            throw error;
        }
    }

    async authenticatePasskey(userId) {
        try {
            await this.loadWebAuthn();

            // Start authentication
            const response = await fetch(`${this.apiBaseUrl}/authenticate-passkey`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId })
            });

            const data = await response.json();

            if (data.status !== 'authentication_initiated') {
                throw new Error(data.message || 'Authentication failed');
            }

            // Get credential
            const requestOptions = this.parseRequestOptionsFromJSON(data.challenge_options);
            const credential = await this.get(requestOptions);

            // Complete authentication
            const verifyResponse = await fetch(`${this.apiBaseUrl}/verify-authentication`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: data.session_id,
                    credential: credential
                })
            });

            const verifyData = await verifyResponse.json();
            return verifyData;

        } catch (error) {
            console.error('Passkey authentication failed:', error);
            throw error;
        }
    }

    // Check if Passkeys are supported
    isSupported() {
        return window.PublicKeyCredential &&
               typeof window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable === 'function';
    }

    // Check if platform authenticator is available
    async isPlatformAuthenticatorAvailable() {
        if (!this.isSupported()) return false;

        try {
            const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
            return available;
        } catch (error) {
            return false;
        }
    }
}

// UI Helper Functions
class AQIPasskeyUI {
    constructor(auth) {
        this.auth = auth;
    }

    createRegistrationUI(containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="aqi-passkey-registration">
                <h3>Secure Your AQI Agent Access</h3>
                <p>Register a Passkey for passwordless authentication</p>
                <form id="passkey-registration-form">
                    <input type="email" id="user-email" placeholder="Enter your email" required>
                    <button type="submit" id="register-btn">Register Passkey</button>
                </form>
                <div id="registration-status"></div>
            </div>
        `;

        document.getElementById('passkey-registration-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('user-email').value;
            const userId = email; // In production, use proper user ID

            const statusDiv = document.getElementById('registration-status');
            statusDiv.textContent = 'Registering Passkey...';

            try {
                const result = await this.auth.registerPasskey(userId, email);
                statusDiv.innerHTML = `<span style="color: green;">✅ ${result.message}</span>`;
            } catch (error) {
                statusDiv.innerHTML = `<span style="color: red;">❌ ${error.message}</span>`;
            }
        });
    }

    createLoginUI(containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="aqi-passkey-login">
                <h3>Access Your AQI Agents</h3>
                <form id="passkey-login-form">
                    <input type="email" id="login-email" placeholder="Enter your email" required>
                    <button type="submit" id="login-btn">Authenticate with Passkey</button>
                </form>
                <div id="login-status"></div>
            </div>
        `;

        document.getElementById('passkey-login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const userId = email; // In production, use proper user ID

            const statusDiv = document.getElementById('login-status');
            statusDiv.textContent = 'Authenticating...';

            try {
                const result = await this.auth.authenticatePasskey(userId);
                if (result.status === 'authenticated') {
                    statusDiv.innerHTML = `<span style="color: green;">✅ Welcome back! Redirecting...</span>`;
                    // Store token and redirect
                    localStorage.setItem('aqi_auth_token', result.token);
                    setTimeout(() => window.location.href = '/dashboard', 2000);
                } else {
                    statusDiv.innerHTML = `<span style="color: red;">❌ ${result.message}</span>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<span style="color: red;">❌ ${error.message}</span>`;
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    const auth = new AQIPasskeyAuth();
    const ui = new AQIPasskeyUI(auth);

    // Check Passkey support
    if (auth.isSupported()) {
        console.log('✅ Passkeys supported');

        const platformAvailable = await auth.isPlatformAuthenticatorAvailable();
        if (platformAvailable) {
            console.log('✅ Platform authenticator available');
        }

        // Make auth system globally available
        window.AQIAuth = auth;
        window.AQIUI = ui;
    } else {
        console.warn('❌ Passkeys not supported in this browser');
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AQIPasskeyAuth, AQIPasskeyUI };
}</content>
<parameter name="filePath">C:\Users\signa\OneDrive\Desktop\AQI North Connector\aqi-passkey-auth.js