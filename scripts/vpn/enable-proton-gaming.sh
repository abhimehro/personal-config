#!/bin/bash

# ======================================================
# enable-proton-gaming.sh
# ======================================================
# This script switches from WARP to ProtonVPN for gaming
# Ensures clean transition without connection locking
# ======================================================

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Configuration
WARP_DAEMON_PLIST="/Library/LaunchDaemons/com.cloudflare.1dot1dot1dot1.macos.warp.daemon.plist"

# Error handling
handle_error() {
    local exit_code=$1
    local error_message=$2
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}ERROR: $error_message${NC}"
        exit $exit_code
    fi
}

# Stop WARP completely
stop_warp() {
    echo "Stopping WARP services..."
    warp-cli --accept-tos disconnect 2>/dev/null
    sudo launchctl unload "$WARP_DAEMON_PLIST" 2>/dev/null
    pkill -f "CloudflareWARP" 2>/dev/null
    sleep 2
    
    # Force kill if necessary
    if pgrep -f "CloudflareWARP" > /dev/null; then
        pkill -9 -f "CloudflareWARP" 2>/dev/null
        sleep 1
    fi
}

# Reset DNS to automatic
reset_dns() {
    echo "Resetting DNS to automatic..."
    while IFS= read -r service; do
        if [[ "$service" != *"*"* ]] && [[ -n "$service" ]]; then
            networksetup -setdnsservers "$service" "Empty"
            echo -e "${GREEN}Reset DNS for: $service${NC}"
        fi
    done < <(networksetup -listallnetworkservices)
}

# Main execution
echo -e "${BOLD}${BLUE}=== Switching to ProtonVPN Gaming Configuration ===${NC}"

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Requesting root privileges...${NC}"
    exec sudo "$0" "$@"
    exit $?
fi

# 1. Stop WARP
echo -e "\n${BOLD}Step 1:${NC} Stopping WARP services..."
stop_warp

# 2. Reset DNS to automatic
echo -e "\n${BOLD}Step 2:${NC} Resetting DNS configuration..."
reset_dns

# 3. Launch ProtonVPN
echo -e "\n${BOLD}Step 3:${NC} Launching ProtonVPN..."
open -a "ProtonVPN"

echo -e "\n${BOLD}${GREEN}Ready for gaming!${NC}"
echo -e "ProtonVPN has been launched. Please select your preferred gaming server."
echo -e "Use 'vpn-normal' to switch back to WARP+Control D when done."

#!/bin/bash

# ======================================================
# enable-proton-gaming.sh
# ======================================================
# This script configures the system for Proton VPN gaming
# It will:
# 1. Disconnect WARP if connected
# 2. Reset DNS configuration to default/automatic
# 3. Verify that Control D DNS is no longer used
# 4. Start Proton VPN if installed
# ======================================================

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Configuration values
PROTON_CLI="/Applications/ProtonVPN.app/Contents/MacOS/ProtonVPN"
PROTON_APP="/Applications/ProtonVPN.app"
MAX_RETRIES=3
CONNECTION_TIMEOUT=30
KEYCHAIN_PATH="$HOME/Library/Keychains/login.keychain-db"
# Preferred server configurations - modify these to your preferred servers
PREFERRED_SERVERS=(
  "US-TX#1 (Dallas)"
  "US-GA#1 (Atlanta)"
  "US-TX#2 (Dallas)"
  "US-GA#2 (Atlanta)"
  "US-TX#3 (Dallas)"
  "US-GA#3 (Atlanta)"
  "US#1 (Fastest US Server)"
  "Fastest Server"
)

echo -e "${BOLD}${BLUE}=== Proton VPN Gaming Configuration ===${NC}"

# Check if script is run with sufficient privileges
if [ "$EUID" -ne 0 ]; then
  echo -e "${YELLOW}This script requires root privileges to modify network settings.${NC}"
  echo -e "Running with sudo..."
  sudo "$0" "$@"
  exit $?
fi

# Function to handle errors
handle_error() {
  local exit_code=$1
  local error_message=$2
  local should_exit=${3:-true}  # Optional third parameter to control whether to exit
  
  if [ $exit_code -ne 0 ]; then
    echo -e "${RED}ERROR: $error_message (exit code: $exit_code)${NC}"
    if [ "$should_exit" = true ]; then
      echo -e "${YELLOW}Configuration failed. Try running the script again or check system logs.${NC}"
      exit $exit_code
    else
      echo -e "${YELLOW}Continuing despite error...${NC}"
      return 1
    fi
  fi
  return 0
}

# Function to manage keychain access
manage_keychain() {
  local action=$1
  local retries=0
  
  case "$action" in
    unlock)
      echo "Unlocking keychain for VPN operations..."
      while [ $retries -lt $MAX_RETRIES ]; do
        security unlock-keychain "$KEYCHAIN_PATH" 2>/dev/null
        if [ $? -eq 0 ]; then
          echo -e "${GREEN}Keychain unlocked successfully.${NC}"
          return 0
        else
          retries=$((retries+1))
          echo -e "${YELLOW}Keychain unlock failed, attempt $retries of $MAX_RETRIES${NC}"
          if [ $retries -lt $MAX_RETRIES ]; then
            echo "Please enter your keychain password when prompted..."
            security unlock-keychain -u "$KEYCHAIN_PATH"
            if [ $? -eq 0 ]; then
              echo -e "${GREEN}Keychain unlocked successfully on interactive attempt.${NC}"
              return 0
            fi
          fi
          sleep 1
        fi
      done
      echo -e "${RED}Failed to unlock keychain after $MAX_RETRIES attempts.${NC}"
      echo -e "${YELLOW}Will attempt to proceed, but VPN operations may fail.${NC}"
      return 1
      ;;
      
    reset)
      echo "Resetting keychain state..."
      security lock-keychain "$KEYCHAIN_PATH" 2>/dev/null
      sleep 1
      security unlock-keychain "$KEYCHAIN_PATH" 2>/dev/null
      if [ $? -eq 0 ]; then
        echo -e "${GREEN}Keychain reset successfully.${NC}"
        return 0
      else
        echo -e "${YELLOW}Keychain reset failed, will prompt for manual unlock...${NC}"
        security unlock-keychain -u "$KEYCHAIN_PATH"
        return $?
      fi
      ;;
      
    lock)
      echo "Locking keychain..."
      security lock-keychain "$KEYCHAIN_PATH" 2>/dev/null
      echo -e "${GREEN}Keychain locked.${NC}"
      return 0
      ;;
  esac
}

# Function to reset DNS with retry logic
reset_dns_for_service() {
  local service=$1
  local retries=0
  
  echo -e "Resetting DNS for '$service' to automatic (empty)..."
  
  while [ $retries -lt $MAX_RETRIES ]; do
    # Verify the service exists and is active
    if ! networksetup -getinfo "$service" &>/dev/null; then
      echo -e "${YELLOW}Warning: '$service' does not appear to be a valid network service.${NC}"
      return 1
    fi
    
    # Reset DNS servers to empty/automatic
    networksetup -setdnsservers "$service" "Empty"
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}Successfully reset DNS for '$service'.${NC}"
      
      # Verify the change took effect by checking current DNS settings
      local dns_check=$(networksetup -getdnsservers "$service")
      if [[ "$dns_check" == *"There aren't any DNS Servers"* ]] || [[ "$dns_check" == *"empty"* ]]; then
        echo -e "${GREEN}Verified DNS settings are reset to automatic.${NC}"
        return 0
      else
        echo -e "${YELLOW}DNS settings don't appear to be empty, retrying...${NC}"
      fi
    else
      echo -e "${YELLOW}Failed to reset DNS for '$service', attempt $((retries+1)) of $MAX_RETRIES.${NC}"
    fi
    
    retries=$((retries+1))
    [ $retries -lt $MAX_RETRIES ] && sleep 2
  done
  
  echo -e "${RED}Failed to reset DNS for '$service' after $MAX_RETRIES attempts.${NC}"
  return 1
}

# Function to manage Cloudflare WARP settings
manage_warp() {
  local action=$1
  local retries=0
  
  # Check if WARP CLI is available
  if ! command -v warp-cli &> /dev/null; then
    echo -e "${YELLOW}WARP CLI not found. WARP management will be skipped.${NC}"
    return 0
  fi
  
  case "$action" in
    disable_autoconnect)
      echo "Disabling WARP auto-connect feature..."
      warp-cli --accept-tos auto-connect off
      if [ $? -eq 0 ]; then
        echo -e "${GREEN}WARP auto-connect disabled.${NC}"
        return 0
      else
        echo -e "${YELLOW}Failed to disable WARP auto-connect.${NC}"
        return 1
      fi
      ;;
      
    disconnect)
      echo "Disconnecting WARP..."
      while [ $retries -lt $MAX_RETRIES ]; do
        warp-cli --accept-tos disconnect
        sleep 2
        
        # Verify disconnection
        local warp_status=$(warp-cli status 2>/dev/null | grep "Status update:" | awk '{print $3}')
        if [ "$warp_status" = "Disconnected" ]; then
          echo -e "${GREEN}WARP successfully disconnected.${NC}"
          return 0
        else
          retries=$((retries+1))
          echo -e "${YELLOW}WARP still appears to be connected or in transition, attempt $retries of $MAX_RETRIES...${NC}"
          sleep 2
        fi
      done
      
      echo -e "${RED}Failed to disconnect WARP after $MAX_RETRIES attempts.${NC}"
      echo -e "${YELLOW}Attempting to force disconnect and disable...${NC}"
      
      # Force kill WARP daemon process as last resort
      pkill -9 "warp-svc" 2>/dev/null
      sleep 2
      
      return 1
      ;;
      
    monitor_start)
      echo "Starting WARP monitoring to prevent reconnection..."
      # Start background process to monitor and disconnect WARP if it reconnects
      # Uses a temporary file to coordinate with the monitor_stop function
      WARP_MONITOR_PID_FILE=$(mktemp -t warp_monitor.XXXXXX)
      
      (
        while [ -f "$WARP_MONITOR_PID_FILE" ]; do
          warp_status=$(warp-cli status 2>/dev/null | grep "Status update:" | awk '{print $3}')
          if [ "$warp_status" = "Connected" ]; then
            echo -e "$(date): WARP reconnection detected. Disconnecting again..."
            warp-cli --accept-tos disconnect
            sleep 1
          fi
          sleep 5
        done
      ) &
      
      echo $! > "$WARP_MONITOR_PID_FILE"
      echo -e "${GREEN}WARP monitoring started (PID: $(cat "$WARP_MONITOR_PID_FILE")).${NC}"
      return 0
      ;;
      
    monitor_stop)
      echo "Stopping WARP monitoring..."
      if [ -f "$WARP_MONITOR_PID_FILE" ]; then
        local monitor_pid=$(cat "$WARP_MONITOR_PID_FILE")
        kill "$monitor_pid" 2>/dev/null
        rm -f "$WARP_MONITOR_PID_FILE"
        echo -e "${GREEN}WARP monitoring stopped.${NC}"
      else
        echo -e "${YELLOW}No active WARP monitoring found.${NC}"
      fi
      return 0
      ;;
  esac
}

# Function to check VPN connection status with timeout
check_vpn_connection() {
  local timeout=$1
  local end_time=$(($(date +%s) + timeout))
  
  echo "Verifying VPN connection (timeout: ${timeout}s)..."
  
  while [ $(date +%s) -lt $end_time ]; do
    # Check if ProtonVPN process is running
    if ! pgrep -x "ProtonVPN" > /dev/null; then
      echo -e "${YELLOW}Warning: ProtonVPN process not detected.${NC}"
      return 1
    fi
    
    # Check if we have a different IP than before connecting
    local current_ip=$(curl -s --max-time 5 https://api.ipify.org)
    if [ -n "$current_ip" ] && [ "$current_ip" != "$ORIGINAL_IP" ]; then
      echo -e "${GREEN}VPN connection verified: IP address has changed.${NC}"
      echo -e "Current IP: $current_ip"
      return 0
    fi
    
    echo "Waiting for VPN connection to establish... ($(($end_time - $(date +%s)))s remaining)"
    sleep 2
  done
  
  echo -e "${RED}Timed out waiting for VPN connection verification.${NC}"
  return 1
}
# Step 1: Handle WARP connection and prevent auto-reconnect
echo -e "\n${BOLD}Step 1:${NC} Disconnecting WARP if connected..."
WARP_STATUS=$(warp-cli status 2>/dev/null | grep "Status update:" | awk '{print $3}')

if command -v warp-cli &> /dev/null; then
  echo "WARP CLI detected. Managing WARP connection..."
  
  # First, disable auto-connect to prevent automatic reconnection
  manage_warp disable_autoconnect
  
  if [ "$WARP_STATUS" = "Connected" ]; then
    echo "WARP is connected. Disconnecting..."
    manage_warp disconnect
    
    # Double-check the disconnection was successful
    WARP_STATUS=$(warp-cli status 2>/dev/null | grep "Status update:" | awk '{print $3}')
    if [ "$WARP_STATUS" = "Connected" ]; then
      echo -e "${YELLOW}Warning: WARP still appears to be connected despite disconnect attempts.${NC}"
      echo -e "${YELLOW}This may cause issues with ProtonVPN connection.${NC}"
      
      echo -e "Would you like to forcibly terminate WARP processes? [y/N]: "
      read -r force_kill
      if [[ "$force_kill" =~ ^[Yy]$ ]]; then
        echo "Forcibly terminating WARP processes..."
        pkill -9 "warp-svc" 2>/dev/null
        pkill -9 "warp-cli" 2>/dev/null
        sleep 3
        echo -e "${GREEN}WARP processes terminated.${NC}"
      fi
    else
      echo -e "${GREEN}Successfully verified WARP disconnection.${NC}"
    fi
  else
    echo "WARP is not connected. Checking for automatic connection settings..."
    # Still disable auto-connect even if not currently connected
    warp-cli --accept-tos auto-connect off
    echo -e "${GREEN}WARP auto-connect disabled.${NC}"
  fi
  
  # Start monitoring to prevent WARP from reconnecting during ProtonVPN operations
  manage_warp monitor_start
else
  echo "WARP CLI not detected. Skipping WARP management..."
fi

# Step 2: Reset DNS configuration to automatic/default
echo -e "\n${BOLD}Step 2:${NC} Resetting DNS configuration to automatic/default..."

# Store original IP for connection verification later
echo "Checking current IP address before VPN connection..."
ORIGINAL_IP=$(curl -s --max-time 5 https://api.ipify.org)
if [ -n "$ORIGINAL_IP" ]; then
  echo "Current IP address: $ORIGINAL_IP"
else
  echo -e "${YELLOW}Warning: Could not determine current IP address.${NC}"
  ORIGINAL_IP="unknown"
fi

# Get active network services
echo "Retrieving active network services..."

# Save current IFS
OLD_IFS="$IFS"

# Set IFS to newline to handle service names with spaces
IFS=$'\n'

# Get network services list
SERVICES=($(networksetup -listallnetworkservices | grep -v "An asterisk"))

# Restore IFS
IFS="$OLD_IFS"

# Check if we found any services
if [ ${#SERVICES[@]} -eq 0 ]; then
  echo -e "${RED}ERROR: No active network services found.${NC}"
  echo "Please check your network configuration and try again."
  exit 1
fi

echo "Active network services found:"
for SERVICE in "${SERVICES[@]}"; do
  echo " - '$SERVICE'"
done

# Configure DNS for each service
DNS_CONFIG_SUCCESS=0

for SERVICE in "${SERVICES[@]}"; do
  echo -e "\nProcessing network service: '$SERVICE'"
  
  # Try to reset DNS with our improved function that includes verification
  if reset_dns_for_service "$SERVICE"; then
    DNS_CONFIG_SUCCESS=1
  fi
  
  # As a fallback, try alternative method if primary method failed
  if [ $DNS_CONFIG_SUCCESS -eq 0 ]; then
    echo -e "${YELLOW}Trying alternative DNS reset method for '$SERVICE'...${NC}"
    
    # Alternative method: explicitly set to ISP provided DNS then clear
    networksetup -setdnsservers "$SERVICE" "Empty"
    sleep 1
    networksetup -setdnsservers "$SERVICE" "Empty"
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}Alternative DNS reset method successful for '$SERVICE'.${NC}"
      DNS_CONFIG_SUCCESS=1
    fi
  fi
done

if [ $DNS_CONFIG_SUCCESS -eq 0 ]; then
  echo -e "${RED}ERROR: Failed to reset DNS on any network service.${NC}"
  echo "Please check network configuration and permissions."
  exit 1
else
  echo -e "${GREEN}Successfully reset DNS on at least one network service.${NC}"
fi

# Flush DNS cache with improved error handling
echo "Flushing DNS cache..."
dscacheutil -flushcache
handle_error $? "Failed to flush DNS cache with dscacheutil" false

killall -HUP mDNSResponder
handle_error $? "Failed to restart mDNSResponder" false

# Additional flush method as backup
echo "Performing additional DNS cache flush methods..."
sudo killall -HUP mDNSResponder
sudo dscacheutil -flushcache

echo -e "${GREEN}DNS cache flush procedures completed.${NC}"

# Step 3: Verify that Control D DNS is no longer used
echo -e "\n${BOLD}Step 3:${NC} Verifying DNS configuration changes..."
sleep 2 # Wait for DNS changes to take effect

DNS_SERVERS=$(scutil --dns | grep "nameserver\[[0-9]*\]" | head -2)
if echo "$DNS_SERVERS" | grep -q "76.76.2.22\|76.76.2.23"; then
  echo -e "${YELLOW}Warning: Control D DNS still appears to be in use. This may be a caching issue.${NC}"
  echo "Current DNS servers:"
  echo "$DNS_SERVERS"
  echo "Waiting additional time for DNS changes to propagate..."
  sleep 5
else
  echo -e "${GREEN}DNS configuration successfully changed away from Control D.${NC}"
  echo "Current DNS servers:"
  echo "$DNS_SERVERS"
fi

# Function to display server selection menu
select_proton_server() {
  echo -e "\n${BOLD}${BLUE}Select Proton VPN Server${NC}"
  echo -e "${YELLOW}Lower numbers typically provide better latency for gaming.${NC}"
  echo ""
  
  for i in "${!PREFERRED_SERVERS[@]}"; do
    echo -e "  ${BOLD}$((i+1))${NC}) ${PREFERRED_SERVERS[$i]}"
  done
  
  echo -e "  ${BOLD}c${NC}) Custom/Manual Selection"
  echo ""
  echo -e "${BOLD}Enter your choice [1-${#PREFERRED_SERVERS[@]}/c]:${NC} "
  read -r choice
  
  # Process choice
  if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#PREFERRED_SERVERS[@]}" ]; then
    # Valid numeric choice
    SELECTED_SERVER="${PREFERRED_SERVERS[$((choice-1))]}"
    echo -e "${GREEN}Selected server: $SELECTED_SERVER${NC}"
    return 0
  elif [[ "$choice" == "c" ]]; then
    # Custom selection - will launch the GUI for manual selection
    SELECTED_SERVER="custom"
    echo -e "${YELLOW}Custom selection: You will need to select a server manually.${NC}"
    return 0
  else
    # Invalid choice
    echo -e "${RED}Invalid selection. Please try again.${NC}"
    select_proton_server
    return $?
  fi
}

# Step 4: Check for Proton VPN and start it if available
echo -e "\n${BOLD}Step 4:${NC} Setting up Proton VPN for gaming..."

if [ -e "$PROTON_APP" ]; then
  echo "Proton VPN detected. Preparing to connect..."
  
  # Check if Proton VPN is already running
  if pgrep -x "ProtonVPN" > /dev/null; then
    echo "Proton VPN is already running. Disconnecting first..."
    if [ -x "$PROTON_CLI" ]; then
      # Unlock keychain before VPN operations
      manage_keychain unlock
      
      # Try disconnection with retry logic
      local disconnect_attempts=0
      while [ $disconnect_attempts -lt $MAX_RETRIES ]; do
        echo "Disconnect attempt $((disconnect_attempts+1)) of $MAX_RETRIES..."
        
        # Use timeout command to prevent hanging
        timeout 30 "$PROTON_CLI" disconnect
        
        if [ $? -eq 0 ]; then
          echo -e "${GREEN}Successfully disconnected from ProtonVPN.${NC}"
          break
        else
          disconnect_attempts=$((disconnect_attempts+1))
          
          if [ $disconnect_attempts -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}Disconnect failed, retrying after keychain reset...${NC}"
            manage_keychain reset
            sleep 2
          else
            echo -e "${RED}Failed to disconnect after $MAX_RETRIES attempts.${NC}"
            echo -e "${YELLOW}Will try to force-quit ProtonVPN and restart it...${NC}"
            
            # Force quit and restart if all else fails
            killall -9 ProtonVPN 2>/dev/null
            sleep 3
          fi
        fi
      done
    else
      # Fallback to GUI disconnect
      echo "Launching ProtonVPN for manual disconnection..."
      open -a "ProtonVPN"
      echo -e "${YELLOW}Please disconnect from any active VPN connections if needed.${NC}"
      echo -e "Press Enter when ready to continue..."
      read -r
    fi
    sleep 2
  fi

  # Server selection
  select_proton_server

  # Connect to Proton VPN
  echo -e "\nConnecting to Proton VPN..."
  
  if [ "$SELECTED_SERVER" == "custom" ] || [ ! -x "$PROTON_CLI" ]; then
    # Launch GUI for manual selection
    echo -e "${YELLOW}Launching Proton VPN app for manual server selection.${NC}"
    echo -e "${YELLOW}Launching ProtonVPN app for manual server selection.${NC}"
    echo -e "${YELLOW}Please select a server close to you (Dallas or Atlanta recommended).${NC}"
    open -a "ProtonVPN"
    echo -e "\n${BOLD}${YELLOW}Important:${NC} Select a nearby server with low latency for best gaming performance."
    echo -e "Recommended servers are in Dallas or Atlanta for US users."
    echo -e "\nPress Enter when you've connected to your preferred server..."
    read -r
    
    # Check if connection is established
    if pgrep -x "ProtonVPN" > /dev/null; then
      echo -e "${GREEN}Proton VPN is running. Assuming connection is established.${NC}"
      # We can't programmatically check which server was selected when using the GUI
    else
      echo -e "${RED}Proton VPN process not detected. Connection may have failed.${NC}"
    fi
  else
    # Try CLI connection with selected server
    # Note: The exact command syntax might vary depending on ProtonVPN CLI version
    # This is a placeholder - modify based on actual CLI syntax
    echo "Attempting to connect to $SELECTED_SERVER via CLI..."
    
    # Extract server code if present (format may vary)
    SERVER_CODE=$(echo "$SELECTED_SERVER" | grep -o 'US-[A-Z][A-Z]#[0-9]' || echo "$SELECTED_SERVER")
    
    # Ensure keychain is unlocked before VPN connection attempt
    manage_keychain unlock
    
    # Try to connect using CLI with retry logic
    local connect_attempts=0
    CONNECT_STATUS=1
    
    while [ $connect_attempts -lt $MAX_RETRIES ] && [ $CONNECT_STATUS -ne 0 ]; do
      echo "Connection attempt $((connect_attempts+1)) of $MAX_RETRIES to $SERVER_CODE..."
      
      # Use timeout to prevent hanging on the connection attempt
      timeout $CONNECTION_TIMEOUT "$PROTON_CLI" connect "$SERVER_CODE"
      CONNECT_STATUS=$?
      
      if [ $CONNECT_STATUS -eq 0 ]; then
        echo -e "${GREEN}Initial connection command successful.${NC}"
        # Additional verification that connection is actually established
        if check_vpn_connection 30; then
          echo -e "${GREEN}VPN connection verified successfully.${NC}"
          break
        else
          echo -e "${YELLOW}Connection command succeeded but VPN verification failed.${NC}"
          CONNECT_STATUS=1
        fi
      fi
      
      connect_attempts=$((connect_attempts+1))
      
      if [ $connect_attempts -lt $MAX_RETRIES ]; then
        echo -e "${YELLOW}Connection attempt failed, resetting keychain and retrying...${NC}"
        manage_keychain reset
        sleep 3
      fi
    done
    
    if [ $CONNECT_STATUS -ne 0 ]; then
      echo -e "${YELLOW}Automated connection to $SELECTED_SERVER failed.${NC}"
      echo -e "${YELLOW}Falling back to manual connection.${NC}"
      open -a "ProtonVPN"
      echo -e "${YELLOW}Please select a server close to you (Dallas or Atlanta recommended).${NC}"
      echo -e "Press Enter when you've connected to your preferred server..."
      read -r
    else
      echo -e "${GREEN}Successfully connected to $SELECTED_SERVER.${NC}"
    fi
  fi
else
  echo -e "${YELLOW}ProtonVPN not found at expected location: $PROTON_APP${NC}"
  echo -e "${YELLOW}Please install ProtonVPN or connect manually if already installed in a non-standard location.${NC}"
  echo -e "You can download ProtonVPN from: https://protonvpn.com/download"
fi

# Step 5: Verify network configuration
echo -e "\n${BOLD}Step 5:${NC} Verifying network configuration..."
sleep 5 # Wait for VPN connection to establish

# Check overall connectivity
echo "Checking internet connectivity..."
curl -s https://www.google.com > /dev/null
if [ $? -eq 0 ]; then
  echo -e "${GREEN}Internet connectivity is working.${NC}"
else
  echo -e "${YELLOW}Warning: Internet connectivity check failed. This may be temporary.${NC}"
fi

# Check if WARP is definitely disconnected
WARP_STATUS=$(warp-cli status 2>/dev/null | grep "Status update:" | awk '{print $3}')
if [ "$WARP_STATUS" = "Disconnected" ]; then
  echo -e "${GREEN}WARP is confirmed disconnected.${NC}"
else
  echo -e "${YELLOW}Warning: WARP status is $WARP_STATUS. It should be 'Disconnected'.${NC}"
fi

# Check current IP and try to determine server location
echo "Checking current IP address and server location..."
CURRENT_IP=$(curl -s https://api.ipify.org)
echo -e "Current public IP: ${BLUE}$CURRENT_IP${NC}"

# Try to get geolocation info
if command -v curl &> /dev/null; then
  echo "Checking server location..."
  SERVER_INFO=$(curl -s "https://ipinfo.io/$CURRENT_IP/json" | grep -E 'city|region|country' | tr -d '"{},')
  if [ -n "$SERVER_INFO" ]; then
    echo -e "Server location: ${BLUE}"
    echo "$SERVER_INFO" | sed 's/^/  /'
    echo -e "${NC}"
  fi
fi

# Check if we're likely connected to a server in Dallas or Atlanta
if echo "$SERVER_INFO" | grep -q -i 'Dallas\|Atlanta'; then
  echo -e "${GREEN}✓ Connected to a recommended low-latency location.${NC}"
elif echo "$SERVER_INFO" | grep -q -i 'TX\|GA\|Texas\|Georgia'; then
  echo -e "${GREEN}✓ Connected to a server in a recommended state (TX or GA).${NC}"
else
  echo -e "${YELLOW}Note: You don't appear to be connected to a Dallas or Atlanta server.${NC}"
  echo -e "${YELLOW}You may want to manually select a closer server for better gaming performance.${NC}"
fi

echo -e "\n${BOLD}${GREEN}======= Configuration Summary =======${NC}"
echo -e "WARP Status: $WARP_STATUS"
echo -e "DNS Configuration: Automatic (system/ISP default)"
echo -e "Public IP: $CURRENT_IP"
if [ -n "$SERVER_INFO" ]; then
  echo -e "Server Location: $(echo "$SERVER_INFO" | grep city | sed 's/city://' | tr -d '[:space:]'), $(echo "$SERVER_INFO" | grep region | sed 's/region://' | tr -d '[:space:]')"
fi
echo -e "${BOLD}${GREEN}=====================================${NC}"

# Stop WARP monitoring now that we're done
manage_warp monitor_stop

echo -e "\n${BOLD}${GREEN}System configured for Proton VPN gaming!${NC}"
echo -e "If ProtonVPN did not connect automatically, please open the app and connect manually."
echo -e "Recommended: Connect to a server with low ping for optimal gaming performance."
echo -e "To switch back to WARP+/Control D configuration, run the restore-warp-controld.sh script."

