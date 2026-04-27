# Raspberry Pi Setup

This guide puts Magic Wall on a Raspberry Pi with a 7-inch touchscreen and starts it as a fullscreen kiosk.

## 1. Prepare the Pi

Use Raspberry Pi OS with desktop enabled. Connect the touchscreen, boot the Pi, and make sure Chromium is installed:

```sh
sudo apt update
sudo apt install -y git python3-venv chromium-browser
```

Some newer images package Chromium as `chromium` instead of `chromium-browser`; the installer will try to detect either.

## 2. Install The Project

From the Pi:

```sh
git clone https://github.com/diptobiswas/magic-wall.git ~/magic-wall
cd ~/magic-wall
```

## 3. Add Your OpenAI Key

Magic Wall stores the key locally on the Pi:

```sh
mkdir -p ~/.config/magic-wall
nano ~/.config/magic-wall/config.toml
```

Paste the default config from the README and set `openai.api_key`, or run `./install.sh` first and edit the generated config afterward.

## 4. Install and Start

On the Pi:

```sh
cd ~/magic-wall
./install.sh
```

The installer creates a virtual environment, installs the app, writes user-level systemd services, starts the local server, and launches Chromium in kiosk mode at:

```text
http://127.0.0.1:8765
```

## 5. Useful Commands on the Pi

Check app status:

```sh
~/magic-wall/.venv/bin/magic-wall status
```

Force a new wallpaper:

```sh
~/magic-wall/.venv/bin/magic-wall generate-now
```

Restart the services:

```sh
systemctl --user restart magic-wall.service
systemctl --user restart magic-wall-kiosk.service
```

View logs:

```sh
journalctl --user -u magic-wall.service -f
```

Stop the kiosk:

```sh
systemctl --user stop magic-wall-kiosk.service
```

## 6. Keep It Running After Reboot

If the app does not auto-start after reboot, enable lingering for the Pi user:

```sh
sudo loginctl enable-linger "$USER"
systemctl --user enable magic-wall.service
systemctl --user enable magic-wall-kiosk.service
```

Then reboot:

```sh
sudo reboot
```

## 7. Touchscreen Polish

Use Raspberry Pi display settings to set the touchscreen orientation and disable sleep. If the screen blanks, open Raspberry Pi Configuration and disable screen blanking, or install a lightweight kiosk helper package such as `unclutter` later.
