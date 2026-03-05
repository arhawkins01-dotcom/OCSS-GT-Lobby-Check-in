# IIS Reverse Proxy Configuration for OCSS GT Lobby Check-In

This document provides the `web.config` snippet and IIS setup steps for proxying HTTPS traffic to the Streamlit application running on `localhost:8501`.

---

## Prerequisites

- **Application Request Routing (ARR) 3.0** must be installed.
- **URL Rewrite Module 2.1** must be installed.
- ARR proxy mode must be **enabled** (IIS Manager → Application Request Routing Cache → Enable Proxy).

---

## web.config

Place this file at the root of your IIS site (e.g., `C:\inetpub\wwwroot\`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>

    <!-- Allow ARR proxy pass-through -->
    <rewrite>
      <rules>
        <!-- Redirect HTTP to HTTPS -->
        <rule name="HTTP to HTTPS Redirect" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="^OFF$" />
          </conditions>
          <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
        </rule>

        <!-- WebSocket support for Streamlit -->
        <rule name="Streamlit WebSocket" stopProcessing="true">
          <match url="^(_stcore/stream)" />
          <action type="Rewrite" url="ws://localhost:8501/{R:0}" />
        </rule>

        <!-- Reverse proxy all other requests to Streamlit -->
        <rule name="Streamlit Reverse Proxy" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="http://localhost:8501/{R:1}" />
        </rule>
      </rules>
    </rewrite>

    <!-- Security headers -->
    <httpProtocol>
      <customHeaders>
        <add name="X-Content-Type-Options" value="nosniff" />
        <add name="X-Frame-Options" value="SAMEORIGIN" />
        <add name="X-XSS-Protection" value="1; mode=block" />
        <add name="Strict-Transport-Security" value="max-age=31536000; includeSubDomains" />
        <remove name="X-Powered-By" />
      </customHeaders>
    </httpProtocol>

    <!-- Prevent IIS from serving static files directly -->
    <staticContent>
      <remove fileExtension=".py" />
    </staticContent>

  </system.webServer>
</configuration>
```

---

## ARR Server Farm (optional – for load balancing)

If you need to run multiple Streamlit instances behind a load balancer, configure a **Server Farm** in ARR:

1. In IIS Manager, right-click **Server Farms** → **Create Server Farm**.
2. Name it `StreamlitFarm`.
3. Add server `localhost:8501` (and any additional instances).
4. Under **Load Balance**, choose **Least Requests**.
5. Enable **Session Affinity** (ARR cookie-based) to prevent Streamlit WebSocket disconnects.

---

## SSL Binding

1. In IIS Manager, select your site.
2. Click **Bindings** → **Add**.
3. Type: **https**, IP: All Unassigned, Port: **443**.
4. Select your SSL certificate.
5. Click **OK**.

---

## Verification

```powershell
# Test that IIS is serving the proxy correctly
Invoke-WebRequest -Uri "https://localhost/" -UseBasicParsing | Select-Object StatusCode, StatusDescription
```

Expected: `StatusCode 200 OK`.

---

## Notes

- Streamlit uses **WebSocket** connections for real-time updates. Ensure the `Streamlit WebSocket` rewrite rule is applied **before** the general reverse proxy rule.
- The `--server.enableCORS false` flag in `start_streamlit.ps1` is safe when IIS handles HTTPS termination.
