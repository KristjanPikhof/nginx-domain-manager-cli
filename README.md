# Nginx Domain Manager CLI

A powerful yet simple Python command-line interface (CLI) designed to streamline the management of Nginx virtual host configurations on Ubuntu servers. This tool simplifies common tasks such as adding new domains (as reverse proxies), enabling/disabling sites, deleting configurations, and integrating with Certbot for automated HTTPS.

---

## Features

*   **Easy Domain Addition:** Quickly add new Nginx server blocks tailored for reverse proxy setups.
*   **Flexible Proxying:** Specify the internal URL (e.g., `http://localhost:3000`) where Nginx should route traffic.
*   **Site Management:** Enable and disable Nginx configurations with a single command.
*   **Clean Deletion:** Safely remove domain configurations and their associated symlinks.
*   **Certbot Integration:** Guides you through the process of setting up HTTPS for your domains using Certbot, with clear instructions for the interactive steps.
*   **Interactive Interface:** Modern CLI experience with screen clearing for better readability and a guided workflow.
*   **Sudo Handling:** Manages `sudo` calls internally, prompting for your password only when necessary.

## Prerequisites

Before using this script, ensure your Ubuntu server has the following installed:

*   **Python 3:** (Usually pre-installed on modern Ubuntu versions)
*   **Nginx:** Your web server.
    ```bash
    sudo apt update
    sudo apt install nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx
    ```
*   **Certbot with Nginx Plugin:** For automated SSL certificate management.
    ```bash
    sudo apt install certbot python3-certbot-nginx
    ```
*   **Firewall/Cloud Security:** Ensure ports 80 (HTTP) and 443 (HTTPS) are open in your server's firewall (e.g., UFW) or your cloud provider's network security group settings (e.g., Oracle Cloud Infrastructure Security Lists/NSGs).

## Installation and Usage

1.  **Save the Script:**
    Download or copy the script content into a file named `nginx_domain_manger.py` on your Ubuntu server.

    ```bash
    nano nginx_domain_manger.py
    # Paste script content, then Ctrl+O, Enter, Ctrl+X
    ```

2.  **Make it Executable:**
    ```bash
    chmod +x nginx_domain_manger.py
    ```

3.  **Run the Script:**
    ```bash
    ./nginx_domain_manger.py
    ```
    You will be prompted for your user's `sudo` password when the script needs to perform administrative actions.

### Important Notes on Certbot Usage

When you select the "Add HTTPS to a domain" option (Option 5), the script will pause and provide you with a specific `sudo certbot` command. **You must copy this command, paste it into your terminal, and run it manually.** This is because Certbot is an interactive tool that may ask you questions (e.g., for email, agreeing to Terms of Service, or redirection preferences). Once Certbot completes successfully, return to the script's window and press `Enter` to continue.

## Domain Configuration Template

When adding a new domain (Option 2), the script generates an Nginx configuration specifically designed for reverse proxying. It looks like this (with SSL parts handled by Certbot later):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name your.domain;

    location / {
        proxy_pass http://your_internal_target:port;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    error_log /var/log/nginx/your.domain_error.log;
    access_log /var/log/nginx/your.domain_access.log;
}
# HTTPS block will be managed by Certbot later
# ... (Certbot automatically adds the 443 block and SSL directives)
