# Email Automator (emailio)

An ugly looking and lack of features Linux desktop app built with Python and CustomTkinter for sending mass emails via Resend API or SMTP (Gmail, iCloud, Hotmail).

## Setup & Running

```fish
# Clone repository
git clone [https://github.com/YOUR_USERNAME/emailio.git](https://github.com/YOUR_USERNAME/emailio.git)
cd emailio

# Install Arch system dependency for Tkinter
sudo pacman -S tk

# Virtual environment setup
python -m venv venv
source venv/bin/activate.fish

# Dependencies & execution
pip install -r requirements.txt
python emailio.py
```
