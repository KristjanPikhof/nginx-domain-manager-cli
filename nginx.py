#!/usr/bin/env python3

import os
import subprocess
import sys
import re # For regular expressions to check http:// prefix
import platform # To detect OS for clear screen command

# --- Configuration ---
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"
NGINX_LOG_DIR = "/var/log/nginx" 

# --- Utility Functions ---

def clear_screen():
    """Clears the terminal screen."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def run_sudo_command(command, check=True):
    """
    Runs a command with sudo. Returns True on success, False on failure.
    """
    print(f"\nRunning: sudo {' '.join(command)}")
    try:
        # Use Popen to allow password prompt to be interactive
        process = subprocess.Popen(['sudo'] + command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            print(f"Error executing: {' '.join(command)}")
            if stdout: print(f"STDOUT:\n{stdout}")
            if stderr: print(f"STDERR:\n{stderr}")
            if check:
                raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)
            return False
        # print(f"Output:\n{stdout}") # Uncomment for verbose output
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print(f"Output:\n{e.stdout}")
        print(f"Error:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: Command '{command[0]}' not found. Is it installed and in your PATH?")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def check_nginx_config():
    """Tests Nginx configuration syntax."""
    print("\nTesting Nginx configuration...")
    result = run_sudo_command(['nginx', '-t'], check=False)
    if not result:
        print("Nginx configuration test failed. Please fix errors before proceeding.")
        return False
    else:
        print("Nginx configuration syntax is OK.")
        return True

def reload_nginx():
    """Reloads Nginx service."""
    print("\nReloading Nginx...")
    if run_sudo_command(['systemctl', 'reload', 'nginx']):
        print("Nginx reloaded successfully.")
        return True
    else:
        print("Failed to reload Nginx. Check logs for details.")
        return False

# --- Domain Management Functions ---

def get_available_domains():
    """Returns a list of all raw filenames in sites-available."""
    if not os.path.isdir(NGINX_SITES_AVAILABLE):
        print(f"Error: Nginx sites-available directory not found: {NGINX_SITES_AVAILABLE}")
        return []
    
    domains = []
    for filename in os.listdir(NGINX_SITES_AVAILABLE):
        if os.path.isfile(os.path.join(NGINX_SITES_AVAILABLE, filename)):
            domains.append(filename)
    return sorted(domains)

def list_domains():
    """Lists all configured domains and indicates if they are enabled."""
    clear_screen() # Clear screen before listing
    print("\n--- Listing all configured domains ---")
    available_domains = get_available_domains() # Get domains directly, don't call list_domains to avoid double clear/pause
    if not available_domains:
        print("No domain configurations found in sites-available.")
        input("\nPress Enter to return to main menu...") # Pause for user to read
        return [] # Return empty list if no domains
    
    print("Available domains:")
    enabled_domains = []
    if os.path.isdir(NGINX_SITES_ENABLED):
        for item in os.listdir(NGINX_SITES_ENABLED):
            full_path = os.path.join(NGINX_SITES_ENABLED, item)
            if os.path.islink(full_path):
                link_target = os.path.realpath(full_path)
                if link_target.startswith(NGINX_SITES_AVAILABLE):
                    enabled_domains.append(os.path.basename(full_path))

    for i, domain in enumerate(available_domains):
        status = " (Enabled)" if domain in enabled_domains else " (Disabled)"
        print(f"  {i+1}. {domain}{status}")
    print("--------------------------------------")
    input("\nPress Enter to return to main menu...") # Pause for user to read
    return available_domains

def add_new_domain():
    """Adds a new domain configuration based on the provided template."""
    clear_screen() # Clear screen before prompt
    print("\n--- Adding a new domain (Reverse Proxy Template) ---")
    server_name = input("Enter the domain name (e.g., ai.pikhof.eu): ").strip()
    proxy_pass_url = input("Enter the internal URL where Nginx should proxy requests (e.g., localhost:3210 or 127.0.0.1:3210): ").strip()

    if not server_name or not proxy_pass_url:
        print("Domain name and proxy pass URL cannot be empty. Aborting.")
        input("\nPress Enter to return to main menu...")
        return False

    config_file_path = os.path.join(NGINX_SITES_AVAILABLE, server_name)

    if os.path.exists(config_file_path):
        print(f"Warning: Configuration file '{config_file_path}' already exists.")
        overwrite = input("Overwrite existing configuration? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Aborting domain creation.")
            input("\nPress Enter to return to main menu...")
            return False

    # Prepend http:// to proxy_pass_url if it's missing (to avoid Nginx 'invalid URL prefix' error)
    if not re.match(r'^(http|https)://', proxy_pass_url):
        proxy_pass_url = "http://" + proxy_pass_url
        print(f"Automatically adjusted proxy_pass_url to: {proxy_pass_url}")

    # Nginx config template with placeholders
    config_content = f"""server {{
    listen 80;
    listen [::]:80;
    server_name {server_name};

    location / {{
        proxy_pass {proxy_pass_url};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    error_log {NGINX_LOG_DIR}/{server_name}_error.log;
    access_log {NGINX_LOG_DIR}/{server_name}_access.log;
}}

# HTTPS block will be managed by Certbot later
# server {{
#     listen 443 ssl;
#     listen [::]:443 ssl;
#     server_name {server_name};
#     
#     location / {{
#         proxy_pass {proxy_pass_url};
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }}
# }}
"""
    print(f"Creating Nginx server block configuration for {server_name} at {config_file_path}...")
    print("This requires sudo to write the file.")
    process = subprocess.Popen(['sudo', 'tee', config_file_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate(input=config_content)

    if process.returncode != 0:
        print(f"Error writing config file: {config_file_path}")
        print(f"STDOUT:\n{stdout}")
        print(f"STDERR:\n{stderr}")
        input("\nPress Enter to return to main menu...")
        return False
    
    print(f"Configuration created: {config_file_path}")
    print("Please enable the domain and add HTTPS with Certbot separately.")
    if check_nginx_config():
        input("\nPress Enter to return to main menu...")
        return True
    input("\nPress Enter to return to main menu...")
    return False

def enable_domain():
    """Enables an existing domain configuration."""
    clear_screen() # Clear screen before prompts
    print("\n--- Enabling an existing domain ---")
    available_domains = get_available_domains() # Get domains directly, don't call list_domains to avoid double clear/pause
    if not available_domains:
        print("No domains available to enable.")
        input("\nPress Enter to return to main menu...")
        return False
    
    print("Select domain to enable:")
    for i, domain in enumerate(available_domains):
        print(f"  {i+1}. {domain}")

    try:
        choice = int(input("Enter the number of the domain to enable: ").strip())
        if 1 <= choice <= len(available_domains):
            domain_name = available_domains[choice - 1]
        else:
            print("Invalid choice.")
            input("\nPress Enter to return to main menu...")
            return False
    except ValueError:
        print("Invalid input. Please enter a number.")
        input("\nPress Enter to return to main menu...")
        return False

    config_file_source = os.path.join(NGINX_SITES_AVAILABLE, domain_name)
    config_file_dest = os.path.join(NGINX_SITES_ENABLED, domain_name)
    
    if os.path.exists(config_file_dest) or os.path.islink(config_file_dest):
        print(f"Warning: Domain '{domain_name}' appears to be already enabled or exists as a link/file in sites-enabled.")
        input("\nPress Enter to return to main menu...")
        return False

    print(f"Enabling domain '{domain_name}' by creating symlink...")
    if not run_sudo_command(['ln', '-s', config_file_source, config_file_dest]):
        print(f"Failed to create symlink for {domain_name}.")
        input("\nPress Enter to return to main menu...")
        return False

    if check_nginx_config():
        if reload_nginx():
            input("\nPress Enter to return to main menu...")
            return True
        else: # Reload failed
            input("\nPress Enter to return to main menu...")
            return False
    else: # Config test failed
        print("Nginx configuration test failed after enabling site. Reverting symlink setup.")
        run_sudo_command(['rm', config_file_dest], check=False) # Attempt to clean up
        input("\nPress Enter to return to main menu...")
        return False

def delete_domain():
    """Deletes a domain configuration (file and symlink) and reloads Nginx."""
    clear_screen() # Clear screen before prompts
    print("\n--- Deleting a domain ---")
    available_domains = get_available_domains() # Get domains directly, don't call list_domains
    if not available_domains:
        print("No domains available to delete.")
        input("\nPress Enter to return to main menu...")
        return False

    print("Select domain to delete:")
    for i, domain in enumerate(available_domains):
        print(f"  {i+1}. {domain}")

    try:
        choice = int(input("Enter the number of the domain to delete: ").strip())
        if 1 <= choice <= len(available_domains):
            domain_name = available_domains[choice - 1]
        else:
            print("Invalid choice.")
            input("\nPress Enter to return to main menu...")
            return False
    except ValueError:
        print("Invalid input. Please enter a number.")
        input("\nPress Enter to return to main menu...")
        return False

    confirm = input(f"Are you sure you want to delete '{domain_name}'? This will remove the config file and disable it. (y/n): ").strip().lower()
    if confirm != 'y':
        print("Deletion aborted.")
        input("\nPress Enter to return to main menu...")
        return False

    config_file_source = os.path.join(NGINX_SITES_AVAILABLE, domain_name)
    config_file_dest = os.path.join(NGINX_SITES_ENABLED, domain_name) # Symlink target

    # 1. Disable (remove symlink)
    if os.path.islink(config_file_dest):
        print(f"Disabling domain '{domain_name}' by removing symlink...")
        if not run_sudo_command(['rm', config_file_dest]):
            print(f"Warning: Failed to remove symlink for {domain_name}. You may need to remove it manually.")
            # Continue to delete the source file anyway
    elif os.path.exists(config_file_dest):
        print(f"Warning: A file (not symlink) exists at {config_file_dest}. Not removing automatically.")

    # 2. Delete source config file
    if os.path.exists(config_file_source):
        print(f"Deleting configuration file: {config_file_source}...")
        if not run_sudo_command(['rm', config_file_source]):
            print(f"Error: Failed to delete configuration file {config_file_source}. Aborting cleanup.")
            input("\nPress Enter to return to main menu...")
            return False
    else:
        print(f"Configuration file {config_file_source} not found. Already deleted or never existed.")

    # 3. Reload Nginx if anything was changed successfully
    if check_nginx_config():
        if reload_nginx():
            input("\nPress Enter to return to main menu...")
            return True
        else: # Reload failed
            input("\nPress Enter to return to main menu...")
            return False
    else: # Config test failed
        print("Nginx configuration test failed after deletion. Check manually!")
        input("\nPress Enter to return to main menu...")
        return False

def add_https():
    """Adds HTTPS using Certbot for Nginx."""
    clear_screen() # Clear screen before prompts
    print("\n--- Adding HTTPS (Certbot for Nginx) ---")
    print("IMPORTANT: Ensure your domain's DNS points to this server.")
    print("Also ensure ports 80 and 443 are open in your server's firewall/security rules.")

    available_domains = get_available_domains() # Get domains directly, don't call list_domains
    if not available_domains:
        print("No domain configurations found in sites-available to secure with HTTPS.")
        input("\nPress Enter to return to main menu...")
        return False
    
    print("\nAvailable domains to secure:")
    for i, domain in enumerate(available_domains):
        print(f"  {i+1}. {domain}")
    
    try:
        choice = int(input("Enter the number of the domain to secure with HTTPS: ").strip())
        if 1 <= choice <= len(available_domains):
            domain_name = available_domains[choice - 1]
        else:
            print("Invalid choice.")
            input("\nPress Enter to return to main menu...")
            return False
    except ValueError:
        print("Invalid input. Please enter a number.")
        input("\nPress Enter to return to main menu...")
        return False

    # Certbot expects the site to be enabled to find it.
    symlink_path = os.path.join(NGINX_SITES_ENABLED, domain_name)
    if not os.path.islink(symlink_path):
        print(f"Warning: Domain '{domain_name}' is not currently enabled (no symlink in sites-enabled).")
        print("Certbot requires the domain to be enabled on port 80 to issue certificates.")
        proceed = input("Do you want to enable it now before running Certbot? (y/n): ").strip().lower()
        if proceed == 'y':
            # Attempt to enable it directly, and if successful, proceed with certbot
            config_file_source = os.path.join(NGINX_SITES_AVAILABLE, domain_name)
            if not run_sudo_command(['ln', '-s', config_file_source, symlink_path]):
                print("Failed to enable domain for Certbot. Aborting HTTPS setup.")
                input("\nPress Enter to return to main menu...")
                return False
            if not check_nginx_config() or not reload_nginx():
                print("Failed to reload Nginx after enabling for Certbot. Aborting HTTPS setup.")
                input("\nPress Enter to return to main menu...")
                return False
            print(f"Domain '{domain_name}' enabled for Certbot.")
        else:
            print("Aborting HTTPS setup as domain is not enabled.")
            input("\nPress Enter to return to main menu...")
            return False

    # Construct Certbot command WITHOUT www subdomain
    certbot_command_str = f"sudo certbot --nginx -d {domain_name}"
    
    print("\n" + "="*70)
    print("THIS SCRIPT HAS PAUSED. PLEASE EXECUTE THE FOLLOWING COMMAND MANUALLY.")
    print("="*70)
    print(f"  {certbot_command_str}")
    print("\nAnswer any questions Certbot may ask (e.g., email, TOS, redirect).")
    print("Certbot will automatically reload Nginx for you if successful.")
    print("="*70 + "\n")

    input("Press Enter AFTER you have run the Certbot command manually and it has completed successfully...")
    
    print("\nCertbot usually handles Nginx reload automatically.")
    print("You can verify automatic renewal: sudo systemctl status certbot.timer")
    print("Returning to main menu.")
    input("\nPress Enter to return to main menu...") # Pause for user to read final message
    return True # We assume user ran it successfully

# --- Main Menu ---

def main_menu():
    while True:
        clear_screen() # Clear screen at the beginning of each loop iteration
        print("\n--- Nginx Domain Management Script ---")
        print("  1. List all configured domains")
        print("  2. Add a new domain (Reverse Proxy)")
        print("  3. Enable an existing domain")
        print("  4. Delete an existing domain")
        print("  5. Add HTTPS to a domain (Certbot - Manual Step)")
        print("  q. Quit")
        
        choice = input("Enter your choice: ").strip().lower()

        if choice == '1':
            list_domains()
        elif choice == '2':
            add_new_domain()
        elif choice == '3':
            enable_domain()
        elif choice == '4':
            delete_domain()
        elif choice == '5':
            add_https()
        elif choice == 'q':
            print("Exiting.")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")
            input("\nPress Enter to continue...") # Pause for invalid choice

if __name__ == "__main__":
    try:
        # Initial check for sudo privileges
        # Changed stdout=subprocess.Stdout() to stdout=subprocess.DEVNULL
        subprocess.run(['sudo', '-v'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print("Sudo privileges seem to be available.")
    except subprocess.CalledProcessError:
        print("Error: This script requires sudo. Please configure your sudo permissions.")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'sudo' command not found. Is it installed and in your PATH?")
        sys.exit(1)

    input("\nPress Enter to start Nginx Management Script...") # Initial pause before clearing
    main_menu()
